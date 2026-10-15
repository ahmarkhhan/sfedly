"""Batch contracts: every source row, zero-call replay, safe limits and durable resume."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from src.skony import pipeline
from src.skony.batch import run_batch
from src.skony.cache import ResponseCache
from test_cache import CountingTransport, stub_settings

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/sample/synthetic-request.pdf"


def corpus(directory, count=2, extras=None):
    directory.mkdir()
    entries = []
    for index in range(count):
        path = directory / f"synthetic-{index}.pdf"
        path.write_bytes(SAMPLE.read_bytes() + f"\n% engineering variant {index}\n".encode())
        entries.append({"document_file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "status": "fetched", "body_key": "synthetic", "openparldata_document_id": index,
                        "language": "de", "role": "request"})
    entries.extend(extras or [])
    (directory / "fetch_manifest.json").write_text(json.dumps({"documents": entries}, indent=2), encoding="utf-8")
    return entries


class BatchTests(unittest.TestCase):
    def test_second_batch_makes_zero_http_calls_and_keeps_fetch_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, extras=[{"status": "failed", "openparldata_document_id": "download-failed"}])
            transport = CountingTransport()
            first = run_batch("live", fetch, root / "first", ResponseCache(root / "cache"),
                              stub_settings(), transport=transport)
            second = run_batch("replay", fetch, root / "second", ResponseCache(root / "cache"),
                               stub_settings(), transport=transport)
            self.assertEqual(first["counts"]["live_calls"], 2)
            self.assertEqual(second["counts"]["live_calls"], 0)
            self.assertEqual(second["counts"]["served_from_cache"], 2)
            self.assertEqual(second["counts"]["total"], 3)
            self.assertEqual(second["counts"]["failed"], 1)
            self.assertEqual(transport.calls, 2)
            self.assertEqual(second["items"][2]["error"]["reason"], "source_fetch_failed")
            for old, new in zip(first["items"][:2], second["items"][:2]):
                self.assertEqual(json.loads((root / "first" / old["result_file"]).read_text()),
                                 json.loads((root / "second" / new["result_file"]).read_text()))

    def test_limit_never_rewrites_source_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch)
            before = (fetch / "fetch_manifest.json").read_bytes()
            ledger = run_batch("live", fetch, root / "run", ResponseCache(root / "cache"),
                               stub_settings(), limit=1, transport=CountingTransport())
            self.assertEqual((fetch / "fetch_manifest.json").read_bytes(), before)
            self.assertEqual(ledger["counts"]["total"], 1)
            self.assertEqual(ledger["excluded_by_limit"], 1)
            self.assertEqual(ledger["source_manifest_items"], 2)

    def test_invalid_model_output_is_cached_and_failure_is_replayed(self):
        response = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                                           "usage": {"total_tokens": 7}})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, count=1)
            transport = CountingTransport([response])
            first = run_batch("live", fetch, root / "first", ResponseCache(root / "cache"),
                              stub_settings(), transport=transport)
            second = run_batch("live", fetch, root / "second", ResponseCache(root / "cache"),
                               stub_settings(), transport=transport)
            self.assertEqual(first["counts"]["live_calls"], 1)
            self.assertEqual(second["counts"]["live_calls"], 0)
            self.assertEqual(second["items"][0]["error"]["stage"], "schema")
            self.assertIn("cache_key", second["items"][0])
            self.assertEqual(first["usage"]["total_tokens"], 7)
            self.assertIsNone(first["usage"]["prompt_tokens"])
            self.assertEqual(second["usage"], first["usage"])
            self.assertEqual(second["usage_reporting"]["reporting_items_by_field"]["total_tokens"], 1)
            self.assertEqual(transport.calls, 1)

    def test_missing_tampered_and_traversing_sources_fail_before_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            entries = corpus(fetch, count=1)
            (fetch / entries[0]["document_file"]).write_bytes(b"changed")
            entries += [dict(entries[0], document_file="missing.pdf"),
                        dict(entries[0], document_file="../outside.pdf"), "malformed row"]
            (fetch / "fetch_manifest.json").write_text(json.dumps({"documents": entries}))
            transport = CountingTransport()
            ledger = run_batch("live", fetch, root / "run", ResponseCache(root / "cache"),
                               stub_settings(), transport=transport)
            self.assertEqual(ledger["counts"]["failed"], 4)
            self.assertEqual(ledger["counts"]["total"], 4)
            self.assertEqual(transport.calls, 0)
            self.assertEqual([item["error"]["reason"] for item in ledger["items"]],
                ["source_checksum_mismatch", "source_file_missing", "source_path_outside_corpus", "invalid_manifest_entry"])

    def test_endpoint_error_counts_call_hides_secret_and_continues(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch)
            ledger = run_batch("live", fetch, root / "run", ResponseCache(root / "cache"), stub_settings(),
                              transport=CountingTransport([httpx.Response(401, text="private-provider-response")]))
            self.assertEqual(ledger["counts"]["live_calls"], 2)
            self.assertEqual(ledger["counts"]["processed"], 1)
            self.assertEqual(ledger["items"][0]["error"]["http_status"], 401)
            text = (root / "run/run_ledger.json").read_text()
            self.assertNotIn("private-provider-response", text)
            self.assertNotIn(stub_settings().api_key, text)

    def test_interrupted_ledger_and_cache_allow_safe_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch)
            transport = CountingTransport()
            cache = ResponseCache(root / "cache")
            original = cache.complete
            calls = []
            def interrupted(*args, **kwargs):
                calls.append(True)
                if len(calls) == 2:
                    raise KeyboardInterrupt
                return original(*args, **kwargs)
            with patch.object(cache, "complete", side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    run_batch("live", fetch, root / "run", cache, stub_settings(), transport=transport)
            saved = json.loads((root / "run/run_ledger.json").read_text())
            self.assertEqual(saved["status"], "interrupted")
            self.assertEqual(saved["counts"]["pending"], 1)
            resumed = run_batch("live", fetch, root / "run", cache, stub_settings(), resume=True, transport=transport)
            self.assertEqual(resumed["counts"]["processed"], 2)
            self.assertEqual(resumed["counts"]["live_calls"], 1)
            self.assertEqual(resumed["counts"]["served_from_cache"], 1)
            self.assertEqual(len(list((root / "run/attempts").glob("*.json"))), 1)
            self.assertEqual(transport.calls, 2)

    def test_changed_resume_configuration_is_rejected_without_overwriting_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, count=1)
            run_batch("live", fetch, root / "run", ResponseCache(root / "cache"), stub_settings(), transport=CountingTransport())
            before = (root / "run/run_ledger.json").read_bytes()
            with self.assertRaises(ValueError):
                run_batch("live", fetch, root / "run", ResponseCache(root / "cache"), stub_settings(),
                          resume=True, max_tokens=128, transport=CountingTransport())
            self.assertEqual((root / "run/run_ledger.json").read_bytes(), before)

    def test_verifier_change_reuses_raw_response_and_preserves_generation_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, count=1)
            transport = CountingTransport()
            run_batch("live", fetch, root / "first", ResponseCache(root / "cache"), stub_settings(), transport=transport)
            with patch.object(pipeline, "VERIFIER_VERSION", "test-verifier-new"):
                replay = run_batch("replay", fetch, root / "next", ResponseCache(root / "cache"), stub_settings(), transport=transport)
            result = json.loads((root / "next" / replay["items"][0]["result_file"]).read_text())
            self.assertEqual(result["verifier_version"], "test-verifier-new")
            self.assertEqual(result["prompt_version"], pipeline.PROMPT_VERSION)
            self.assertEqual(transport.calls, 1)

    def test_replay_script_needs_no_env_file_or_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, count=1)
            run_batch("live", fetch, root / "first", ResponseCache(root / "cache"), stub_settings(), transport=CountingTransport())
            env_file = root / "invalid.env"
            env_file.write_text("this is not a valid env file")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/batch_extract.py"),
                "--mode", "replay", "--fetch-dir", str(fetch), "--cache-dir", str(root / "cache"),
                "--out", str(root / "offline"), "--env-file", str(env_file),
                "--model", stub_settings().model, "--base-url", stub_settings().base_url],
                capture_output=True, text=True, cwd=ROOT, env=os.environ.copy())
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = json.loads((root / "offline/run_ledger.json").read_text())
            self.assertEqual(ledger["counts"]["live_calls"], 0)

    def test_nonpositive_limit_does_not_create_a_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            corpus(fetch, count=1)
            with self.assertRaises(ValueError):
                run_batch("replay", fetch, root / "run", ResponseCache(root / "cache"), stub_settings(), limit=-1)
            self.assertFalse((root / "run").exists())


if __name__ == "__main__":
    unittest.main()
