"""Read PDF text with stable per-page offsets; do not silently OCR scans."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .schema import Document, Page


def read_pdf(path: Path) -> Document:
    return parse_pdf(path.read_bytes(), path.name)


def parse_pdf(contents: bytes, filename: str) -> Document:
    """Parse and hash one immutable byte snapshot."""
    if len(contents) > 25 * 1024 * 1024:
        raise ValueError("PDF exceeds this prototype's 25 MB input limit")
    reader = PdfReader(BytesIO(contents))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs require an unlocked local copy")
    if not reader.pages or len(reader.pages) > 60:
        raise ValueError("This prototype accepts PDFs containing 1–60 pages")
    pages = [Page(number=i + 1, text=page.extract_text() or "") for i, page in enumerate(reader.pages)]
    digest = sha256(contents).hexdigest()
    return Document(
        document_id=digest,
        filename=filename,
        sha256=digest,
        pages=pages,
        textless_pages=[p.number for p in pages if not p.text.strip()],
    )

