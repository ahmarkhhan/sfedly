"""B1: acquisition gates and connected, immutable study cohorts."""

from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .batch import InputFailure, _input
from .contracts import DocumentRole, StrictModel, identity
from .evaluation_common import checked, seal, timestamp, unique

COHORT_SCHEMA = "skony.study-cohort.v1"


class IntakeReview(StrictModel):
    reviewer_id: str = Field(min_length=1)
    kind: Literal["human", "automated", "synthetic"]
    locked_at: str
    artifact_id: str
    body_id: str
    affair_id: str
    language: str
    role: DocumentRole
    jurisdiction_level: Literal["municipal", "cantonal", "federal", "unknown"] = "unknown"
    checked_pages: list[int] = Field(min_length=1)
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid(self):
        timestamp(self.locked_at)
        if not self.reviewer_id.strip() or not self.note.strip():
            raise ValueError("Intake review needs a named reviewer and basis")
        if self.checked_pages != sorted(set(self.checked_pages)) or self.checked_pages[0] < 1:
            raise ValueError("Intake checked pages must be positive and unique")
        return self


class StudyUnit(StrictModel):
    unit_id: str
    source_id: str
    artifact_id: str | None
    scope_id: str
    provider: str = "openparldata"
    body_id: str
    body_key: str
    level: Literal["municipal", "cantonal", "federal", "unknown"] = "unknown"
    affair_id: str | None
    language_hint: str = "unknown"
    role_hint: str = "unknown"
    source_status: Literal["ready", "failed"]
    failure_reason: str | None = None
    available_pages: list[int]
    hard_case: bool = False
    split: Literal["unassigned", "development", "test"] = "unassigned"
    review: IntakeReview | None = None

    @model_validator(mode="after")
    def valid(self):
        if self.source_status == "ready" and (not self.artifact_id or not self.available_pages or self.failure_reason):
            raise ValueError("Ready units require a pinned artifact and pages")
        if self.source_status == "failed" and not self.failure_reason:
            raise ValueError("Failed units must retain their reason")
        expected = (self.artifact_id or "unavailable:" + self.source_id) + ":" + self.scope_id
        if self.unit_id != expected:
            raise ValueError("Unit identity must identify its artifact and explicit scope")
        if self.review:
            r = self.review
            if (self.source_status != "ready" or r.artifact_id != self.artifact_id or r.body_id != self.body_id
                    or r.affair_id != self.affair_id or r.jurisdiction_level != self.level
                    or set(r.checked_pages) - set(self.available_pages)):
                raise ValueError("Intake review does not match this unit's source and membership")
        return self

    @property
    def affair_key(self):
        return identity([self.provider, self.body_id, self.affair_id]) if self.affair_id else None

    @property
    def verified(self):
        return bool(self.review and self.review.kind == "human" and self.review.language not in {"", "unknown", "und"}
                    and self.review.role != "unknown" and self.affair_id)


class StudyPolicy(StrictModel):
    mode: Literal["large", "small", "bounded"] = "small"
    minimum_documents: int = Field(default=12, ge=1)
    maximum_documents: int | None = Field(default=16, ge=1)
    minimum_affairs: int = Field(default=1, ge=1)
    minimum_bodies: int = Field(default=3, ge=1)
    minimum_levels: int = Field(default=2, ge=1)
    minimum_pairs: int = Field(default=0, ge=0)
    required_languages: list[str] = Field(default_factory=lambda: ["de", "fr"], min_length=1)
    claims: list[str] = Field(default_factory=lambda: ["sampled_body_field_agreement"])

    @model_validator(mode="after")
    def valid(self):
        unique(self.required_languages, "required language")
        if self.maximum_documents is not None and self.maximum_documents < self.minimum_documents:
            raise ValueError("Maximum sample size is below its minimum")
        if self.mode == "large" and (self.minimum_documents < 48 or self.minimum_affairs < 24
                or self.minimum_bodies < 6 or self.minimum_pairs < 12):
            raise ValueError("The large study requires 48 documents, 24 affairs, six bodies and 12 verified pairs")
        if self.mode == "small" and (self.minimum_documents < 12 or self.maximum_documents is None
                or self.maximum_documents > 16 or self.minimum_bodies < 3 or self.minimum_levels < 2):
            raise ValueError("The planned smaller study requires 12–16 documents, three bodies and two levels")
        if any(c in self.claims for c in ("nationwide_accuracy", "unseen_body_transfer", "all_swiss_languages")):
            raise ValueError("These claims need a separate study design")
        return self


class SplitLink(StrictModel):
    left: str
    right: str
    kind: Literal["translation", "confirmed_duplicate"]
    reviewer: str = Field(min_length=1)
    reference: str = Field(min_length=1)


def connected_groups(units: list[StudyUnit], links: list[SplitLink]):
    unique([u.unit_id for u in units], "study unit")
    parent = {u.unit_id: u.unit_id for u in units}

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)

    seen = {}
    for unit in units:
        # Even unverified same-affair hints conservatively prevent split leakage.
        for key in [("artifact", unit.artifact_id), ("affair", unit.affair_key)]:
            if key[1] is not None:
                if key in seen:
                    union(unit.unit_id, seen[key])
                seen[key] = unit.unit_id
    for link in links:
        if link.left not in parent or link.right not in parent or link.left == link.right:
            raise ValueError("Split link references an unknown or identical unit")
        union(link.left, link.right)
    groups = defaultdict(list)
    for uid in parent:
        groups[root(uid)].append(uid)
    return {identity(sorted(ids)): sorted(ids) for ids in groups.values()}


def acquisition_report(units: list[StudyUnit], policy: StudyPolicy):
    eligible = [u for u in units if u.verified]
    documents = len({u.artifact_id for u in eligible})
    affairs = {u.affair_key for u in eligible}
    by_affair = defaultdict(set)
    for u in eligible:
        by_affair[u.affair_key].add(u.review.role)
    pairs = sum("submission" in roles and "executive_response" in roles for roles in by_affair.values())
    bodies = {u.body_id for u in eligible}
    levels = {u.level for u in eligible} - {"unknown"}
    languages = Counter(u.review.language for u in eligible)
    reasons = []
    for name, got, needed in [("documents", documents, policy.minimum_documents),
                              ("affairs", len(affairs), policy.minimum_affairs),
                              ("bodies", len(bodies), policy.minimum_bodies),
                              ("levels", len(levels), policy.minimum_levels), ("pairs", pairs, policy.minimum_pairs)]:
        if got < needed:
            reasons.append(f"insufficient_verified_{name}:{got}/{needed}")
    if policy.maximum_documents is not None and documents > policy.maximum_documents:
        reasons.append("sample_exceeds_predeclared_maximum")
    for language in policy.required_languages:
        if not languages[language]:
            reasons.append("missing_verified_language:" + language)
    return {"passed": not reasons, "reasons": reasons, "selected_units": len(units),
            "source_failures": sum(u.source_status == "failed" for u in units),
            "unverified_units": sum(u.source_status == "ready" and not u.verified for u in units),
            "verified_documents": documents, "verified_affairs": len(affairs), "verified_pairs": pairs,
            "verified_bodies": sorted(bodies), "verified_levels": sorted(levels),
            "verified_languages": dict(sorted(languages.items())),
            "achieved_matrix": [{"body_id": body, "language": lang, "role": role, "units": count}
                for (body, lang, role), count in sorted(Counter(
                    (u.body_id, u.review.language, u.review.role) for u in eligible).items())],
            "allowed_claims": policy.claims if not reasons else [],
            "relation_claims_require_separate_frozen_universes": True}


def freeze_cohort(units: list[StudyUnit], policy: StudyPolicy, *, links=None, frozen_at: str):
    timestamp(frozen_at)
    if any(u.review and timestamp(u.review.locked_at) > timestamp(frozen_at) for u in units):
        raise ValueError("Intake review must precede the frozen cohort")
    links = links or []
    groups = connected_groups(units, links)
    by_id = {u.unit_id: u for u in units}
    for ids in groups.values():
        splits = {by_id[uid].split for uid in ids} - {"unassigned"}
        if len(splits) > 1:
            raise ValueError("Shared artifact/affair/translation component crosses development and test")
    return seal({"schema_version": COHORT_SCHEMA, "frozen_at": frozen_at,
                 "policy": policy.model_dump(), "units": [u.model_dump() for u in sorted(units, key=lambda u: u.unit_id)],
                 "split_links": [l.model_dump() for l in links], "split_groups": dict(sorted(groups.items())),
                 "acquisition": acquisition_report(units, policy),
                 "experiment_committed": acquisition_report(units, policy)["passed"] and
                     all(u.split != "unassigned" for u in units)})


def load_cohort(value):
    body = checked(value, COHORT_SCHEMA)
    units = [StudyUnit.model_validate(u) for u in body["units"]]
    policy = StudyPolicy.model_validate(body["policy"])
    rebuilt = freeze_cohort(units, policy, links=[SplitLink.model_validate(l) for l in body["split_links"]],
                            frozen_at=body["frozen_at"])
    if rebuilt != value:
        raise ValueError("Frozen cohort derived counts or groups do not match")
    return units


def inspect_manifest(fetch_dir: Path):
    """Read every source row, verify actual bytes and retain every failed fetch."""
    import json
    import pypdf
    from pypdf.errors import PdfReadError
    from .contracts import LayerPage, TextSnapshot
    raw = (fetch_dir / "fetch_manifest.json").read_bytes()
    rows = json.loads(raw)["documents"]
    units, texts = [], {}
    for index, row in enumerate(rows):
        source_id = identity([index, row])
        scope = "source:" + source_id
        artifact, pages, reason = None, [], None
        try:
            doc = _input(fetch_dir, row)
            artifact, pages = doc.sha256, [p.number for p in doc.pages]
            text = TextSnapshot(artifact_id=artifact, origin="recorded", parser_name="pypdf",
                parser_version=pypdf.__version__, configuration={"policy": "native-text;no-OCR;no-repair"},
                pages=[LayerPage(page=p.number, layer_id="native", text=p.text) for p in doc.pages])
            texts[text.id] = text.model_dump()
        except (ValueError, OSError, PdfReadError) as error:
            reason = error.reason if isinstance(error, InputFailure) else "source_intake_error"
        row = row if isinstance(row, dict) else {}
        units.append(StudyUnit(unit_id=(artifact or "unavailable:" + source_id) + ":" + scope,
            source_id=source_id, artifact_id=artifact, scope_id=scope, body_id=str(row.get("body_id", "unknown")),
            body_key=str(row.get("body_key", "unknown")), level=row.get("level") if row.get("level") in
                {"municipal", "cantonal", "federal"} else "unknown",
            affair_id=str(row["affair_id"]) if row.get("affair_id") is not None else None,
            language_hint=row.get("language") or "unknown", role_hint=row.get("role") or "unknown",
            source_status="failed" if reason else "ready", failure_reason=reason, available_pages=pages,
            hard_case=bool(row.get("likely_scanned"))))
    return {"source_manifest_digest": identity(json.loads(raw)), "units": [u.model_dump() for u in units],
            "texts": [texts[k] for k in sorted(texts)]}


def field_packet(cohort, texts, reviewer_id):
    units = load_cohort(cohort)
    by_artifact = {t.artifact_id: t for t in texts}
    tasks = []
    for unit in units:
        if unit.split != "test":
            continue
        text = by_artifact.get(unit.artifact_id)
        tasks.append({"unit": unit.model_dump(), "text": text.model_dump() if text else None,
                      "intake_review": None, "gold_fields": None,
                      "instruction": "Record original blind annotations and checked scope. Unknown/unreadable is not absent."})
    return {"schema_version": "skony.field-review-packet.v1", "cohort_digest": cohort["digest"],
            "reviewer_id": reviewer_id, "mode": "blind", "model_outputs_included": False, "tasks": tasks}
