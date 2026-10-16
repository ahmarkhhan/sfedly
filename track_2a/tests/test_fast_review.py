"""Review records must remain bound to their source, reviewer and exposure."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from finalize_fast_review import score_pilot_records, validate_review
from evaluation_helpers import AT, citation, source, study_unit
from src.skony.contracts import identity


def fixture():
    text, unit = source(), study_unit(verified=False)
    document = {"id": text.artifact_id, "text": text.model_dump(), "text_snapshot_id": text.id,
        "unit": unit.model_dump(), "hints": {"language": "de", "level": "municipal"},
        "manifest_index": 0, "filename": "fixture.pdf", "body_label": "Fixture"}
    pack = {"schema_version": "skony.fast-review-pack.v1", "documents": [document],
        "fields": ["title"], "schema_tasks": [], "question": "Fixture only"}
    pack["digest"] = identity(pack)
    review = {"schema_version": "skony.fast-review.v1", "pack_digest": pack["digest"],
        "reviewer": {"id": "test-reviewer", "languages": ["de"], "competence_note": "Engineering fixture, not real review"},
        "documents": {}, "schema_reviews": {}}
    return pack, review


class FastReviewTests(unittest.TestCase):
    def test_empty_review_does_not_manufacture_findings_or_verified_intake(self):
        pack, review = fixture()
        result, cohort, annotations = validate_review(pack, review)
        self.assertEqual(result["counts"]["verified_intake"], 0)
        self.assertEqual(annotations, [])
        self.assertFalse(result["cross_body_answer_demonstrated"])
        self.assertFalse(cohort["experiment_committed"])

    def test_exact_source_quote_required_and_exposure_cannot_be_hidden(self):
        pack, review = fixture()
        doc_id = pack["documents"][0]["id"]
        entry = {"assessment": "present", "value": "Motion", "evidence": citation().model_dump(),
            "reviewer_id": "test-reviewer", "updated_at": AT, "mode": "source_only", "note": ""}
        review["documents"][doc_id] = {"intake": {"status": "unreviewed"}, "fields": {"title": entry}}
        result, _, annotations = validate_review(pack, review)
        self.assertEqual(result["counts"]["source_only_fields"], 1)
        changed = copy.deepcopy(review)
        changed["documents"][doc_id]["fields"]["title"]["evidence"]["quote"] = "Invented"
        with self.assertRaisesRegex(ValueError, "quotation"):
            validate_review(pack, changed)
        changed = copy.deepcopy(review)
        changed["documents"][doc_id]["exposure_at"] = "2026-10-15T07:00:00Z"
        with self.assertRaisesRegex(ValueError, "exposure"):
            validate_review(pack, changed)

    def test_declared_language_competence_is_required(self):
        pack, review = fixture()
        review["reviewer"]["languages"] = []
        with self.assertRaisesRegex(ValueError, "competence"):
            validate_review(pack, review)

    def test_modified_pack_cannot_reuse_reviews(self):
        pack, review = fixture()
        pack["question"] = "Changed after review"
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_review(pack, review)

    def test_wrong_present_prediction_counts_as_false_positive_and_false_negative(self):
        prediction = {"doc": {"fields": {"title": {"status": "source_located", "value": "Wrong"}}}}
        annotation = {"document_id": "doc", "field": "title", "intake_confirmed": True,
            "mode": "source_only", "updated_at": AT, "assessment": "present", "value": "Correct",
            "body_id": "fixture", "language": "de", "level": "municipal"}
        score = score_pilot_records(prediction, [annotation], "2026-10-15T07:00:00Z")
        self.assertEqual(score["counts"], {"tp": 0, "fp": 1, "fn": 1, "tn": 0, "reviewed_fields": 1})
        self.assertEqual(score["exact_field_agreement"], 0)

    def test_assisted_reviews_do_not_enter_production_pilot_denominator(self):
        prediction = {"doc": {"fields": {"title": {"status": "source_located", "value": "Correct"}}}}
        annotation = {"document_id": "doc", "field": "title", "intake_confirmed": True, "mode": "assisted"}
        score = score_pilot_records(prediction, [annotation], "2026-10-15T07:00:00Z")
        self.assertEqual(score["counts"]["reviewed_fields"], 0)
        self.assertIsNone(score["precision"])
