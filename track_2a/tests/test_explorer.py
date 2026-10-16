"""Research behavior and source integrity; all fixtures are synthetic engineering QA."""

import csv
import hashlib
import io
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx

from src.skony.explorer import Explorer, iso_date, safe_url
from src.skony.review import ReviewAction, ReviewError, ReviewStore
from src.skony.schema import CandidateField, Document, ExtractionResult, Page
from src.skony.server import Workbench, make_handler
from src.skony.verify import abstain, locate


class ExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ReviewStore(Path(self.temporary.name) / "store")
        self.explorer = Explorer(self.store)
        self.serial = 0

    def tearDown(self):
        self.temporary.cleanup()

    def add(self, text="Verkehr und écoles", *, source=None, values=None):
        self.serial += 1
        data = f"%PDF-engineering-fixture-{self.serial}".encode()
        pdf = Path(self.temporary.name) / "source.pdf"
        pdf.write_bytes(data)
        document = Document(document_id=f"source-{self.serial}", filename=f"qa-{self.serial}.pdf",
                            sha256=hashlib.sha256(data).hexdigest(), pages=[Page(number=1, text=text)])
        fields = {key: abstain("model_abstained") for key in
                  ("title", "affair_type_raw", "submitter_raw", "submitted_date_raw", "question_text",
                   "answer_text", "decision_raw", "decision_date_raw")}
        for name, value in (values or {}).items():
            fields[name] = locate(CandidateField(value=value, quote=value, page=1), document, name)
            self.assertEqual(fields[name].value, value)
        result = ExtractionResult(document=document, model_name="synthetic-engineering-not-inference",
                                  prompt_version="test", latency_seconds=0.0, fields=fields) if values else None
        return self.store.add(document, pdf, source or {}, result)

    def test_unextracted_source_search_preserves_unicode_offsets_and_needs_no_model(self):
        self.add("😀 Les écoles et la mobilité à Genève.", source={"language": "fr", "body_id": "G"})
        with patch("src.skony.server.complete") as model:
            result = self.explorer.search({"q": "ECOLES mobilite"})
            self.assertEqual(result["total"], 1)
            snippet = result["results"][0]["snippet"]
            page = self.store.list()[0]["id"]
            text = self.store.get(page)["document"]["pages"][0]["text"]
            self.assertEqual(text[snippet["start"]:snippet["end"]], snippet["quote"])
            self.assertFalse(result["results"][0]["has_answer"])
            model.assert_not_called()

    def test_multilingual_keyword_discovery_and_language_and_body_filters(self):
        for language, text in [("de", "Verkehr im Dorf"), ("fr", "Les transports publics"), ("it", "Trasporti pubblici")]:
            self.add(text, source={"language": language, "body_id": language, "body_label": language})
        self.assertEqual(self.explorer.search({"topic": "transport"})["total"], 3)
        result = self.explorer.search({"topic": "transport", "language": "fr", "body": "id:fr"})
        self.assertEqual(result["total"], 1)
        self.assertEqual(self.explorer.search({"topic": "transport", "language": "de", "body": "id:fr"})["total"], 0)

    def test_group_identity_does_not_merge_bodies_providers_missing_ids_or_practice(self):
        base = {"body_id": "A", "affair_id": 5, "provider_namespace": "one"}
        for source in [base, base, {**base, "body_id": "B"}, {**base, "provider_namespace": "two"},
                       {**base, "synthetic": True}, {}, {}, {"body_key": "A", "affair_id": 5, "provider_namespace": "one"}]:
            self.add(source=source)
        result = self.explorer.search({})
        self.assertEqual(result["total"], 7)
        self.assertEqual(result["insights"]["documents"], 8)
        grouped = next(d for d in result["results"] if d["document_count"] == 2)
        self.assertEqual(grouped["association_status"], "unverified_source_metadata")
        self.assertEqual(self.explorer.search({"sources": "practice"})["total"], 1)
        self.assertEqual(self.explorer.search({"sources": "real"})["total"], 6)

    def test_reviewed_mode_withholds_proposals_and_keeps_explicit_absence_and_undo(self):
        identifier = self.add("Question. Réponse.", values={"question_text": "Question.", "answer_text": "Réponse."})
        self.store.review(identifier, ReviewAction(field="question_text", action="confirm", revision=0, reviewer="QA not gold"))
        self.store.review(identifier, ReviewAction(field="answer_text", action="missing", revision=1, reviewer="QA not gold", note="Engineering absence example"))
        result = self.explorer.search({"reviewed_only": "true"})
        detail = self.explorer.detail(result["results"][0]["id"], reviewed_only=True)
        field = detail["documents"][0]["fields"]["answer_text"]
        self.assertEqual(field["review_decision"], "absent")
        self.assertIsNone(field["value"])
        self.assertFalse(result["results"][0]["has_answer"])
        self.assertEqual(len(detail["timeline"]), 1)
        # Original text remains discoverable even if proposals are hidden.
        self.assertEqual(self.explorer.search({"q": "Reponse", "reviewed_only": "true"})["total"], 1)
        self.store.review(identifier, ReviewAction(field="question_text", action="undo", revision=2, reviewer="QA not gold"))
        self.assertFalse(self.explorer.search({"reviewed_only": "true"})["results"][0]["has_request"])
        hidden = self.explorer.detail(result["results"][0]["id"], reviewed_only=True)["documents"][0]["fields"]["question_text"]
        self.assertEqual(hidden["status"], "withheld_unreviewed")
        self.assertIsNone(hidden["citation"])
        self.assertTrue(self.explorer.search({})["results"][0]["has_request"])

    def test_source_fields_and_dates_keep_independent_evidence_and_no_fake_pending_status(self):
        self.add("Request\nAnswer\nDecision\n16.10.2026\n2026-10-17\nAlice et Bob",
                 values={"question_text": "Request", "answer_text": "Answer", "decision_raw": "Decision",
                         "submitted_date_raw": "16.10.2026", "decision_date_raw": "2026-10-17", "submitter_raw": "Alice et Bob"})
        detail = self.explorer.detail(self.explorer.search({})["results"][0]["id"])
        self.assertEqual([e["date_iso"] for e in detail["timeline"]], ["2026-10-16", "2026-10-17", None])
        self.assertEqual(detail["timeline"][-1]["kind"], "Government answer")
        event = detail["timeline"][0]
        self.assertEqual(event["content"]["citation"]["quote"], "Request")
        self.assertEqual(event["date_evidence"]["citation"]["quote"], "16.10.2026")
        self.assertEqual(len(detail["actors"]), 1)
        self.assertEqual(detail["actors"][0]["value"], "Alice et Bob")
        self.assertNotIn("procedural_status", detail)
        for invalid in ["10/11/2026", "31.2.2026", "15 mars 2026", "2026-13-01"]:
            self.assertIsNone(iso_date(invalid))

    def test_brief_is_unpaginated_traceable_and_csv_neutralizes_formulas(self):
        self.add("=SUM(1,2)\nQuoted, value\nnext line", source={"body_label": "@body", "source_url": "javascript:alert(1)"},
                 values={"title": "=SUM(1,2)", "question_text": "Quoted, value\nnext line"})
        self.add("Another document")
        self.assertEqual(len(self.explorer.search({"limit": "1"})["results"]), 1)
        brief = self.explorer.brief({"limit": "1"})
        self.assertEqual(len(brief["dossiers"]), 2)
        self.assertEqual(brief["schema_version"], "skony.research-brief.v1")
        doc = next(d["documents"][0] for d in brief["dossiers"] if d["documents"][0]["fields"]["title"]["value"])
        self.assertIsNone(doc["source_url"])
        self.assertNotIn("pages", doc)
        self.assertEqual(doc["fields"]["title"]["status"], "source_located_unreviewed")
        self.assertTrue(doc["fields"]["title"]["citation"]["pdf_url"].endswith("#page=1"))
        rows = list(csv.DictReader(io.StringIO(self.explorer.csv(brief).decode("utf-8-sig"))))
        self.assertEqual(next(r["value"] for r in rows if r["field"] == "title" and r["value"]), "'=SUM(1,2)")
        self.assertEqual(next(r["value"] for r in rows if r["field"] == "question_text" and r["value"]), "Quoted, value\nnext line")
        self.assertTrue(next(r["body"] for r in rows if r["body"] == "'@body"))

    def test_facets_deduplicate_body_labels_and_distinguish_same_named_bodies(self):
        for body_id, label, key in [(1, "Bern", "BE"), (1, "Bern · Canton", "BE"), (2, "Bern", "351")]:
            self.add(source={"body_id": body_id, "body_label": label, "body_key": key})
        facets = self.explorer.search({})["facets"]["bodies"]
        self.assertEqual(len(facets), 2)
        self.assertEqual({f["label"] for f in facets}, {"Bern · BE", "Bern · 351"})

    def test_empty_store_unknown_queries_and_read_only_projection_do_not_migrate(self):
        self.assertEqual(self.explorer.search({})["insights"]["dossiers"], 0)
        for params in [{"limit": "-1"}, {"limit": "wat"}, {"offset": "-1"}, {"topic": "invented"},
                       {"q": "x" * 251}, {"reviewed_only": "yes"}, {"sources": "elsewhere"}, {"bogus": "1"}]:
            with self.assertRaises(ReviewError): self.explorer.search(params)
        self.add()
        read_only = Explorer(ReviewStore(self.store.directory, read_only=True))
        self.assertEqual(read_only.search({})["total"], 1)
        with self.store.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='v2_objects'").fetchone())
        with self.assertRaises(ReviewError): self.explorer.detail("not-a-dossier")
        for _ in range(2):
            self.add(source={"body_id": "A", "affair_id": "5"})
        self.assertEqual(self.explorer.search({})["total"], 3)  # Unknown provider cannot establish identity.
        self.assertIsNone(safe_url("https://user:password@example.test/file"))
        self.assertEqual(safe_url("https://example.test/file.pdf"), "https://example.test/file.pdf")


class ExplorerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = Workbench(Path(self.temporary.name), mode="replay")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.server.server_port}", trust_env=False)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_search_detail_exports_and_static_routes_make_no_model_calls(self):
        with patch("src.skony.server.complete") as model:
            for path in ["/explore", "/explore.js", "/explore.css"]:
                self.assertEqual(self.client.get(path).status_code, 200)
            response = self.client.get("/api/explorer")
            self.assertEqual(response.status_code, 200)
            dossier = response.json()["results"][0]
            self.assertTrue(dossier["synthetic"])
            detail = self.client.get("/api/explorer/dossiers/" + dossier["id"]).json()
            self.assertEqual(detail["documents"][0]["fields"]["question_text"]["status"], "source_located_unreviewed")
            for format in ["csv", "json"]:
                export = self.client.get("/api/explorer/export", params={"format": format})
                self.assertEqual(export.status_code, 200)
                self.assertIn("attachment", export.headers["Content-Disposition"])
            model.assert_not_called()
        self.assertEqual(self.app.store.get(self.app.store.list()[0]["id"])["revision"], 0)

    def test_invalid_filter_format_duplicate_filters_and_foreign_hosts_are_rejected(self):
        for path in ["/api/explorer?q=a&q=b", "/api/explorer?limit=1000", "/api/explorer/export?format=html",
                     "/api/explorer/dossiers/missing?bogus=yes"]:
            self.assertEqual(self.client.get(path).status_code, 400, path)
        self.assertEqual(self.client.get("/api/explorer/dossiers/missing").status_code, 404)
        self.assertEqual(self.client.get("/api/explorer", headers={"Host": "other.example"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
