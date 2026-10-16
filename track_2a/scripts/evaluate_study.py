"""Versioned B1–B7 evaluation tooling. All operations default to offline replay."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skony.cache import atomic_json
from skony.client import Settings
from skony.contracts import TextSnapshot
from skony.evaluation_api import OPERATIONS, evaluate, schemas
from skony.evaluation_insights import corpus_coverage_markdown, matrix_markdown
from skony.experiments import ExperimentInput, run_experiment, run_variants
from skony.relations import relation_packet
from skony.study import field_packet, inspect_manifest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=[*OPERATIONS, "inspect", "schemas", "relation-packet", "field-packet",
                                              "experiment-calibrate", "experiment-run"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fetch-dir", type=Path)
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--mode", choices=["live", "replay"], default="replay")
    parser.add_argument("--maximum-calls", type=int, default=0)
    parser.add_argument("--cache", type=Path, default=Path("output/evaluation-cache"))
    parser.add_argument("--structure-census", type=Path,
                        help="Optional structural-census JSON for the coverage operation")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Choose a new output path; frozen evidence is never overwritten")
    if args.operation == "inspect":
        if not args.fetch_dir:
            parser.error("inspect needs --fetch-dir")
        result = inspect_manifest(args.fetch_dir)
    elif args.operation == "schemas":
        result = schemas()
    else:
        if not args.input:
            parser.error("This operation needs --input")
        data = read(args.input)
        if args.operation == "coverage" and data.get("schema_version") == "skony.study-cohort.v1":
            data = {"cohort": data}
        if args.operation == "coverage" and args.structure_census:
            if "cohort" not in data:
                data = {"cohort": data}
            data["structure_census"] = read(args.structure_census)
        if args.operation == "relation-packet":
            if not args.reviewer.strip():
                parser.error("Name the independent reviewer with --reviewer")
            result = relation_packet(data, args.reviewer)
        elif args.operation == "field-packet":
            if not args.reviewer.strip():
                parser.error("Name the independent reviewer with --reviewer")
            result = field_packet(data["cohort"], [TextSnapshot.model_validate(t) for t in data["texts"]], args.reviewer)
        elif args.operation in {"experiment-calibrate", "experiment-run"}:
            inputs = [ExperimentInput.model_validate(i) for i in data["inputs"]]
            if args.mode == "live":
                if args.maximum_calls < 1:
                    parser.error("Live execution requires an explicit positive --maximum-calls budget")
                from skony.__main__ import load_env
                load_env(Path(__file__).resolve().parents[1] / ".env")
                settings = Settings.from_environment()
            else:
                config = data.get("plan", data)
                settings = Settings(config["model"], config["endpoint"], "")
            if args.operation == "experiment-calibrate":
                result = run_variants(inputs, settings, caps=data["caps"], cache=args.cache, mode=args.mode,
                                      maximum_calls=args.maximum_calls)
            else:
                result = run_experiment(data["plan"], data["cohort"], inputs, settings, cache=args.cache,
                                        mode=args.mode, maximum_calls=args.maximum_calls)
        else:
            result = evaluate(args.operation, data)
    atomic_json(args.out, result)
    if args.operation == "feasibility":
        args.out.with_suffix(".md").write_text(matrix_markdown(result), encoding="utf-8")
    elif args.operation == "coverage":
        args.out.with_suffix(".md").write_text(corpus_coverage_markdown(result), encoding="utf-8")
    print(json.dumps({"operation": args.operation, "output": str(args.out),
                      "passed": result.get("passed", result.get("gate_passed")),
                      "live_calls": result.get("live_calls", result.get("recordings", {}).get("live_calls", 0))}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as error:
        print("Evaluation input or artifact rejected: " + str(error), file=sys.stderr)
        raise SystemExit(2)
