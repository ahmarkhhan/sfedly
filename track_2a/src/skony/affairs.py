"""Transactional scoped review and immutable historical closures (A2/A4).

Mutable heads select current immutable versions; decisions and snapshots never
change. A newly built current export rechecks every dependency in one transaction.
"""

from __future__ import annotations

import hashlib
import json

from .citations import citation
from .comparison import query_snapshot
from .completeness import SectionCheck, assess_completeness
from .contracts import (FIELDS, PROJECTION_VERSION, SERIALIZATION_VERSION, ScopeBinding,
                        ScopeWindow, TextSnapshot, canonical, identity)
from .migration import (_write_once, get_object, head, migrate, put_object, set_head,
                        source_record)
from .review import ReviewError, ReviewStore, timestamp
from .review_contracts import (AffairRecord, Claim, ComparisonSpec, MappingRule,
                               ReviewInput, ScopeRecord)
from .schema import Document


class AffairStore:
    def __init__(self, store: ReviewStore, *, source_manifests=None):
        self.store = store
        self.migration_report = migrate(store, source_manifests=source_manifests)

    def _audit(self, db, scope_id, action, reviewer, body):
        db.execute("INSERT INTO audit(document_id,field,action,reviewer,snapshot_json,created_at) VALUES(?,?,?,?,?,?)",
                   (scope_id, None, "v2:" + action, reviewer, canonical(body).decode(), timestamp()))

    def _scope(self, db, scope_id):
        row = head(db, "scope", scope_id)
        if not row:
            raise ReviewError("Scope not found", 404)
        return row, ScopeRecord.model_validate(get_object(db, row["object_id"], "scope"))

    def get(self, identifier, kind=None):
        with self.store.db() as db:
            return get_object(db, identifier, kind)

    def scopes(self):
        with self.store.db() as db:
            return [{"id": r["entity_key"], "version": r["object_id"], "revision": r["revision"],
                     **get_object(db, r["object_id"], "scope")} for r in
                    db.execute("SELECT * FROM v2_heads WHERE kind='scope' ORDER BY entity_key")]

    def register_document(self, legacy_id: str, metadata: dict):
        item = self.store.get(legacy_id)
        document = Document.model_validate(item["document"])
        data = self.store.pdf_path(legacy_id).read_bytes()
        if hashlib.sha256(data).hexdigest() != document.sha256:
            raise ReviewError("Original PDF digest mismatch", 409)
        _write_once(self.store.directory / "artifacts" / (document.sha256 + ".pdf"), data)
        with self.store.db(write=True) as db:
            artifact = {"schema_version": "skony.artifact.v0.2", "sha256": document.sha256,
                        "size": len(data), "pages": sorted(p.number for p in document.pages),
                        "file": "artifacts/" + document.sha256 + ".pdf", "legacy_document_id": legacy_id}
            artifact_head = head(db, "artifact", document.sha256)
            if not artifact_head:
                set_head(db, "artifact", document.sha256, put_object(db, "artifact", artifact), 0)
            text = TextSnapshot.legacy(document.sha256, document.pages)
            text_id = put_object(db, "text", text)
            source_id = put_object(db, "source", source_record(metadata, document.sha256, origin="registered_source"))
            scope_id = "source:" + source_id
            previous = head(db, "scope", scope_id)
            if previous:
                return {"scope_id": scope_id, "revision": previous["revision"], "source_id": source_id}
            scope = ScopeRecord(binding=ScopeBinding(scope_id=scope_id, subject_id="unresolved:" + source_id,
                artifact_id=document.sha256, text_snapshot_id=text_id,
                association_version="unverified", role_version="unverified", role="unknown",
                windows=[ScopeWindow(page=p.page, layer_id=p.layer_id, start=0, end=len(p.text)) for p in text.pages]),
                source_ids=[source_id])
            version = put_object(db, "scope", scope)
            revision = set_head(db, "scope", scope_id, version, 0)
            self._audit(db, scope_id, "source_registered", "intake", {"source_id": source_id, "scope_version": version})
            return {"scope_id": scope_id, "revision": revision, "source_id": source_id}

    def register_text(self, text: TextSnapshot):
        with self.store.db(write=True) as db:
            artifact_head = head(db, "artifact", text.artifact_id)
            if not artifact_head:
                raise ReviewError("Text snapshot artifact is not registered", 404)
            artifact = get_object(db, artifact_head["object_id"], "artifact")
            if {p.page for p in text.pages} - set(artifact["pages"]):
                raise ReviewError("Text snapshot contains unknown pages", 422)
            return put_object(db, "text", text)

    def put_affair(self, record: AffairRecord, *, revision=0):
        with self.store.db(write=True) as db:
            for source_id in record.source_ids:
                get_object(db, source_id, "source")
            if record.official_affair_id is not None:
                key = identity([record.provider_namespace, record.body_id, record.official_affair_id])
                official = head(db, "official_affair", key)
                if official and get_object(db, official["object_id"], "affair")["internal_id"] != record.internal_id:
                    raise ReviewError("This namespaced affair identity already exists", 409)
            old = head(db, "affair", record.internal_id)
            if old:
                prior = get_object(db, old["object_id"], "affair")
                if any(prior[k] != getattr(record, k) for k in ("provider_namespace", "body_id", "official_affair_id")):
                    raise ReviewError("Identity corrections require a successor affair and reassigned scopes", 409)
            oid = put_object(db, "affair", record)
            rev = set_head(db, "affair", record.internal_id, oid, revision)
            if record.official_affair_id is not None:
                set_head(db, "official_affair", key, oid, official["revision"] if official else 0)
            return {"id": record.internal_id, "version": oid, "revision": rev}

    def put_scope(self, scope: ScopeRecord, *, revision: int, reviewer: str, note: str):
        if not reviewer.strip() or not note.strip():
            raise ReviewError("Scope changes require a reviewer and reason", 422)
        with self.store.db(write=True) as db:
            binding = scope.binding
            artifact = head(db, "artifact", binding.artifact_id)
            if not artifact:
                raise ReviewError("Scope artifact is not registered", 404)
            text = TextSnapshot.model_validate(get_object(db, binding.text_snapshot_id, "text"))
            if text.artifact_id != binding.artifact_id:
                raise ReviewError("Scope and text refer to different artifacts", 422)
            if binding.membership == "reviewed" and not head(db, "affair", binding.subject_id):
                raise ReviewError("Reviewed membership requires a registered affair identity", 422)
            for window in binding.windows:
                if window.end > len(text.page_text(window.page, window.layer_id)):
                    raise ReviewError("Scope window exceeds the immutable text", 422)
            for source_id in scope.source_ids:
                if get_object(db, source_id, "source")["artifact_id"] != binding.artifact_id:
                    raise ReviewError("Source record belongs to another artifact", 422)
            for mapping_id in scope.mapping_ids:
                mapping = get_object(db, mapping_id, "mapping")
                current = head(db, "mapping", mapping["key"])
                if current["object_id"] != mapping_id:
                    raise ReviewError("Use the current mapping version", 409)
                affair = head(db, "affair", binding.subject_id)
                if not affair or get_object(db, affair["object_id"], "affair")["body_id"] != mapping["body_id"]:
                    raise ReviewError("Mapping does not apply to this source body", 422)
            # The service generates semantic dependency versions; callers cannot
            # keep an old version string while silently changing its meaning.
            binding = binding.model_copy(update={
                "association_version": identity([binding.subject_id, binding.membership,
                                                  [w.model_dump() for w in binding.windows]]),
                "role_version": identity(binding.role)})
            scope = scope.model_copy(update={"binding": binding, "source_ids": sorted(set(scope.source_ids)),
                                             "mapping_ids": sorted(set(scope.mapping_ids))})
            old = head(db, "scope", binding.scope_id)
            oid = put_object(db, "scope", scope)
            rev = set_head(db, "scope", binding.scope_id, oid, revision)
            self._audit(db, binding.scope_id, "scope_changed", reviewer,
                        {"before": old["object_id"] if old else None, "after": oid, "note": note})
            return {"scope_id": binding.scope_id, "version": oid, "revision": rev}

    def put_mapping(self, mapping: MappingRule, *, revision: int):
        with self.store.db(write=True) as db:
            oid = put_object(db, "mapping", mapping)
            rev = set_head(db, "mapping", mapping.key, oid, revision)
            self._audit(db, mapping.key, "mapping_changed", mapping.reviewer, {"version": oid})
            return {"version": oid, "revision": rev}

    def _validate_evidence(self, db, claim, scope):
        for segment in claim.evidence:
            if segment.artifact_id != scope.binding.artifact_id:
                raise ReviewError("Evidence belongs to another artifact", 422)
            if segment.basis == "text":
                if segment.text_snapshot_id != scope.binding.text_snapshot_id:
                    raise ReviewError("Evidence uses another text snapshot", 409)
                text = TextSnapshot.model_validate(get_object(db, segment.text_snapshot_id, "text"))
                citation(segment, text)
                if not any(w.page == segment.page and w.layer_id == segment.layer_id and
                           w.start <= segment.start < segment.end <= w.end for w in scope.binding.windows):
                    raise ReviewError("Evidence lies outside the claim's subject scope", 422)
            elif segment.page not in {w.page for w in scope.binding.windows}:
                raise ReviewError("Image evidence is outside the source scope", 422)

    def put_claim(self, claim: Claim):
        with self.store.db(write=True) as db:
            _, scope = self._scope(db, claim.scope_id)
            if claim.subject_id != scope.binding.subject_id:
                raise ReviewError("Claim subject differs from the scoped association", 422)
            self._validate_evidence(db, claim, scope)
            if claim.origin_id is not None:
                origin = get_object(db, claim.origin_id, "extraction")
                result = origin.get("result")
                items = [item for target in (result or {}).get("targets", [])
                         if target["scope_id"] == claim.scope_id
                         for item in target["fields"].get(claim.predicate, {}).get("items", [])]
                if not any(i["value"] == claim.value and i["evidence"] ==
                           [e.model_dump() for e in claim.evidence] for i in items):
                    raise ReviewError("Claim does not match its recorded extraction origin", 422)
                if (claim.chunk_manifest is None or claim.chunk_manifest.model_dump() != origin["manifest"]
                        or [o.model_dump() for o in claim.chunk_outcomes] != [origin["outcome"]]):
                    raise ReviewError("Claim must preserve its recorded extraction coverage and outcome", 422)
            if claim.relation is not None:
                raise ReviewError("Use imported typed structural proposals for relations", 422)
            if claim.predicate not in FIELDS:
                raise ReviewError("Structural proposals remain untested and require a dedicated review adapter", 422)
            if claim.chunk_manifest:
                artifact = get_object(db, head(db, "artifact", scope.binding.artifact_id)["object_id"], "artifact")
                if claim.chunk_manifest.available_pages != artifact["pages"]:
                    raise ReviewError("Coverage must report all available artifact pages", 422)
                if not {e.page for e in claim.evidence}.issubset(claim.chunk_manifest.selected_pages):
                    raise ReviewError("Chunk manifest does not cover the claim evidence", 422)
                assess_completeness(claim.chunk_manifest, claim.chunk_outcomes,
                                    scope_identity="validation", assertion_identity="validation")
            oid = put_object(db, "claim", claim)
            # Exact repeated assertions are idempotent; alternative values remain
            # separate claims and automatically invalidate unresolved acceptances.
            if not head(db, "claim", oid):
                set_head(db, "claim", oid, oid, 0)
                self._audit(db, claim.scope_id, "claim_added", "proposal", {"claim_id": oid})
            return oid

    def save_extraction(self, result):
        with self.store.db(write=True) as db:
            return put_object(db, "extraction", result)

    def claims(self, scope_id):
        with self.store.db() as db:
            self._scope(db, scope_id)
            return [{"id": r["id"], **get_object(db, r["id"], "claim")} for r in
                    db.execute("SELECT id FROM v2_objects WHERE kind='claim' ORDER BY id")
                    if get_object(db, r["id"], "claim")["scope_id"] == scope_id]

    def current_reviews(self):
        with self.store.db() as db:
            return [{"decision_id": r["object_id"], "revision": r["revision"],
                     "decision": get_object(db, r["object_id"], "review"),
                     **self._eligibility(db, r["object_id"])} for r in
                    db.execute("SELECT * FROM v2_heads WHERE kind='review' ORDER BY entity_key")]

    def versions(self, kind):
        with self.store.db() as db:
            if kind == "snapshot":
                return [{"id": r["id"], "value": get_object(db, r["id"], "snapshot")} for r in
                        db.execute("SELECT id FROM v2_objects WHERE kind='snapshot' ORDER BY id")]
            return [{"id": r["entity_key"], "version": r["object_id"], "revision": r["revision"],
                     "value": get_object(db, r["object_id"], kind)} for r in
                    db.execute("SELECT * FROM v2_heads WHERE kind=? ORDER BY entity_key", (kind,))]

    def _dependencies(self, db, claim_id, claim, coverage):
        scope_head, scope = self._scope(db, claim.scope_id)
        scoped = []
        for row in db.execute("SELECT * FROM v2_heads WHERE kind='scope' ORDER BY entity_key"):
            candidate = get_object(db, row["object_id"], "scope")
            if ((coverage == "affair" and candidate["binding"]["subject_id"] == scope.binding.subject_id)
                    or row["entity_key"] == claim.scope_id):
                scoped.append({"scope_id": row["entity_key"], "version": row["object_id"]})
        mappings = []
        for mid in scope.mapping_ids:
            mapping = get_object(db, mid, "mapping")
            current = head(db, "mapping", mapping["key"])
            mappings.append({"key": mapping["key"], "version": current["object_id"]})
        alternatives = {}
        for row in db.execute("SELECT id FROM v2_objects WHERE kind='claim' ORDER BY rowid"):
            other = get_object(db, row["id"], "claim")
            if other["scope_id"] == claim.scope_id and other["predicate"] == claim.predicate:
                # Multiple distinct values/dispositions constitute a conflict.
                signature = identity([other["value"], other["source_assessment"]])
                alternatives.setdefault(signature, []).append(row["id"])
        # The first immutable representative of each distinct disposition is
        # stable across identical reruns with new timing/origin metadata.
        conflict_ids = sorted(group[0] for group in alternatives.values()) if len(alternatives) > 1 else []
        affair = head(db, "affair", scope.binding.subject_id)
        return {"subject_id": claim.subject_id, "affair_version": affair["object_id"] if affair else None,
                "predicate": claim.predicate, "assertion_version": claim_id,
                "evidence_identity": identity([e.model_dump() for e in claim.evidence]),
                "scope_version": scope_head["object_id"], "association_version": scope.binding.association_version,
                "role_version": scope.binding.role_version, "text_snapshot_id": scope.binding.text_snapshot_id,
                "reviewed_scope": scoped, "reviewed_scope_identity": identity(scoped),
                "mappings": mappings, "conflicting_assertions": conflict_ids}

    @staticmethod
    def _review_key(claim, coverage):
        return identity([claim.scope_id, claim.predicate, coverage])

    def review_revision(self, claim_id, coverage="document"):
        with self.store.db() as db:
            claim = Claim.model_validate(get_object(db, claim_id, "claim"))
            current = head(db, "review", self._review_key(claim, coverage))
            return current["revision"] if current else 0

    def review(self, request: ReviewInput):
        with self.store.db(write=True) as db:
            claim = Claim.model_validate(get_object(db, request.claim_id, "claim"))
            _, scope = self._scope(db, claim.scope_id)
            dependencies = self._dependencies(db, request.claim_id, claim, request.coverage)
            if claim.subject_id != scope.binding.subject_id:
                raise ReviewError("Reassigned claims require a successor assertion", 409)
            self._validate_evidence(db, claim, scope)
            expected_scopes = {s["scope_id"] for s in dependencies["reviewed_scope"]}
            if set(request.checked_scope) != expected_scopes:
                raise ReviewError("Declare every checked scope for this review", 422)
            for scope_id, pages in request.checked_scope.items():
                _, checked = self._scope(db, scope_id)
                expected_pages = {w.page for w in checked.binding.windows}
                if len(pages) != len(set(pages)) or set(pages) != expected_pages:
                    raise ReviewError("Checked pages must cover the declared review scope", 422)
            if request.action in {"accepted", "corrected"}:
                if scope.binding.membership != "reviewed" or scope.binding.role == "unknown":
                    raise ReviewError("Resolve affair membership and document role first", 409)
                if dependencies["conflicting_assertions"] and not request.resolve_conflicts:
                    raise ReviewError("Resolve the conflicting assertions with a reason before accepting", 409)
            completeness = {"semantic_completeness": "unknown"}
            if claim.predicate in {"question_text", "answer_text"}:
                check = None
                if request.section_complete is not None:
                    check = SectionCheck(reviewer=request.reviewer, note=request.note,
                        scope_identity=dependencies["reviewed_scope_identity"], assertion_identity=request.claim_id,
                        boundary_checked=request.boundary_checked, required_clauses_checked=request.required_clauses_checked,
                        complete=request.section_complete)
                if claim.chunk_manifest:
                    completeness = assess_completeness(claim.chunk_manifest, claim.chunk_outcomes,
                        scope_identity=dependencies["reviewed_scope_identity"], assertion_identity=request.claim_id,
                        unsatisfied_continuation=claim.unsatisfied_continuation, check=check)
                else:
                    reasons = []
                    if claim.unsatisfied_continuation:
                        reasons.append("unsatisfied_continuation")
                    if check and not check.complete:
                        reasons.append("human_incomplete_section")
                    semantic = "incomplete" if reasons else "unknown"
                    if not reasons and check and check.complete and check.boundary_checked and check.required_clauses_checked:
                        semantic = "complete_in_reviewed_scope"
                    completeness = {"semantic_completeness": semantic, "reasons": reasons,
                        "section_check": check.model_dump() if check else None,
                        "input_coverage": "unknown", "generation_completion": "unknown"}
            decision = {"schema_version": "skony.decision.v0.2", "request": request.model_dump(),
                        "dependencies": dependencies, "completeness": completeness, "created_at": timestamp()}
            oid = put_object(db, "review", decision)
            rev = set_head(db, "review", self._review_key(claim, request.coverage), oid, request.revision)
            self._audit(db, claim.scope_id, "review", request.reviewer, {"decision_id": oid, "claim_id": request.claim_id})
            return {"decision_id": oid, "revision": rev, "completeness": completeness}

    def _eligibility(self, db, decision_id):
        decision = get_object(db, decision_id, "review")
        request = ReviewInput.model_validate(decision["request"])
        claim = Claim.model_validate(get_object(db, request.claim_id, "claim"))
        current = self._dependencies(db, request.claim_id, claim, request.coverage)
        reasons = []
        if request.action not in {"accepted", "corrected"}:
            reasons.append("decision_not_accepted")
        for key, original in decision["dependencies"].items():
            if current[key] != original:
                reasons.append("changed_" + key)
        review_head = head(db, "review", self._review_key(claim, request.coverage))
        if not review_head or review_head["object_id"] != decision_id:
            reasons.append("superseded_review")
        _, scope = self._scope(db, claim.scope_id)
        if scope.binding.membership != "reviewed" or scope.binding.role == "unknown":
            reasons.append("unresolved_membership_or_role")
        if claim.subject_id != scope.binding.subject_id:
            reasons.append("changed_subject")
        if current["conflicting_assertions"] and not request.resolve_conflicts:
            reasons.append("unresolved_conflict")
        if any(m["version"] not in scope.mapping_ids for m in current["mappings"]):
            reasons.append("scope_mapping_requires_successor")
        return {"eligible": not reasons, "reasons": sorted(set(reasons))}

    def eligibility(self, decision_id):
        with self.store.db() as db:
            return self._eligibility(db, decision_id)

    def freeze(self, decision_ids: list[str], *, scope_ids: list[str], exclusions=None):
        if not decision_ids or len(decision_ids) != len(set(decision_ids)):
            raise ReviewError("Supply a nonempty unique decision set", 422)
        if not scope_ids or len(scope_ids) != len(set(scope_ids)):
            raise ReviewError("Supply unique snapshot scopes", 422)
        with self.store.db(write=True) as db:
            closure, rows, seen = {}, [], set()

            def pin(oid, kind):
                value = get_object(db, oid, kind)
                closure[oid] = {"kind": kind, "value": value}
                return value

            def pin_scope(scope_id, version=None):
                current, _ = self._scope(db, scope_id)
                scope = ScopeRecord.model_validate(pin(version or current["object_id"], "scope"))
                pin(scope.binding.text_snapshot_id, "text")
                artifact = head(db, "artifact", scope.binding.artifact_id)
                meta = pin(artifact["object_id"], "artifact")
                artifact_path = self.store.directory / "artifacts" / (scope.binding.artifact_id + ".pdf")
                if not artifact_path.is_file() or hashlib.sha256(artifact_path.read_bytes()).hexdigest() != meta["sha256"]:
                    raise ReviewError("Snapshot artifact is missing or corrupt", 409)
                for sid in scope.source_ids:
                    pin(sid, "source")
                for mid in scope.mapping_ids:
                    pin(mid, "mapping")
                affair = head(db, "affair", scope.binding.subject_id)
                if affair:
                    record = pin(affair["object_id"], "affair")
                    for sid in record["source_ids"]:
                        pin(sid, "source")
                return scope

            scopes = {sid: pin_scope(sid) for sid in sorted(scope_ids)}
            for did in sorted(decision_ids):
                status = self._eligibility(db, did)
                if not status["eligible"]:
                    raise ReviewError("Current snapshot blocked: " + ", ".join(status["reasons"]), 409)
                decision = pin(did, "review")
                claim = Claim.model_validate(pin(decision["request"]["claim_id"], "claim"))
                if claim.scope_id not in scopes:
                    raise ReviewError("Decision is outside the requested snapshot scope", 422)
                key = (claim.scope_id, claim.predicate)
                if key in seen:
                    raise ReviewError("Choose one resolved disposition per scope/predicate", 422)
                seen.add(key)
                if claim.origin_id:
                    pin(claim.origin_id, "extraction")
                for dep in decision["dependencies"]["reviewed_scope"]:
                    pin_scope(dep["scope_id"], dep["version"])
                for conflict_id in decision["dependencies"]["conflicting_assertions"]:
                    other = Claim.model_validate(pin(conflict_id, "claim"))
                    for ev in other.evidence:
                        historical_artifact = head(db, "artifact", ev.artifact_id)
                        if historical_artifact:
                            pin(historical_artifact["object_id"], "artifact")
                        if ev.text_snapshot_id:
                            pin(ev.text_snapshot_id, "text")
                    if other.origin_id:
                        pin(other.origin_id, "extraction")
                citations = [citation(e, TextSnapshot.model_validate(pin(e.text_snapshot_id, "text"))
                                      if e.basis == "text" else None) for e in claim.evidence]
                rows.append({"scope_id": claim.scope_id, "subject_id": claim.subject_id,
                             "predicate": claim.predicate, "value": claim.value,
                             "source_assessment": claim.source_assessment, "decision_id": did,
                             "coverage": decision["request"]["coverage"],
                             "completeness": decision["completeness"], "citations": citations})
            body = {"schema_version": "skony.snapshot.v0.2", "projection_version": PROJECTION_VERSION,
                    "serialization_version": SERIALIZATION_VERSION, "query_version": "skony.query.v0.2",
                    "scope_ids": sorted(scope_ids), "decisions": sorted(decision_ids),
                    "scope_versions": {sid: head(db, "scope", sid)["object_id"] for sid in sorted(scope_ids)},
                    "exclusions": sorted(exclusions or [], key=lambda x: canonical(x)),
                    "rows": sorted(rows, key=lambda r: (r["subject_id"], r["scope_id"], r["predicate"])),
                    "objects": {key: closure[key] for key in sorted(closure)}}
            sid = put_object(db, "snapshot", body)
            return {"snapshot_id": sid, "snapshot": body}

    def snapshot(self, identifier):
        with self.store.db() as db:
            body = get_object(db, identifier, "snapshot")
            for oid, obj in body["objects"].items():
                if identity(obj["value"]) != oid:
                    raise ReviewError("Frozen dependency digest mismatch", 409)
            statuses = [dict(r) for r in db.execute(
                "SELECT status,successor_id,reason,created_at FROM v2_snapshot_status WHERE snapshot_id=? ORDER BY id", (identifier,))]
            warnings = []
            for did in body["decisions"]:
                eligible = self._eligibility(db, did)
                if not eligible["eligible"]:
                    warnings.append({"decision_id": did, **eligible})
            return {"snapshot_id": identifier, "snapshot": body, "status_history": statuses,
                    "historical_warning": bool(statuses or warnings), "current_eligibility_warnings": warnings}

    def mark_snapshot(self, identifier, *, status, reason, successor_id=None):
        if status not in {"superseded", "withdrawn"} or not reason.strip():
            raise ReviewError("Supply superseded/withdrawn status and a reason", 422)
        if status == "superseded" and (not successor_id or successor_id == identifier):
            raise ReviewError("Supersession requires a different successor snapshot", 422)
        with self.store.db(write=True) as db:
            get_object(db, identifier, "snapshot")
            if successor_id:
                get_object(db, successor_id, "snapshot")
            db.execute("INSERT INTO v2_snapshot_status(snapshot_id,status,successor_id,reason,created_at) VALUES(?,?,?,?,?)",
                       (identifier, status, successor_id, reason, timestamp()))

    def compare(self, spec: ComparisonSpec, *, current=False):
        replay = self.snapshot(spec.snapshot_id)
        snapshot = replay["snapshot"]
        if current and replay["historical_warning"]:
            raise ReviewError("Snapshot is historical; build a newly eligible snapshot", 409)
        result = query_snapshot(snapshot, spec)
        # Mutable warnings deliberately live outside the deterministic artifact.
        return {**result, "historical_warning": replay["historical_warning"],
                "status_history": replay["status_history"]}
