"""Input coverage, generation status and section completeness are independent."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StrictModel, identity


class Chunk(StrictModel):
    id: str
    pages: list[int] = Field(min_length=1)


class ChunkManifest(StrictModel):
    available_pages: list[int] = Field(min_length=1)
    selected_pages: list[int] = Field(min_length=1)
    chunks: list[Chunk] = Field(min_length=1)
    selection_policy: str = Field(min_length=1)

    @model_validator(mode="after")
    def coverage(self):
        for pages in [self.available_pages, self.selected_pages] + [c.pages for c in self.chunks]:
            if pages != sorted(set(pages)) or min(pages) < 1:
                raise ValueError("Pages must be unique, positive and ordered")
        if not set(self.selected_pages).issubset(self.available_pages):
            raise ValueError("Selected page is unavailable")
        if len({c.id for c in self.chunks}) != len(self.chunks):
            raise ValueError("Duplicate chunk ID")
        if {p for c in self.chunks for p in c.pages} != set(self.selected_pages):
            raise ValueError("Chunk manifest must cover exactly the selected pages")
        return self

    @property
    def id(self):
        return identity(self)


class ChunkOutcome(StrictModel):
    chunk_id: str
    state: Literal["completed", "failed", "interrupted", "unsupported", "cancelled"]
    finish_reason: str | None
    response_valid: bool
    raw_response_digest: str | None = None


class SectionCheck(StrictModel):
    # An application-recorded human check, never a model output key.
    reviewer: str = Field(min_length=1)
    note: str = Field(min_length=1)
    scope_identity: str
    assertion_identity: str
    boundary_checked: bool
    required_clauses_checked: bool
    complete: bool


def assess_completeness(manifest: ChunkManifest, outcomes: list[ChunkOutcome], *,
                        scope_identity: str, assertion_identity: str,
                        unsatisfied_continuation: bool = False,
                        check: SectionCheck | None = None):
    expected = {c.id for c in manifest.chunks}
    reported = {o.chunk_id for o in outcomes}
    if len(reported) != len(outcomes) or not reported.issubset(expected):
        raise ValueError("Duplicate or unknown chunk outcome")
    missing = sorted(expected - reported)
    successful = {o.chunk_id for o in outcomes if o.state == "completed"}
    processed = sorted({p for c in manifest.chunks if c.id in successful for p in c.pages})
    generation_incomplete = any(o.state != "completed" or not o.response_valid or
                                o.finish_reason not in {"stop", None} for o in outcomes)
    generation = ("incomplete" if missing or generation_incomplete else
                  "unknown" if any(o.finish_reason is None for o in outcomes) else "complete")
    reasons = []
    if missing:
        reasons.append("missing_scheduled_chunk")
    if generation_incomplete:
        reasons.append("failed_invalid_or_truncated_generation")
    if unsatisfied_continuation:
        reasons.append("unsatisfied_continuation")
    if check and (check.scope_identity != scope_identity or check.assertion_identity != assertion_identity):
        raise ValueError("Section check belongs to different scope/assertion")
    if check and not check.complete:
        reasons.append("human_incomplete_section")
    semantic = "incomplete" if reasons else "unknown"
    if not reasons and check and check.complete and check.boundary_checked and check.required_clauses_checked:
        semantic = "complete_in_reviewed_scope"
    return {"manifest_id": manifest.id,
            "input_coverage": {"available_pages": manifest.available_pages,
                               "selected_pages": manifest.selected_pages, "processed_pages": processed,
                               "unselected_pages": sorted(set(manifest.available_pages) - set(manifest.selected_pages)),
                               "missing_chunks": missing, "all_selected_processed": not missing and successful == expected},
            "generation_completion": generation, "chunk_outcomes": [o.model_dump() for o in sorted(outcomes, key=lambda o: o.chunk_id)],
            "semantic_completeness": semantic, "reasons": reasons,
            "section_check": check.model_dump() if check else None}
