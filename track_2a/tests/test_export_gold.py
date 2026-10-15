"""Gold export: completeness gate and automated-QA exclusion."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.skony.review import ReviewAction, ReviewStore
from src.skony.schema import Document, Page

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["title", "affair_type_raw", "submitter_raw", "submitted_date_raw",
          "question_text", "answer_text", "decision_raw", "decision_date_raw"]


def make_store(tmp: Path) -> ReviewStore:
    return ReviewStore(tmp / "store")


def add_document(store: ReviewStore, text: str) -> str:
    pdf = store.directory / "in.pdf"
    # Minimal PDF bytes are not needed: add() copies the file, so give it one.
    pdf.write_bytes(b"%PDF-1.4 fake")
    doc = Document(document_id="sha", filename="in.pdf", sha256="sha",
                   pages=[Page(number=1, text=text)], textless_pages=[])
    return store.add(doc, pdf, {"body_key": "743", "body_label": "Nidau",
                                "language": "de"})


def review_all(store: ReviewStore, identifier: str, reviewer: str):
    for field in FIELDS:
        store.review(identifier, ReviewAction(
            field=field, action="missing", revision=_rev(store, identifier),
            reviewer=reviewer, note="Checked page 1; not present here."))


def _rev(store: ReviewStore, identifier: str) -> int:
    return store.get(identifier)["revision"]


class ExportGoldTests(unittest.TestCase):
    def run_export(self, store_dir: Path, out_dir: Path):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "export_gold.py"),
             "--store", str(store_dir), "--out", str(out_dir)],
            capture_output=True, text=True, cwd=ROOT)

    def test_complete_human_document_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = make_store(tmp)
            identifier = add_document(store, "Antrag text")
            review_all(store, identifier, "Human Reviewer")
            out = tmp / "gold"
            result = self.run_export(store.directory, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            gold_files = [p for p in out.glob("*.json") if p.name != "manifest.json"]
            self.assertEqual(len(gold_files), 1)
            record = json.loads(gold_files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["gold_schema_version"], "skony.gold.v0.1")
            self.assertEqual(set(record["decisions"]), set(FIELDS))
            self.assertTrue((out / "README.md").is_file())
            self.assertTrue((out / "manifest.json").is_file())

    def test_incomplete_document_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = make_store(tmp)
            identifier = add_document(store, "Antrag text")
            # Review only one field; leave the rest undecided.
            store.review(identifier, ReviewAction(
                field="title", action="missing", revision=_rev(store, identifier),
                reviewer="Human Reviewer", note="Checked page 1; no title."))
            out = tmp / "gold"
            result = self.run_export(store.directory, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["documents"], 0)
            self.assertEqual(manifest["summary"]["skipped_incomplete"], 1)

    def test_automated_qa_document_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = make_store(tmp)
            identifier = add_document(store, "Antrag text")
            review_all(store, identifier, "Automated UI QA — not gold labels")
            out = tmp / "gold"
            result = self.run_export(store.directory, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["documents"], 0)
            self.assertEqual(manifest["summary"]["skipped_automated_qa"], 1)

    def test_synthetic_document_cannot_become_gold_even_with_human_labels(self):
        for flags in ({"synthetic": True}, {"gold_annotation": False}):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                store = make_store(tmp)
                identifier = add_document(store, "Practice example")
                with store.db(write=True) as db:
                    db.execute("UPDATE documents SET source_json=? WHERE id=?", (json.dumps(flags), identifier))
                review_all(store, identifier, "Human Reviewer")
                out = tmp / "gold"
                result = self.run_export(store.directory, out)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["summary"]["documents"], 0)
                self.assertEqual(manifest["summary"]["skipped_excluded_source"], 1)
                self.assertEqual(manifest["files"], [])

    def test_reused_output_rejected_without_overwriting_old_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = make_store(tmp)
            identifier = add_document(store, "Antrag text")
            review_all(store, identifier, "Human Reviewer")
            out = tmp / "gold"
            self.assertEqual(self.run_export(store.directory, out).returncode, 0)
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            store.review(identifier, ReviewAction(field="title", action="undo",
                revision=_rev(store, identifier), reviewer="Human Reviewer"))
            result = self.run_export(store.directory, out)
            self.assertEqual(result.returncode, 2)
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)

    def test_export_preserves_source_rights_and_records_checksums(self):
        from skony.cache import digest
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = make_store(tmp)
            identifier = add_document(store, "Antrag text")
            source = {"body_key": "../../unsafe", "language": "de", "licence_status": "unverified",
                      "role": "request", "role_origin": "heuristic", "role_review_required": True}
            with store.db(write=True) as db:
                db.execute("UPDATE documents SET source_json=? WHERE id=?", (json.dumps(source), identifier))
            review_all(store, identifier, "Human Reviewer")
            out = tmp / "gold"
            result = self.run_export(store.directory, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            entry = manifest["files"][0]
            record = json.loads((out / entry["file"]).read_text(encoding="utf-8"))
            self.assertEqual(entry["record_sha256"], digest(record))
            self.assertEqual(record["source"], source)
            readonly = ReviewStore(store.directory, read_only=True)
            with self.assertRaises(ValueError):
                readonly.review(identifier, ReviewAction(field="title", action="undo",
                    revision=_rev(store, identifier), reviewer="Human Reviewer"))


if __name__ == "__main__":
    unittest.main()
