"""First extraction slice: raw source fields, without inferred categories."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Page(StrictModel):
    number: int = Field(ge=1)
    text: str


class Document(StrictModel):
    document_id: str
    filename: str
    sha256: str
    pages: list[Page] = Field(min_length=1)
    textless_pages: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_pages(self):
        numbers = [page.number for page in self.pages]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Page numbers must be unique")
        return self


class CandidateField(StrictModel):
    value: str | None
    page: int | None = Field(ge=1)
    quote: str | None

    @model_validator(mode="after")
    def complete_evidence(self):
        if self.value is None:
            if self.page is not None or self.quote is not None:
                raise ValueError("Abstained fields must have null page and quote")
        elif self.page is None or not self.quote or not self.value.strip():
            raise ValueError("Non-null values require a page and nonempty quote")
        return self


class CandidateExtraction(StrictModel):
    title: CandidateField
    affair_type_raw: CandidateField
    submitter_raw: CandidateField
    submitted_date_raw: CandidateField
    question_text: CandidateField
    answer_text: CandidateField
    decision_raw: CandidateField
    decision_date_raw: CandidateField


class Provenance(StrictModel):
    document_id: str
    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str
    match_method: Literal["exact", "whitespace_normalized"] = "exact"


class LocatedField(StrictModel):
    value: str | None
    status: Literal["source_located", "abstained"]
    provenance: Provenance | None
    reason: str | None
    semantic_review_required: Literal[True] = True


class ExtractionResult(StrictModel):
    schema_version: Literal["skony.raw.v0.1"] = "skony.raw.v0.1"
    document: Document
    model_name: str
    prompt_version: str
    verifier_version: str = "evidence-v0.2"
    fields: dict[str, LocatedField]
    usage: dict[str, int] = Field(default_factory=dict)
    latency_seconds: float = Field(ge=0)
    state: Literal["needs_human_review"] = "needs_human_review"

