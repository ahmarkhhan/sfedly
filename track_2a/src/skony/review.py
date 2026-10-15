"""Persistent human review, separate from immutable model suggestions."""

from __future__ import annotations

import json
import hashlib
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from .schema import CandidateExtraction, CandidateField, Document, ExtractionResult, StrictModel
from .verify import locate

FIELD_NAMES = tuple(CandidateExtraction.model_fields)


class ReviewError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class ReviewAction(StrictModel):
    field: str
    action: Literal["confirm", "correct", "missing", "undo"]
    revision: int = Field(ge=0)
    reviewer: str = Field(default="Local reviewer", min_length=1, max_length=80)
    basis: Literal["text", "image"] = "text"
    value: str | None = Field(default=None, max_length=50000)
    page: int | None = Field(default=None, ge=1)
    quote: str | None = Field(default=None, max_length=50000)
    note: str = Field(default="", max_length=2000)

    @field_validator("reviewer")
    @classmethod
    def named_reviewer(cls, value):
        if not value.strip():
            raise ValueError("A reviewer name is required")
        return value.strip()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class ReviewStore:
    def __init__(self, directory: Path, *, read_only=False):
        self.directory = directory.resolve()
        self.pdf_directory = self.directory / "documents"
        self.database = self.directory / "review.sqlite3"
        self.read_only = read_only
        if read_only:
            if not self.database.is_file():
                raise ReviewError("Review database is unavailable", 404)
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pdf_directory.mkdir(exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
                    document_json TEXT NOT NULL, source_json TEXT NOT NULL,
                    result_json TEXT, revision INTEGER NOT NULL DEFAULT 0,
                    extraction_state TEXT NOT NULL DEFAULT 'idle', extraction_error TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    document_id TEXT NOT NULL, field TEXT NOT NULL, review_json TEXT NOT NULL,
                    PRIMARY KEY (document_id, field)
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
                    field TEXT, action TEXT NOT NULL, reviewer TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL, model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL, verifier_version TEXT NOT NULL,
                    response_text TEXT, result_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS document_sources (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                    source_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def db(self, *, write=False):
        if write and self.read_only:
            raise ReviewError("This review store was opened read-only")
        db = (sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True, timeout=10)
              if self.read_only else sqlite3.connect(self.database, timeout=10))
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        if not self.read_only:
            db.execute("PRAGMA journal_mode=WAL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def add(self, document: Document, pdf: Path, source: dict | None = None,
            result: ExtractionResult | None = None) -> str:
        with self.db(write=True) as db:
            existing = db.execute("SELECT id FROM documents WHERE sha256=?", (document.sha256,)).fetchone()
            if existing:
                if source is not None:
                    self._preserve_source(db, existing["id"], source)
                return existing["id"]
            identifier = uuid.uuid4().hex
            destination = self.pdf_directory / f"{identifier}.pdf"
            shutil.copyfile(pdf, destination)
            db.execute("INSERT INTO documents(id,sha256,filename,document_json,source_json,result_json,created_at) VALUES(?,?,?,?,?,?,?)",
                       (identifier, document.sha256, document.filename, document.model_dump_json(),
                        json.dumps(source or {}), result.model_dump_json() if result else None, timestamp()))
            self._preserve_source(db, identifier, source or {})
        return identifier

    @staticmethod
    def _preserve_source(db, identifier, source):
        encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        source_id = hashlib.sha256((identifier + "\n" + encoded).encode("utf-8")).hexdigest()
        db.execute("INSERT OR IGNORE INTO document_sources VALUES(?,?,?,?)",
                   (source_id, identifier, encoded, timestamp()))

    def get(self, identifier: str) -> dict:
        with self.db() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (identifier,)).fetchone()
            if not row:
                raise ReviewError("Document not found", 404)
            reviews = {r["field"]: json.loads(r["review_json"]) for r in
                       db.execute("SELECT field,review_json FROM reviews WHERE document_id=?", (identifier,))}
            latest_run = db.execute("SELECT id FROM runs WHERE document_id=? ORDER BY created_at DESC LIMIT 1", (identifier,)).fetchone()
        document = json.loads(row["document_json"])
        source = json.loads(row["source_json"])
        result = json.loads(row["result_json"]) if row["result_json"] else None
        empty = {"value": None, "status": "not_extracted", "reason": "not_run", "provenance": None}
        fields = {name: {"suggestion": result["fields"][name] if result else dict(empty),
                         "review": reviews.get(name)} for name in FIELD_NAMES}
        return {"id": identifier, "filename": row["filename"], "document": document,
                "source": source, "fields": fields,
                "revision": row["revision"], "extraction_state": row["extraction_state"],
                "extraction_error": row["extraction_error"],
                "model": result["model_name"] if result else None,
                "extraction_origin": ("cached_batch" if latest_run["id"].startswith("batch-") else "workbench_run") if latest_run else
                    "synthetic_fixture" if result and source.get("synthetic") else "recorded_pilot" if result else None,
                "prompt_version": result["prompt_version"] if result else None,
                "verifier_version": result.get("verifier_version") if result else None,
                "usage": result["usage"] if result else {},
                "latency_seconds": result["latency_seconds"] if result else None}

    def list(self) -> list[dict]:
        with self.db() as db:
            identifiers = [r["id"] for r in db.execute("SELECT id FROM documents ORDER BY created_at DESC")]
        output = []
        for identifier in identifiers:
            item = self.get(identifier)
            title = item["fields"]["title"]["review"] or item["fields"]["title"]["suggestion"]
            output.append({"id": identifier, "filename": item["filename"], "title": title.get("value") or item["filename"],
                           "pages": len(item["document"]["pages"]), "source": item["source"],
                           "reviewed": sum(f["review"] is not None for f in item["fields"].values()),
                           "located": sum(f["suggestion"]["status"] == "source_located" for f in item["fields"].values()),
                           "extraction_state": item["extraction_state"], "model": item["model"]})
        return output

    def pdf_path(self, identifier: str) -> Path:
        self.get(identifier)
        path = self.pdf_directory / f"{identifier}.pdf"
        if not path.is_file():
            raise ReviewError("Original PDF is unavailable", 404)
        return path

    def review(self, identifier: str, action: ReviewAction):
        if action.field not in FIELD_NAMES:
            raise ReviewError("Unknown extraction field")
        with self.db(write=True) as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (identifier,)).fetchone()
            if not row:
                raise ReviewError("Document not found", 404)
            if row["revision"] != action.revision:
                raise ReviewError("This document changed. Reload it before saving your review.", 409)
            if row["extraction_state"] == "running":
                raise ReviewError("Wait for the current extraction to finish before reviewing.", 409)
            document = Document.model_validate_json(row["document_json"])
            before = db.execute("SELECT review_json FROM reviews WHERE document_id=? AND field=?",
                                (identifier, action.field)).fetchone()
            review = None
            if action.action == "confirm":
                if not row["result_json"]:
                    raise ReviewError("Extract the document before confirming a suggestion")
                result = ExtractionResult.model_validate_json(row["result_json"])
                suggestion = result.fields[action.field]
                if suggestion.value is None or suggestion.provenance is None:
                    raise ReviewError("There is no source-located suggestion to confirm. Add a correction or mark it absent.")
                review = {"value": suggestion.value, "provenance": {**suggestion.provenance.model_dump(), "basis": "text"},
                          "decision": "confirmed"}
            elif action.action == "correct":
                if not action.value or not action.value.strip() or not action.quote or not action.page:
                    raise ReviewError("A correction needs a value, page and supporting passage")
                if action.page not in {p.number for p in document.pages}:
                    raise ReviewError("The selected page does not exist")
                if action.basis == "text":
                    located = locate(CandidateField(value=action.value, page=action.page, quote=action.quote), document, action.field)
                    if located.provenance is None:
                        raise ReviewError("The correction cannot be located in the selected page's text. Check the passage or use visual page evidence.")
                    review = {"value": located.value, "provenance": {**located.provenance.model_dump(), "basis": "text"},
                              "decision": "corrected"}
                else:
                    if len(action.note.strip()) < 8:
                        raise ReviewError("Describe where you checked the correction on the original page")
                    review = {"value": action.value, "provenance": {"document_id": document.document_id, "page": action.page,
                              "quote": action.quote, "start": None, "end": None, "basis": "image", "match_method": None},
                              "decision": "corrected"}
            elif action.action == "missing":
                if len(action.note.strip()) < 8:
                    raise ReviewError("Explain which source pages you checked before marking the field absent")
                review = {"value": None, "provenance": None, "decision": "absent"}
            if review is not None:
                review.update({"reviewer": action.reviewer.strip(), "reviewed_at": timestamp(), "note": action.note.strip()})
                db.execute("INSERT INTO reviews(document_id,field,review_json) VALUES(?,?,?) ON CONFLICT(document_id,field) DO UPDATE SET review_json=excluded.review_json",
                           (identifier, action.field, json.dumps(review)))
            else:
                db.execute("DELETE FROM reviews WHERE document_id=? AND field=?", (identifier, action.field))
            snapshot = {"before": json.loads(before["review_json"]) if before else None, "after": review}
            db.execute("INSERT INTO audit(document_id,field,action,reviewer,snapshot_json,created_at) VALUES(?,?,?,?,?,?)",
                       (identifier, action.field, action.action, action.reviewer.strip(), json.dumps(snapshot), timestamp()))
            db.execute("UPDATE documents SET revision=revision+1 WHERE id=?", (identifier,))
        return self.get(identifier)

    def start_extraction(self, identifier: str):
        with self.db(write=True) as db:
            row = db.execute("SELECT extraction_state FROM documents WHERE id=?", (identifier,)).fetchone()
            if not row:
                raise ReviewError("Document not found", 404)
            if row["extraction_state"] == "running":
                raise ReviewError("An extraction is already running", 409)
            db.execute("UPDATE documents SET extraction_state='running',extraction_error=NULL,revision=revision+1 WHERE id=?", (identifier,))

    def finish_extraction(self, identifier: str, result: ExtractionResult, response: str, *,
                          batch_key: str | None = None) -> bool:
        with self.db(write=True) as db:
            row = db.execute("SELECT sha256,document_json,extraction_state FROM documents WHERE id=?", (identifier,)).fetchone()
            if not row or row["sha256"] != result.document.sha256:
                raise ReviewError("Extraction result does not match the document")
            original = Document.model_validate_json(row["document_json"])
            if original.pages != result.document.pages:
                raise ReviewError("Text changed. Register a new v0.2 text snapshot and revalidate dependent reviews.", 409)
            run_id = "batch-" + batch_key if batch_key else uuid.uuid4().hex
            if batch_key:
                if row["extraction_state"] == "running":
                    raise ReviewError("Wait for extraction to finish before importing a batch result", 409)
                if db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                    return False
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)", (run_id, identifier, result.model_name,
                       result.prompt_version, result.verifier_version, response, result.model_dump_json(), timestamp()))
            db.execute("UPDATE documents SET result_json=?,extraction_state='idle',extraction_error=NULL,revision=revision+1 WHERE id=?",
                       (result.model_dump_json(), identifier))
        return True

    def backfill_source(self, identifier: str, source: dict):
        """Fill previously unrecorded provenance without replacing existing labels."""
        with self.db(write=True) as db:
            row = db.execute("SELECT source_json FROM documents WHERE id=?", (identifier,)).fetchone()
            if not row:
                raise ReviewError("Document not found", 404)
            original = json.loads(row["source_json"])
            self._preserve_source(db, identifier, original)
            self._preserve_source(db, identifier, source)
            merged = {**source, **{key: value for key, value in original.items() if value is not None}}
            if merged != original:
                db.execute("UPDATE documents SET source_json=?,revision=revision+1 WHERE id=?",
                           (json.dumps(merged), identifier))

    def fail_extraction(self, identifier: str, message: str):
        with self.db(write=True) as db:
            db.execute("UPDATE documents SET extraction_state='failed',extraction_error=?,revision=revision+1 WHERE id=?", (message, identifier))

    def audit(self, identifier: str) -> list[dict]:
        self.get(identifier)
        with self.db() as db:
            return [{"field": r["field"], "action": r["action"], "reviewer": r["reviewer"],
                     "snapshot": json.loads(r["snapshot_json"]), "created_at": r["created_at"]}
                    for r in db.execute("SELECT * FROM audit WHERE document_id=? ORDER BY id DESC", (identifier,))]

    def export(self, identifier: str) -> dict:
        item = self.get(identifier)
        reviewed = {name: field["review"] for name, field in item["fields"].items() if field["review"] is not None}
        if not reviewed:
            raise ReviewError("Review at least one field before exporting")
        return {"schema_version": "skony.reviewed.v0.1", "document_id": item["document"]["document_id"],
                "document_sha256": item["document"]["sha256"], "revision": item["revision"],
                "filename": item["filename"], "source": item["source"], "model": item["model"],
                "prompt_version": item["prompt_version"], "verifier_version": item["verifier_version"],
                "fields": reviewed, "unreviewed_fields": [name for name in FIELD_NAMES if name not in reviewed],
                "exported_at": timestamp(), "review_scope": "Only explicit reviewer decisions are included"}
