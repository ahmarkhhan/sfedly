"""Expose only the citation interaction supported by recorded evidence."""

from .contracts import EvidenceSegment, TextSnapshot


def citation(segment: EvidenceSegment, snapshot: TextSnapshot | None = None):
    target = {"artifact_id": segment.artifact_id, "page": segment.page,
              "quote": segment.quote, "note": segment.note}
    if segment.basis == "text":
        if snapshot is None or snapshot.id != segment.text_snapshot_id or snapshot.artifact_id != segment.artifact_id:
            raise ValueError("Citation text snapshot is missing or mismatched")
        page = snapshot.page_text(segment.page, segment.layer_id)
        if page[segment.start:segment.end] != segment.quote:
            raise ValueError("Citation does not resolve in the frozen text")
        # Include the authoritative code-point offsets and conversion for clients
        # indexing UTF-16 strings. Combining characters are intentionally kept.
        utf16_start = len(page[:segment.start].encode("utf-16-le")) // 2
        utf16_end = len(page[:segment.end].encode("utf-16-le")) // 2
        target.update(capability="text_highlight", text_snapshot_id=snapshot.id,
                      layer_id=segment.layer_id, start=segment.start, end=segment.end,
                      utf16_start=utf16_start, utf16_end=utf16_end)
    elif segment.region:
        target.update(capability="pdf_region", region=segment.region.model_dump(),
                      label="Recorded image region with human transcription")
    else:
        target.update(capability="page_transcription",
                      label="Page and human transcription; no region coordinates recorded")
    return target
