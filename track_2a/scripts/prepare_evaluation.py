"""Prepare a real-source preflight and blind intake packet without inventing reviews."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skony.cache import atomic_json
from skony.client import Settings
from skony.contracts import FIELDS, RunEnvelope, ScopeBinding, ScopeWindow, TextSnapshot, identity
from skony.evaluation_common import seal
from skony.evaluation_insights import (corpus_coverage, corpus_coverage_markdown, feasibility_matrix,
    matrix_markdown, metadata_baseline, novelty_report)
from skony.evaluation_protocol import review_protocol
from skony.experiments import ExperimentInput
from skony.pipeline_v2 import PROMPT_ID, candidate_schema, chunk_manifest
from skony.study import StudyPolicy, StudyUnit, freeze_cohort
from skony.evaluation_status import research_readiness


def prepare(intake, *, metadata_paths, model, endpoint, recorded_at, structure_census=None):
    units = [StudyUnit.model_validate(u) for u in intake["units"]]
    texts = [TextSnapshot.model_validate(t) for t in intake["texts"]]
    cohort = freeze_cohort(units, StudyPolicy(), frozen_at=recorded_at)
    coverage = corpus_coverage(cohort, structure_census)
    matrix = feasibility_matrix(sorted({u.body_id for u in units}), list(FIELDS), [], texts, [], [], cohort=cohort)
    packet = {"schema_version": "skony.intake-review-packet.v1", "candidate_cohort_digest": cohort["digest"],
        "model_proposals_included": False, "human_reviews_created": 0,
        "instruction": "Verify original PDFs, actual language, scoped role and namespaced affair membership. Fill review records; do not treat hints as verification.",
        "units": [u.model_dump() for u in units], "texts": [t.model_dump() for t in texts]}
    snapshots = []
    for path in metadata_paths:
        raw = path.read_bytes()
        rows = [json.loads(line) for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
        snapshots.append({"source_path": str(path.resolve()), "file_sha256": hashlib.sha256(raw).hexdigest(), "records": rows})
    baseline = metadata_baseline({"saved_api_samples": snapshots},
        question="Which conditions accompany executive responses, and which linked parliamentary decisions follow them?",
        source_reference="Retained OpenParlData API samples; sample coverage is not a complete API capability audit",
        queries={"existing_source_text": "/saved_api_samples/0/records/0/text",
                 "existing_affair_link": "/saved_api_samples/0/records/0/affair_id",
                 "response_decision_alignment": "/saved_api_samples/0/records/0/response_decision_alignment"},
        recorded_at=recorded_at)
    protocol = review_protocol(cohort, [], [])
    novelty = novelty_report(baseline, [], texts, cohort=cohort)
    readiness = research_readiness(cohort, protocol=protocol, novelty=novelty, matrix=matrix)
    by_artifact = {t.artifact_id: t for t in texts}
    selected, inputs = [], []
    for language in ("de", "fr"):
        choices = [u for u in units if u.source_status == "ready" and u.language_hint == language
                   and 300 <= sum(len(p.text) for p in by_artifact[u.artifact_id].pages) <= 10000
                   and len(by_artifact[u.artifact_id].pages) <= 4]
        if not choices:
            continue
        unit = sorted(choices, key=lambda u: (u.role_hint != "response", len(by_artifact[u.artifact_id].pages), u.unit_id))[0]
        text = by_artifact[unit.artifact_id]
        manifest = chunk_manifest(text)
        binding = ScopeBinding(scope_id=unit.scope_id, subject_id="unresolved:" + unit.source_id,
            artifact_id=unit.artifact_id, text_snapshot_id=text.id, association_version="unverified", role_version="unverified",
            membership="unresolved", role="unknown", windows=[ScopeWindow(page=p.page, layer_id=p.layer_id, start=0, end=len(p.text)) for p in text.pages])
        run = RunEnvelope(artifact_id=text.artifact_id, text_snapshot_id=text.id, model_identity=model,
            prompt_identity=PROMPT_ID, schema_identity=identity(candidate_schema()), chunk_manifest_id=manifest.id, scopes=[binding])
        inputs.append(ExperimentInput(unit_id=unit.unit_id, text=text, manifest=manifest, runs=[run]).model_dump())
        selected.append({"unit_id": unit.unit_id, "language_hint": language, "role_hint": unit.role_hint,
                         "purpose": "development capacity probe; no human labels or test accuracy"})
    calibration = {"model": model, "endpoint": endpoint, "caps": {"B0": 16384, "B1": 16384}, "inputs": inputs}
    development_units = [u.model_copy(update={"split": "development"}) for u in units if u.unit_id in {i["unit_id"] for i in inputs}]
    development = freeze_cohort(development_units, StudyPolicy(mode="bounded", minimum_documents=1, maximum_documents=None,
        minimum_bodies=1, minimum_levels=1), frozen_at=recorded_at)
    report = seal({"schema_version": "skony.evaluation-preflight.v1", "recorded_at": recorded_at,
        "candidate_cohort_digest": cohort["digest"], "source_manifest_digest": intake["source_manifest_digest"],
        "structure_census_digest": coverage["structural_inventory"]["census_digest"]
            if coverage["structural_inventory"] else None,
        "selected_source_rows": len(units), "verified_pdf_bytes": sum(u.source_status == "ready" for u in units),
        "unique_pinned_artifacts": len(by_artifact), "failed_source_rows": sum(u.source_status == "failed" for u in units),
        "metadata_language_hints": dict(Counter(u.language_hint for u in units)),
        "metadata_role_hints": dict(Counter(u.role_hint for u in units)),
        "new_human_annotations": 0, "model_calls": 0, "acquisition_gate": cohort["acquisition"],
        "review_protocol_passed": protocol["passed"], "novelty_gate_passed": novelty["passed"],
        "relation_gold": "not_supplied", "capacity_probe_selection": selected,
        "research_results_ready": False})
    artifacts = {"candidate-cohort.json": cohort, "intake-review-packet.json": packet,
        "corpus-coverage.json": coverage, "metadata-baseline.json": baseline,
        "novelty-report.json": novelty, "review-protocol.json": protocol, "feasibility-matrix.json": matrix,
        "development-cohort.json": development, "capacity-probe-input.json": calibration,
        "research-readiness.json": readiness, "preflight.json": report}
    if structure_census is not None:
        artifacts["structure-census.json"] = structure_census
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--structure-census", type=Path,
                        help="Optional structural-census JSON to include hard-case inventory counts")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Use a new output directory to preserve prior evidence")
    if args.model and args.endpoint:
        settings = Settings(args.model, args.endpoint, "")
    else:
        from skony.__main__ import load_env
        load_env(Path(__file__).resolve().parents[1] / ".env")
        settings = Settings.from_environment()
    artifacts = prepare(json.loads(args.intake.read_text(encoding="utf-8-sig")), metadata_paths=args.metadata,
        model=settings.model, endpoint=settings.base_url, recorded_at=datetime.now(timezone.utc).isoformat(),
        structure_census=json.loads(args.structure_census.read_text(encoding="utf-8-sig")) if args.structure_census else None)
    for filename, value in artifacts.items():
        atomic_json(args.out / filename, value)
    (args.out / "feasibility-matrix.md").write_text(matrix_markdown(artifacts["feasibility-matrix.json"]), encoding="utf-8")
    (args.out / "corpus-coverage.md").write_text(corpus_coverage_markdown(artifacts["corpus-coverage.json"]), encoding="utf-8")
    report = artifacts["preflight.json"]
    print(json.dumps({key: report[key] for key in ("selected_source_rows", "verified_pdf_bytes", "failed_source_rows",
        "new_human_annotations", "model_calls", "research_results_ready")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
