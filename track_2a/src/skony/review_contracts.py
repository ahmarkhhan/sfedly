"""Human review contracts, distinct from model proposals and legacy decisions."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .completeness import ChunkManifest, ChunkOutcome
from .contracts import EvidenceSegment, FIELDS, ScopeBinding, StrictModel


class AffairRecord(StrictModel):
    internal_id: str = Field(min_length=1)
    provider_namespace: str = Field(min_length=1)
    body_id: str = Field(min_length=1)
    body_key: str = Field(min_length=1)
    official_affair_id: str | None
    jurisdiction_level: Literal["municipal", "cantonal", "federal", "unknown"]
    source_ids: list[str]


class ScopeRecord(StrictModel):
    binding: ScopeBinding
    source_ids: list[str]
    mapping_ids: list[str] = Field(default_factory=list)


SourceAssessment = Literal["present", "absent_in_reviewed_scope", "unreadable", "ambiguous",
                           "outside_available_scope", "not_assessed"]


class Claim(StrictModel):
    scope_id: str
    subject_id: str
    predicate: str
    value: str | None
    source_assessment: SourceAssessment = "present"
    evidence: list[EvidenceSegment]
    origin_id: str | None = None
    relation: dict | None = None
    chunk_manifest: ChunkManifest | None = None
    chunk_outcomes: list[ChunkOutcome] = Field(default_factory=list)
    unsatisfied_continuation: bool = False

    @model_validator(mode="after")
    def supported(self):
        if self.predicate not in FIELDS + ("actor", "question", "response", "event", "affair_document",
                                          "question_response", "response_decision", "related_affair"):
            raise ValueError("Unknown predicate")
        if self.source_assessment == "present":
            if not self.value or not self.value.strip() or not self.evidence or self.value != "\n\n".join(e.quote for e in self.evidence):
                raise ValueError("Present claims must preserve the ordered evidence wording")
        elif self.value is not None or self.evidence:
            raise ValueError("Non-present dispositions cannot carry a value/evidence")
        previous = None
        for segment in self.evidence:
            if previous and (segment.page < previous.page or (segment.page == previous.page and
                    segment.basis == previous.basis == "text" and
                    (segment.layer_id != previous.layer_id or segment.start < previous.end))):
                raise ValueError("Claim evidence must preserve page/span order without overlap")
            previous = segment
        return self


class ReviewInput(StrictModel):
    claim_id: str
    revision: int = Field(ge=0)
    action: Literal["accepted", "corrected", "rejected", "adjudication_required"]
    reviewer: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=1, max_length=4000)
    coverage: Literal["document", "affair"] = "document"
    checked_scope: dict[str, list[int]]
    resolve_conflicts: bool = False
    boundary_checked: bool = False
    required_clauses_checked: bool = False
    section_complete: bool | None = None

    @field_validator("reviewer", "note")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Reviewer and note must be nonblank")
        return value.strip()


class MappingRule(StrictModel):
    key: str
    body_id: str
    source_label: str
    destination: str | None
    relation: Literal["exact_in_scope", "broader", "narrower", "related", "unmapped"]
    rationale: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)


class ComparisonSpec(StrictModel):
    schema_version: Literal["skony.comparison.v0.2"] = "skony.comparison.v0.2"
    question: str = Field(min_length=1)
    snapshot_id: str
    scope_ids: list[str] = Field(min_length=1)
    columns: list[str] = Field(min_length=1)
    permitted_mapping_relations: list[Literal["exact_in_scope", "broader", "narrower", "related", "unmapped"]]
    ordering: Literal["subject_scope_predicate"] = "subject_scope_predicate"
    unknown_policy: Literal["preserve"] = "preserve"

    @model_validator(mode="after")
    def valid(self):
        if len(set(self.scope_ids)) != len(self.scope_ids) or len(set(self.columns)) != len(self.columns):
            raise ValueError("Duplicate scope or column")
        if set(self.columns) - set(FIELDS):
            raise ValueError("Only the eight core comparison columns are implemented")
        return self
