import copy
import unittest

from src.skony.study import SplitLink, StudyPolicy, StudyUnit, acquisition_report, connected_groups, freeze_cohort, load_cohort
from evaluation_helpers import AT, cohort_for, study_unit


class StudyTests(unittest.TestCase):
    def test_metadata_hints_do_not_close_acquisition_gate(self):
        cohort = cohort_for([study_unit(verified=False)])
        self.assertFalse(cohort["acquisition"]["passed"])
        self.assertEqual(cohort["acquisition"]["verified_documents"], 0)
        self.assertEqual(cohort["acquisition"]["unverified_units"], 1)

    def test_pairs_require_verified_roles_and_namespaced_affair(self):
        a, b = study_unit("request", affair="42"), study_unit("response", affair="42", role="executive_response")
        report = cohort_for([a, b])["acquisition"]
        self.assertEqual(report["verified_pairs"], 1)
        b = study_unit("response", affair="42", body="another-body", role="executive_response")
        self.assertEqual(cohort_for([a, b])["acquisition"]["verified_pairs"], 0)

    def test_automated_intake_is_not_human_verification(self):
        unit = study_unit()
        unit.review.kind = "automated"
        self.assertFalse(cohort_for([unit])["experiment_committed"])

    def test_large_study_cannot_lower_its_own_thresholds(self):
        with self.assertRaises(ValueError):
            StudyPolicy(mode="large")

    def test_failed_sources_remain_in_frozen_denominator(self):
        failed = StudyUnit(unit_id="unavailable:s:failed", source_id="s", artifact_id=None, scope_id="failed",
            body_id="body1", body_key="body1", affair_id="lost", source_status="failed", failure_reason="source_fetch_failed",
            available_pages=[], split="test")
        cohort = cohort_for([study_unit(), failed])
        self.assertEqual(len(load_cohort(cohort)), 2)
        self.assertEqual(cohort["acquisition"]["source_failures"], 1)

    def test_shared_artifacts_link_separate_affairs_for_split_only(self):
        a, b = study_unit("a", verified=False), study_unit("b", verified=False)
        b.artifact_id = a.artifact_id
        b.unit_id = a.artifact_id + ":" + b.scope_id
        self.assertEqual(len(connected_groups([a, b], [])), 1)
        self.assertNotEqual(a.affair_id, b.affair_id)

    def test_shared_affair_and_translation_transitive_split_leakage_is_rejected(self):
        a, b, c = study_unit("a", affair="x"), study_unit("b", affair="x"), study_unit("c", split="development")
        with self.assertRaisesRegex(ValueError, "crosses"):
            freeze_cohort([a, b, c], StudyPolicy(mode="bounded", minimum_bodies=1, minimum_levels=1),
                links=[SplitLink(left=b.unit_id, right=c.unit_id, kind="translation", reviewer="test", reference="fixture")],
                frozen_at=AT)

    def test_duplicate_units_and_tampering_are_rejected(self):
        with self.assertRaises(ValueError):
            cohort_for([study_unit(), study_unit()])
        cohort = copy.deepcopy(cohort_for())
        cohort["acquisition"]["verified_pairs"] = 99
        with self.assertRaises(ValueError):
            load_cohort(cohort)

    def test_unassigned_units_do_not_commit_an_experiment(self):
        self.assertFalse(cohort_for([study_unit(split="unassigned")])["experiment_committed"])

    def test_cohort_round_trip_is_deterministic(self):
        cohort = cohort_for()
        self.assertEqual(len(load_cohort(cohort)), 2)
        self.assertEqual(cohort["digest"], cohort_for()["digest"])
