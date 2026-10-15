import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import httpx

from src.skony.api_v2 import V2API
from src.skony.comparison import query_snapshot
from src.skony.contracts import RunEnvelope, ScopeBinding, TextSnapshot, canonical, identity
from src.skony.pipeline_v2 import PROMPT_ID, candidate_schema, chunk_manifest
from src.skony.review_contracts import ComparisonSpec
from src.skony.server import Workbench, make_handler
from v2_helpers import accept, claim_for, review_fixture, wire, propose


class V2IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.legacy, self.domain, self.doc_id, self.document, self.scope = review_fixture(self.directory)
        self.api = V2API(self.legacy)

    def tearDown(self):
        self.tmp.cleanup()

    def recording(self, content=None):
        text = TextSnapshot.model_validate(self.domain.get(self.scope["binding"]["text_snapshot_id"], "text"))
        manifest = chunk_manifest(text)
        run = RunEnvelope(artifact_id=text.artifact_id, text_snapshot_id=text.id,
            model_identity="engineering-fixture-not-a-model-run", prompt_identity=PROMPT_ID,
            schema_identity=identity(candidate_schema()), chunk_manifest_id=manifest.id,
            scopes=[ScopeBinding.model_validate(self.scope["binding"])])
        data = propose(wire((self.scope["id"],)), "answer_text", [(1, "Answer complete.")])
        data["targets"][0]["fields"]["answer_text"]["items"][0]["segments"][0]["layer_id"] = "legacy"
        return {"run": run.model_dump(), "manifest": manifest.model_dump(), "chunk_id": "chunk-1",
                "content": json.dumps(data) if content is None else content, "finish_reason": "stop"}

    def test_recording_review_snapshot_offline_replay_never_calls_model(self):
        with patch("src.skony.client.httpx.Client", side_effect=AssertionError("No model calls during replay")):
            imported = self.api.post(["extractions"], self.recording())
            self.assertEqual(len(imported["claim_ids"]), 1)
            self.assertEqual(self.api.post(["extractions"], self.recording())["extraction_id"], imported["extraction_id"])
            claim_id = imported["claim_ids"][0]
            decision = accept(self.domain, claim_id, self.scope)
            frozen = self.domain.freeze([decision["decision_id"]], scope_ids=[self.scope["id"]])
            spec = ComparisonSpec(question="Engineering fixture", snapshot_id=frozen["snapshot_id"],
                scope_ids=[self.scope["id"]], columns=["answer_text"], permitted_mapping_relations=[])
            live_store_result = self.domain.compare(spec)
            standalone = query_snapshot(json.loads(canonical(frozen["snapshot"])), spec)
            self.assertEqual(standalone["result_id"], live_store_result["result_id"])
            self.assertEqual(standalone["result"], live_store_result["result"])
            self.assertEqual(standalone["result"]["rows"][0]["fields"]["answer_text"]["completeness"]["semantic_completeness"], "unknown")

    def test_invalid_raw_output_is_retained_without_claims_or_review(self):
        raw = '{"schema_version":"skony.candidate.v0.2","approved":true,"fetch":"https://untrusted.invalid"}'
        result = self.api.post(["extractions"], self.recording(raw))
        self.assertIsNone(result["result"])
        self.assertEqual(result["claim_ids"], [])
        self.assertEqual(self.domain.get(result["extraction_id"], "extraction")["content"], raw)
        self.assertEqual(self.domain.current_reviews(), [])

    def test_identical_value_rerun_does_not_reopen_a_resolved_conflict(self):
        first = self.api.post(["extractions"], self.recording())
        claim_for(self.domain, self.scope, quote="Alternative answer.")
        accepted = accept(self.domain, first["claim_ids"][0], self.scope, resolve_conflicts=True)
        later = self.recording()
        later["run"]["model_identity"] = "second-engineering-run"
        self.api.post(["extractions"], later)
        self.assertTrue(self.domain.eligibility(accepted["decision_id"])["eligible"])

    def test_visual_transcription_can_be_reviewed_and_replayed_without_offsets(self):
        evidence = {"artifact_id": self.document.sha256, "text_snapshot_id": None, "page": 1, "layer_id": None,
                    "basis": "image", "quote": "Human visual transcription", "note": "Engineering image fixture"}
        imported = self.api.post(["corrections"], {"scope_id": self.scope["id"], "predicate": "title",
                                                  "image_segments": [evidence]})
        decision = accept(self.domain, imported["claim_id"], self.scope)
        frozen = self.domain.freeze([decision["decision_id"]], scope_ids=[self.scope["id"]])
        citation = frozen["snapshot"]["rows"][0]["citations"][0]
        self.assertEqual(citation["capability"], "page_transcription")
        self.assertNotIn("start", citation)

    def test_later_duplicate_source_is_preserved_and_synced_to_independent_scope(self):
        second = {"source_url": "https://fixture.invalid/independent", "body_id": "body2"}
        self.assertEqual(self.legacy.add(self.document, self.directory / "fixture.pdf", second), self.doc_id)
        first_count = len(self.api.get(["scopes"]))
        self.assertGreater(first_count, 1)
        self.assertEqual(len(self.api.get(["scopes"])), first_count)
        self.assertEqual(self.legacy.get(self.doc_id)["source"]["source_url"], "https://fixture.invalid/a")

    def test_snapshot_detects_tampered_serialized_dependencies(self):
        decision = accept(self.domain, claim_for(self.domain, self.scope), self.scope)
        frozen = self.domain.freeze([decision["decision_id"]], scope_ids=[self.scope["id"]])
        spec = ComparisonSpec(question="Fixture", snapshot_id=frozen["snapshot_id"], scope_ids=[self.scope["id"]],
                              columns=["answer_text"], permitted_mapping_relations=[])
        frozen["snapshot"]["rows"][0]["value"] = "silently changed"
        with self.assertRaisesRegex(ValueError, "digest"):
            query_snapshot(frozen["snapshot"], spec)


class V2HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        legacy, self.domain, self.doc_id, self.document, self.scope = review_fixture(self.directory)
        self.app = Workbench(legacy.directory, seed_pilot=False)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.server.server_port}", trust_env=False)

    def tearDown(self):
        self.client.close(); self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_v2_routes_keep_origin_token_and_input_validation_boundaries(self):
        for path in ["/scoped", "/scoped.js", "/scoped.css", "/api/v2/scopes", "/api/v2/schemas"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.client.get("/api/v2/scopes/" + quote(self.scope["id"], safe="") + "/claims").status_code, 200)
        response = self.client.post("/api/v2/reviews", json={})
        self.assertEqual(response.status_code, 403)
        response = self.client.post("/api/v2/reviews", json={}, headers={"X-Skony-Token": self.app.token})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["reason_code"], "invalid_contract")
        self.assertEqual(self.client.get("/api/v2/objects/not-found").status_code, 404)

    def test_frozen_pdf_route_uses_pinned_bytes_and_rejects_path_traversal(self):
        path = f"/api/v2/artifacts/{self.document.sha256}/pdf"
        before = self.client.get(path)
        self.assertEqual(before.status_code, 200)
        self.app.store.pdf_path(self.doc_id).write_bytes(b"changed legacy file")
        self.assertEqual(self.client.get(path).content, before.content)
        self.assertEqual(self.client.get("/api/v2/artifacts/../../.env/pdf").status_code, 404)


if __name__ == "__main__":
    unittest.main()
