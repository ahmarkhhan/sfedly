import copy
import unittest

from src.skony.evaluation_insights import (FeasibilityJudgment, PDFAddition, feasibility_matrix,
    corpus_coverage, corpus_coverage_markdown, metadata_baseline, novelty_report, pointer)
from src.skony.gold import Prediction
from src.skony.study import StudyPolicy, StudyUnit, freeze_cohort
from evaluation_helpers import AT, citation, cohort_for, gold_for, source, study_unit


def addition(**changes):
    data = dict(fact_key="answer", value="Motion", contribution="additional_detail",
        explanation="Invented example, not an actual novelty conclusion", reviewer_id="simulated-reviewer",
        reviewer_kind="human", reviewed_at="2026-10-15T09:00:00Z", snapshot_id="fixture-snapshot",
        review_decision_id="fixture-decision", evidence=[citation()])
    data.update(changes)
    return PDFAddition(**data)


class InsightsTests(unittest.TestCase):
    def test_saved_metadata_query_is_reproducible_and_escaped_paths_work(self):
        data = {"a/b": [{"x~y": "Motion"}]}
        self.assertEqual(pointer(data, "/a~1b/0/x~0y")["value"], "Motion")
        self.assertFalse(pointer(data, "/missing")["available"])
        with self.assertRaises(ValueError):
            pointer(data, "not-a-pointer")

    def test_metadata_only_demonstration_does_not_pass_novelty(self):
        baseline = metadata_baseline({"answer": "Motion"}, question="Fixture?", source_reference="fixture://metadata",
                                     queries={"answer": "/answer"}, recorded_at=AT)
        self.assertFalse(novelty_report(baseline, [addition()], [source()])["passed"])

    def test_missing_structured_key_cannot_hide_an_answer_already_in_metadata_text(self):
        baseline = metadata_baseline({"text": "The printed title is Motion."}, question="Fixture?", source_reference="fixture://metadata",
                                     queries={"answer": "/answer"}, recorded_at=AT)
        result = novelty_report(baseline, [addition()], [source()])
        self.assertFalse(result["passed"])
        self.assertTrue(result["findings"][0]["value_found_in_saved_metadata_text"])

    def test_additional_human_reviewed_pdf_fact_has_anchored_evidence(self):
        baseline = metadata_baseline({}, question="Fixture?", source_reference="fixture://metadata",
                                     queries={"answer": "/answer"}, recorded_at=AT)
        self.assertTrue(novelty_report(baseline, [addition()], [source()])["passed"])
        self.assertFalse(novelty_report(baseline, [addition(reviewer_kind="automated")], [source()])["passed"])

    def test_baseline_before_pdf_review_and_source_identity_are_required(self):
        baseline = metadata_baseline({}, question="Fixture?", source_reference="fixture://metadata",
                                     queries={"answer": "/answer"}, recorded_at=AT)
        with self.assertRaises(ValueError):
            novelty_report(baseline, [addition(reviewed_at="2026-10-15T07:00:00Z")], [source()])
        bad = addition()
        bad.evidence[0].quote = "Fabricated"
        with self.assertRaises(ValueError):
            novelty_report(baseline, [bad], [source()])
        baseline["facts"]["answer"] = {"available": True, "value": "Fake"}
        with self.assertRaises(ValueError):
            novelty_report(baseline, [], [])

    def test_pipeline_failure_does_not_infer_schema_infeasibility(self):
        unit = study_unit()
        gold = gold_for(unit, cohort_for())
        matrix = feasibility_matrix([unit.body_id], ["title"], [], [], [gold],
                                    [Prediction(unit_id=unit.unit_id, outcome="failed", fields={})])
        cell = matrix["cells"][0]
        self.assertEqual(cell["expressivity"], "untested")
        self.assertEqual(cell["harmonization"], "unmapped")
        self.assertEqual(cell["pipeline_recovery"]["recall"], 0)

    def test_partial_or_negative_schema_and_mapping_need_counterexamples(self):
        for expressivity, mapping in (("partial", "unmapped"), ("not_representable", "unmapped"),
                                      ("faithful", "conditional_with_mapping"), ("faithful", "semantic_collision")):
            with self.assertRaisesRegex(ValueError, "counterexample"):
                FeasibilityJudgment(body_id="body1", concept="title", expressivity=expressivity,
                    harmonization=mapping, reviewer_id="simulated", reviewer_kind="human", rationale="Fixture",
                    evidence=[citation()], counterexamples=[])

    def test_automated_schema_judgments_remain_explicitly_untested(self):
        judgment = FeasibilityJudgment(body_id="body1", concept="title", expressivity="partial",
            harmonization="semantic_collision", reviewer_id="automated-fixture", reviewer_kind="automated",
            rationale="Fixture only", evidence=[citation()], counterexamples=[citation()])
        matrix = feasibility_matrix(["body1"], ["title"], [judgment], [source()], [], [])
        self.assertEqual(matrix["cells"][0]["expressivity"], "untested")

    def test_conditional_human_judgment_preserves_cited_counterexample(self):
        judgment = FeasibilityJudgment(body_id="body1", concept="title", expressivity="partial",
            harmonization="unmapped", reviewer_id="simulated", reviewer_kind="human", rationale="Fixture only",
            evidence=[citation()], counterexamples=[citation()])
        matrix = feasibility_matrix(["body1"], ["title"], [judgment], [source()], [], [])
        self.assertEqual(matrix["cells"][0]["expressivity"], "partial")
        self.assertTrue(matrix["cells"][0]["judgment"]["counterexamples"])

    def test_corpus_coverage_separates_verified_values_from_hints_and_keeps_failures(self):
        checked = study_unit("checked", body="body-fr", language="fr", role="executive_response")
        hint = study_unit("hint", body="body-de", language="de", role="submission", verified=False)
        failed = StudyUnit(unit_id="unavailable:missing:scope-missing", source_id="missing", artifact_id=None,
            scope_id="scope-missing", body_id="body-de", body_key="body-de", affair_id="lost",
            language_hint="de", role_hint="submission", source_status="failed",
            failure_reason="source_fetch_failed", available_pages=[], hard_case=True, split="unassigned")
        cohort = freeze_cohort([checked, hint, failed], StudyPolicy(mode="bounded", minimum_documents=1,
            maximum_documents=None, minimum_bodies=1, minimum_levels=1), frozen_at=AT)

        report = corpus_coverage(cohort)

        self.assertEqual(report["counts"]["unit_count"], 3)
        self.assertEqual(report["counts"]["distinct_artifact_count"], 2)
        self.assertEqual(report["counts"]["failed_unit_count"], 1)
        languages = {(row["value"], row["basis"]): row["unit_count"]
                     for row in report["dimensions"]["language"]}
        self.assertEqual(languages[("fr", "human_checked")], 1)
        self.assertEqual(languages[("unverified:de", "metadata_hint")], 2)
        self.assertIn("| Source units | 3 |", corpus_coverage_markdown(report))

    def test_coverage_detects_tampered_cohort_and_is_deterministic(self):
        cohort = cohort_for([study_unit("verified"), study_unit("candidate", verified=False)])
        report = corpus_coverage(cohort)
        self.assertEqual(report, corpus_coverage(cohort))
        cohort["units"][0]["language_hint"] = "fr"
        with self.assertRaisesRegex(ValueError, "identity check"):
            corpus_coverage(cohort)

    def test_structural_census_joins_only_frozen_pdf_hashes_and_reports_hard_cases(self):
        checked = study_unit("checked", body="body-fr", language="fr", role="executive_response")
        hint = study_unit("hint", body="body-de", language="de", role="submission", verified=False)
        cohort = freeze_cohort([checked, hint], StudyPolicy(mode="bounded", minimum_documents=1,
            maximum_documents=None, minimum_bodies=1, minimum_levels=1), frozen_at=AT)
        census = {"schema_version": "skony.structure-census.v0.1", "counts": {"processed": 2}, "documents": [
            {"document_id": checked.artifact_id, "body": "Body FR", "language": "fr", "pages": 2,
             "textless_pages": 1, "annexes": 0, "images": 1, "table_hints": 0},
            {"document_id": hint.artifact_id, "body": "Body DE", "language": "de", "pages": 3,
             "textless_pages": 0, "annexes": 1, "images": 0, "table_hints": 2},
        ]}

        report = corpus_coverage(cohort, census)

        structural = report["structural_inventory"]
        self.assertEqual(structural["joined_document_count"], 2)
        self.assertEqual(structural["documents_with_textless_pages"], 1)
        self.assertEqual(structural["totals"]["images"], 1)
        self.assertIn("Structural hard-case inventory", corpus_coverage_markdown(report))
        census["documents"][0]["document_id"] = "outside-the-cohort"
        with self.assertRaisesRegex(ValueError, "outside the frozen cohort"):
            corpus_coverage(cohort, census)
