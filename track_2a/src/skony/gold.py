"""Explicit annotation quality and deterministic scoped field scoring (A6)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .cache import atomic_json
from .contracts import FIELDS, PROJECTION_VERSION, StrictModel, identity
from .review_contracts import SourceAssessment

LabelStatus = Literal["single_annotator_final", "independently_agreed", "adjudicated", "unresolved"]
STATUSES = ("single_annotator_final", "independently_agreed", "adjudicated", "unresolved")


class Annotation(StrictModel):
    annotator_id: str = Field(min_length=1)
    kind: Literal["human", "automated", "synthetic"]
    mode: Literal["blind", "assisted"]
    language_competence: str = Field(min_length=1)
    procedural_competence: str = Field(min_length=1)
    locked_at: str = Field(min_length=1)
    scope_identity: str
    independent: bool
    assessment: SourceAssessment
    acceptable_values: list[str]


class Adjudication(StrictModel):
    adjudicator_id: str = Field(min_length=1)
    note: str = Field(min_length=1)
    locked_at: str = Field(min_length=1)


class GoldLabel(StrictModel):
    assessment: SourceAssessment
    acceptable_values: list[str]
    checked_scope: dict[str, list[int]]
    scope_identity: str
    status: LabelStatus
    annotations: list[Annotation]
    adjudication: Adjudication | None = None
    completeness_requirements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def quality(self):
        if not self.checked_scope or any(not pages or any(p < 1 for p in pages)
                                         or len(pages) != len(set(pages)) for pages in self.checked_scope.values()):
            raise ValueError("Gold requires structured checked scope")
        if self.scope_identity != identity(self.checked_scope):
            raise ValueError("Gold checked-scope identity mismatch")
        if self.assessment == "present":
            if not self.acceptable_values or any(not v.strip() for v in self.acceptable_values):
                raise ValueError("Known-present gold needs acceptable verbatim values")
        elif self.acceptable_values:
            raise ValueError("Non-present disposition must not carry accepted values")
        ids = [a.annotator_id for a in self.annotations]
        if len(set(ids)) != len(ids):
            raise ValueError("Repeated reviewer is not independent annotation")
        if any(a.scope_identity != self.scope_identity for a in self.annotations):
            raise ValueError("Annotations have different checked scopes")
        if self.status != "unresolved" and not self.annotations:
            raise ValueError("Final labels need annotation provenance")
        if self.status == "single_annotator_final":
            if len(self.annotations) != 1 or self.adjudication is not None:
                raise ValueError("Single-annotator final must remain explicitly single")
            one = self.annotations[0]
            if one.assessment != self.assessment or set(one.acceptable_values) != set(self.acceptable_values):
                raise ValueError("Final label differs from its sole annotation")
        if self.status in {"independently_agreed", "adjudicated"}:
            if len(self.annotations) < 2 or any(not a.independent for a in self.annotations):
                raise ValueError("Independent/adjudicated labels need independent annotations")
        if self.status == "independently_agreed":
            if self.adjudication is not None or any(a.assessment != self.assessment or
                    set(a.acceptable_values) != set(self.acceptable_values) for a in self.annotations):
                raise ValueError("Independent agreement requires matching original annotations")
        if self.status == "adjudicated":
            if not self.adjudication or self.adjudication.adjudicator_id in ids:
                raise ValueError("Adjudication requires a separately recorded adjudicator")
        elif self.adjudication is not None:
            raise ValueError("Only adjudicated labels may carry adjudication")
        return self


class GoldUnit(StrictModel):
    gold_schema_version: Literal["skony.gold.v0.2"] = "skony.gold.v0.2"
    artifact_id: str
    scope_id: str
    split_group: str
    body_id: str
    language: str
    synthetic: bool = False
    fields: dict[str, GoldLabel]

    @property
    def unit_id(self):
        return self.artifact_id + ":" + self.scope_id

    @model_validator(mode="after")
    def slots(self):
        if set(self.fields) != set(FIELDS):
            raise ValueError("Gold requires exactly eight field dispositions per target scope")
        if any(self.scope_id not in label.checked_scope for label in self.fields.values()):
            raise ValueError("Gold label checked scope excludes its target")
        return self


class Prediction(StrictModel):
    unit_id: str
    outcome: Literal["completed", "failed", "unsupported", "not_run"]
    fields: dict[str, str | None]

    @model_validator(mode="after")
    def slots(self):
        if self.outcome == "completed" and set(self.fields) != set(FIELDS):
            raise ValueError("Completed prediction requires all eight slots")
        if self.outcome != "completed" and self.fields:
            raise ValueError("Failed inputs must not masquerade as successful empty outputs")
        return self


def label_eligibility(label: GoldLabel, *, sensitivity=False):
    if label.status == "unresolved":
        return False, "unresolved"
    if any(a.kind != "human" for a in label.annotations):
        return False, "not_human_gold"
    if any(a.mode != "blind" for a in label.annotations):
        return False, "assisted_gold_development_only"
    if label.assessment not in {"present", "absent_in_reviewed_scope"}:
        return False, label.assessment
    if sensitivity and label.status == "single_annotator_final":
        return False, "single_annotator_excluded_from_sensitivity"
    return True, None


def _ratio(n, d):
    return n / d if d else None


def _score_subset(units, predictions, *, sensitivity, total_units):
    counts = {name: {"tp": 0, "fp": 0, "fn": 0, "scorable": 0,
                     "known_absent": 0, "correct_absence": 0, "failed_absent": 0} for name in FIELDS}
    statuses, eligible_statuses, excluded = Counter(), Counter(), Counter()
    for unit in units:
        prediction = predictions.get(unit.unit_id)
        completed = prediction is not None and prediction.outcome == "completed"
        for name in FIELDS:
            label = unit.fields[name]
            statuses[label.status] += 1
            eligible, reason = label_eligibility(label, sensitivity=sensitivity)
            if unit.synthetic:
                eligible, reason = False, "synthetic_unit"
            if not eligible:
                excluded[reason] += 1
                continue
            eligible_statuses[label.status] += 1
            c = counts[name]
            c["scorable"] += 1
            value = prediction.fields[name] if completed else None
            if label.assessment == "present":
                if value is not None and " ".join(value.split()) in {" ".join(v.split()) for v in label.acceptable_values}:
                    c["tp"] += 1
                else:
                    c["fn"] += 1
                    c["fp"] += value is not None
            else:
                c["known_absent"] += 1
                c["fp"] += value is not None
                c["correct_absence"] += completed and value is None
                c["failed_absent"] += not completed
    micro = {key: sum(v[key] for v in counts.values()) for key in next(iter(counts.values()))}

    def metrics(c):
        return {**c, "precision": _ratio(c["tp"], c["tp"] + c["fp"]),
                "recall": _ratio(c["tp"], c["tp"] + c["fn"]),
                "f1": _ratio(2 * c["tp"], 2 * c["tp"] + c["fp"] + c["fn"]),
                "correct_absence_rate": _ratio(c["correct_absence"], c["known_absent"])}

    return {"micro": metrics(micro), "per_field": {k: metrics(v) for k, v in counts.items()},
            "label_status_counts": {s: statuses[s] for s in STATUSES},
            "scored_status_counts": {s: eligible_statuses[s] for s in STATUSES},
            "excluded_by_reason": dict(sorted(excluded.items())),
            "scorable_field_fraction": _ratio(micro["scorable"], total_units * len(FIELDS)),
            "annotated_field_slots": len(units) * len(FIELDS),
            "full_cohort_field_slots": total_units * len(FIELDS)}


def score(units: list[GoldUnit], predictions: list[Prediction], *, frozen_unit_ids: list[str]):
    ids = [u.unit_id for u in units]
    predicted_ids = [p.unit_id for p in predictions]
    if (not frozen_unit_ids or len(set(frozen_unit_ids)) != len(frozen_unit_ids)
            or len(set(ids)) != len(ids) or len(set(predicted_ids)) != len(predicted_ids)
            or set(ids) - set(frozen_unit_ids) or set(predicted_ids) - set(frozen_unit_ids)):
        raise ValueError("Duplicate/out-of-cohort unit; scoring units are artifact-plus-scope")
    by_id = {p.unit_id: p for p in predictions}
    outcomes = Counter(by_id[uid].outcome if uid in by_id else "not_run" for uid in frozen_unit_ids)
    return {"schema_version": "skony.score.v0.2", "projection_version": PROJECTION_VERSION,
            "matching_policy": "exact_words_punctuation_case_with_whitespace_only_normalization",
            "semantic_accuracy_claim": False,
            "cohort_digest": identity(sorted(frozen_unit_ids)),
            "gold_digest": identity([u.model_dump() for u in sorted(units, key=lambda u: u.unit_id)]),
            "prediction_digest": identity([p.model_dump() for p in sorted(predictions, key=lambda p: p.unit_id)]),
            "frozen_units": len(frozen_unit_ids), "artifact_count_with_gold": len({u.artifact_id for u in units}),
            "units_with_gold": len(units), "units_without_gold": len(frozen_unit_ids) - len(units),
            "operational_outcomes": dict(sorted(outcomes.items())),
            "full_cohort_success": _ratio(outcomes["completed"], len(frozen_unit_ids)),
            "primary": _score_subset(units, by_id, sensitivity=False, total_units=len(frozen_unit_ids)),
            "independently_checked_sensitivity": _score_subset(units, by_id, sensitivity=True, total_units=len(frozen_unit_ids))}


def export_gold_v2(units: list[GoldUnit], directory: Path):
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Use a new export directory")
    if len({u.unit_id for u in units}) != len(units):
        raise ValueError("Duplicate scoped gold unit")
    for unit in units:
        if unit.synthetic or any(a.kind != "human" for f in unit.fields.values() for a in f.annotations):
            raise ValueError("Synthetic/automated annotations cannot be exported as human gold")
    directory.mkdir(parents=True, exist_ok=True)
    files, statuses = [], Counter()
    for unit in sorted(units, key=lambda u: u.unit_id):
        filename = identity(unit.unit_id) + ".json"
        value = unit.model_dump()
        atomic_json(directory / filename, value)
        files.append({"file": filename, "unit_id": unit.unit_id, "digest": identity(value)})
        statuses.update(label.status for label in unit.fields.values())
    manifest = {"gold_schema_version": "skony.gold.v0.2", "files": files,
                "label_status_counts": {s: statuses[s] for s in STATUSES},
                "primary_statuses": list(STATUSES[:3]), "sensitivity_statuses": list(STATUSES[1:3]),
                "eligibility_policy": "Known labels with human blind annotation; all other dispositions remain visible."}
    atomic_json(directory / "manifest.json", manifest)
    return manifest
