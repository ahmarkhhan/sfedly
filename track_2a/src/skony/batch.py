"""Manifest-driven extraction with complete failure accounting and cached replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pypdf
from pydantic import ValidationError
from pypdf.errors import PdfReadError

from . import pipeline
from .cache import (PARSER_POLICY, CacheIntegrityError, CacheMiss, ResponseCache,
                    atomic_json, digest, endpoint_identity)
from .client import EndpointError, Settings
from .pdf import parse_pdf
from .schema import CandidateExtraction

ROOT = Path(__file__).resolve().parents[2]
BATCH_SCHEMA = "skony.batch.v0.2"
SOURCE_FIELDS = ("body_key", "body_id", "body_label", "affair_id", "openparldata_document_id",
                 "document_file", "language", "level", "role", "role_origin", "role_review_required",
                 "source_url", "retrieved_url", "licence_status", "likely_scanned")


class InputFailure(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def load_manifest(fetch_dir: Path, *, source_bytes: bytes | None = None) -> list[dict]:
    manifest = json.loads(source_bytes if source_bytes is not None else
                          (fetch_dir / "fetch_manifest.json").read_bytes())
    if not isinstance(manifest, dict) or not isinstance(manifest.get("documents"), list):
        raise ValueError("Fetch manifest must contain a documents list")
    # Keep failed downloads and malformed rows: none may silently disappear.
    return manifest["documents"]


def _input(fetch_dir: Path, entry: dict):
    if not isinstance(entry, dict):
        raise InputFailure("invalid_manifest_entry")
    if entry.get("status") not in {"fetched", "cached"}:
        raise InputFailure("source_fetch_failed")
    filename = entry.get("document_file")
    if not isinstance(filename, str) or not filename or "\\" in filename or ":" in filename:
        raise InputFailure("invalid_source_path")
    path = (fetch_dir / filename).resolve()
    if not path.is_relative_to(fetch_dir.resolve()):
        raise InputFailure("source_path_outside_corpus")
    expected = entry.get("sha256")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise InputFailure("missing_document_sha256")
    if not path.is_file():
        raise InputFailure("source_file_missing")
    if path.stat().st_size > 25 * 1024 * 1024:
        raise InputFailure("pdf_size_limit")
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != expected:
        raise InputFailure("source_checksum_mismatch")
    return parse_pdf(contents, path.name)


def _counts(items, cache: ResponseCache, initial: dict):
    states = [item["status"] for item in items]
    stats = cache.stats()
    return {"total": len(items), "processed": states.count("ok"), "failed": states.count("failed"),
            "pending": sum(state not in {"ok", "failed"} for state in states),
            "served_from_cache": stats["hits"] - initial["hits"],
            "cache_misses": stats["misses"] - initial["misses"],
            "live_calls": stats["http_calls"] - initial["http_calls"]}


def run_batch(mode: str, fetch_dir: Path, out_dir: Path, cache: ResponseCache,
              settings: Settings, *, limit: int | None = None, max_tokens=4096,
              model_revision: str | None = None, resume=False,
              transport: httpx.BaseTransport | None = None) -> dict:
    if mode not in {"live", "replay"} or settings is None:
        raise ValueError("Choose live/replay and provide model/endpoint identity")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("limit must be positive")
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be positive")
    if mode == "live" and ("apertus" not in settings.model.lower() or "1.5" not in settings.model):
        raise ValueError("Live extraction requires an explicitly identified Apertus 1.5 model")
    endpoint_identity(settings.base_url)
    source_path = fetch_dir / "fetch_manifest.json"
    source_bytes = source_path.read_bytes()
    all_entries = load_manifest(fetch_dir, source_bytes=source_bytes)
    entries = all_entries if limit is None else all_entries[:limit]
    prompt_text = pipeline.PROMPT_PATH.read_text(encoding="utf-8")
    prompt_version = pipeline.PROMPT_VERSION
    schema = CandidateExtraction.model_json_schema()
    config = {"schema": BATCH_SCHEMA, "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
              "limit": limit, "model": settings.model, "base_url": settings.base_url.rstrip("/"),
              "model_revision": model_revision, "max_tokens": max_tokens, "temperature": 0,
              "prompt_version": prompt_version, "prompt_sha256": digest(prompt_text),
              "output_schema_sha256": digest(schema), "parser_policy": PARSER_POLICY,
              "parser_version": pypdf.__version__,
              "verifier_version": pipeline.VERIFIER_VERSION}
    config_hash = digest(config)
    ledger_path = out_dir / "run_ledger.json"
    if out_dir.exists() and any(out_dir.iterdir()):
        if not resume or not ledger_path.is_file():
            raise ValueError("Output directory is not empty; select a new one or use --resume for a matching run")
        previous = json.loads(ledger_path.read_text(encoding="utf-8"))
        if previous.get("config_sha256") != config_hash:
            raise ValueError("Resume configuration differs; preserve the previous run and choose a new output directory")
        atomic_json(out_dir / "attempts" / f"{uuid.uuid4().hex}.json", previous)
    out_dir.mkdir(parents=True, exist_ok=True)
    attempt = uuid.uuid4().hex
    ledger = {"schema_version": BATCH_SCHEMA, "run_id": out_dir.name, "attempt_id": attempt,
              "mode": mode, "config": config, "config_sha256": config_hash,
              "source_manifest_items": len(all_entries), "excluded_by_limit": len(all_entries) - len(entries),
              "started_at": utcnow(), "status": "running", "items": []}
    for index, entry in enumerate(entries):
        source = {name: entry.get(name) for name in SOURCE_FIELDS} if isinstance(entry, dict) else {}
        if source.get("role") and not source.get("role_origin"):
            source.update(role_origin="unverified_selection_hint", role_review_required=True)
        ledger["items"].append({"index": index, "item_id": f"{index:04}-{digest(entry)[:12]}",
                                "source": source, "status": "pending"})
    initial = cache.stats()
    started = time.monotonic()

    def save():
        ledger["counts"] = _counts(ledger["items"], cache, initial)
        # These are original inference tokens, including responses that failed
        # schema validation. Cache replay consumes no new inference tokens.
        ledger["usage"] = {name: (sum(item["usage"][name] for item in ledger["items"] if name in item.get("usage", {}))
                                  if any(name in item.get("usage", {}) for item in ledger["items"]) else None)
                           for name in ("prompt_tokens", "completion_tokens", "total_tokens")}
        ledger["usage_reporting"] = {"items_with_usage": sum(bool(item.get("usage")) for item in ledger["items"]),
                                    "reporting_items_by_field": {name: sum(name in item.get("usage", {}) for item in ledger["items"])
                                                                 for name in ledger["usage"]},
                                    "semantics": "original inference usage; missing provider values are unknown"}
        ledger["elapsed_seconds"] = time.monotonic() - started
        atomic_json(ledger_path, ledger)

    save()
    try:
        for index, (entry, item) in enumerate(zip(entries, ledger["items"])):
            item["status"] = "processing"
            save()
            item_started = time.monotonic()
            try:
                document = _input(fetch_dir, entry)
                item["document_sha256"] = document.sha256
                content, usage, key, from_cache = cache.complete(settings, document,
                    allow_live=mode == "live", max_tokens=max_tokens, prompt_text=prompt_text,
                    prompt_version=prompt_version, json_schema=schema,
                    model_revision=model_revision, transport=transport)
                recorded = cache.get(key)
                item.update(cache_key=key, from_cache=from_cache, usage=usage,
                            model_latency_seconds=recorded["latency_seconds"],
                            response_sha256=recorded["content_sha256"],
                            cache_entry_sha256=recorded["entry_sha256"])
                result = pipeline.verify_response(document, content, settings.model,
                    recorded["latency_seconds"], usage,
                    prompt_version=recorded["request"]["prompt_version"])
                relative = Path("results") / attempt / f"{item['item_id']}.json"
                result_data = result.model_dump(mode="json")
                atomic_json(out_dir / relative, result_data)
                item.update(status="ok", result_file=relative.as_posix(),
                            result_sha256=digest(result_data),
                            located_fields=sum(field.status == "source_located" for field in result.fields.values()))
            except InputFailure as error:
                item.update(status="failed", error={"stage": "intake", "reason": error.reason})
            except CacheMiss:
                item.update(status="failed", error={"stage": "cache", "reason": "cache_miss"})
            except CacheIntegrityError:
                item.update(status="failed", error={"stage": "cache", "reason": "cache_integrity_failure"})
            except EndpointError as error:
                item.update(status="failed", error={"stage": "endpoint", "reason": error.reason,
                                                     "http_status": error.status_code})
            except ValidationError as error:
                item.update(status="failed", error={"stage": "schema", "reason": "invalid_model_output",
                    "details": [{"field": list(issue["loc"]), "type": issue["type"]}
                                for issue in error.errors(include_input=False, include_context=False, include_url=False)]})
            except PdfReadError:
                item.update(status="failed", error={"stage": "intake", "reason": "invalid_pdf"})
            except ValueError:
                item.update(status="failed", error={"stage": "preparation", "reason": "unsupported_input_or_request"})
            except OSError:
                item.update(status="failed", error={"stage": "filesystem", "reason": "file_operation_failed"})
            except Exception as error:
                # Preserve the row without echoing provider responses/source values in tracebacks.
                item.update(status="failed", error={"stage": "internal", "reason": type(error).__name__})
            item["processing_seconds"] = time.monotonic() - item_started
            save()
            print(f"[{index + 1}/{len(entries)}] {item['item_id']}: {item['status']}", flush=True)
        ledger["status"] = "completed"
    except BaseException:
        ledger["status"] = "interrupted"
        raise
    finally:
        ledger["finished_at"] = utcnow()
        save()
    if mode == "replay" and ledger["counts"]["live_calls"]:
        raise RuntimeError("Replay attempted a live model call")
    return ledger


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["live", "replay"], default="replay")
    parser.add_argument("--fetch-dir", type=Path, default=ROOT / "data/private/gold")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "output/cache")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--model-revision")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.mode == "live":
            from .__main__ import load_env
            load_env(args.env_file)
        model = args.model or os.environ.get("LLM_NAME") or "swiss-ai/Apertus-v1.5-70B"
        base = args.base_url or os.environ.get("LLM_BASE_URL") or "https://api.inference.cscs.ch/v1"
        settings = Settings(model.strip(), endpoint_identity(base),
                            os.environ.get("LLM_API_KEY", "").strip() if args.mode == "live" else "")
        output = args.out or ROOT / "output/batch" / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8])
        ledger = run_batch(args.mode, args.fetch_dir, output, ResponseCache(args.cache_dir), settings,
                           limit=args.limit, max_tokens=args.max_tokens, model_revision=args.model_revision,
                           resume=args.resume)
        print(json.dumps(ledger["counts"], indent=2))
        print(f"Saved run ledger in {output}")
        return 0 if ledger["counts"]["total"] and not ledger["counts"]["failed"] else 1
    except (ValueError, OSError, KeyError):
        print("Batch could not start. Check manifest, endpoint identity, options and output directory; no source manifest was changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
