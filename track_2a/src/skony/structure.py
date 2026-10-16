"""Structural content inventory: annexes, embedded images, table hints.

Conservative *inventory, not interpretation*: this module records that a
document carries annexes, embedded raster images, or table-like text regions,
each with page + span provenance against the unchanged extracted page text.
It never reconstructs values from layout and never OCRs. Anything it cannot
locate verbatim is recorded as a limitation, not guessed.

Design rules matching the rest of the pipeline:
- detection only, deterministic, no model involvement;
- every item carries its method label so downstream users know exactly how
  it was found (and what it does not cover);
- output is a separate attached artifact (``skony.structure-inventory.v0.1``),
  never part of the cached extraction payload, so replay identity is
  unaffected.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .schema import Document

SCHEMA_VERSION = "skony.structure-inventory.v0.1"
METHOD_ANNEX = "line-anchored-marker-v1"
METHOD_IMAGE = "pypdf-xobject-v1"
METHOD_TABLE = "text-grid-heuristic-v1"

# Annex markers as printed by Swiss bodies. Line-anchored and restricted to
# marker + optional number/letter + short label tail to avoid body-text
# mentions ("siehe Annexe 2" mid-sentence is NOT an annex heading).
_ANNEX_MARKER = re.compile(
    r"^(?P<label>(?P<marker>annexe|beilage|anhang|allegato|annex)"
    r"(?P<num>\s*(?:nr\.?\s*)?[0-9]{0,2}[a-z]?)"
    r"(?P<tail>\s*[:\-.–]?\s*[^\n]{0,80})?)$",
    re.IGNORECASE | re.MULTILINE,
)

_TABLE_KEYWORD = re.compile(r"\b(CHF|Fr\.|Total|Summe|total|Budget|Voranschlag|Rechnung)\b")
_DIGIT_DENSE = re.compile(r"^\s*[-+’'\d][\d\s’'.,\-+]*\d\s*$")


@dataclass(frozen=True)
class AnnexItem:
    label: str
    page: int
    start: int
    end: int
    quote: str
    textless_page: bool
    method: str = METHOD_ANNEX


@dataclass(frozen=True)
class ImageItem:
    page: int
    name: str
    width: int | None
    height: int | None
    method: str = METHOD_IMAGE


@dataclass(frozen=True)
class TableHint:
    page: int
    start: int
    end: int
    reason: str
    method: str = METHOD_TABLE


@dataclass(frozen=True)
class StructureInventory:
    schema_version: str
    document_id: str
    annexes: list[AnnexItem] = field(default_factory=list)
    images: list[ImageItem] = field(default_factory=list)
    table_hints: list[TableHint] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def annex_inventory(document: Document) -> list[AnnexItem]:
    """Detect annex headings in extracted page text (line-anchored only)."""
    items: list[AnnexItem] = []
    textless = set(document.textless_pages)
    for page in document.pages:
        for match in _ANNEX_MARKER.finditer(page.text):
            label = " ".join(match.group("label").split())
            # Bare word "annex" alone on a line is weak; require a number or tail.
            if not match.group("num").strip() and not (match.group("tail") or "").strip():
                continue
            items.append(AnnexItem(
                label=label,
                page=page.number,
                start=match.start("label"),
                end=match.end("label"),
                quote=page.text[match.start("label"):match.end("label")],
                textless_page=page.number in textless,
            ))
    return items


def image_inventory(document: Document, pdf_bytes: bytes | None) -> list[ImageItem]:
    """Enumerate /XObject raster images per page. Shallow by design: inline
    BI/EI images and SMasks are not counted; the method label says so."""
    if pdf_bytes is None:
        return []
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        return []
    items: list[ImageItem] = []
    for number, page in enumerate(reader.pages, 1):
        try:
            xobjects = (page.get("/Resources") or {}).get("/XObject") or {}
            xobjects = xobjects.get_object()
        except Exception:
            continue
        for name, ref in xobjects.items():
            try:
                obj = ref.get_object()
                if obj.get("/Subtype") != "/Image":
                    continue
                width, height = obj.get("/Width"), obj.get("/Height")
                items.append(ImageItem(
                    page=number,
                    name=str(name),
                    width=int(width) if width is not None else None,
                    height=int(height) if height is not None else None,
                ))
            except Exception:
                items.append(ImageItem(page=number, name=str(name), width=None, height=None))
    return items


def table_hints(document: Document) -> list[TableHint]:
    """Detect table-like text regions without parsing cells. A region qualifies
    when it has >=3 lines each carrying either a wide whitespace gap (column
    gap of 2+ spaces between non-space runs) plus digit-dense content, or a
    table keyword co-occurring with digit-dense lines."""
    hints: list[TableHint] = []
    for page in document.pages:
        lines = page.text.splitlines(keepends=True)
        offsets, pos = [], 0
        for line in lines:
            offsets.append(pos)
            pos += len(line)
        run_start, run_count = None, 0
        for idx, line in enumerate(lines):
            text = line.rstrip("\n")
            has_gap = bool(re.search(r"\S\s{2,}\S", text))
            digit_lines = bool(_DIGIT_DENSE.match(text)) or (
                has_gap and bool(re.search(r"\d", text)))
            keyword = bool(_TABLE_KEYWORD.search(text))
            qualifies = (has_gap and digit_lines) or (keyword and digit_lines)
            if qualifies:
                if run_start is None:
                    run_start = idx
                run_count += 1
            else:
                if run_count >= 3 and run_start is not None:
                    start = offsets[run_start]
                    end = offsets[idx - 1] + len(lines[idx - 1].rstrip("\n"))
                    hints.append(TableHint(page=page.number, start=start, end=end,
                                           reason=f"{run_count} column-gap/digit-dense lines"))
                run_start, run_count = None, 0
        if run_count >= 3 and run_start is not None:
            start = offsets[run_start]
            end = offsets[len(lines) - 1] + len(lines[-1].rstrip("\n"))
            hints.append(TableHint(page=page.number, start=start, end=end,
                                   reason=f"{run_count} column-gap/digit-dense lines"))
    return hints


def build_inventory(document: Document, pdf_bytes: bytes | None = None) -> StructureInventory:
    limitations = [
        "tables: detected as text-grid hints only; cells are not parsed and "
        "borderless or multi-page tables may be missed",
        "images: only /XObject raster resources are counted; inline images and "
        "vector graphics are not",
        "annexes: detected via line-anchored printed markers; unmarked "
        "attachments are not detected",
        "textless pages are not OCRed by design",
    ]
    return StructureInventory(
        schema_version=SCHEMA_VERSION,
        document_id=document.document_id,
        annexes=annex_inventory(document),
        images=image_inventory(document, pdf_bytes),
        table_hints=table_hints(document),
        limitations=limitations,
    )


def inventory_json(inv: StructureInventory) -> str:
    return json.dumps(asdict(inv), ensure_ascii=False, indent=2)


def inventory_file(document: Document, path: Path) -> StructureInventory:
    pdf_bytes = path.read_bytes() if path.suffix.lower() == ".pdf" and path.exists() else None
    return build_inventory(document, pdf_bytes)
