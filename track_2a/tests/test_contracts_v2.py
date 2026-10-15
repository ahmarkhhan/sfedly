import copy
import json
import unittest

import httpx
from pydantic import ValidationError

from src.skony.client import Settings, complete_recorded
from src.skony.completeness import Chunk, ChunkManifest, ChunkOutcome, SectionCheck, assess_completeness
from src.skony.contracts import CandidateV2, EvidenceSegment, PDFRegion, ScopeBinding, ScopeWindow, TextSnapshot, identity
from src.skony.citations import citation
from src.skony.evidence_v2 import benchmark_projection, legacy_projection, verify_v2
from src.skony.pipeline_v2 import chunk_manifest, extract_chunk, verify_recording
from v2_helpers import envelope, propose, text_fixture, wire


class CandidateV2Tests(unittest.TestCase):
    def setUp(self):
        self.text = text_fixture()
        self.run = envelope(self.text)

    def test_multi_page_answer_retains_both_segments_and_refuses_legacy_export(self):
        result = verify_v2(CandidateV2.model_validate(propose(wire())), self.run, self.text)
        item = result.targets[0].fields["answer_text"].items[0]
        self.assertEqual([e.page for e in item.evidence], [2, 3])
        self.assertEqual(item.value, "Réponse: première clause.\n\nSuite: sous condition de financement.")
        with self.assertRaisesRegex(ValueError, "Lossy"):
            legacy_projection(result)
        self.assertEqual(benchmark_projection(result)["fields"]["answer_text"]["value"], item.value)

    def test_two_submitters_keep_original_block_and_both_typed_mentions(self):
        data = propose(wire(), "submitter_raw", [(1, "Alice Example; Bob Exemple")], pid="block")
        data["targets"][0]["actors"] = [{"proposal_id": "a" + str(i), "name": {
            "item_id": "block", "segment_index": 0, "quote": name}, "role": None}
            for i, name in enumerate(["Alice Example", "Bob Exemple"])]
        result = verify_v2(CandidateV2.model_validate(data), self.run, self.text)
        actors = result.targets[0].structures["actors"]
        self.assertEqual([a["evidence"][0]["quote"] for a in actors], ["Alice Example", "Bob Exemple"])
        self.assertEqual(result.targets[0].structure_status["events"], "not_extracted")
        with self.assertRaisesRegex(ValueError, "typed structures"):
            legacy_projection(result)

    def test_two_affairs_in_minutes_cannot_steal_the_other_section(self):
        text = text_fixture(["Affair 1: approved.\nAffair 2: rejected."])
        split = text.pages[0].text.index("Affair 2")
        scopes = [ScopeBinding(scope_id=sid, subject_id=subject, artifact_id=text.artifact_id, text_snapshot_id=text.id,
            association_version="1", role_version="1", role="minutes", membership="reviewed",
            windows=[ScopeWindow(page=1, layer_id="native", start=start, end=end)]) for sid, subject, start, end in
            [("s1", "affair1", 0, split), ("s2", "affair2", split, len(text.pages[0].text))]]
        run = envelope(text, scopes)
        data = propose(wire(("s1", "s2")), "decision_raw", [(1, "approved.")], pid="d1")
        propose(data, "decision_raw", [(1, "rejected.")], target=1, pid="d2")
        result = verify_v2(CandidateV2.model_validate(data), run, text)
        with self.assertRaisesRegex(ValueError, "explicit target"):
            legacy_projection(result)
        self.assertEqual(legacy_projection(result, "s2").decision_raw.value, "rejected.")
        data["targets"][0]["fields"]["decision_raw"]["items"][0]["segments"][0]["quote"] = "rejected."
        invalid = verify_v2(CandidateV2.model_validate(data), run, text)
        self.assertEqual(invalid.targets[0].fields["decision_raw"].items[0].reason, "outside_subject_scope")

    def test_wire_rejects_missing_slots_extra_keys_and_false_abstention(self):
        variants = []
        data = wire(); del data["targets"][0]["fields"]["title"]; variants.append(data)
        data = wire(); data["approved"] = True; variants.append(data)
        data = wire(); data["targets"][0]["fields"]["title"]["abstention_reason"] = None; variants.append(data)
        data = propose(wire()); data["targets"][0]["fields"]["answer_text"]["items"][0]["segments"][0]["start"] = 0; variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                CandidateV2.model_validate(data)

    def test_duplicate_ids_dangling_refs_out_of_manifest_and_unknown_scope_rejected(self):
        variants = []
        data = propose(wire()); propose(data, "title", [(1, "Motion")], pid="answer1"); variants.append(data)
        data = propose(wire()); data["targets"][0]["actors"] = [{"proposal_id": "a", "name": {"item_id": "missing", "segment_index": 0, "quote": "name"}, "role": None}]; variants.append(data)
        data = propose(wire()); data["targets"][0]["fields"]["answer_text"]["items"][0]["segments"][0]["page"] = 99; variants.append(data)
        data = wire(("unknown",)); variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                verify_v2(CandidateV2.model_validate(data), self.run, self.text)

    def test_repeated_quote_needs_unique_exact_context_and_unicode_offsets(self):
        text = text_fixture(["😀 e\u0301 Motion.\nOther Motion."])
        run = envelope(text)
        data = propose(wire(), "title", [(1, "Motion")], pid="title")
        ambiguous = verify_v2(CandidateV2.model_validate(data), run, text)
        self.assertEqual(ambiguous.targets[0].fields["title"].items[0].evidence_outcome, "ambiguous_location")
        data["targets"][0]["fields"]["title"]["items"][0]["segments"][0]["context_anchor"] = "😀 e\u0301 Motion."
        resolved = verify_v2(CandidateV2.model_validate(data), run, text)
        evidence = resolved.targets[0].fields["title"].items[0].evidence[0]
        self.assertEqual(text.pages[0].text[evidence.start:evidence.end], "Motion")
        target = citation(evidence, text)
        self.assertEqual(target["utf16_start"], evidence.start + 1)

    def test_wrong_order_and_overlapping_segments_rejected(self):
        for segments in [[(3, self.text.pages[2].text), (2, self.text.pages[1].text)],
                         [(2, self.text.pages[1].text), (2, "première clause.")]]:
            with self.assertRaises(ValueError):
                verify_v2(CandidateV2.model_validate(propose(wire(), segments=segments)), self.run, self.text)

    def test_unresolved_alternatives_are_not_arbitrarily_selected(self):
        data = propose(wire(), "title", [(1, "Motion")], pid="title1")
        extra = {"proposal_id": "title2", "segments": [{"page": 1, "layer_id": "native", "quote": "Question?"}]}
        data["targets"][0]["fields"]["title"]["items"].append(extra)
        result = verify_v2(CandidateV2.model_validate(data), self.run, self.text)
        self.assertIsNone(benchmark_projection(result)["fields"]["title"]["value"])
        self.assertEqual(benchmark_projection(result, selections={"title": "title2"})["fields"]["title"]["value"], "Question?")

    def test_recommendation_is_not_a_decision_relation(self):
        data = propose(wire())
        ref = {"item_id": "answer1", "segment_index": 0, "quote": self.text.pages[1].text}
        target = data["targets"][0]
        target["response_items"] = [{"proposal_id": "r", "content": [ref], "label": None}]
        target["events"] = [{"proposal_id": "e", "kind": "recommendation", "act": [ref], "date": None, "actor_ids": []}]
        target["relations"] = [{"proposal_id": "link", "kind": "response_decision", "source": {"kind": "response", "id": "r"},
                               "target": {"kind": "event", "id": "e"}, "evidence": [ref], "printed_label": None}]
        with self.assertRaisesRegex(ValueError, "recommendation"):
            verify_v2(CandidateV2.model_validate(data), self.run, self.text)
        target["events"][0]["kind"] = "decision"
        result = verify_v2(CandidateV2.model_validate(data), self.run, self.text)
        self.assertTrue(result.targets[0].structures["relations"][0]["semantic_review_required"])


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self.manifest = ChunkManifest(available_pages=[1, 2, 3, 4], selected_pages=[1, 2, 3],
            chunks=[Chunk(id="a", pages=[1, 2]), Chunk(id="b", pages=[2, 3])], selection_policy="fixture_overlap")
        self.outcomes = [ChunkOutcome(chunk_id=k, state="completed", finish_reason="stop", response_valid=True) for k in ["a", "b"]]

    def assess(self, outcomes=None, **kwargs):
        return assess_completeness(self.manifest, self.outcomes if outcomes is None else outcomes,
                                   scope_identity="scope", assertion_identity="claim", **kwargs)

    def test_successful_chunks_prove_coverage_but_not_semantic_completeness(self):
        result = self.assess()
        self.assertTrue(result["input_coverage"]["all_selected_processed"])
        self.assertEqual(result["input_coverage"]["unselected_pages"], [4])
        self.assertEqual(result["generation_completion"], "complete")
        self.assertEqual(result["semantic_completeness"], "unknown")

    def test_missing_chunk_truncation_and_observed_continuation_force_incomplete(self):
        self.assertEqual(self.assess(self.outcomes[:1])["semantic_completeness"], "incomplete")
        truncated = self.outcomes[1].model_copy(update={"finish_reason": "length"})
        self.assertEqual(self.assess([self.outcomes[0], truncated])["semantic_completeness"], "incomplete")
        self.assertEqual(self.assess(unsatisfied_continuation=True)["semantic_completeness"], "incomplete")

    def test_checked_boundaries_and_clauses_required_and_cannot_override_failed_chunk(self):
        check = SectionCheck(reviewer="Engineering fixture", note="Checked synthetic section", scope_identity="scope",
                             assertion_identity="claim", boundary_checked=True, required_clauses_checked=False, complete=True)
        self.assertEqual(self.assess(check=check)["semantic_completeness"], "unknown")
        check.required_clauses_checked = True
        self.assertEqual(self.assess(check=check)["semantic_completeness"], "complete_in_reviewed_scope")
        self.assertEqual(self.assess(self.outcomes[:1], check=check)["semantic_completeness"], "incomplete")
        check.assertion_identity = "another_claim"
        with self.assertRaises(ValueError):
            self.assess(check=check)

    def test_valid_fully_located_shortened_answer_stays_unknown(self):
        text = text_fixture()
        run = envelope(text)
        data = propose(wire(), segments=[(2, text.pages[1].text)])
        record = verify_recording(text, run, chunk_manifest(text), chunk_id="chunk-1", content=json.dumps(data), finish_reason="stop")
        self.assertIsNotNone(record["result"])
        report = assess_completeness(chunk_manifest(text), [ChunkOutcome.model_validate(record["outcome"])],
                                      scope_identity="s", assertion_identity="short")
        self.assertEqual(report["semantic_completeness"], "unknown")

    def test_unknown_provider_signal_retained_and_raw_truncation_saved(self):
        text = text_fixture(); run = envelope(text); manifest = chunk_manifest(text)
        data = json.dumps(propose(wire()))
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"model": run.model_identity,
            "choices": [{"finish_reason": "length", "message": {"content": data}}]}))
        record = extract_chunk(text, run, manifest, chunk_id="chunk-1", settings=Settings(run.model_identity, "https://fixture.invalid", ""),
                               max_tokens=8192, transport=transport)
        self.assertEqual(record["content"], data)
        self.assertEqual(record["outcome"]["finish_reason"], "length")
        self.assertIsNone(record["result"])
        unknown = self.outcomes[1].model_copy(update={"finish_reason": None})
        self.assertEqual(self.assess([self.outcomes[0], unknown])["generation_completion"], "unknown")

    def test_transport_failure_is_one_recorded_uncertain_attempt_without_retry(self):
        text = text_fixture(); run = envelope(text); calls = []
        def timeout(request):
            calls.append(request)
            raise httpx.ReadTimeout("fixture timeout")
        record = extract_chunk(text, run, chunk_manifest(text), chunk_id="chunk-1",
            settings=Settings(run.model_identity, "https://fixture.invalid", ""), max_tokens=8192,
            transport=httpx.MockTransport(timeout))
        self.assertEqual(len(calls), 1)
        self.assertEqual(record["remote_completion"], "unknown")
        self.assertEqual(record["outcome"]["state"], "failed")
        self.assertIsNone(record["usage"])
        self.assertIsNone(record["content"])


class CitationTests(unittest.TestCase):
    def test_image_transcription_and_recorded_region_capabilities(self):
        segment = EvidenceSegment(artifact_id="fixture", text_snapshot_id=None, page=1, layer_id=None,
                                   basis="image", quote="Transcribed wording", note="Checked original page footer")
        self.assertEqual(citation(segment)["capability"], "page_transcription")
        self.assertNotIn("start", citation(segment))
        segment.region = PDFRegion(x=10.0, y=20.0, width=40.0, height=20.0, render_width=100, render_height=200,
                                   transform=[1.0, 0.0, 0.0, 1.0, 0.0, 0.0], render_identity="fixture-render")
        self.assertEqual(citation(segment)["capability"], "pdf_region")

    def test_invalid_region_image_offsets_and_stale_text_rejected(self):
        with self.assertRaises(ValidationError):
            PDFRegion(x=90.0, y=20.0, width=40.0, height=20.0, render_width=100, render_height=200,
                      transform=[1.0, 0.0, 0.0, 1.0, 0.0, 0.0], render_identity="fixture")
        with self.assertRaises(ValidationError):
            EvidenceSegment(artifact_id="fixture", text_snapshot_id=None, page=1, layer_id=None, basis="image",
                            quote="Text", note="Visual", start=0, end=4)
        text = text_fixture(); result = verify_v2(CandidateV2.model_validate(propose(wire())), envelope(text), text)
        evidence = result.targets[0].fields["answer_text"].items[0].evidence[0]
        other = text.model_copy(deep=True); other.pages[0].text += " parser change"
        with self.assertRaises(ValueError):
            citation(evidence, other)


if __name__ == "__main__":
    unittest.main()
