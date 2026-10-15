"""Additive v0.2 migration with a SQLite/WAL-consistent, verified backup (A5)."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from .contracts import ScopeBinding, ScopeWindow, TextSnapshot, canonical, identity
from .review import ReviewError, ReviewStore, timestamp
from .review_contracts import ScopeRecord
from .schema import Document

DDL = [
    "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, report_json TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS v2_objects(id TEXT PRIMARY KEY, kind TEXT NOT NULL, body_json TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS v2_heads(kind TEXT NOT NULL, entity_key TEXT NOT NULL,
       object_id TEXT NOT NULL REFERENCES v2_objects(id), revision INTEGER NOT NULL,
       PRIMARY KEY(kind,entity_key))""",
    """CREATE TABLE IF NOT EXISTS v2_snapshot_status(id INTEGER PRIMARY KEY AUTOINCREMENT,
       snapshot_id TEXT NOT NULL REFERENCES v2_objects(id), status TEXT NOT NULL,
       successor_id TEXT REFERENCES v2_objects(id), reason TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TRIGGER IF NOT EXISTS v2_objects_no_update BEFORE UPDATE ON v2_objects
       BEGIN SELECT RAISE(ABORT, 'Immutable object'); END""",
    """CREATE TRIGGER IF NOT EXISTS v2_objects_no_delete BEFORE DELETE ON v2_objects
       BEGIN SELECT RAISE(ABORT, 'Immutable object'); END""",
]


def put_object(db, kind, value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    identifier = identity(value)
    encoded = canonical(value).decode("utf-8")
    previous = db.execute("SELECT kind,body_json FROM v2_objects WHERE id=?", (identifier,)).fetchone()
    if previous and (previous["kind"] != kind or previous["body_json"] != encoded):
        raise ReviewError("Immutable object identity collision", 409)
    if not previous:
        db.execute("INSERT INTO v2_objects VALUES(?,?,?)", (identifier, kind, encoded))
    return identifier


def get_object(db, identifier, kind=None):
    row = db.execute("SELECT * FROM v2_objects WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise ReviewError("Versioned object not found", 404)
    body = json.loads(row["body_json"])
    if identity(body) != identifier or (kind and row["kind"] != kind):
        raise ReviewError("Versioned object failed identity/type validation", 409)
    return body


def head(db, kind, key):
    return db.execute("SELECT * FROM v2_heads WHERE kind=? AND entity_key=?", (kind, key)).fetchone()


def set_head(db, kind, key, object_id, expected_revision):
    current = head(db, kind, key)
    revision = current["revision"] if current else 0
    if expected_revision != revision:
        raise ReviewError("This record changed. Reload before saving.", 409)
    if current and current["object_id"] == object_id:
        return revision
    db.execute("""INSERT INTO v2_heads VALUES(?,?,?,?) ON CONFLICT(kind,entity_key)
               DO UPDATE SET object_id=excluded.object_id, revision=excluded.revision""",
               (kind, key, object_id, revision + 1))
    return revision + 1


def legacy_inventory(db):
    inventory = {}
    for table, order in [("documents", "id"), ("reviews", "document_id,field"),
                         ("audit", "id"), ("runs", "id")]:
        rows = [dict(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        inventory[table] = {"count": len(rows), "digest": identity(rows)}
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='document_sources'").fetchone():
        rows = [dict(r) for r in db.execute("SELECT * FROM document_sources ORDER BY id")]
        inventory["document_sources"] = {"count": len(rows), "digest": identity(rows)}
    return inventory


def source_record(metadata, artifact_id, *, origin):
    return {"schema_version": "skony.source.v0.2", "artifact_id": artifact_id,
            "provider_namespace": metadata.get("provider_namespace") or
                ("openparldata" if metadata.get("openparldata_document_id") is not None else "unknown"),
            "original_ids": {k: metadata[k] for k in ("body_id", "body_key", "affair_id", "openparldata_document_id") if k in metadata},
            "source_url": metadata.get("source_url"),
            "retrieved_at": metadata.get("retrieved_at_utc"),
            "rights_status": metadata.get("licence_status") or "unknown",
            "metadata": metadata, "metadata_digest": identity(metadata), "origin": origin,
            "association_review": "unverified"}


def _write_once(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ReviewError("Content-addressed artifact mismatch", 409)
        return
    with path.open("xb") as stream:
        stream.write(data)


def migrate(store: ReviewStore, *, source_manifests: list[Path] | None = None):
    """No reparsing, legacy rewrites or inferred human decisions.

    A writer reservation prevents concurrent intake/review while a separate
    SQLite backup connection captures committed WAL contents and artifacts.
    Schema and backfills commit together. Failed migration leaves v1 usable.
    """
    if store.read_only:
        raise ReviewError("Migration needs a writable store")
    with store.db(write=True) as db:
        db.execute("PRAGMA foreign_keys=ON")
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
        if exists:
            row = db.execute("SELECT report_json FROM schema_migrations WHERE version=2").fetchone()
            if row:
                return json.loads(row[0])
        before = legacy_inventory(db)
        documents = list(db.execute("SELECT * FROM documents ORDER BY id"))
        artifacts = []
        for row in documents:
            # IDs come from the database but still cannot become arbitrary paths.
            if not row["id"] or any(c not in "0123456789abcdef" for c in row["id"]):
                raise ReviewError("Legacy document identity is not a safe artifact name")
            path = store.pdf_directory / (row["id"] + ".pdf")
            if not path.is_file():
                raise ReviewError("Migration blocked: a referenced PDF is missing", 409)
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            document = Document.model_validate_json(row["document_json"])
            if digest != row["sha256"] or document.sha256 != digest:
                raise ReviewError("Migration blocked: a referenced PDF digest does not match", 409)
            artifacts.append((row, document, path, digest, len(data)))
        backup = None
        if documents or any(v["count"] for v in before.values()):
            backup = store.directory / "backups" / ("v1-" + uuid.uuid4().hex)
            backup.mkdir(parents=True)
            with closing(sqlite3.connect(store.database.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(backup / "review.sqlite3")) as destination:
                    source.backup(destination)
                    if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ReviewError("SQLite backup failed integrity verification", 409)
                    destination.row_factory = sqlite3.Row
                    if legacy_inventory(destination) != before:
                        raise ReviewError("SQLite backup does not match the migration snapshot", 409)
            manifest = []
            for row, document, path, digest, size in artifacts:
                copied = backup / "documents" / path.name
                copied.parent.mkdir(exist_ok=True)
                shutil.copyfile(path, copied)
                if hashlib.sha256(copied.read_bytes()).hexdigest() != digest:
                    raise ReviewError("Artifact backup failed digest verification", 409)
                manifest.append({"document_id": row["id"], "file": "documents/" + path.name,
                                 "sha256": digest, "size": size})
            _write_once(backup / "manifest.json", canonical({"legacy_inventory": before,
                        "database_sha256": hashlib.sha256((backup / "review.sqlite3").read_bytes()).hexdigest(),
                        "artifacts": manifest, "backup_method": "sqlite3.backup_including_committed_WAL"}) + b"\n")
        for statement in DDL:
            db.execute(statement)
        recovered, source_count = 0, 0
        source_rows = {}
        manifest_digests = []
        for manifest_path in source_manifests or []:
            raw = manifest_path.read_bytes()
            manifest_digests.append(hashlib.sha256(raw).hexdigest())
            parsed = json.loads(raw)
            entries = parsed.get("documents", []) if isinstance(parsed, dict) else parsed
            if not isinstance(entries, list):
                raise ReviewError("Invalid historical source manifest")
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("sha256"), str):
                    source_rows.setdefault(entry["sha256"], []).append(entry)
        legacy_reviews = 0
        for row, document, path, digest, size in artifacts:
            pdf_copy = store.directory / "artifacts" / (digest + ".pdf")
            _write_once(pdf_copy, path.read_bytes())
            artifact = {"schema_version": "skony.artifact.v0.2", "sha256": digest, "size": size,
                        "pages": sorted(p.number for p in document.pages),
                        "file": "artifacts/" + digest + ".pdf", "legacy_document_id": row["id"]}
            artifact_id = put_object(db, "artifact", artifact)
            set_head(db, "artifact", digest, artifact_id, 0)
            text = TextSnapshot.legacy(digest, document.pages)
            text_id = put_object(db, "text", text)
            source_ids = [put_object(db, "source", source_record(json.loads(row["source_json"]), digest,
                                                                  origin="legacy_source_json"))]
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='document_sources'").fetchone():
                original_digest = identity(json.loads(row["source_json"]))
                for prior in db.execute("SELECT source_json FROM document_sources WHERE document_id=? ORDER BY id", (row["id"],)):
                    metadata = json.loads(prior["source_json"])
                    if identity(metadata) != original_digest:
                        source_ids.append(put_object(db, "source", source_record(metadata, digest, origin="recorded_source_history")))
            for entry in source_rows.get(digest, []):
                sid = put_object(db, "source", source_record(entry, digest, origin="historical_manifest"))
                if sid not in source_ids:
                    recovered += 1
                    source_ids.append(sid)
            source_count += len(source_ids)
            scope_id = "legacy:" + row["id"]
            binding = ScopeBinding(scope_id=scope_id, subject_id="unresolved:" + row["id"],
                artifact_id=digest, text_snapshot_id=text_id, association_version="legacy-unverified",
                role_version="legacy-unverified", role="unknown", membership="unresolved",
                windows=[ScopeWindow(page=p.page, layer_id=p.layer_id, start=0, end=len(p.text)) for p in text.pages])
            scope = ScopeRecord(binding=binding, source_ids=sorted(source_ids))
            set_head(db, "scope", scope_id, put_object(db, "scope", scope), 0)
            for review in db.execute("SELECT * FROM reviews WHERE document_id=? ORDER BY field", (row["id"],)):
                old = json.loads(review["review_json"])
                put_object(db, "legacy_review", {"schema_version": "skony.legacy-review.v0.2",
                    "document_id": row["id"], "scope_id": scope_id, "predicate": review["field"],
                    "original": old, "text_snapshot_id": text_id, "origin": "assisted_legacy",
                    "structured_scope": "unverified", "eligible_for_current_export": False,
                    "revalidation_required": True})
                legacy_reviews += 1
        after = legacy_inventory(db)
        if after != before:
            raise ReviewError("Migration changed legacy records; rolled back", 409)
        report = {"schema_version": "skony.migration.v0.2", "completed_at": timestamp(),
                  "backup_directory": str(backup) if backup else None, "before": before, "after": after,
                  "legacy_text_snapshots": len(artifacts), "legacy_reviews_preserved": legacy_reviews,
                  "source_records": source_count, "manifest_source_records_recovered": recovered,
                  "manifest_digests": sorted(manifest_digests),
                  "limitations": ["Legacy parser/configuration is unknown; exact stored text was retained.",
                                 "Historical decisions need structured scope and dependency revalidation.",
                                 "Collapsed source associations absent from retained manifests cannot be reconstructed."]}
        db.execute("INSERT INTO schema_migrations VALUES(2,?)", (canonical(report).decode("utf-8"),))
        return report
