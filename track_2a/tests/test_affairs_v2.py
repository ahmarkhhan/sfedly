import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing

from src.skony.affairs import AffairStore
from src.skony.contracts import TextSnapshot, canonical
from src.skony.migration import legacy_inventory, migrate
from src.skony.review import ReviewAction, ReviewError, ReviewStore
from src.skony.review_contracts import AffairRecord, Claim, ComparisonSpec, MappingRule, ScopeRecord
from src.skony.schema import Document, Page
from v2_helpers import accept, claim_for, review_fixture


class ScopedReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.legacy, self.store, self.doc_id, self.document, self.scope = review_fixture(self.directory)
        self.claim = claim_for(self.store, self.scope)

    def tearDown(self):
        self.tmp.cleanup()

    def scope_model(self):
        latest = next(s for s in self.store.scopes() if s["id"] == self.scope["id"])
        return latest, ScopeRecord.model_validate({k: latest[k] for k in ("binding", "source_ids", "mapping_ids")})

    def update_scope(self, mutate):
        latest, scope = self.scope_model()
        mutate(scope)
        self.store.put_scope(scope, revision=latest["revision"], reviewer="Engineering test", note="Fixture dependency change")

    def freeze(self, decision):
        return self.store.freeze([decision["decision_id"]], scope_ids=[self.scope["id"]])

    def test_stale_review_compare_and_swap_preserves_original_decision(self):
        accepted = accept(self.store, self.claim, self.scope)
        with self.assertRaises(ReviewError) as error:
            accept(self.store, self.claim, self.scope, revision=0)
        self.assertEqual(error.exception.status, 409)
        self.assertTrue(self.store.eligibility(accepted["decision_id"])["eligible"])
        self.assertEqual(self.store.review_revision(self.claim), 1)

    def test_role_change_invalidates_semantics_without_destroying_history(self):
        accepted = accept(self.store, self.claim, self.scope)
        frozen = self.freeze(accepted)
        self.update_scope(lambda s: setattr(s.binding, "role", "minutes"))
        status = self.store.eligibility(accepted["decision_id"])
        self.assertIn("changed_role_version", status["reasons"])
        with self.assertRaises(ReviewError):
            self.freeze(accepted)
        historical = self.store.snapshot(frozen["snapshot_id"])
        self.assertEqual(historical["snapshot"], frozen["snapshot"])
        self.assertTrue(historical["historical_warning"])

    def test_membership_change_requires_successor_assertion_even_with_same_quote(self):
        accepted = accept(self.store, self.claim, self.scope)
        self.store.put_affair(AffairRecord(internal_id="affair2", provider_namespace="fixture", body_id="body2", body_key="B2",
            official_affair_id="1", jurisdiction_level="cantonal", source_ids=self.scope["source_ids"]))
        self.update_scope(lambda s: setattr(s.binding, "subject_id", "affair2"))
        status = self.store.eligibility(accepted["decision_id"])
        self.assertIn("changed_association_version", status["reasons"])
        self.assertIn("changed_subject", status["reasons"])
        with self.assertRaisesRegex(ReviewError, "successor assertion"):
            accept(self.store, self.claim, self.scope)

    def test_same_number_in_two_bodies_is_distinct_and_same_body_collision_rejected(self):
        self.store.put_affair(AffairRecord(internal_id="other-body", provider_namespace="fixture", body_id="body2", body_key="B2",
            official_affair_id="1", jurisdiction_level="cantonal", source_ids=self.scope["source_ids"]))
        with self.assertRaises(ReviewError):
            self.store.put_affair(AffairRecord(internal_id="duplicate", provider_namespace="fixture", body_id="body1", body_key="B1",
                official_affair_id="1", jurisdiction_level="municipal", source_ids=self.scope["source_ids"]))

    def test_parser_change_invalidates_offsets_and_approvals(self):
        accepted = accept(self.store, self.claim, self.scope)
        text = TextSnapshot.model_validate(self.store.get(self.scope["binding"]["text_snapshot_id"], "text"))
        text.origin = "recorded"; text.parser_name = "new-parser"; text.parser_version = "2"; text.configuration = {}
        text.pages[0].text = "prefix " + text.pages[0].text
        new_id = self.store.register_text(text)
        self.update_scope(lambda s: setattr(s.binding, "text_snapshot_id", new_id))
        self.assertIn("changed_text_snapshot_id", self.store.eligibility(accepted["decision_id"])["reasons"])
        with self.assertRaisesRegex(ReviewError, "another text snapshot"):
            accept(self.store, self.claim, self.scope)

    def test_scope_expansion_invalidates_aggregate_absence_but_not_document_local(self):
        absent = claim_for(self.store, self.scope, predicate="decision_raw", quote=None, assessment="absent_in_reviewed_scope")
        local = accept(self.store, absent, self.scope)
        aggregate = accept(self.store, absent, self.scope, coverage="affair")
        extra = self.store.register_document(self.doc_id, {"source_url": "https://fixture.invalid/second-response"})
        current = next(s for s in self.store.scopes() if s["id"] == extra["scope_id"])
        scope = ScopeRecord.model_validate({k: current[k] for k in ("binding", "source_ids", "mapping_ids")})
        scope.binding.subject_id = "affair1"; scope.binding.membership = "reviewed"; scope.binding.role = "executive_response"
        self.store.put_scope(scope, revision=current["revision"], reviewer="Engineering test", note="Additional response linked")
        self.assertTrue(self.store.eligibility(local["decision_id"])["eligible"])
        self.assertFalse(self.store.eligibility(aggregate["decision_id"])["eligible"])
        self.assertEqual(self.store.get(aggregate["decision_id"], "review")["request"]["checked_scope"], {self.scope["id"]: [1]})

    def test_new_conflict_blocks_export_until_explicit_resolution(self):
        accepted = accept(self.store, self.claim, self.scope)
        claim_for(self.store, self.scope, quote="Alternative answer.")
        self.assertIn("changed_conflicting_assertions", self.store.eligibility(accepted["decision_id"])["reasons"])
        with self.assertRaisesRegex(ReviewError, "conflicting"):
            accept(self.store, self.claim, self.scope)
        resolved = accept(self.store, self.claim, self.scope, resolve_conflicts=True, note="Fixture explicitly chooses the complete answer")
        snapshot = self.freeze(resolved)
        self.assertEqual(snapshot["snapshot"]["rows"][0]["value"], "Answer complete.")
        self.assertEqual(len([o for o in snapshot["snapshot"]["objects"].values() if o["kind"] == "claim"]), 2)

    def test_unchanged_rerun_keeps_current_review_eligible(self):
        accepted = accept(self.store, self.claim, self.scope)
        self.assertEqual(claim_for(self.store, self.scope), self.claim)
        self.assertTrue(self.store.eligibility(accepted["decision_id"])["eligible"])

    def test_human_completeness_is_bound_to_exact_claim_and_scope(self):
        accepted = accept(self.store, self.claim, self.scope)
        self.assertEqual(accepted["completeness"]["semantic_completeness"], "unknown")
        checked = accept(self.store, self.claim, self.scope, section_complete=True,
                         boundary_checked=True, required_clauses_checked=True)
        self.assertEqual(checked["completeness"]["semantic_completeness"], "complete_in_reviewed_scope")
        self.update_scope(lambda s: setattr(s.binding, "role", "minutes"))
        self.assertFalse(self.store.eligibility(checked["decision_id"])["eligible"])

    def test_observed_continuation_stays_incomplete_without_chunk_history(self):
        claim = Claim.model_validate(self.store.get(self.claim, "claim"))
        claim.unsatisfied_continuation = True
        claim_id = self.store.put_claim(claim)
        for check in (None, True):
            reviewed = accept(self.store, claim_id, self.scope, section_complete=check,
                              boundary_checked=True, required_clauses_checked=True)
            self.assertEqual(reviewed["completeness"]["semantic_completeness"], "incomplete")
            self.assertIn("unsatisfied_continuation", reviewed["completeness"]["reasons"])
        data = claim.model_dump()
        data["chunk_outcomes"] = [{"chunk_id": "missing-manifest", "state": "interrupted",
                                   "finish_reason": None, "response_valid": False}]
        with self.assertRaisesRegex(ValueError, "coverage manifest"):
            Claim.model_validate(data)

    def test_snapshot_and_query_replay_after_mapping_change_and_affair_split(self):
        mapping = MappingRule(key="local-type", body_id="body1", source_label="Motion", destination="request",
            relation="exact_in_scope", rationale="Synthetic mapping", reference="fixture", reviewer="Engineering test")
        original = self.store.put_mapping(mapping, revision=0)
        self.update_scope(lambda s: s.mapping_ids.append(original["version"]))
        accepted = accept(self.store, self.claim, self.scope)
        frozen = self.freeze(accepted)
        spec = ComparisonSpec(question="Fixture comparison", snapshot_id=frozen["snapshot_id"], scope_ids=[self.scope["id"]],
                              columns=["answer_text", "decision_raw"], permitted_mapping_relations=["exact_in_scope"])
        before = self.store.compare(spec, current=True)
        mapping.destination = "conditional request"; mapping.relation = "related"
        self.store.put_mapping(mapping, revision=original["revision"])
        after_mapping = self.store.compare(spec)
        self.assertEqual(canonical(before["result"]), canonical(after_mapping["result"]))
        self.assertEqual(before["result_id"], after_mapping["result_id"])
        with self.assertRaises(ReviewError):
            self.store.compare(spec, current=True)
        self.store.put_affair(AffairRecord(internal_id="split-successor", provider_namespace="fixture", body_id="body1", body_key="B1",
            official_affair_id="2", jurisdiction_level="municipal", source_ids=self.scope["source_ids"]))
        def split(scope):
            scope.binding.subject_id = "split-successor"; scope.mapping_ids = []
        self.update_scope(split)
        self.assertEqual(canonical(before["result"]), canonical(self.store.compare(spec)["result"]))
        self.store.mark_snapshot(frozen["snapshot_id"], status="withdrawn", reason="Historical fixture warning")
        after_status = self.store.compare(spec)
        self.assertEqual(before["result_id"], after_status["result_id"])
        self.assertTrue(after_status["historical_warning"])
        self.assertEqual(after_status["result"]["rows"][0]["fields"]["decision_raw"]["source_assessment"], "not_assessed")

    def test_disallowed_mapping_suppresses_categories_while_preserving_raw_rows(self):
        mapping = self.store.put_mapping(MappingRule(key="local", body_id="body1", source_label="Motion", destination="request",
            relation="related", rationale="Conditional fixture", reference="fixture", reviewer="Engineering test"), revision=0)
        self.update_scope(lambda s: s.mapping_ids.append(mapping["version"]))
        frozen = self.freeze(accept(self.store, self.claim, self.scope))
        spec = ComparisonSpec(question="Fixture", snapshot_id=frozen["snapshot_id"], scope_ids=[self.scope["id"]],
                              columns=["answer_text"], permitted_mapping_relations=["exact_in_scope"])
        row = self.store.compare(spec)["result"]["rows"][0]
        self.assertFalse(row["compatible_for_aggregation"])
        self.assertEqual(row["categories"], [])
        self.assertEqual(row["fields"]["answer_text"]["value"], "Answer complete.")

    def test_current_snapshot_refuses_missing_artifact_and_immutable_rows_cannot_change(self):
        accepted = accept(self.store, self.claim, self.scope)
        with self.legacy.db(write=True) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE v2_objects SET body_json='{}' WHERE id=?", (self.claim,))
        path = self.legacy.directory / "artifacts" / (self.document.sha256 + ".pdf")
        path.write_bytes(b"corruption")
        with self.assertRaisesRegex(ReviewError, "missing or corrupt"):
            self.freeze(accepted)

    def test_duplicate_pdf_sources_remain_independent_and_registration_idempotent(self):
        one = self.store.register_document(self.doc_id, {"source_url": "https://fixture.invalid/one", "body_id": "1"})
        two = self.store.register_document(self.doc_id, {"source_url": "https://fixture.invalid/two", "body_id": "2"})
        self.assertNotEqual(one["source_id"], two["source_id"])
        self.assertNotEqual(one["scope_id"], two["scope_id"])
        self.assertEqual(one, self.store.register_document(self.doc_id, {"source_url": "https://fixture.invalid/one", "body_id": "1"}))


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.legacy = ReviewStore(self.directory / "store")
        self.pdf = self.directory / "source.pdf"
        self.pdf.write_bytes(b"%PDF-synthetic-migration-fixture")
        self.sha = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.document = Document(document_id=self.sha, filename="source.pdf", sha256=self.sha,
                                 pages=[Page(number=1, text="😀 exact legacy\nspacing e\u0301")])
        self.doc_id = self.legacy.add(self.document, self.pdf, {"source_url": "https://fixture.invalid/first"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_wal_backup_exact_text_unknown_parser_and_unverified_absence_are_preserved(self):
        keeper = sqlite3.connect(self.legacy.database)
        try:
            keeper.execute("PRAGMA journal_mode=WAL")
            keeper.execute("SELECT * FROM documents").fetchall()
            self.legacy.review(self.doc_id, ReviewAction(field="answer_text", action="missing", revision=0,
                reviewer="Engineering fixture not gold", note="Checked the one source page for an answer"))
            with self.legacy.db() as db:
                before = legacy_inventory(db)
            manifest = self.directory / "manifest.json"
            manifest.write_text(json.dumps({"documents": [{"sha256": self.sha, "source_url": "https://fixture.invalid/second"}]}))
            with patch("src.skony.pdf.parse_pdf", side_effect=AssertionError("Legacy must never reparse")):
                report = migrate(self.legacy, source_manifests=[manifest])
            self.assertEqual(report["before"], report["after"])
            self.assertEqual(report["before"], before)
            with closing(sqlite3.connect(Path(report["backup_directory"]) / "review.sqlite3")) as db:
                db.row_factory = sqlite3.Row
                self.assertEqual(legacy_inventory(db), before)
            with self.legacy.db() as db:
                texts = [json.loads(r[0]) for r in db.execute("SELECT body_json FROM v2_objects WHERE kind='text'")]
                reviews = [json.loads(r[0]) for r in db.execute("SELECT body_json FROM v2_objects WHERE kind='legacy_review'")]
            self.assertEqual(texts[0]["pages"][0]["text"], self.document.pages[0].text)
            self.assertEqual(texts[0]["origin"], "legacy_unknown")
            self.assertIsNone(texts[0]["parser_version"])
            self.assertFalse(reviews[0]["eligible_for_current_export"])
            self.assertEqual(reviews[0]["structured_scope"], "unverified")
            self.assertIn("Checked the one", reviews[0]["original"]["note"])
            self.assertEqual(report["manifest_source_records_recovered"], 1)
            self.assertEqual(migrate(self.legacy), report)
        finally:
            keeper.close()

    def test_missing_or_mismatched_pdf_blocks_before_migration(self):
        path = self.legacy.pdf_path(self.doc_id)
        path.write_bytes(b"changed source")
        with self.assertRaises(ReviewError):
            migrate(self.legacy)
        with self.legacy.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='v2_objects'").fetchone())
            self.assertEqual(db.execute("SELECT count(*) FROM documents").fetchone()[0], 1)

    def test_migration_failure_rolls_back_schema_and_retains_usable_legacy(self):
        with patch("src.skony.migration.put_object", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                migrate(self.legacy)
        self.assertEqual(self.legacy.get(self.doc_id)["document"]["pages"][0]["text"], self.document.pages[0].text)
        with self.legacy.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='v2_objects'").fetchone())


if __name__ == "__main__":
    unittest.main()
