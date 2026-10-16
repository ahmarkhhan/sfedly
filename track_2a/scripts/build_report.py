"""Rebuild ``technical_report.pdf`` from ``technical_report.md`` with reportlab.

No pandoc or network access is required; reportlab is the only dependency
beyond the pinned runtime requirements. Usage from ``track_2a/``:

    python scripts/build_report.py            # writes technical_report.pdf
    python scripts/build_report.py --check    # additionally asserts <= 6 pages

The renderer intentionally supports only the Markdown subset used by the
report: headings, paragraphs, bullet lists and pipe tables, with inline
``**bold**``, ``` ``code`` ``` and ``[text](url)`` links. Anything else raises
so a silently mis-rendered report can never be committed.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import pypdf
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGES = 6

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=13,
                      alignment=TA_LEFT, spaceAfter=5)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=15,
                    leading=19, spaceBefore=2, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=11.5,
                    leading=15, spaceBefore=10, spaceAfter=5)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", fontSize=9.8,
                    leading=13, spaceBefore=8, spaceAfter=4)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=5 * mm, spaceAfter=3)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.4, leading=11, spaceAfter=0)
CELL_HEAD = ParagraphStyle("cellhead", parent=CELL, fontName="Helvetica-Bold")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 16 * mm, 15 * mm, 15 * mm


ZWSP = "\u200b"  # zero-width space: lets long paths wrap without visible change


def _break_separators(fragment: str) -> str:
    for sep in ("/", "_", "-", "."):
        fragment = fragment.replace(sep, sep + ZWSP)
    return fragment.replace(" " + ZWSP, " ")


def inline(text: str) -> str:
    """Markdown inline subset -> reportlab paragraph XML."""
    text = html.escape(text)
    text = re.sub(r"``(.+?)``", r'<font face="Courier">\1</font>', text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Break hints inside text only, never inside tags.
    return re.sub(r"(^|>)([^<]+)", lambda m: m.group(1) + _break_separators(m.group(2)), text)

    def link(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        return f"{label} ({url})" if url.startswith(("http://", "https://")) else label

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)


def table_block(rows: list[list[str]]) -> Table:
    head, body = rows[0], rows[1:]
    cells = [[Paragraph(inline(c), CELL_HEAD) for c in head]]
    cells += [[Paragraph(inline(c), CELL) for c in row] for row in body]
    usable = PAGE_WIDTH - 2 * MARGIN_X
    padding = 8  # left + right cell padding
    char_width = CELL.fontSize * 0.55
    mins, weights = [], []
    for col in range(len(head)):
        column = [head[col]] + [r[col] for r in body]
        # Cells get zero-width break hints in inline(), so the min width tracks
        # a mid-length token, not the longest unbreakable word.
        longest_word = max(len(word) for cell in column for word in cell.split())
        mins.append(min(longest_word, 14) * char_width + padding)
        longest_cell = max(len(c) for c in column)
        weights.append(max(longest_cell, 8) ** 0.5)
    remaining = usable - sum(mins)
    if remaining < 0:
        raise ValueError(f"Table too wide for the page: {head!r}")
    total = sum(weights)
    widths = [mins[col] + remaining * weights[col] / total for col in range(len(head))]
    table = Table(cells, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa0a6")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse(markdown: str):
    flow = []
    paragraph: list[str] = []
    lines = markdown.split("\n")
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            flow.append(Paragraph(inline(" ".join(paragraph)), BODY))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                index += 1
            if any(len(r) != len(rows[0]) for r in rows):
                raise ValueError(f"Ragged table near: {rows[0]!r}")
            flow.append(table_block(rows))
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("#"):
            flush_paragraph()
            level = len(line) - len(line.lstrip("#"))
            text = line[level:].strip()
            if level == 1:
                flow.append(Paragraph(inline(text), H1))
            elif level == 2:
                flow.append(Paragraph(inline(text), H2))
            elif level == 3:
                flow.append(Paragraph(inline(text), H3))
            else:
                raise ValueError(f"Unsupported heading level: {line!r}")
            index += 1
            continue
        if line.startswith("- "):
            flush_paragraph()
            while index < len(lines) and lines[index].rstrip().startswith("- "):
                flow.append(Paragraph("&bull; " + inline(lines[index].rstrip()[2:].strip()), BULLET))
                index += 1
            continue
        if line.startswith(("```", "    ")):
            raise ValueError(f"Unsupported block (code/indented) in report: {line!r}")
        paragraph.append(line.strip())
        index += 1
    flush_paragraph()
    return flow


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#5f6368"))
    canvas.drawString(MARGIN_X, 8 * mm, "Skony - Track 2A technical report")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 8 * mm, f"page {doc.page}")
    canvas.restoreState()


def build(source: Path, target: Path) -> int:
    flow = parse(source.read_text(encoding="utf-8"))
    doc = BaseDocTemplate(str(target), pagesize=A4,
                          leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                          topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
                          title="Skony - Track 2A OpenParlData: Technical Report",
                          author="Skony team")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=footer)])
    doc.build(flow)
    return len(pypdf.PdfReader(str(target)).pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=ROOT / "technical_report.md")
    parser.add_argument("--target", type=Path, default=ROOT / "technical_report.pdf")
    parser.add_argument("--check", action="store_true", help=f"fail if the PDF exceeds {MAX_PAGES} pages")
    args = parser.parse_args()
    pages = build(args.source, args.target)
    print(f"wrote {args.target} ({pages} pages)")
    if args.check and pages > MAX_PAGES:
        print(f"report exceeds {MAX_PAGES} pages", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
