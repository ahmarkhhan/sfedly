import copy
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

import httpx

from src.skony.contracts import FIELDS, identity
from src.skony.evaluation_common import seal
from src.skony.experiments import (ExperimentInput, freeze_experiment, generation_request, run_experiment,
                                   run_variants, score_experiment)
from src.skony.study import StudyUnit
from evaluation_helpers import AT, cohort_for, extraction_input, gold_for, settings, study_unit, transport

CAPS = {"B0": 500, "B1": 1000}

def now():
    return datetime.now(timezone.utc).isoformat()


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.dev, self.test = extraction_input("dev"), extraction_input()
        self.cohort = cohort_for()
        self.calibration = run_variants([self.dev], settings(), caps=CAPS, cache=self.directory / "dev",
                                       mode="live", maximum_calls=2, transport=transport(), source_kind="synthetic")

    def plan(self, calibration=None):
        return freeze_experiment(self.cohort, [self.test], calibration or self.calibration,
                                 frozen_at=now(), engineering_only=True)

    def test_two_generation_variants_and_zero_call_B2_share_input_text(self):
        result = run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "run", mode="live",
                              maximum_calls=2, transport=transport(wrong_answer=True), source_kind="synthetic")
        self.assertEqual(result["live_calls"], 2)
        self.assertEqual(result["B2_generation_calls"], 0)
        self.assertEqual(result["predictions"]["B1"][0]["fields"]["answer_text"], "Invented answer")
        self.assertIsNone(result["predictions"]["B2"][0]["fields"]["answer_text"])
        a, b = result["records"]
        self.assertEqual(a["request"]["payload"]["messages"][1], b["request"]["payload"]["messages"][1])
        self.assertEqual(result["B2_input_digests"], [b["raw_response_digest"]])
        self.assertNotIn(settings().api_key, json.dumps(result))

    def test_replay_is_identical_in_values_and_never_uses_network(self):
        plan = self.plan()
        first = run_experiment(plan, self.cohort, [self.test], settings(), cache=self.directory / "run",
                               mode="live", maximum_calls=2, transport=transport())
        def forbidden(request):
            raise AssertionError("Replay contacted the model")
        replay = run_experiment(plan, self.cohort, [self.test], settings(), cache=self.directory / "run",
                                mode="replay", maximum_calls=0, transport=httpx.MockTransport(forbidden))
        self.assertEqual(replay["recordings"]["live_calls"], 0)
        self.assertEqual(replay["recordings"]["cache_hits"], 2)
        self.assertEqual(first["recordings"]["predictions"], replay["recordings"]["predictions"])
        self.assertEqual(first["recordings"]["B2_input_digests"], replay["recordings"]["B2_input_digests"])

    def test_replay_miss_is_a_preserved_failure_and_never_a_live_fallback(self):
        result = run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "empty", mode="replay",
                              maximum_calls=100, transport=transport())
        self.assertEqual(result["live_calls"], 0)
        self.assertTrue(all(r["error"] == "cache_miss" for r in result["records"]))
        self.assertTrue(all(p[0]["outcome"] == "failed" for p in result["predictions"].values()))

    def test_truncated_and_unknown_completion_do_not_earn_successful_empty_outputs(self):
        for finish in ("length", None):
            result = run_variants([self.test], settings(), caps=CAPS, cache=self.directory / str(finish), mode="live",
                                  maximum_calls=2, transport=transport(finish=finish))
            self.assertTrue(all(r["contract_valid"] for r in result["records"]))
            self.assertTrue(all(p[0]["fields"] == {} for p in result["predictions"].values()))
            self.assertTrue(all(p[0]["outcome"] == "failed" for p in result["predictions"].values()))

    def test_explicit_call_budget_preserves_unrun_method_in_denominator(self):
        result = run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "budget", mode="live",
                              maximum_calls=1, transport=transport())
        self.assertEqual(result["live_calls"], 1)
        self.assertEqual(result["records"][1]["error"], "live_call_budget_exhausted")

    def test_transport_failure_is_preserved_without_retry_or_secret(self):
        def fail(request):
            raise httpx.ConnectError("secret must not leak: " + settings().api_key)
        result = run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "failure", mode="live",
                              maximum_calls=2, transport=httpx.MockTransport(fail))
        self.assertEqual(result["live_calls"], 2)
        self.assertTrue(all(r["error"] == "connection_error" for r in result["records"]))
        self.assertNotIn(settings().api_key, json.dumps(result))

    def test_changed_input_or_configuration_after_freeze_is_rejected(self):
        plan = self.plan()
        plan["caps"]["B1"] = 50
        with self.assertRaises(ValueError):
            run_experiment(plan, self.cohort, [self.test], settings(), cache=self.directory / "run", mode="replay", maximum_calls=0)

    def test_calibration_cannot_use_test_units_truncation_or_unknown_token_use(self):
        for problem in ("test", "truncation", "usage"):
            calibration = copy.deepcopy(self.calibration)
            if problem == "test":
                calibration["records"][0]["unit_id"] = self.test.unit_id
            elif problem == "truncation":
                calibration["records"][0]["finish_reason"] = "length"
            else:
                calibration["records"][0]["usage"] = {}
            calibration = seal({k: v for k, v in calibration.items() if k != "digest"})
            with self.assertRaises(ValueError):
                self.plan(calibration)

    def test_synthetic_capacity_proof_cannot_commit_a_real_study(self):
        with self.assertRaises(ValueError):
            freeze_experiment(self.cohort, [self.test], self.calibration, frozen_at=now())

    def test_failed_fetch_is_retained_in_every_method_and_scoring_cohort(self):
        failed = StudyUnit(unit_id="unavailable:lost:scope-lost", source_id="lost", artifact_id=None, scope_id="scope-lost",
            body_id="body1", body_key="body1", affair_id="lost", source_status="failed", failure_reason="source_fetch_failed",
            available_pages=[], split="test")
        cohort = cohort_for([study_unit("dev", split="development"), study_unit(), failed])
        missing = ExperimentInput(unit_id=failed.unit_id, input_failure=failed.failure_reason)
        plan = freeze_experiment(cohort, [self.test, missing], self.calibration, frozen_at=now(), engineering_only=True)
        result = run_experiment(plan, cohort, [self.test, missing], settings(), cache=self.directory / "failed-fetch",
            mode="live", maximum_calls=2, transport=transport())
        scored = score_experiment(result, [gold_for(study_unit(), cohort)], cohort)
        self.assertEqual(result["recordings"]["live_calls"], 2)
        for variant in ("B0", "B1", "B2"):
            self.assertEqual(scored["results"][variant]["frozen_units"], 2)
            self.assertEqual(scored["results"][variant]["operational_outcomes"]["failed"], 1)
            self.assertEqual(scored["results"][variant]["full_cohort_success"], .5)

    def test_scores_share_fields_and_show_filter_tradeoff(self):
        result = run_experiment(self.plan(), self.cohort, [self.test], settings(), cache=self.directory / "score",
            mode="live", maximum_calls=2, transport=transport(wrong_answer=True))
        scored = score_experiment(result, [gold_for(study_unit(), self.cohort)], self.cohort)
        self.assertEqual(scored["results"]["B2"]["primary"]["micro"]["fp"], 0)
        self.assertEqual(scored["results"]["B1"]["primary"]["micro"]["fp"], 1)
        self.assertEqual(scored["verifier_tradeoff"]["incorrect_B1_rejected"], 1)
        self.assertFalse(scored["semantic_accuracy_claim"])

    def test_corrupt_cache_is_rejected_without_overwriting_it(self):
        run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "corrupt", mode="live",
                     maximum_calls=2, transport=transport())
        path = next((self.directory / "corrupt").glob("*.json"))
        data = json.loads(path.read_text())
        data["completion"]["content"] = "fabricated"
        path.write_text(json.dumps(data), encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            run_variants([self.test], settings(), caps=CAPS, cache=self.directory / "corrupt", mode="replay", maximum_calls=0)
        self.assertEqual(before, path.read_bytes())

    def test_resealed_predictions_still_must_match_saved_response_bytes(self):
        result = run_experiment(self.plan(), self.cohort, [self.test], settings(), cache=self.directory / "tamper",
                               mode="live", maximum_calls=2, transport=transport())
        result["recordings"]["predictions"]["B2"][0]["fields"]["title"] = "A forged prediction"
        result["recordings"] = seal({k: v for k, v in result["recordings"].items() if k != "digest"})
        result = seal({k: v for k, v in result.items() if k != "digest"})
        with self.assertRaisesRegex(ValueError, "predictions"):
            score_experiment(result, [gold_for(study_unit(), self.cohort)], self.cohort)

    def test_replayed_synthetic_calibration_does_not_become_real_model_evidence(self):
        replay = run_variants([self.dev], settings(), caps=CAPS, cache=self.directory / "dev", mode="replay",
                              maximum_calls=0)
        self.assertTrue(all(r["source_kind"] == "synthetic" for r in replay["records"]))
        with self.assertRaises(ValueError):
            freeze_experiment(self.cohort, [self.test], replay, frozen_at=now())

    def test_capacity_must_be_frozen_after_development_observations(self):
        with self.assertRaisesRegex(ValueError, "precede"):
            freeze_experiment(self.cohort, [self.test], self.calibration, frozen_at=AT, engineering_only=True)

    def test_multiple_chunks_are_all_processed_without_dropping_repeated_wording(self):
        from src.skony.contracts import LayerPage, ScopeWindow
        from src.skony.pipeline_v2 import chunk_manifest
        from v2_helpers import propose, wire
        item = extraction_input()
        text = item.text.model_copy(update={"pages": [LayerPage(page=1, layer_id="native", text="Answer."),
                                                       LayerPage(page=2, layer_id="native", text="Answer.")]})
        manifest = chunk_manifest(text, max_characters=7)
        runs = []
        for page in (1, 2):
            binding = item.runs[0].scopes[0].model_copy(update={"text_snapshot_id": text.id,
                "windows": [ScopeWindow(page=page, layer_id="native", start=0, end=7)]})
            runs.append(item.runs[0].model_copy(update={"text_snapshot_id": text.id,
                                                      "chunk_manifest_id": manifest.id, "scopes": [binding]}))
        item = ExperimentInput(unit_id=item.unit_id, text=text, manifest=manifest, runs=runs)
        def answer(request):
            data = json.loads(request.content)
            target = json.loads(data["messages"][1]["content"])["targets"][0]
            page = target["pages"][0]["page"]
            if data.get("response_format"):
                values = propose(wire([target["scope_id"]]), segments=[(page, "Answer.")])
            else:
                values = {f: "Answer." if f == "answer_text" else None for f in FIELDS}
            return httpx.Response(200, json={"model": settings().model, "choices": [{"finish_reason": "stop",
                "message": {"content": json.dumps(values)}}], "usage": {"completion_tokens": 100}})
        result = run_variants([item], settings(), caps=CAPS, cache=self.directory / "chunks", mode="live",
                              maximum_calls=4, transport=httpx.MockTransport(answer), source_kind="synthetic")
        self.assertEqual(result["live_calls"], 4)
        for variant in ("B0", "B1", "B2"):
            self.assertEqual(result["predictions"][variant][0]["fields"]["answer_text"], "Answer.\n\nAnswer.")
        with self.assertRaises(ValueError):
            ExperimentInput(unit_id=item.unit_id, text=text, manifest=manifest, runs=runs[:1])
