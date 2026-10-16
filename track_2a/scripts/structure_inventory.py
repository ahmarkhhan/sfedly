"""Structural census over the private PDF corpus (keyless, no model calls).

Reads the gold fetch manifest, parses every downloaded PDF, and writes one
``skony.structure-inventory.v0.1`` artifact per document plus a corpus-level
summary aggregated by body and language. The summary is evidence: it
quantifies which bodies/languages carry annexes, embedded images, table-like
regions and textless (scan) pages.

Usage (from track_2a/):
    python scripts/structure_inventory.py --manifest data/private/gold/fetch_manifest.json --out output/structure-census
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skony import structure  # noqa: E402
from skony.pdf import read_pdf  # noqa: E402


def _bucket(rows: list[dict], key: str) -> dict:
    out: dict[str, Counter] = {}
    for row in rows:
        c = out.setdefault(str(row.get(key) or "unknown"), Counter())
        c["docs"] += 1
        for field in ("annexes", "images", "table_hints", "textless_pages", "pages"):
            c[field] += row[field]
        c["docs_with_annexes"] += bool(row["annexes"])
        c["docs_with_images"] += bool(row["images"])
        c["docs_with_table_hints"] += bool(row["table_hints"])
        c["docs_with_textless_pages"] += bool(row["textless_pages"])
    return {k: dict(v) for k, v in sorted(out.items())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = manifest.get("documents") or manifest.get("entries") or []
    base = args.manifest.parent

    args.out.mkdir(parents=True, exist_ok=True)
    inv_dir = args.out / "inventories"
    inv_dir.mkdir(exist_ok=True)

    summary_rows, failures = [], []
    counters = Counter()

    for entry in entries:
        rel = entry.get("document_file") or entry.get("path") or entry.get("file")
        status = entry.get("status", "fetched")
        if not rel or status not in ("fetched", "cached", "downloaded", "ok", "success"):
            failures.append({"entry": rel or entry.get("name", "?"), "reason": f"fetch status {status}"})
            counters["fetch_failed"] += 1
            continue
        pdf_path = base / rel
        if not pdf_path.exists():
            failures.append({"entry": rel, "reason": "file missing"})
            counters["missing_file"] += 1
            continue
        try:
            document = read_pdf(pdf_path)
            inv = structure.inventory_file(document, pdf_path)
        except Exception as exc:
            failures.append({"entry": rel, "reason": f"{type(exc).__name__}: {exc}"})
            counters["parse_failed"] += 1
            continue

        (inv_dir / f"{pdf_path.stem}.json").write_text(
            structure.inventory_json(inv), encoding="utf-8")

        row = {
            "file": rel,
            "body": entry.get("body_label") or entry.get("body_key"),
            "language": entry.get("language"),
            "category": entry.get("category"),
            "document_id": document.document_id,
            "pages": len(document.pages),
            "textless_pages": len(document.textless_pages),
            "annexes": len(inv.annexes),
            "images": len(inv.images),
            "table_hints": len(inv.table_hints),
        }
        summary_rows.append(row)
        counters["processed"] += 1
        counters["docs_with_annexes"] += bool(row["annexes"])
        counters["docs_with_images"] += bool(row["images"])
        counters["docs_with_table_hints"] += bool(row["table_hints"])
        counters["docs_with_textless_pages"] += bool(row["textless_pages"])
        counters["total_annexes"] += row["annexes"]
        counters["total_images"] += row["images"]
        counters["total_pages"] += row["pages"]

    summary = {
        "schema_version": "skony.structure-census.v0.1",
        "manifest": str(args.manifest),
        "counts": dict(counters),
        "by_body": _bucket(summary_rows, "body"),
        "by_language": _bucket(summary_rows, "language"),
        "failures": failures,
        "documents": summary_rows,
        "method_note": "Inventory, not interpretation: annex markers are "
                       "line-anchored prints; images are /XObject rasters; "
                       "table hints are text-grid heuristics. No OCR, no cell "
                       "parsing, no model calls.",
    }
    out_file = args.out / "census.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary["counts"], indent=2))
    print(json.dumps(summary["by_body"], indent=2, ensure_ascii=False))
    print(f"failures: {len(failures)}; census written to {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
