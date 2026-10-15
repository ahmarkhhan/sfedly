"""Versioned, closed-set extraction and evidence contracts (audit A1/A3/A7).

The model supplies quotations and local proposals. Identity, offsets, review and
completeness belong to application services. v0.1 remains in schema.py.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .schema import CandidateExtraction, Page, StrictModel

FIELDS = tuple(CandidateExtraction.model_fields)
FieldName = Literal["title", "affair_type_raw", "submitter_raw", "submitted_date_raw",
                    "question_text", "answer_text", "decision_raw", "decision_date_raw"]
DocumentRole = Literal["submission", "executive_response", "decision_record", "minutes",
                       "annex", "combined", "unknown"]
PROJECTION_VERSION = "skony.projection.v0.2"
SERIALIZATION_VERSION = "skony.canonical-json.v1"


def canonical(value) -> bytes:
    if isinstance(value, StrictModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def identity(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class LayerPage(StrictModel):
    page: int = Field(ge=1)
    layer_id: str = Field(min_length=1)
    text: str


class TextSnapshot(StrictModel):
    schema_version: Literal["skony.text.v0.2"] = "skony.text.v0.2"
    artifact_id: str
    parser_name: str | None = None
    parser_version: str | None = None
    configuration: dict | None = None
    origin: Literal["recorded", "legacy_unknown"]
    pages: list[LayerPage] = Field(min_length=1)

    @model_validator(mode="after")
    def check_pages(self):
        keys = [(p.page, p.layer_id) for p in self.pages]
        if keys != sorted(set(keys)):
            raise ValueError("Text pages must be unique and ordered by page/layer")
        if self.origin == "legacy_unknown" and any(
            v is not None for v in (self.parser_name, self.parser_version, self.configuration)
        ):
            raise ValueError("Unknown legacy provenance must not invent parser identity")
        if self.origin == "recorded" and (not self.parser_name or not self.parser_version
                                          or self.configuration is None):
            raise ValueError("Recorded parser provenance requires identity and configuration")
        return self

    @property
    def id(self):
        return identity(self)

    def page_text(self, page: int, layer_id: str) -> str:
        for item in self.pages:
            if item.page == page and item.layer_id == layer_id:
                return item.text
        raise ValueError("Page/layer not in text snapshot")

    @classmethod
    def legacy(cls, artifact_id: str, pages: list[Page]):
        return cls(artifact_id=artifact_id, origin="legacy_unknown",
                   pages=[LayerPage(page=p.number, layer_id="legacy", text=p.text)
                          for p in sorted(pages, key=lambda p: p.number)])


class ScopeWindow(StrictModel):
    page: int = Field(ge=1)
    layer_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("Invalid scope window")
        return self


class ScopeBinding(StrictModel):
    scope_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    artifact_id: str
    text_snapshot_id: str
    association_version: str
    role_version: str
    role: DocumentRole
    membership: Literal["reviewed", "unresolved"] = "unresolved"
    windows: list[ScopeWindow] = Field(min_length=1)


EndpointKind = Literal["affair", "affair_document", "question", "response", "event"]


class Endpoint(StrictModel):
    kind: EndpointKind
    id: str = Field(min_length=1)


class AllowedEndpoint(Endpoint):
    scope_id: str
    event_kind: Literal["decision", "recommendation", "other", "unknown"] | None = None


class RunEnvelope(StrictModel):
    schema_version: Literal["skony.run.v0.2"] = "skony.run.v0.2"
    artifact_id: str
    text_snapshot_id: str
    model_identity: str
    prompt_identity: str
    schema_identity: str
    chunk_manifest_id: str
    scopes: list[ScopeBinding] = Field(min_length=1)
    allowed_endpoints: list[AllowedEndpoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def closed_scope(self):
        ids = [s.scope_id for s in self.scopes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scope")
        if any(s.artifact_id != self.artifact_id or s.text_snapshot_id != self.text_snapshot_id
               for s in self.scopes):
            raise ValueError("Scope does not belong to this run's artifact/text snapshot")
        endpoint_ids = [e.id for e in self.allowed_endpoints]
        if len(endpoint_ids) != len(set(endpoint_ids)):
            raise ValueError("Duplicate permitted endpoint")
        if any(e.scope_id not in ids for e in self.allowed_endpoints):
            raise ValueError("Endpoint has unknown scope")
        return self


class QuoteSegment(StrictModel):
    page: int = Field(ge=1)
    layer_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    context_anchor: str | None = Field(default=None, min_length=1)

    @field_validator("quote", "context_anchor")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Quotation and context must contain non-whitespace text")
        return value


class ProposalItem(StrictModel):
    proposal_id: str = Field(min_length=1)
    segments: list[QuoteSegment] = Field(min_length=1)


class FieldSlot(StrictModel):
    outcome: Literal["proposed", "abstained"]
    items: list[ProposalItem]
    abstention_reason: str | None

    @model_validator(mode="after")
    def disposition(self):
        if self.outcome == "abstained":
            if self.items or not self.abstention_reason or not self.abstention_reason.strip():
                raise ValueError("Abstention requires a reason and no items")
        elif not self.items or self.abstention_reason is not None:
            raise ValueError("Proposal requires items and no abstention reason")
        return self


class CoreFields(StrictModel):
    title: FieldSlot
    affair_type_raw: FieldSlot
    submitter_raw: FieldSlot
    submitted_date_raw: FieldSlot
    question_text: FieldSlot
    answer_text: FieldSlot
    decision_raw: FieldSlot
    decision_date_raw: FieldSlot


class SegmentReference(StrictModel):
    item_id: str
    segment_index: int = Field(ge=0)
    quote: str = Field(min_length=1)


class ActorProposal(StrictModel):
    proposal_id: str = Field(min_length=1)
    name: SegmentReference
    role: SegmentReference | None


class ContentProposal(StrictModel):
    proposal_id: str = Field(min_length=1)
    content: list[SegmentReference] = Field(min_length=1)
    label: SegmentReference | None


class EventProposal(StrictModel):
    proposal_id: str = Field(min_length=1)
    kind: Literal["decision", "recommendation", "other", "unknown"]
    act: list[SegmentReference] = Field(min_length=1)
    date: SegmentReference | None
    actor_ids: list[str]


class RelationProposal(StrictModel):
    proposal_id: str = Field(min_length=1)
    kind: Literal["affair_document", "question_response", "response_decision", "related_affair"]
    source: Endpoint
    target: Endpoint
    evidence: list[SegmentReference] = Field(min_length=1)
    printed_label: SegmentReference | None

    @model_validator(mode="after")
    def endpoint_types(self):
        expected = {"affair_document": ("affair", "affair_document"),
                    "question_response": ("question", "response"),
                    "response_decision": ("response", "event"),
                    "related_affair": ("affair", "affair")}
        if (self.source.kind, self.target.kind) != expected[self.kind]:
            raise ValueError("Invalid typed relation endpoints")
        if self.source.id == self.target.id:
            raise ValueError("Self-relations are not supported")
        if self.kind == "related_affair" and self.printed_label is None:
            raise ValueError("Related affairs require the printed relation label")
        return self


class TargetProposal(StrictModel):
    scope_id: str
    fields: CoreFields
    # null means not_extracted; [] means the capability ran and proposed none.
    actors: list[ActorProposal] | None
    question_items: list[ContentProposal] | None
    response_items: list[ContentProposal] | None
    events: list[EventProposal] | None
    relations: list[RelationProposal] | None


class CandidateV2(StrictModel):
    schema_version: Literal["skony.candidate.v0.2"]
    targets: list[TargetProposal] = Field(min_length=1)


class PDFRegion(StrictModel):
    # Coordinates are recorded in a rendered image coordinate system. This
    # affine PDF-to-image transform must be supplied by the renderer/reviewer.
    x: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)
    width: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    render_width: int = Field(gt=0)
    render_height: int = Field(gt=0)
    transform: list[float] = Field(min_length=6, max_length=6)
    render_identity: str = Field(min_length=1)

    @model_validator(mode="after")
    def bounded(self):
        import math
        if (self.x + self.width > self.render_width or self.y + self.height > self.render_height
                or not all(math.isfinite(v) for v in self.transform)
                or abs(self.transform[0] * self.transform[3] - self.transform[1] * self.transform[2]) < 1e-12):
            raise ValueError("Invalid recorded region or coordinate transform")
        return self


class EvidenceSegment(StrictModel):
    artifact_id: str
    text_snapshot_id: str | None
    page: int = Field(ge=1)
    layer_id: str | None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, gt=0)
    quote: str = Field(min_length=1)
    basis: Literal["text", "image"] = "text"
    match_method: Literal["exact", "whitespace_normalized"] | None = None
    region: PDFRegion | None = None
    note: str = ""

    @model_validator(mode="after")
    def capability(self):
        if not self.quote.strip():
            raise ValueError("Evidence must contain non-whitespace text")
        if self.basis == "text":
            if (self.start is None or self.end is None or self.end <= self.start
                    or not self.text_snapshot_id or not self.layer_id or not self.match_method):
                raise ValueError("Text evidence requires snapshot, layer and resolved offsets")
        elif (self.start is not None or self.end is not None or self.layer_id is not None
              or self.text_snapshot_id is not None or self.match_method is not None or not self.note.strip()):
            raise ValueError("Image evidence requires a note and must not claim text offsets")
        return self


class ResolvedItem(StrictModel):
    proposal_id: str
    value: str | None
    evidence: list[EvidenceSegment]
    evidence_outcome: Literal["located", "ambiguous_location", "not_located", "image_only"]
    reason: str | None = None
    semantic_review_required: Literal[True] = True


class ResolvedSlot(StrictModel):
    outcome: Literal["proposed", "abstained"]
    items: list[ResolvedItem]
    abstention_reason: str | None


class ResolvedTarget(StrictModel):
    scope_id: str
    fields: dict[FieldName, ResolvedSlot]
    structures: dict
    structure_status: dict[str, Literal["proposed", "not_extracted"]]


class ResolvedV2(StrictModel):
    schema_version: Literal["skony.raw.v0.2"] = "skony.raw.v0.2"
    projection_version: Literal["skony.projection.v0.2"] = PROJECTION_VERSION
    run: RunEnvelope
    targets: list[ResolvedTarget]


# This dictionary is also exported with the schemas and fixes score units.
FIELD_DICTIONARY = {
    "title": {"subject": "affair_document_scope", "cardinality": "primary_with_alternatives"},
    "affair_type_raw": {"subject": "affair_document_scope", "cardinality": "zero_or_more"},
    "submitter_raw": {"subject": "submission_scope", "cardinality": "original_block"},
    "submitted_date_raw": {"subject": "submission_event", "cardinality": "zero_or_more"},
    "question_text": {"subject": "submission_scope", "cardinality": "ordered_section"},
    "answer_text": {"subject": "specific_response_scope", "cardinality": "ordered_section"},
    "decision_raw": {"subject": "decision_event", "cardinality": "zero_or_more"},
    "decision_date_raw": {"subject": "decision_event", "cardinality": "zero_or_more"},
}
