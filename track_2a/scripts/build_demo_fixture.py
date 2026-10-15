"""Rebuild Skony's authored engineering example; no inference or source scraping."""

import json
from hashlib import sha256
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "sample"


def build():
    lines = (DIRECTORY / "synthetic-request.txt").read_text(encoding="utf-8").splitlines()
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    })
    commands = ["BT /F1 10 Tf 15 TL 36 804 Td"]
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj T*")
    commands.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "Synthetic engineering fixture - not a real parliamentary record"})
    pdf = DIRECTORY / "synthetic-request.pdf"
    writer.write(pdf)
    manifest = {
        "fixture_id": "skony.synthetic.request.v1",
        "kind": "synthetic_engineering_fixture",
        "source": "Authored for Skony; no real parliamentary record or person",
        "language": "de",
        "licence": "CDLA-Permissive-2.0",
        "candidate_origin": "Authored engineering suggestions; not model output or human gold",
        "pdf_sha256": sha256(pdf.read_bytes()).hexdigest(),
        "candidate_sha256": sha256((DIRECTORY / "candidate.json").read_bytes()).hexdigest(),
    }
    (DIRECTORY / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Built the labelled synthetic fixture and checksum manifest")


if __name__ == "__main__":
    build()
