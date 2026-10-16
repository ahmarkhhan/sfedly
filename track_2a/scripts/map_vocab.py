"""Map raw fields of an extraction result to controlled-vocabulary terms.

Reads a skony extraction result JSON (skony.raw.v0.1) and emits a mapping
record per routed field. Raw values are never modified; output is a separate,
replayable JSON compatible with review_contracts.MappingRule.

Usage:
    python scripts/map_vocab.py RESULT.json [--out MAPPINGS.json]
    python scripts/map_vocab.py output/batch/first/results/*.json --out mapped/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skony import vocab  # noqa: E402


def map_result(path: Path, vocabs: dict) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    fields = result.get("fields", {})
    raw = {name: (slot.get("value") if isinstance(slot, dict) else None)
           for name, slot in fields.items()}
    mapped = vocab.map_fields(vocabs, raw)
    return {
        "schema_version": "skony.vocab-mapping.v0.1",
        "source_result": str(path),
        "document_id": result.get("document", {}).get("document_id"),
        "mappings": {name: {
            "vocabulary_id": m.vocabulary_id,
            "vocabulary_version": m.vocabulary_version,
            "source_label": m.source_label,
            "destination": m.destination,
            "relation": m.relation,
            "rule": m.rule,
            "rationale": m.rationale,
        } for name, m in mapped.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, help="Output file (single input) or directory (multiple).")
    args = ap.parse_args()

    vocabs = vocab.load_all()
    records = [map_result(p, vocabs) for p in args.inputs]

    if args.out and len(records) > 1:
        args.out.mkdir(parents=True, exist_ok=True)
        for rec, src in zip(records, args.inputs):
            (args.out / f"{src.stem}.vocab.json").write_text(
                json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {len(records)} mapping files to {args.out}")
    else:
        payload = records[0] if len(records) == 1 else records
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        if args.out:
            args.out.write_text(text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(text)

    unmapped = sum(1 for r in records for m in r["mappings"].values()
                   if m["relation"] == "unmapped")
    total = sum(len(r["mappings"]) for r in records)
    print(f"mapped {total - unmapped}/{total} fields; {unmapped} unmapped (review queue)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
