"""Execution mode, public demo integrity, review persistence and mapped ports."""

import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx

from src.skony.demo import SAMPLE, load_demo
from src.skony.review import ReviewAction, ReviewError
from src.skony.server import Workbench, make_handler


class ReplayTests(unittest.TestCase):
    def test_seed_replay_and_extraction_rejection_make_no_model_call(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("src.skony.server.Settings.from_environment") as settings, \
                patch("src.skony.server.complete") as complete:
            app = Workbench(Path(directory), mode="replay")
            state = app.state()
            self.assertEqual(state["mode"], "replay")
            self.assertFalse(state["api_configured"])
            self.assertIsNone(state["configured_model"])
            self.assertEqual(len(state["documents"]), 1)
            document = app.store.get(state["documents"][0]["id"])
            self.assertEqual(document["extraction_origin"], "synthetic_fixture")
            self.assertTrue(document["source"]["synthetic"])
            self.assertFalse(document["source"]["gold_annotation"])
            self.assertEqual(document["model"], "synthetic_fixture_not_model_inference")
            self.assertEqual(sum(f["suggestion"]["status"] == "source_located"
                                 for f in document["fields"].values()), 5)
            with self.assertRaises(ReviewError):
                app.start(document["id"])
            settings.assert_not_called()
            complete.assert_not_called()

    def test_restarting_replay_keeps_review_and_does_not_duplicate_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Workbench(Path(directory), mode="replay")
            identifier = app.store.list()[0]["id"]
            app.store.review(identifier, ReviewAction(field="title", action="confirm", revision=0,
                reviewer="Automated engineering test - not gold"))
            restarted = Workbench(Path(directory), mode="replay")
            self.assertEqual(len(restarted.store.list()), 1)
            self.assertEqual(restarted.store.get(identifier)["revision"], 1)
            exported = restarted.store.export(identifier)
            self.assertEqual(len(exported["fields"]), 1)
            self.assertEqual(len(exported["unreviewed_fields"]), 7)
            self.assertTrue(exported["source"]["synthetic"])
            self.assertEqual(len(restarted.store.audit(identifier)), 1)

    def test_tampered_public_pdf_or_candidate_cannot_seed_a_valid_demo(self):
        for filename in ("synthetic-request.pdf", "candidate.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                sample = Path(directory) / "sample"
                shutil.copytree(SAMPLE, sample)
                with (sample / filename).open("ab") as stream:
                    stream.write(b"tampered")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    load_demo(sample)

    def test_live_mode_does_not_import_synthetic_suggestions_implicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Workbench(Path(directory), mode="live", seed_pilot=False)
            self.assertEqual(app.store.list(), [])


class ContainerHostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = Workbench(Path(self.temporary.name), mode="replay", public_port=18765)
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

    def test_healthcheck_and_declared_mapped_port_work_without_foreign_hosts(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.json(), {"status": "ok", "mode": "replay"})
        self.assertEqual(self.client.get("/api/state", headers={"Host": "localhost:18765"}).status_code, 200)
        for host in ("localhost:18766", "foreign.example:18765"):
            self.assertEqual(self.client.get("/api/state", headers={"Host": host}).status_code, 403)

    def test_mapped_origin_still_requires_token_and_rejects_foreign_origin(self):
        headers = {"Host": "localhost:18765", "Origin": "http://localhost:18765"}
        self.assertEqual(self.client.post("/api/upload", content=b"invalid", headers=headers).status_code, 403)
        headers["X-Skony-Token"] = self.app.token
        self.assertEqual(self.client.post("/api/upload", content=b"invalid", headers=headers).status_code, 400)
        headers["Origin"] = "http://localhost:18766"
        self.assertEqual(self.client.post("/api/upload", content=b"invalid", headers=headers).status_code, 403)

    def test_replay_endpoint_rejects_live_extraction_without_changing_state(self):
        identifier = self.app.store.list()[0]["id"]
        with patch("src.skony.server.complete") as complete:
            response = self.client.post(f"/api/documents/{identifier}/extract", content=b"{}",
                                       headers={"X-Skony-Token": self.app.token})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(self.app.store.get(identifier)["extraction_state"], "idle")
            complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
