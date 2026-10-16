"""Resolve an unambiguous supporting passage to the displayed PDF page.

Coordinates are presentation metadata, never extraction or review decisions.
Only whitespace differences are tolerated; uncertain geometry stays unavailable.
"""

from pathlib import Path

import pymupdf

from .verify import find_span, whitespace_view


def passage_regions(path: Path, page_number: int, quote: str) -> dict:
    unavailable = {"status": "unavailable", "regions": [],
                   "reason": "The passage could not be positioned uniquely on the PDF. Use extracted text."}
    if page_number < 1 or not quote or not quote.strip():
        return unavailable
    try:
        with pymupdf.open(path) as pdf:
            page = pdf[page_number - 1]
            characters, boxes, lines = [], [], []
            for block in page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]:
                for line in block.get("lines", []):
                    line_id = len(lines)
                    lines.append(line)
                    for span in line["spans"]:
                        for char in span["chars"]:
                            # Some glyphs expand to multiple Unicode code points.
                            for value in char["c"]:
                                characters.append(value)
                                boxes.append((line_id, char["bbox"]))
                    characters.append("\n")
                    boxes.append(None)
            normalized, offsets = whitespace_view("".join(characters))
            requested, _ = whitespace_view(quote)
            match, _ = find_span(normalized, requested)
            if match is None:
                return unavailable
            matched_start, matched_end, _ = match
            start, end = offsets[matched_start][0], offsets[matched_end - 1][1]
            grouped = {}
            for index in range(start, end):
                if boxes[index] is None or characters[index].isspace():
                    continue
                line_id, bbox = boxes[index]
                rect = pymupdf.Rect(bbox) * page.rotation_matrix
                rect = rect & page.rect
                if rect.is_empty or rect.is_infinite:
                    return unavailable
                grouped[line_id] = grouped[line_id] | rect if line_id in grouped else rect
            if not grouped:
                return unavailable
            width, height = page.rect.width, page.rect.height
            return {"status": "located", "regions": [
                {"x": rect.x0 / width, "y": rect.y0 / height,
                 "width": rect.width / width, "height": rect.height / height}
                for rect in grouped.values()], "reason": None}
    except (RuntimeError, ValueError, IndexError, OSError):
        return unavailable
