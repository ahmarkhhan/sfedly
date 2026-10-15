"""Batch suggestions enter review once; source mismatches never replace reviews."""

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from src.skony.batch import run_batch
from src.skony.cache import ResponseCache, atomic_json
from src.skony.corpus import import_corpus
from src.skony.review import ReviewAction, ReviewStore
from test_batch import corpus
from test_cache import CountingTransport, stub_settings


class CorpusImportTests(unittest.TestCase):
    def setup_run(self, root):
        fetch, run = root / "input", root / "run"
        corpus(fetch, count=1)
        cache = ResponseCache(root / "cache")
        ledger = run_batch("live", fetch, run, cache, stub_settings(), transport=CountingTransport())
        return fetch, run, cache, ledger

    def test_import_is_idempotent_and_preserves_human_reviews(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch, run, cache, ledger = self.setup_run(root)
            store = ReviewStore(root / "store")
            first = import_corpus(fetch, store, run_dir=run, cache=cache)
            self.assertEqual(first["results_imported"], 1)
            identifier = store.list()[0]["id"]
            item = store.get(identifier)
            self.assertEqual(item["extraction_origin"], "cached_batch")
            self.assertEqual(item["source"]["role_origin"], "unverified_selection_hint")
            store.review(identifier, ReviewAction(field="answer_text", action="missing", revision=item["revision"],
                reviewer="Human Reviewer", note="Checked page 1, no answer here."))
            before = store.get(identifier)
            second = import_corpus(fetch, store, run_dir=run, cache=cache)
            self.assertEqual(second["results_already_present"], 1)
            self.assertEqual(store.get(identifier), before)
            self.assertEqual(len(store.audit(identifier)), 1)
            self.assertEqual(cache.http_calls, 1)  # only the original stub inference

    def test_changed_source_manifest_refuses_whole_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch, run, cache, ledger = self.setup_run(root)
            (fetch / "fetch_manifest.json").write_text('{"documents": []}', encoding="utf-8")
            store = ReviewStore(root / "store")
            with self.assertRaises(ValueError):
                import_corpus(fetch, store, run_dir=run, cache=cache)
            self.assertEqual(store.list(), [])

    def test_tampered_result_is_not_imported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch, run, cache, ledger = self.setup_run(root)
            result_path = run / ledger["items"][0]["result_file"]
            data = json.loads(result_path.read_bytes())
            data["latency_seconds"] += 1
            atomic_json(result_path, data)
            store = ReviewStore(root / "store")
            summary = import_corpus(fetch, store, run_dir=run, cache=cache)
            self.assertEqual(summary["result_failed"], 1)
            self.assertIsNone(store.get(store.list()[0]["id"])["model"])

    def test_bad_source_hash_and_failed_download_are_counted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            entries = corpus(fetch, count=1, extras=[{"status": "failed"}])
            (fetch / entries[0]["document_file"]).write_bytes(b"tampered")
            store = ReviewStore(root / "store")
            summary = import_corpus(fetch, store)
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["source_failed"], 2)
            self.assertEqual(store.list(), [])

    def test_running_extraction_cannot_be_overwritten_by_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch, run, cache, ledger = self.setup_run(root)
            store = ReviewStore(root / "store")
            import_corpus(fetch, store)
            identifier = store.list()[0]["id"]
            store.start_extraction(identifier)
            summary = import_corpus(fetch, store, run_dir=run, cache=cache)
            self.assertEqual(summary["result_failed"], 1)
            self.assertEqual(store.get(identifier)["extraction_state"], "running")

    def test_corrupt_pdf_with_matching_hash_does_not_abort_later_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fetch = root / "input"
            entries = corpus(fetch, count=2)
            broken = fetch / entries[0]["document_file"]
            broken.write_bytes(b"%PDF-1.4 corrupt engineering fixture")
            entries[0]["sha256"] = hashlib.sha256(broken.read_bytes()).hexdigest()
            atomic_json(fetch / "fetch_manifest.json", {"documents": entries})
            store = ReviewStore(root / "store")
            summary = import_corpus(fetch, store)
            self.assertEqual(summary["source_failed"], 1)
            self.assertEqual(summary["added"], 1)
            self.assertEqual(len(store.list()), 1)


if __name__ == "__main__":
    unittest.main()
