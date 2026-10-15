"""Exercise the actual cached client, request invalidation and corrupt-entry rejection."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from src.skony import pipeline
from src.skony.cache import CacheIntegrityError, CacheMiss, ResponseCache, request_fingerprint
from src.skony.client import EndpointError, Settings
from src.skony.schema import CandidateExtraction, Document, Page


def make_document(text="Antrag: Der Rat soll handeln."):
    return Document(document_id="fixture", filename="fixture.pdf", sha256="synthetic-source-digest",
                    pages=[Page(number=1, text=text)])


def stub_settings(**changes):
    values = {"model": "swiss-ai/Apertus-v1.5-70B", "base_url": "https://endpoint.test/v1",
              "api_key": "test-secret-never-cache"}
    return Settings(**(values | changes))


class CountingTransport(httpx.BaseTransport):
    def __init__(self, responses=None):
        self.calls = 0
        self.requests = []
        self.responses = responses or []

    def handle_request(self, request):
        self.calls += 1
        self.requests.append(json.loads(request.content))
        if self.calls <= len(self.responses):
            return self.responses[self.calls - 1]
        content = json.dumps({name: {"value": None, "page": None, "quote": None}
                              for name in CandidateExtraction.model_fields})
        return httpx.Response(200, json={"model": self.requests[-1]["model"],
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


class FingerprintTests(unittest.TestCase):
    def test_same_input_same_key(self):
        self.assertEqual(request_fingerprint(make_document(), stub_settings()),
                         request_fingerprint(make_document(), stub_settings()))

    def test_changed_text_model_endpoint_or_generation_changes_key(self):
        original = request_fingerprint(make_document(), stub_settings())
        alternatives = [
            request_fingerprint(make_document("Different page text"), stub_settings()),
            request_fingerprint(make_document(), stub_settings(model="swiss-ai/Apertus-v1.5-8B")),
            request_fingerprint(make_document(), stub_settings(base_url="https://another.test/v1")),
            request_fingerprint(make_document(), stub_settings(), max_tokens=2048),
            request_fingerprint(make_document(), stub_settings(), temperature=0.2),
            request_fingerprint(make_document(), stub_settings(), model_revision="revision-2"),
        ]
        self.assertNotIn(original, alternatives)

    def test_prompt_bytes_invalidate_even_without_version_bump(self):
        original = request_fingerprint(make_document(), stub_settings())
        with tempfile.TemporaryDirectory() as temporary:
            prompt = Path(temporary) / "prompt.txt"
            prompt.write_text(pipeline.PROMPT_PATH.read_text(encoding="utf-8") + "\nChanged instruction.", encoding="utf-8")
            with patch.object(pipeline, "PROMPT_PATH", prompt):
                self.assertNotEqual(original, request_fingerprint(make_document(), stub_settings()))

    def test_schema_and_prompt_version_change_key_but_verifier_does_not(self):
        original = request_fingerprint(make_document(), stub_settings())
        schema = CandidateExtraction.model_json_schema()
        schema["description"] = "Changed candidate contract"
        self.assertNotEqual(original, request_fingerprint(make_document(), stub_settings(), json_schema=schema))
        self.assertNotEqual(original, request_fingerprint(make_document(), stub_settings(), prompt_version="next-prompt"))
        with patch.object(pipeline, "VERIFIER_VERSION", "next-verifier"):
            self.assertEqual(original, request_fingerprint(make_document(), stub_settings()))

    def test_rotated_key_does_not_change_request_identity(self):
        self.assertEqual(request_fingerprint(make_document(), stub_settings()),
                         request_fingerprint(make_document(), stub_settings(api_key="rotated-test-secret")))


class CacheBehaviourTests(unittest.TestCase):
    def test_second_run_makes_zero_http_calls(self):
        transport = CountingTransport()
        with tempfile.TemporaryDirectory() as temporary:
            first = ResponseCache(Path(temporary))
            content1, usage1, key1, hit1 = first.complete(stub_settings(), make_document(), transport=transport)
            second = ResponseCache(Path(temporary))
            content2, usage2, key2, hit2 = second.complete(stub_settings(), make_document(), transport=transport)
            self.assertFalse(hit1)
            self.assertTrue(hit2)
            self.assertEqual((content1, usage1, key1), (content2, usage2, key2))
            self.assertEqual(transport.calls, 1)
            self.assertEqual(second.stats()["http_calls"], 0)
            self.assertEqual(transport.requests[0], second.get(key2)["request"]["payload"])

    def test_credentials_are_not_serialized_to_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            cache.complete(stub_settings(), make_document(), transport=CountingTransport())
            text = next(Path(temporary).glob("*.json")).read_text(encoding="utf-8")
            self.assertNotIn(stub_settings().api_key, text)
            self.assertNotIn("Authorization", text)

    def test_replay_miss_raises_instead_of_live_call(self):
        transport = CountingTransport()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(CacheMiss):
                ResponseCache(Path(temporary)).complete(stub_settings(), make_document(),
                    allow_live=False, transport=transport)
            self.assertEqual(transport.calls, 0)

    def test_corrupt_json_never_refetches_even_in_live_mode(self):
        transport = CountingTransport()
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            key = request_fingerprint(make_document(), stub_settings())
            path = Path(temporary) / f"{key}.json"
            path.write_text("{invalid", encoding="utf-8")
            with self.assertRaises(CacheIntegrityError):
                cache.complete(stub_settings(), make_document(), transport=transport)
            self.assertEqual(transport.calls, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "{invalid")

    def test_valid_json_with_modified_content_is_rejected(self):
        transport = CountingTransport()
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            _, _, key, _ = cache.complete(stub_settings(), make_document(), transport=transport)
            path = Path(temporary) / f"{key}.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["content"] = "altered text"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(CacheIntegrityError):
                cache.complete(stub_settings(), make_document(), transport=transport)
            self.assertEqual(transport.calls, 1)

    def test_entry_copied_under_another_request_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            _, _, key, _ = cache.complete(stub_settings(), make_document(), transport=CountingTransport())
            other = request_fingerprint(make_document("Other text"), stub_settings())
            (Path(temporary) / f"{other}.json").write_bytes((Path(temporary) / f"{key}.json").read_bytes())
            with self.assertRaises(CacheIntegrityError):
                cache.get(other)

    def test_atomic_write_failure_preserves_preceding_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            _, _, key, _ = cache.complete(stub_settings(), make_document(), transport=CountingTransport())
            original = (Path(temporary) / f"{key}.json").read_bytes()
            record = cache.get(key)
            record["content"] = "another completed response"
            with patch("src.skony.cache.os.replace", side_effect=OSError("simulated write failure")):
                with self.assertRaises(OSError):
                    cache.put(key, record)
            self.assertEqual((Path(temporary) / f"{key}.json").read_bytes(), original)
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])

    def test_endpoint_failure_is_counted_and_not_cached(self):
        transport = CountingTransport([httpx.Response(503, text="private-provider-response")])
        with tempfile.TemporaryDirectory() as temporary:
            cache = ResponseCache(Path(temporary))
            with self.assertRaises(EndpointError):
                cache.complete(stub_settings(), make_document(), transport=transport)
            self.assertEqual(cache.stats()["http_calls"], 1)
            self.assertEqual(list(Path(temporary).glob("*.json")), [])

    def test_cache_key_cannot_be_used_as_a_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                ResponseCache(Path(temporary)).get("../not-a-cache-key")


if __name__ == "__main__":
    unittest.main()
