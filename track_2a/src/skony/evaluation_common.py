"""Shared integrity checks for frozen evaluation artifacts, never human judgment."""

import json
from datetime import datetime

from .contracts import EvidenceSegment, TextSnapshot, canonical, identity


def timestamp(value: str):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Evaluation timestamps must include a timezone")
    return parsed


def seal(value: dict):
    if "digest" in value:
        raise ValueError("Cannot seal an already identified artifact")
    # Detach nested caller-owned dictionaries too: editing a later plan must
    # never mutate its calibration evidence or a previous frozen artifact.
    detached = json.loads(canonical(value))
    return {**detached, "digest": identity(detached)}


def checked(value: dict, schema: str):
    body = {k: v for k, v in value.items() if k != "digest"}
    if value.get("schema_version") != schema or value.get("digest") != identity(body):
        raise ValueError("Frozen evaluation artifact failed its identity check")
    return body


def verify_citations(evidence: list[EvidenceSegment], texts: list[TextSnapshot]):
    """Check anchors, not semantic support. Image review remains a human claim."""
    by_id = {text.id: text for text in texts}
    for segment in evidence:
        if segment.basis == "image":
            # A transcription note is not independently checked PDF content.
            raise ValueError("Evaluation evidence needs a pinned text layer; image-only evidence requires transcription first")
        text = by_id.get(segment.text_snapshot_id)
        if text is None or text.artifact_id != segment.artifact_id:
            raise ValueError("Citation refers to an unavailable source snapshot")
        page = text.page_text(segment.page, segment.layer_id)
        if not (0 <= segment.start < segment.end <= len(page)) or page[segment.start:segment.end] != segment.quote:
            raise ValueError("Citation does not match the pinned text")


def unique(values, what):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate " + what)


def ratio(n, d):
    return n / d if d else None


def link_metrics(tp, fp, fn):
    return {"tp": tp, "fp": fp, "fn": fn, "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn), "f1": ratio(2 * tp, 2 * tp + fp + fn)}
