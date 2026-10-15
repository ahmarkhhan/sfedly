"""Import pinned corpus sources and verified batch suggestions without model calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import pipeline
from .batch import BATCH_SCHEMA, SOURCE_FIELDS, InputFailure, _input, load_manifest
from .cache import ResponseCache, digest
from .review import ReviewStore
from .schema import ExtractionResult


def batch_results(run_dir: Path, manifest_bytes: bytes, entries: list) -> dict:
    ledger = json.loads((run_dir / "run_ledger.json").read_bytes())
    if (ledger.get("schema_version") != BATCH_SCHEMA or ledger.get("config_sha256") != digest(ledger["config"])
            or ledger["config"]["source_manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest()):
        raise ValueError("Batch ledger does not match this source manifest")
    results, seen = {}, set()
    for item in ledger["items"]:
        index = item["index"]
        if (type(index) is not int or not 0 <= index < len(entries) or index in seen
                or item["item_id"] != f"{index:04}-{digest(entries[index])[:12]}"):
            raise ValueError("Batch item identity is invalid")
        seen.add(index)
        if item["status"] == "ok":
            results[index] = item
    return results


def verified_result(run_dir: Path, item: dict, document, cache: ResponseCache):
    filename = item["result_file"]
    if not isinstance(filename, str) or "\\" in filename or ":" in filename:
        raise ValueError("Invalid batch result path")
    path = (run_dir / filename).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ValueError("Batch result path is outside the run directory")
    data = json.loads(path.read_bytes())
    if digest(data) != item["result_sha256"] or item["document_sha256"] != document.sha256:
        raise ValueError("Batch result checksum mismatch")
    result = ExtractionResult.model_validate(data)
    record = cache.get(item["cache_key"])
    if (record is None or record["entry_sha256"] != item["cache_entry_sha256"]
            or record["content_sha256"] != item["response_sha256"]
            or record["request"]["document_sha256"] != document.sha256
            or record["request"]["page_text_sha256"] != digest([
                {"number": page.number, "text": page.text} for page in document.pages])):
        raise ValueError("Cached response does not match the batch result")
    rebuilt = pipeline.verify_response(document, record["content"], record["request"]["payload"]["model"],
        record["latency_seconds"], record["usage"], prompt_version=record["request"]["prompt_version"])
    if rebuilt.model_dump(mode="json") != data:
        raise ValueError("Batch verification changed; rerun batch in replay mode first")
    return result, record["content"]


def import_corpus(fetch_dir: Path, store: ReviewStore, *, run_dir: Path | None = None,
                  cache: ResponseCache | None = None) -> dict:
    manifest_bytes = (fetch_dir / "fetch_manifest.json").read_bytes()
    entries = load_manifest(fetch_dir, source_bytes=manifest_bytes)
    if run_dir is not None and cache is None:
        raise ValueError("Importing batch results requires their response cache")
    results = batch_results(run_dir, manifest_bytes, entries) if run_dir is not None else {}
    known = {store.get(summary["id"])["document"]["sha256"] for summary in store.list()}
    counts = {"total": len(entries), "added": 0, "already_present": 0, "source_failed": 0,
              "results_imported": 0, "results_already_present": 0, "result_failed": 0, "errors": []}
    for index, entry in enumerate(entries):
        try:
            document = _input(fetch_dir, entry)
            source = {name: entry.get(name) for name in (*SOURCE_FIELDS, "category", "date", "retrieved_at_utc",
                                                       "synthetic", "gold_annotation") if name in entry}
            source.update(gold_candidate=not source.get("synthetic"), recorded_pilot=False)
            if source.get("role") and not source.get("role_origin"):
                source.update(role_origin="unverified_selection_hint", role_review_required=True)
            identifier = store.add(document, fetch_dir / entry["document_file"], source)
            counts["already_present" if document.sha256 in known else "added"] += 1
            known.add(document.sha256)
            store.backfill_source(identifier, source)
        except Exception as error:
            counts["source_failed"] += 1
            counts["errors"].append({"index": index, "stage": "source",
                                     "reason": error.reason if isinstance(error, InputFailure) else type(error).__name__})
            continue
        if index not in results:
            continue
        try:
            item = results[index]
            result, response = verified_result(run_dir, item, document, cache)
            batch_key = digest({"document": identifier, "cache": item["cache_key"], "result": item["result_sha256"]})
            changed = store.finish_extraction(identifier, result, response, batch_key=batch_key)
            counts["results_imported" if changed else "results_already_present"] += 1
        except Exception as error:
            counts["result_failed"] += 1
            counts["errors"].append({"index": index, "stage": "result", "reason": type(error).__name__})
    return counts
