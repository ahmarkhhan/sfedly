import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx

from src.skony.evaluation_api import evaluate, schemas
from src.skony.evaluation_status import research_readiness
from src.skony.server import Workbench, make_handler
from src.skony.study import StudyPolicy
from src.skony.evaluation_common import seal
from evaluation_helpers import AT, cohort_for, study_unit


class EvaluationServiceTests(unittest.TestCase):
    def test_offline_operations_have_strict_versioned_schemas(self):
        self.assertIn("relation-merge", schemas())
        self.assertIn("readiness", schemas())
        self.assertIn("coverage", schemas())
        with self.assertRaises(ValueError):
            evaluate("cohort", {"units": [], "policy": {}, "frozen_at": AT, "extra": "not accepted"})

    def test_engineering_tests_and_an_empty_corpus_are_not_research_evidence(self):
        report = research_readiness(cohort_for())
        self.assertFalse(report["research_evidence_ready"])
        self.assertIn("B2_independent_relation_gold", report["open_gates"])
        self.assertIn("B7_frozen_experiment_results", report["open_gates"])


class EvaluationHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.app = Workbench(Path(cls.tmp.name) / "workbench", mode="replay")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.app))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = httpx.Client(base_url=f"http://127.0.0.1:{cls.server.server_port}", trust_env=False)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)
        cls.tmp.cleanup()

    def test_schema_discovery_and_existing_write_guards_apply_to_evaluation(self):
        self.assertEqual(self.client.get("/api/v2/evaluation/schemas").status_code, 200)
        data = {"units": [study_unit().model_dump()], "policy": StudyPolicy(mode="bounded", minimum_bodies=1,
            minimum_levels=1, required_languages=["de"]).model_dump(), "frozen_at": AT}
        self.assertEqual(self.client.post("/api/v2/evaluation/cohort", json=data).status_code, 403)
        headers = {"X-Skony-Token": self.app.token}
        result = self.client.post("/api/v2/evaluation/cohort", json=data, headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn("acquisition", result.json())
        coverage = self.client.post("/api/v2/evaluation/coverage", json={"cohort": result.json()}, headers=headers)
        self.assertEqual(coverage.status_code, 200, coverage.text)
        self.assertEqual(coverage.json()["counts"]["unit_count"], 1)
        self.assertEqual(coverage.json()["counts"]["verified_intake_count"], 1)
        bad = self.client.post("/api/v2/evaluation/cohort", json={**data, "unexpected": True}, headers=headers)
        self.assertEqual(bad.status_code, 422)
        foreign = self.client.post("/api/v2/evaluation/cohort", json=data,
            headers={**headers, "Origin": "https://untrusted.invalid"})
        self.assertEqual(foreign.status_code, 403)

    def test_http_has_no_live_experiment_operation(self):
        response = self.client.post("/api/v2/evaluation/experiment-run", json={}, headers={"X-Skony-Token": self.app.token})
        self.assertEqual(response.status_code, 422)

    def test_malformed_frozen_artifact_is_input_error_not_server_failure(self):
        response = self.client.post("/api/v2/evaluation/readiness", json={"cohort": seal({"schema_version": "skony.study-cohort.v1"})},
            headers={"X-Skony-Token": self.app.token})
        self.assertEqual(response.status_code, 422)
