import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from src.skony.pipeline import verify_response
from src.skony.review import ReviewAction, ReviewError, ReviewStore
from src.skony.schema import CandidateExtraction, Document, Page
from src.skony.server import Workbench, make_handler


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.pdf = self.directory / "synthetic.pdf"
        self.pdf.write_bytes(b"%PDF-synthetic-engineering-fixture-not-a-real-document")
        self.document = Document(document_id="synthetic-review", filename=self.pdf.name, sha256="synthetic-digest",
                                 pages=[Page(number=1, text="Motion\nAlice Example\n12 octobre 2026\nBr~~r~ Name")])
        null = {"value": None, "page": None, "quote": None}
        candidate = {name: dict(null) for name in CandidateExtraction.model_fields}
        candidate["title"] = {"value": "Motion", "page": 1, "quote": "Motion"}
        self.result = verify_response(self.document, json.dumps(candidate), "synthetic-test-model")
        self.store = ReviewStore(self.directory / "store")
        self.identifier = self.store.add(self.document, self.pdf, {"synthetic": True}, self.result)

    def tearDown(self):
        self.temporary.cleanup()

    def action(self, field="title", action="confirm", **extra):
        return ReviewAction(field=field, action=action, revision=self.store.get(self.identifier)["revision"],
                            reviewer="Engineering test — not gold annotation", **extra)

    def test_unreviewed_suggestions_cannot_be_exported(self):
        with self.assertRaises(ReviewError):
            self.store.export(self.identifier)

    def test_confirmation_is_separate_persistent_and_export_excludes_other_fields(self):
        original = self.store.get(self.identifier)["fields"]["title"]["suggestion"]
        self.store.review(self.identifier, self.action())
        reopened = ReviewStore(self.directory / "store")
        item = reopened.get(self.identifier)
        self.assertEqual(item["fields"]["title"]["suggestion"], original)
        self.assertEqual(item["fields"]["title"]["review"]["value"], "Motion")
        exported = reopened.export(self.identifier)
        self.assertEqual(list(exported["fields"]), ["title"])
        self.assertEqual(len(exported["unreviewed_fields"]), 7)
        self.assertEqual(exported["document_sha256"], self.document.sha256)

    def test_stale_review_cannot_overwrite_new_review(self):
        stale = self.action()
        self.store.review(self.identifier, stale)
        with self.assertRaises(ReviewError) as error:
            self.store.review(self.identifier, stale)
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(len(self.store.audit(self.identifier)), 1)

    def test_source_text_correction_records_original_offsets(self):
        value = "Alice Example"
        reviewed = self.store.review(self.identifier, self.action("submitter_raw", "correct", value=value,
                                     page=1, quote=value))
        proof = reviewed["fields"]["submitter_raw"]["review"]["provenance"]
        self.assertEqual(self.document.pages[0].text[proof["start"]:proof["end"]], value)
        self.assertEqual(proof["basis"], "text")

    def test_fabricated_text_correction_is_rejected_without_mutation(self):
        with self.assertRaises(ReviewError):
            self.store.review(self.identifier, self.action("submitter_raw", "correct", value="Invented Name",
                                                          page=1, quote="Alice Example"))
        self.assertEqual(self.store.get(self.identifier)["revision"], 0)
        self.assertEqual(self.store.audit(self.identifier), [])

    def test_image_transcription_requires_note_and_never_claims_text_offsets(self):
        with self.assertRaises(ReviewError):
            self.store.review(self.identifier, self.action("submitter_raw", "correct", value="Readable Name",
                                 page=1, quote="Readable Name", basis="image"))
        item = self.store.review(self.identifier, self.action("submitter_raw", "correct", value="Readable Name",
                 page=1, quote="Readable Name", basis="image", note="Synthetic visual review at the page footer."))
        proof = item["fields"]["submitter_raw"]["review"]["provenance"]
        self.assertEqual(proof["basis"], "image")
        self.assertIsNone(proof["start"])
        self.assertIsNone(proof["match_method"])

    def test_absence_requires_explanation_and_exports_explicit_null(self):
        with self.assertRaises(ReviewError):
            self.store.review(self.identifier, self.action("answer_text", "missing"))
        self.store.review(self.identifier, self.action("answer_text", "missing", note="Checked the only source page; no government answer."))
        reviewed = self.store.export(self.identifier)["fields"]["answer_text"]
        self.assertIsNone(reviewed["value"])
        self.assertEqual(reviewed["decision"], "absent")

    def test_undo_retains_audited_before_snapshot(self):
        self.store.review(self.identifier, self.action())
        self.store.review(self.identifier, self.action(action="undo"))
        self.assertIsNone(self.store.get(self.identifier)["fields"]["title"]["review"])
        audit = self.store.audit(self.identifier)
        self.assertIsNotNone(audit[0]["snapshot"]["before"])
        self.assertIsNone(audit[0]["snapshot"]["after"])

    def test_new_extraction_preserves_human_review(self):
        self.store.review(self.identifier, self.action())
        before = self.store.get(self.identifier)["fields"]["title"]["review"]
        self.store.start_extraction(self.identifier)
        with self.assertRaises(ReviewError):
            self.store.review(self.identifier, self.action("answer_text", "missing", note="Checked this page."))
        self.store.finish_extraction(self.identifier, self.result, "synthetic response")
        self.assertEqual(self.store.get(self.identifier)["fields"]["title"]["review"], before)
        self.assertEqual(self.store.get(self.identifier)["extraction_origin"], "workbench_run")

    def test_null_suggestion_cannot_be_confirmed(self):
        with self.assertRaises(ReviewError):
            self.store.review(self.identifier, self.action("answer_text"))

    def test_duplicate_digest_reuses_document_and_blank_reviewer_is_invalid(self):
        self.assertEqual(self.store.add(self.document, self.pdf), self.identifier)
        with self.assertRaises(ValidationError):
            ReviewAction(field="title", action="confirm", revision=0, reviewer="   ")


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = Workbench(Path(self.temporary.name), seed_pilot=False)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.server.server_port}", trust_env=False)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_static_routes_work_and_private_paths_are_not_served(self):
        for path in ["/", "/app.js", "/style.css"]:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ["/.env", "/output/workbench/review.sqlite3", "/src/skony/server.py", "/api/documents/../../.env"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_state_has_no_secret_and_foreign_host_is_rejected(self):
        with patch.dict("os.environ", {"LLM_NAME":"swiss-ai/Apertus-v1.5-70B", "LLM_BASE_URL":"https://api.inference.cscs.ch/v1", "LLM_API_KEY":"secret-engineering-fixture"}):
            response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("secret-engineering-fixture", response.text)
        self.assertEqual(self.client.get("/api/state", headers={"Host":"foreign.example"}).status_code, 403)

    def test_mutation_requires_token_and_matching_origin(self):
        def post(**kwargs):
            # Retry transient Windows loopback aborts (WinError 10053) so a flaky
            # socket does not mask the security assertion being tested.
            for _ in range(3):
                try:
                    return self.client.post("/api/upload", content=b"not-pdf", **kwargs)
                except httpx.ReadError:
                    continue
            return self.client.post("/api/upload", content=b"not-pdf", **kwargs)
        self.assertEqual(post().status_code, 403)
        response = post(headers={"X-Skony-Token":self.app.token, "Origin":"https://foreign.example"})
        self.assertEqual(response.status_code, 403)
        response = post(headers={"X-Skony-Token":self.app.token})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
