"""Corpus fetching respects redirects, pinned bytes and partial retries."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_gold_pdfs", ROOT / "scripts/fetch_gold_pdfs.py")
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


def entry(**changes):
    return {"body_key": "743", "openparldata_document_id": 1,
            "retrieved_url": "https://files.openparldata.ch/source.pdf", "role": "request", **changes}


class FetchTests(unittest.TestCase):
    def test_redirect_outside_allowlist_never_contacts_target(self):
        calls = []

        def handle(request):
            calls.append(str(request.url))
            return httpx.Response(302, headers={"location": "https://outside.example/private"})

        with tempfile.TemporaryDirectory() as temporary, httpx.Client(
                transport=httpx.MockTransport(handle), follow_redirects=True) as client:
            result = fetcher.fetch_one(client, entry(), Path(temporary))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(len(calls), 1)
            self.assertFalse(list(Path(temporary).glob("*.pdf")))

    def test_allowed_redirect_and_second_fetch_reuse_pinned_bytes(self):
        calls = []

        def handle(request):
            calls.append(str(request.url))
            if len(calls) == 1:
                return httpx.Response(302, headers={"location": "/final.pdf"})
            return httpx.Response(200, content=b"%PDF-1.4 engineering fixture")

        with tempfile.TemporaryDirectory() as temporary, httpx.Client(transport=httpx.MockTransport(handle)) as client:
            first = fetcher.fetch_one(client, entry(), Path(temporary))
            second = fetcher.fetch_one(client, entry(), Path(temporary))
            self.assertEqual(first["status"], "fetched")
            self.assertEqual(second["status"], "cached")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["final_download_url"], "https://files.openparldata.ch/final.pdf")
            self.assertTrue(first["role_review_required"])
            self.assertEqual(len(calls), 2)

    def test_unsafe_filename_and_http_url_fail_before_network(self):
        def forbidden(request):
            self.fail("A rejected source must make no HTTP request")

        for changes in ({"body_key": "../escape"}, {"retrieved_url": "http://files.openparldata.ch/source.pdf"}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temporary, httpx.Client(
                    transport=httpx.MockTransport(forbidden)) as client:
                self.assertEqual(fetcher.fetch_one(client, entry(**changes), Path(temporary))["status"], "failed")

    def test_partial_retry_preserves_unselected_documents_and_failures(self):
        first = entry(status="fetched", sha256="first")
        failed = entry(openparldata_document_id=2, status="failed")
        retry = entry(status="cached", sha256="first")
        self.assertEqual(fetcher.merge_documents([first, failed], [retry]), [retry, failed])


if __name__ == "__main__":
    unittest.main()
