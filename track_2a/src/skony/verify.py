"""Locate source evidence without altering words, punctuation or page attribution."""

import re

from .schema import CandidateField, Document, LocatedField, Provenance


def abstain(reason: str) -> LocatedField:
    return LocatedField(value=None, status="abstained", provenance=None, reason=reason)


def whitespace_view(text: str) -> tuple[str, list[tuple[int, int]]]:
    characters = []
    offsets = []
    for token in re.finditer(r"\s+|\S+", text):
        if token.group().isspace():
            if characters:
                characters.append(" ")
                offsets.append((token.start(), token.end()))
        else:
            for index in range(token.start(), token.end()):
                characters.append(text[index])
                offsets.append((index, index + 1))
    if characters and characters[-1] == " ":
        characters.pop()
        offsets.pop()
    return "".join(characters), offsets


def find_span(text: str, needle: str, *, unique: bool = True):
    start = text.find(needle)
    if start >= 0:
        if unique and text.find(needle, start + 1) >= 0:
            return None, "ambiguous_quote"
        return (start, start + len(needle), "exact"), None
    normalized, offsets = whitespace_view(text)
    requested, _ = whitespace_view(needle)
    if not requested:
        return None, "empty_quote"
    start = normalized.find(requested)
    if start < 0:
        return None, "quote_not_found_on_claimed_page"
    if unique and normalized.find(requested, start + 1) >= 0:
        return None, "ambiguous_quote"
    return (offsets[start][0], offsets[start + len(requested) - 1][1], "whitespace_normalized"), None


def locate(field: CandidateField, document: Document, field_name: str | None = None) -> LocatedField:
    if field.value is None:
        return abstain("model_abstained")
    page = next((p for p in document.pages if p.number == field.page), None)
    if page is None:
        return abstain("page_not_found")
    if not page.text.strip():
        return abstain("page_has_no_text")
    quote = field.quote
    assert quote is not None
    span, reason = find_span(page.text, quote)
    if span is None:
        return abstain(reason)
    start, end, match_method = span
    original_quote = page.text[start:end]
    value_span, _ = find_span(original_quote, field.value, unique=False)
    if value_span is None:
        return abstain("value_not_in_quote")
    value_start, value_end, value_method = value_span
    original_value = original_quote[value_start:value_end]
    if field_name == "submitter_raw" and re.search(r"~{2,}|\ufffd", original_value):
        return abstain("submitter_contains_ocr_noise")
    if value_method == "whitespace_normalized":
        match_method = "whitespace_normalized"
    return LocatedField(
        value=original_value,
        status="source_located",
        provenance=Provenance(
            document_id=document.document_id,
            page=page.number,
            start=start,
            end=end,
            quote=original_quote,
            match_method=match_method,
        ),
        reason=None,
    )

