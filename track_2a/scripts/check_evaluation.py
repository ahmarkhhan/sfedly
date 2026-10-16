"""Reproduce the real-source preflight, CLI artifacts and evidence gates offline."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.cache import atomic_json
from skony.evaluation_api import schemas
from skony.evaluation_common import seal
from skony.evaluation_insights import (corpus_coverage, corpus_coverage_markdown, feasibility_matrix,
    load_baseline, matrix_markdown, novelty_report)
from skony.evaluation_protocol import review_protocol
from skony.evaluation_status import research_readiness
from skony.contracts import FIELDS, TextSnapshot, identity
from skony.study import load_cohort


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--tests-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Use a new verification directory")
    cohort = read(args.preflight / "candidate-cohort.json")
    units = load_cohort(cohort)
    structure_path = args.preflight / "structure-census.json"
    structure_census = read(structure_path) if structure_path.exists() else None
    coverage = corpus_coverage(cohort, structure_census)
    if read(args.preflight / "corpus-coverage.json") != coverage:
        raise ValueError("Offline reconstruction differed: corpus-coverage.json")
    if (args.preflight / "corpus-coverage.md").read_text(encoding="utf-8") != corpus_coverage_markdown(coverage):
        raise ValueError("Displayed corpus coverage differs from its data")
    intake = read(args.intake)
    if [u.model_dump() for u in sorted(units, key=lambda u: u.unit_id)] != sorted(intake["units"], key=lambda u: u["unit_id"]):
        raise ValueError("Intake changed after the candidate freeze")
    texts = [TextSnapshot.model_validate(t) for t in intake["texts"]]
    baseline = read(args.preflight / "metadata-baseline.json")
    load_baseline(baseline)
    protocol = review_protocol(cohort, [], [])
    novelty = novelty_report(baseline, [], texts, cohort=cohort)
    matrix = feasibility_matrix(sorted({u.body_id for u in units}), list(FIELDS), [], texts, [], [], cohort=cohort)
    readiness = research_readiness(cohort, protocol=protocol, novelty=novelty, matrix=matrix)
    for filename, actual in {"review-protocol.json": protocol, "novelty-report.json": novelty,
                             "feasibility-matrix.json": matrix, "research-readiness.json": readiness}.items():
        if read(args.preflight / filename) != actual:
            raise ValueError("Offline reconstruction differed: " + filename)
    if (args.preflight / "feasibility-matrix.md").read_text(encoding="utf-8") != matrix_markdown(matrix):
        raise ValueError("Displayed feasibility matrix differs from its data")
    if read(ROOT / "docs/evaluation-v1/input-schemas.json") != schemas():
        raise ValueError("Published evaluation schemas differ from the service")
    expected_plan = "32249cd419b72ec6dd181ff2a4e046c5b2baa7c587ac859996244b69b19aa86e"
    if hashlib.sha256((ROOT.parent / "docs/19-prototype-excellence-plan.md").read_bytes()).hexdigest() != expected_plan:
        raise ValueError("The frozen independently audited plan changed")
    tests = args.tests_log.read_text(encoding="utf-8-sig")
    found = re.search(r"Ran (\d+) tests in ([\d.]+)s", tests)
    if not found or not tests.rstrip().endswith("OK"):
        raise ValueError("No successful full test result found")
    args.out.mkdir(parents=True)
    request = {"units": cohort["units"], "policy": cohort["policy"], "links": cohort["split_links"],
               "frozen_at": cohort["frozen_at"]}
    atomic_json(args.out / "cohort-request.json", request)
    command = [sys.executable, str(ROOT / "scripts/evaluate_study.py"), "cohort", "--input",
               str((args.out / "cohort-request.json").resolve()), "--out", str((args.out / "cohort.json").resolve())]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode or read(args.out / "cohort.json") != cohort:
        raise ValueError("CLI cohort round trip failed")
    before = (args.out / "cohort.json").read_bytes()
    rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if rejected.returncode != 2 or (args.out / "cohort.json").read_bytes() != before:
        raise ValueError("CLI did not preserve existing frozen output")
    files = [*sorted((ROOT / "src/skony").glob("*.py")), ROOT / "scripts/evaluate_study.py",
             ROOT / "scripts/prepare_evaluation.py", Path(__file__).resolve(), args.tests_log,
             ROOT / "docs/evaluation-v1/input-schemas.json", args.preflight / "research-readiness.json"]
    if structure_path.exists():
        files.append(structure_path)
    proof = seal({"schema_version": "skony.evaluation-verification.v1", "timezone": "Asia/Karachi",
        "verification_date": "2026-10-16", "tests": {"count": int(found[1]), "seconds": float(found[2]), "result": "OK"},
        "source_rows": len(units), "pinned_pdfs": sum(u.source_status == "ready" for u in units),
        "failed_sources_retained": sum(u.source_status == "failed" for u in units),
        "offline_reconstruction_matches": True, "cli_round_trip_matches": True, "existing_output_rejected_unchanged": True,
        "schemas_match_code": True, "audited_plan_unchanged": expected_plan,
        "new_live_calls": 0, "new_human_annotations": 0, "research_readiness": readiness,
        "live_capacity_probe": {"status": "blocked_by_automatic_approval_review", "maximum_prepared_calls": 4,
            "reason": "External transmission of identified locally stored PDF text requires explicit payload/destination approval"},
        "file_sha256": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}})
    atomic_json(args.out / "proof.json", proof)
    print(json.dumps({"python_tests": proof["tests"]["count"], "offline_reconstruction_matches": True,
        "new_live_calls": 0, "new_human_annotations": 0, "proof": str(args.out / "proof.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
