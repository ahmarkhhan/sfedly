import json
import unittest

import httpx
from pydantic import ValidationError

from src.skony.client import Settings, complete
from src.skony.pipeline import messages_for, verify_response
from src.skony.schema import CandidateExtraction, CandidateField, Document, Page
from src.skony.verify import locate


def document(text="Motion\nLa demande est rejetée.\n12 octobre 2026", pages=None):
    return Document(document_id="synthetic-test", filename="synthetic.pdf", sha256="test-only",
                    pages=pages or [Page(number=1, text=text)])


def candidate(value, quote=None, page=1):
    return CandidateField(value=value, page=page, quote=quote or value)


class EvidenceTests(unittest.TestCase):
    def test_line_breaks_resolve_to_original_text_and_offsets(self):
        source = document("Der Gemeinderat wird beauftragt \n abzuklären.")
        result = locate(candidate("Der Gemeinderat wird beauftragt abzuklären."), source)
        self.assertEqual(result.value, source.pages[0].text)
        self.assertEqual(result.provenance.match_method, "whitespace_normalized")
        self.assertEqual(source.pages[0].text[result.provenance.start:result.provenance.end], result.provenance.quote)

    def test_whitespace_matching_does_not_change_punctuation(self):
        result = locate(candidate("21. März 2013"), document("21.März 2013"))
        self.assertIsNone(result.value)

    def test_repeated_normalized_quote_is_ambiguous(self):
        result = locate(candidate("Der Rat entscheidet."), document("Der Rat\nentscheidet.\nDer Rat  entscheidet."))
        self.assertEqual(result.reason, "ambiguous_quote")

    def test_corrupt_ocr_submitter_is_abstained_despite_a_matching_quote(self):
        result = locate(candidate("Br~~r~::! ILL~~ cL"), document("Br~~r~::! ILL~~ cL"), "submitter_raw")
        self.assertEqual(result.reason, "submitter_contains_ocr_noise")
        self.assertIsNone(result.value)

    def test_exact_quote_has_offsets_into_unchanged_page(self):
        source = document()
        result = locate(candidate("rejetée", "La demande est rejetée."), source)
        evidence = result.provenance
        self.assertEqual(source.pages[0].text[evidence.start:evidence.end], evidence.quote)
        self.assertEqual(result.status, "source_located")
        self.assertTrue(result.semantic_review_required)

    def test_invented_value_with_real_quote_abstains(self):
        result = locate(candidate("adoptée", "La demande est rejetée."), document())
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "value_not_in_quote")

    def test_invented_quote_abstains(self):
        result = locate(candidate("adoptée", "La demande est adoptée."), document())
        self.assertIsNone(result.value)

    def test_wrong_page_does_not_search_other_pages(self):
        source = document(pages=[Page(number=1, text="Motion"), Page(number=2, text="Réponse")])
        result = locate(candidate("Réponse", page=1), source)
        self.assertIsNone(result.value)

    def test_duplicate_quote_requires_review(self):
        self.assertEqual(locate(candidate("Motion"), document("Motion\nMotion")).reason, "ambiguous_quote")

    def test_ocr_like_fuzzy_match_is_not_accepted(self):
        self.assertIsNone(locate(candidate("Motion"), document("M0tion")).value)

    def test_copied_wrong_semantic_field_is_never_approved(self):
        # A perfectly copied proposed decision can still be the wrong decision.
        result = locate(candidate("adoptée", "Proposition: la demande doit être adoptée."),
                        document("Proposition: la demande doit être adoptée."))
        self.assertEqual(result.status, "source_located")
        self.assertTrue(result.semantic_review_required)

    def test_missing_evidence_fails_schema(self):
        with self.assertRaises(ValidationError):
            CandidateField(value="Motion", page=None, quote=None)

    def test_empty_page_fails_closed(self):
        self.assertEqual(locate(candidate("Motion"), document(" ")).reason, "page_has_no_text")
        with self.assertRaises(ValueError):
            messages_for(document(""))

    def test_long_document_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            messages_for(document("x" * 50001))

    def test_extra_model_keys_and_prose_rejected(self):
        null = {"value": None, "page": None, "quote": None}
        fields = {key: null for key in CandidateExtraction.model_fields}
        with self.assertRaises(ValidationError):
            verify_response(document(), json.dumps({**fields, "ignore_rules": "yes"}), "fixture")
        with self.assertRaises(ValidationError):
            verify_response(document(), "```json\n" + json.dumps(fields) + "\n```", "fixture")

    def test_valid_missing_fields_are_explicit_abstentions(self):
        null = {"value": None, "page": None, "quote": None}
        result = verify_response(document(), json.dumps({key: null for key in CandidateExtraction.model_fields}), "fixture")
        self.assertEqual(result.state, "needs_human_review")
        self.assertTrue(all(f.value is None for f in result.fields.values()))


class EndpointTests(unittest.TestCase):
    def test_extraction_requires_structured_response_without_changing_model(self):
        def respond(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["response_format"]["type"], "json_schema")
            self.assertTrue(payload["response_format"]["json_schema"]["strict"])
            self.assertEqual(payload["response_format"]["json_schema"]["schema"], CandidateExtraction.model_json_schema())
            return httpx.Response(200, json={"model": "apertus", "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
        complete(Settings("apertus", "https://endpoint.example/v1", ""), [],
                 json_schema=CandidateExtraction.model_json_schema(), transport=httpx.MockTransport(respond))

    def test_different_served_model_is_rejected(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
            "model": "different-model", "choices": [{"finish_reason": "stop", "message": {"content": "text"}}]}))
        with self.assertRaises(ValueError):
            complete(Settings("apertus", "https://endpoint.example/v1", ""), [], transport=transport)

    def test_configured_model_name_and_key_sent_only_to_configured_endpoint(self):
        def respond(request):
            self.assertEqual(str(request.url), "https://endpoint.example/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            self.assertEqual(json.loads(request.content)["model"], "Apertus-1.5-test-alias")
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "APERTUS_READY"}}],
                                            "usage": {"total_tokens": 7}})
        text, usage = complete(Settings("Apertus-1.5-test-alias", "https://endpoint.example/v1", "test-key"),
                               [{"role": "user", "content": "test"}], transport=httpx.MockTransport(respond))
        self.assertEqual(text, "APERTUS_READY")
        self.assertEqual(usage["total_tokens"], 7)

    def test_truncated_response_rejected(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
            "choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}))
        with self.assertRaises(ValueError):
            complete(Settings("apertus", "https://endpoint.example/v1", ""), [], transport=transport)

    def test_http_failure_does_not_echo_key_or_provider_body(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(401, text="sensitive-provider-response"))
        with self.assertRaises(ValueError) as error:
            complete(Settings("apertus", "https://endpoint.example/v1", "test-key"), [], transport=transport)
        self.assertNotIn("sensitive-provider-response", str(error.exception))
        self.assertNotIn("test-key", str(error.exception))


if __name__ == "__main__":
    unittest.main()

