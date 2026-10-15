"""Local A1–A7 utilities. No credential loading, network access or model calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skony.cache import atomic_json
from skony.comparison import query_snapshot
from skony.contracts import FIELD_DICTIONARY, PROJECTION_VERSION, RunEnvelope
from skony.gold import GoldUnit, Prediction, export_gold_v2, score
from skony.migration import migrate
from skony.pipeline_v2 import candidate_schema
from skony.review import ReviewStore
from skony.review_contracts import ComparisonSpec, ReviewInput


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    schemas = commands.add_parser("schemas")
    schemas.add_argument("--out", type=Path, default=Path("docs/contracts-v0.2"))
    migration = commands.add_parser("migrate")
    migration.add_argument("--store", type=Path, required=True)
    migration.add_argument("--source-manifest", type=Path, action="append", default=[])
    migration.add_argument("--report", type=Path, required=True)
    scorer = commands.add_parser("score")
    scorer.add_argument("--gold", type=Path, required=True, help="JSON array of v0.2 GoldUnit objects")
    scorer.add_argument("--predictions", type=Path, required=True)
    scorer.add_argument("--cohort", type=Path, required=True, help="Frozen JSON array of artifact:scope unit IDs")
    scorer.add_argument("--out", type=Path, required=True)
    gold = commands.add_parser("export-gold")
    gold.add_argument("--annotations", type=Path, required=True)
    gold.add_argument("--out", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("--snapshot", type=Path, required=True)
    comparison.add_argument("--spec", type=Path, required=True)
    comparison.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "schemas":
        for name, schema in {"candidate": candidate_schema(), "run": RunEnvelope.model_json_schema(),
                             "review": ReviewInput.model_json_schema(), "gold": GoldUnit.model_json_schema(),
                             "comparison": ComparisonSpec.model_json_schema(),
                             "field-dictionary": {"projection_version": PROJECTION_VERSION,
                                "scoring_unit": "document artifact + explicit target scope",
                                "fields": FIELD_DICTIONARY}}.items():
            atomic_json(args.out / (name + ".schema.json"), schema)
        print("Saved six versioned contract artifacts.")
    elif args.command == "migrate":
        if not (args.store / "review.sqlite3").is_file():
            parser.error("The existing review database was not found")
        report = migrate(ReviewStore(args.store), source_manifests=args.source_manifest)
        atomic_json(args.report, report)
        print(json.dumps({k: report[k] for k in ("before", "after", "backup_directory", "legacy_text_snapshots",
                                               "legacy_reviews_preserved", "manifest_source_records_recovered")}, indent=2))
    elif args.command == "score":
        result = score([GoldUnit.model_validate(g) for g in read(args.gold)],
                       [Prediction.model_validate(p) for p in read(args.predictions)], frozen_unit_ids=read(args.cohort))
        atomic_json(args.out, result)
        print("Saved deterministic field counts, status denominators and independent sensitivity results.")
    elif args.command == "export-gold":
        export_gold_v2([GoldUnit.model_validate(g) for g in read(args.annotations)], args.out)
        print("Exported supplied annotations with their original quality status; no new labels were created.")
    elif args.command == "compare":
        snapshot = read(args.snapshot)
        result = query_snapshot(snapshot.get("snapshot", snapshot), ComparisonSpec.model_validate(read(args.spec)))
        atomic_json(args.out, result)
        print("Reproduced comparison from the frozen closure without a database or model call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
