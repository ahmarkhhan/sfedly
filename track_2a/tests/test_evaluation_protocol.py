import unittest

from src.skony.evaluation_protocol import Calibration, Reviewer, ReviewSession, UpliftDesign, review_protocol, review_uplift
from src.skony.gold import Prediction
from src.skony.contracts import FIELDS, identity
from evaluation_helpers import AT, cohort_for, gold_for, study_unit


def reviewer(name, development=None, language="de", body="body1"):
    development = development or study_unit("dev", split="development")
    return Reviewer(id=name, kind="human", languages=[language], body_ids=[body],
        procedural_competence="Simulated competence, engineering fixture only",
        calibration=[Calibration(development_unit_ids=[development.unit_id], guide_digest="invented-guide",
            completed_at="2026-10-15T08:10:00Z", resolution_note="Simulated calibration, not human work")])


def session(name, person, unit=None, **kwargs):
    unit = unit or study_unit()
    values = dict(id=name, reviewer_id=person, mode="blind", unit_ids=[unit.unit_id], capabilities=["fields", "roles", "relations"],
        independent=True, exposure_disclosed=True, exposed_gold_unit_ids=[], saw_model_output=False,
        started_at="2026-10-15T09:00:00Z", finished_at="2026-10-15T09:10:00Z", active_seconds=300.0,
        actions=8, corrections=1, reversals=0, unresolved_fields=0)
    values.update(kwargs)
    return ReviewSession(**values)


class ProtocolTests(unittest.TestCase):
    def test_two_calibrated_independent_reviewers_pass_and_report_workload_only(self):
        result = review_protocol(cohort_for(), [reviewer("a"), reviewer("b")], [session("a1", "a"), session("b1", "b")])
        self.assertTrue(result["passed"], result["reasons"])
        self.assertFalse(result["accuracy_uplift_claim"])
        self.assertEqual(result["workload"]["blind"]["actions"], 16)

    def test_one_review_is_disclosed_and_does_not_pass_independent_gate(self):
        result = review_protocol(cohort_for(), [reviewer("a")], [session("a1", "a")])
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["singly_or_unreviewed_strata"]), 1)

    def test_independent_minimum_covers_every_body_not_only_twenty_five_percent(self):
        dev = study_unit("dev", split="development")
        units = [dev] + [study_unit(str(i), body="body" + str(i % 6)) for i in range(18)]
        result = review_protocol(cohort_for(units), [], [])
        self.assertEqual(result["required_independent_affairs"], 6)

    def test_calibration_on_test_cases_is_rejected(self):
        person = reviewer("a", study_unit())
        with self.assertRaisesRegex(ValueError, "development"):
            review_protocol(cohort_for(), [person], [])

    def test_wrong_language_wrong_body_and_automated_reviewer_are_not_eligible(self):
        for change in ("language", "body", "automated"):
            person = reviewer("a")
            if change == "language":
                person.languages = ["fr"]
            elif change == "body":
                person.body_ids = ["other"]
            else:
                person.kind = "automated"
            self.assertFalse(review_protocol(cohort_for(), [person], [session("a1", "a")])["passed"])

    def test_assisted_exposed_or_uncalibrated_sessions_do_not_count_as_blind(self):
        a = session("a1", "a", mode="assisted", saw_model_output=True)
        result = review_protocol(cohort_for(), [reviewer("a"), reviewer("b")], [a, session("b1", "b")])
        self.assertFalse(result["passed"])
        with self.assertRaises(ValueError):
            session("a1", "a", exposed_gold_unit_ids=[study_unit().unit_id])

    def test_unchecked_hard_case_and_relation_capability_leave_gate_open(self):
        hard = study_unit("hard")
        hard.hard_case = True
        result = review_protocol(cohort_for([study_unit("dev", split="development"), study_unit(), hard]),
            [reviewer("a"), reviewer("b")], [session("a1", "a"), session("b1", "b")], claimed_relations=True)
        self.assertIn("no_independently_reviewed_hard_case", result["reasons"])

    def test_impossible_time_and_action_records_are_rejected(self):
        for args in ({"active_seconds": 1000.0}, {"actions": 0}, {"started_at": "2026-10-15T09:00:00"}):
            with self.assertRaises(ValueError):
                session("a1", "a", **args)

    def test_default_does_not_turn_reviewed_outputs_into_gold_uplift(self):
        result = review_protocol(cohort_for(), [], [])
        self.assertFalse(result["accuracy_uplift_claim"])

    def test_independent_matched_uplift_and_circular_overlap_rejection(self):
        cohort = cohort_for()
        gold = [gold_for(study_unit(), cohort)]
        gold_digest = identity([g.model_dump() for g in gold])
        control = session("control", "c")
        assisted = session("assisted", "d", mode="assisted", saw_model_output=True)
        control.predictions = [Prediction(unit_id=study_unit().unit_id, outcome="completed", fields={f: None for f in FIELDS})]
        assisted.predictions = [Prediction(unit_id=study_unit().unit_id, outcome="completed",
                                           fields={f: "Motion" if f == "title" else None for f in FIELDS})]
        sessions = [session("gold1", "a"), session("gold2", "b"), control, assisted]
        people = [reviewer(name) for name in "abcd"]
        design = UpliftDesign(design="matched_tasks_independent_reviewers", predeclared_at="2026-10-15T08:30:00Z",
            frozen_gold_at="2026-10-15T08:30:00Z", frozen_gold_digest=gold_digest,
            control_session_ids=["control"], assisted_session_ids=["assisted"],
            memory_effects_policy="disjoint_reviewers_no_prior_task_exposure")
        result = review_uplift(cohort, people, sessions, gold, design)
        self.assertEqual(result["field_agreement_f1_difference"], 1.0)
        self.assertFalse(result["semantic_accuracy_claim"])
        assisted.reviewer_id = gold[0].fields["title"].annotations[0].annotator_id
        people.append(reviewer(assisted.reviewer_id))
        with self.assertRaisesRegex(ValueError, "overlap"):
            review_uplift(cohort, people, sessions, gold, design)
