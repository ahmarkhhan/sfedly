import copy
import unittest

from src.skony.relations import (RelationAnnotation, RelationGold, RelationNode, RelationPrediction,
                                 freeze_universe, merge_relation_packets, relation_packet, score_relations)
from evaluation_helpers import AT, citation, source


def universe():
    evidence = [citation()]
    nodes = [RelationNode(id="a1", kind="affair", body_id="b1", affair_key="b1:42"),
             RelationNode(id="a2", kind="affair", body_id="b2", affair_key="b2:42"),
             RelationNode(id="d", kind="affair_document", body_id="b1", affair_key="b1:42", unit_id="u", evidence=evidence),
             RelationNode(id="q", kind="question", body_id="b1", affair_key="b1:42", unit_id="u", evidence=evidence),
             RelationNode(id="r1", kind="response", body_id="b1", affair_key="b1:42", unit_id="u", evidence=evidence),
             RelationNode(id="r2", kind="response", body_id="b1", affair_key="b1:42", unit_id="u", evidence=evidence),
             RelationNode(id="decision", kind="decision", body_id="b1", affair_key="b1:42", unit_id="u", evidence=evidence)]
    return freeze_universe(nodes, [source()], kinds=["affair_document", "question_response", "response_decision"],
                           frozen_at=AT, inventory_note="Invented candidate inventory for engineering tests only")


def relation_gold(uni, pair, disposition="positive", status="independently_agreed"):
    annotation = dict(annotator_id="simulated-a", kind="human", mode="blind", independent=True,
        language_competence="simulated", procedural_competence="simulated", locked_at="2026-10-15T09:00:00Z",
        label=disposition, checked_node_ids=[pair["source_id"], pair["target_id"]], evidence=[citation()],
        rationale="Invented engineering review record")
    return RelationGold(universe_digest=uni["digest"], candidate_id=pair["candidate_id"], label=disposition,
        status=status, annotations=[RelationAnnotation(**annotation), RelationAnnotation(**{**annotation, "annotator_id": "simulated-b"})]
        if status != "single_annotator_final" else [RelationAnnotation(**annotation)])


class RelationTests(unittest.TestCase):
    def test_inventory_contains_cross_body_decoys_and_unaligned_candidates(self):
        uni = universe()
        self.assertEqual(len(uni["candidates"]), 6)
        self.assertTrue(any(p["source_id"] == "a2" and p["target_id"] == "d" for p in uni["candidates"]))

    def test_positive_negative_and_unknowns_score_separately_per_relation_kind(self):
        uni = universe()
        labels = [relation_gold(uni, p, "positive" if i % 2 else "negative") for i, p in enumerate(uni["candidates"])]
        predictions = [RelationPrediction(candidate_id=g.candidate_id, label=g.label) for g in labels]
        result = score_relations(uni, labels, predictions)
        self.assertTrue(result["gate_passed"])
        self.assertEqual(set(result["per_kind"]), {"affair_document", "question_response", "response_decision"})
        self.assertEqual(sum(v["fp"] + v["fn"] for v in result["per_kind"].values()), 0)

    def test_unlabelled_candidates_are_not_silently_dropped(self):
        result = score_relations(universe(), [], [])
        self.assertEqual(result["unlabelled"], 6)
        self.assertFalse(result["gate_passed"])

    def test_unknown_gold_and_missing_prediction_are_not_correct_negatives(self):
        uni = universe()
        g = relation_gold(uni, uni["candidates"][0], "unknown")
        result = score_relations(uni, [g], [])
        self.assertEqual(sum(v.get("correct_negative", 0) for v in result["per_kind"].values()), 0)

    def test_duplicate_predictions_and_out_of_universe_links_are_rejected(self):
        uni = universe()
        p = RelationPrediction(candidate_id=uni["candidates"][0]["candidate_id"], label="positive")
        for predictions in ([p, p], [RelationPrediction(candidate_id="invented", label="positive")]):
            with self.assertRaises(ValueError):
                score_relations(uni, [], predictions)

    def test_single_assisted_and_automated_labels_are_excluded(self):
        uni = universe()
        for kind in ("single", "assisted", "automated"):
            g = relation_gold(uni, uni["candidates"][0], status="single_annotator_final" if kind == "single" else "independently_agreed")
            if kind != "single":
                for a in g.annotations:
                    if kind == "assisted":
                        a.mode = "assisted"
                    else:
                        a.kind = "automated"
            result = score_relations(uni, [g], [])
            self.assertEqual(sum(v.get("scorable", 0) for v in result["per_kind"].values()), 0)

    def test_relation_reviews_check_both_endpoints_and_original_citations(self):
        uni = universe()
        g = relation_gold(uni, uni["candidates"][0])
        g.annotations[0].checked_node_ids = ["other", "another"]
        with self.assertRaises(ValueError):
            score_relations(uni, [g], [])
        g = relation_gold(uni, uni["candidates"][0])
        g.annotations[0].evidence[0].quote = "Fabricated"
        with self.assertRaises(ValueError):
            score_relations(uni, [g], [])

    def test_packet_has_every_candidate_and_no_model_labels(self):
        uni = universe()
        packet = relation_packet(uni, "independent-reviewer")
        self.assertEqual(len(packet["tasks"]), 6)
        self.assertTrue(all(t["annotation"] is None for t in packet["tasks"]))
        self.assertFalse(packet["model_proposals_included"])

    def test_tampered_universe_is_rejected(self):
        uni = copy.deepcopy(universe())
        uni["candidates"].pop()
        with self.assertRaises(ValueError):
            score_relations(uni, [], [])

    def test_independent_packet_merge_retains_disagreements_and_missing_annotations(self):
        uni = universe()
        packets = [relation_packet(uni, person) for person in ("simulated-a", "simulated-b")]
        pair = uni["candidates"][0]
        g = relation_gold(uni, pair)
        for packet, annotation in zip(packets, g.annotations):
            packet["tasks"][0]["annotation"] = annotation.model_dump()
        merged = merge_relation_packets(uni, packets)
        first = next(g for g in merged["labels"] if g["candidate_id"] == pair["candidate_id"])
        self.assertEqual(first["status"], "independently_agreed")
        packets[1]["tasks"][0]["annotation"]["label"] = "negative"
        merged = merge_relation_packets(uni, packets)
        first = next(g for g in merged["labels"] if g["candidate_id"] == pair["candidate_id"])
        self.assertEqual(first["status"], "unresolved")
        self.assertEqual(first["label"], "unknown")
        self.assertEqual(len(first["annotations"]), 2)

    def test_packet_dropping_a_negative_candidate_is_rejected(self):
        uni = universe()
        packet = relation_packet(uni, "simulated-a")
        packet["tasks"].pop()
        with self.assertRaisesRegex(ValueError, "dropped"):
            merge_relation_packets(uni, [packet])

    def test_all_unknown_labels_preserve_coverage_but_cannot_claim_relation_accuracy(self):
        uni = universe()
        labels = [relation_gold(uni, pair, "unknown") for pair in uni["candidates"]]
        self.assertFalse(score_relations(uni, labels, [])["gate_passed"])
