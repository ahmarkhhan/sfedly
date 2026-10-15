import copy
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.skony.contracts import FIELDS, identity
from src.skony.gold import GoldLabel, GoldUnit, Prediction, export_gold_v2, score


def label(assessment="present", status="single_annotator_final", value="Motion", scope="s1"):
    checked = {scope: [1]}
    values = [value] if assessment == "present" else []
    annotation = {"annotator_id": "synthetic-test-person-a", "kind": "human", "mode": "blind",
        "language_competence": "test contract only", "procedural_competence": "test contract only",
        "locked_at": "2026-10-15T00:00:00Z", "scope_identity": identity(checked), "independent": True,
        "assessment": assessment, "acceptable_values": values}
    annotations = [annotation]
    if status in {"independently_agreed", "adjudicated"}:
        annotations.append({**annotation, "annotator_id": "synthetic-test-person-b"})
    return {"assessment": assessment, "acceptable_values": values, "checked_scope": checked,
        "scope_identity": identity(checked), "status": status, "annotations": annotations,
        "adjudication": {"adjudicator_id": "synthetic-test-person-c", "note": "Engineering fixture only",
                         "locked_at": "2026-10-15T00:00:01Z"} if status == "adjudicated" else None}


def unit(scope="s1"):
    return GoldUnit(artifact_id="engineering-fixture-not-gold", scope_id=scope, split_group="fixture-group",
        body_id="fixture-body", language="fixture", fields={name: GoldLabel.model_validate(label(scope=scope)) for name in FIELDS})


class GoldV2Tests(unittest.TestCase):
    def test_primary_and_independent_sensitivity_have_explicit_different_denominators(self):
        gold = unit()
        gold.fields["title"] = GoldLabel.model_validate(label(status="independently_agreed"))
        gold.fields["answer_text"] = GoldLabel.model_validate(label(status="adjudicated"))
        prediction = Prediction(unit_id=gold.unit_id, outcome="completed", fields={name: "Motion" for name in FIELDS})
        result = score([gold], [prediction], frozen_unit_ids=[gold.unit_id])
        self.assertEqual(result["primary"]["micro"]["scorable"], 8)
        self.assertEqual(result["independently_checked_sensitivity"]["micro"]["scorable"], 2)
        self.assertEqual(result["primary"]["scored_status_counts"], {
            "single_annotator_final": 6, "independently_agreed": 1, "adjudicated": 1, "unresolved": 0})

    def test_independence_and_adjudication_cannot_be_faked_by_status_only(self):
        invalid = []
        data = label(); data["status"] = "adjudicated"; invalid.append(data)
        data = label(status="independently_agreed"); data["annotations"][1]["annotator_id"] = data["annotations"][0]["annotator_id"]; invalid.append(data)
        data = label(status="independently_agreed"); data["annotations"][1]["acceptable_values"] = ["Postulat"]; invalid.append(data)
        data = label(status="adjudicated"); data["adjudication"]["adjudicator_id"] = data["annotations"][0]["annotator_id"]; invalid.append(data)
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                GoldLabel.model_validate(data)

    def test_wrong_value_is_fp_and_fn_null_is_fn_and_unknown_is_unscorable(self):
        gold = unit()
        gold.fields["decision_raw"] = GoldLabel.model_validate(label("unreadable"))
        prediction = Prediction(unit_id=gold.unit_id, outcome="completed", fields={name: None for name in FIELDS})
        prediction.fields["title"] = "Wrong"
        prediction.fields["submitter_raw"] = "Motion"
        result = score([gold], [prediction], frozen_unit_ids=[gold.unit_id])["primary"]
        self.assertEqual((result["micro"]["tp"], result["micro"]["fp"], result["micro"]["fn"]), (1, 1, 6))
        self.assertEqual(result["excluded_by_reason"], {"unreadable": 1})

    def test_failed_document_does_not_earn_correct_absence(self):
        gold = unit()
        gold.fields["answer_text"] = GoldLabel.model_validate(label("absent_in_reviewed_scope"))
        failed = Prediction(unit_id=gold.unit_id, outcome="failed", fields={})
        result = score([gold], [failed], frozen_unit_ids=[gold.unit_id, "unlabelled:intake-failure"])
        counts = result["primary"]["per_field"]["answer_text"]
        self.assertEqual((counts["known_absent"], counts["correct_absence"], counts["failed_absent"]), (1, 0, 1))
        self.assertEqual(result["units_without_gold"], 1)
        self.assertEqual(result["operational_outcomes"], {"failed": 1, "not_run": 1})
        self.assertEqual(result["full_cohort_success"], 0)
        self.assertEqual(result["primary"]["scorable_field_fraction"], 8/16)

    def test_correct_absence_absent_fp_and_all_abstain_f1(self):
        gold = unit()
        prediction = Prediction(unit_id=gold.unit_id, outcome="completed", fields={name: None for name in FIELDS})
        micro = score([gold], [prediction], frozen_unit_ids=[gold.unit_id])["primary"]["micro"]
        self.assertIsNone(micro["precision"])
        self.assertEqual((micro["recall"], micro["f1"]), (0, 0))
        gold.fields["answer_text"] = GoldLabel.model_validate(label("absent_in_reviewed_scope"))
        counts = score([gold], [prediction], frozen_unit_ids=[gold.unit_id])["primary"]["per_field"]["answer_text"]
        self.assertEqual(counts["correct_absence"], 1)
        self.assertIsNone(counts["f1"])
        prediction.fields["answer_text"] = "Invented"
        counts = score([gold], [prediction], frozen_unit_ids=[gold.unit_id])["primary"]["per_field"]["answer_text"]
        self.assertEqual(counts["fp"], 1)

    def test_automated_assisted_unresolved_and_synthetic_labels_are_excluded(self):
        for kind in ("automated", "assisted", "unresolved", "synthetic"):
            gold = unit()
            if kind == "synthetic":
                gold.synthetic = True
            else:
                for field in gold.fields.values():
                    if kind == "automated": field.annotations[0].kind = "automated"
                    if kind == "assisted": field.annotations[0].mode = "assisted"
                    if kind == "unresolved": field.status = "unresolved"
            result = score([gold], [], frozen_unit_ids=[gold.unit_id])
            self.assertEqual(result["primary"]["micro"]["scorable"], 0)
            self.assertEqual(sum(result["primary"]["excluded_by_reason"].values()), 8)

    def test_multi_affair_scoring_counts_scopes_and_rejects_duplicate_or_missing_slots(self):
        one, two = unit("s1"), unit("s2")
        result = score([one, two], [], frozen_unit_ids=[one.unit_id, two.unit_id])
        self.assertEqual((result["artifact_count_with_gold"], result["units_with_gold"]), (1, 2))
        self.assertEqual(result["primary"]["micro"]["fn"], 16)
        with self.assertRaises(ValueError):
            score([one, one], [], frozen_unit_ids=[one.unit_id])
        with self.assertRaises(ValidationError):
            Prediction(unit_id=one.unit_id, outcome="completed", fields={})

    def test_v2_export_does_not_overwrite_or_relabel_legacy_gold(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gold"
            gold = unit()
            manifest = export_gold_v2([gold], path)
            self.assertEqual(manifest["gold_schema_version"], "skony.gold.v0.2")
            self.assertEqual(manifest["label_status_counts"]["single_annotator_final"], 8)
            with self.assertRaises(ValueError):
                export_gold_v2([gold], path)
            gold.synthetic = True
            with self.assertRaises(ValueError):
                export_gold_v2([gold], Path(temporary) / "bad")
            self.assertFalse((Path(temporary) / "bad").exists())


if __name__ == "__main__":
    unittest.main()
