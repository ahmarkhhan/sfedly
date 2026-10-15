"""Cache exact, secret-free model requests; offline replay never calls a model."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pypdf

from . import pipeline
from .client import Settings, complete, request_payload
from .schema import CandidateExtraction, Document

CACHE_SCHEMA_VERSION = "skony.cache.v0.2"
PARSER_POLICY = "skony.pdf.v0.1"
USAGE_FIELDS = {"prompt_tokens", "completion_tokens", "total_tokens"}


class CacheMiss(ValueError):
    pass


class CacheIntegrityError(ValueError):
    pass


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def atomic_json(path: Path, value) -> None:
    """Replace a complete JSON file; interrupted writes do not truncate its predecessor."""
    atomic_bytes(path, canonical_json(value) + b"\n")


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".skony-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def endpoint_identity(base_url: str) -> str:
    url = urlsplit(base_url)
    if (not url.hostname or url.username or url.password or url.query or url.fragment
            or (url.scheme != "https" and not (url.scheme == "http" and
                url.hostname in {"localhost", "127.0.0.1", "::1"}))):
        raise ValueError("Cache endpoint must be a credential-free HTTPS base URL or localhost")
    return base_url.rstrip("/")


def request_identity(document: Document, settings: Settings, *, max_tokens=4096, temperature=0,
                     prompt_text: str | None = None, prompt_version: str | None = None,
                     model_revision: str | None = None, json_schema: dict | None = None) -> dict:
    messages = pipeline.messages_for(document, prompt_text=prompt_text)
    schema = CandidateExtraction.model_json_schema() if json_schema is None else json_schema
    return {
        "cache_schema": CACHE_SCHEMA_VERSION,
        "document_sha256": document.sha256,
        "page_text_sha256": digest([{"number": page.number, "text": page.text} for page in document.pages]),
        "parser": {"name": "pypdf", "version": pypdf.__version__, "policy": PARSER_POLICY},
        "prompt_version": pipeline.PROMPT_VERSION if prompt_version is None else prompt_version,
        "model_revision": model_revision,
        "base_url": endpoint_identity(settings.base_url),
        "payload": request_payload(settings, messages, max_tokens=max_tokens, temperature=temperature,
                                   json_schema=schema),
    }


def request_fingerprint(document: Document, model: str | Settings, *,
                        base_url: str = "https://cache-key.invalid", **options) -> str:
    # String model names remain supported for callers comparing fingerprints.
    # Runtime cache lookups always pass Settings so the real endpoint is included.
    settings = model if isinstance(model, Settings) else Settings(model, base_url, "")
    return digest(request_identity(document, settings, **options))


class ResponseCache:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.hits = self.misses = self.http_calls = 0

    def _path(self, key: str) -> Path:
        if not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{64}", key) is None:
            raise ValueError("Invalid cache key")
        return self.directory / f"{key}.json"

    def _validate(self, key: str, entry: dict) -> None:
        try:
            if not isinstance(entry, dict) or entry["cache_schema"] != CACHE_SCHEMA_VERSION:
                raise ValueError
            if entry["cache_key"] != key or digest(entry["request"]) != key:
                raise ValueError
            body = {name: value for name, value in entry.items() if name != "entry_sha256"}
            if entry["entry_sha256"] != digest(body):
                raise ValueError
            if not isinstance(entry["content"], str) or not entry["content"].strip():
                raise ValueError
            if entry["content_sha256"] != hashlib.sha256(entry["content"].encode("utf-8")).hexdigest():
                raise ValueError
            usage = entry["usage"]
            if (not isinstance(usage, dict) or not set(usage).issubset(USAGE_FIELDS)
                    or any(type(value) is not int or value < 0 for value in usage.values())):
                raise ValueError
            latency = entry["latency_seconds"]
            if type(latency) not in {int, float} or not math.isfinite(latency) or latency < 0:
                raise ValueError
            completed = datetime.fromisoformat(entry["completed_at"])
            if completed.tzinfo is None:
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise CacheIntegrityError("Cached response failed integrity checks; no live fallback was attempted") from None

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            raise CacheIntegrityError("Cached response cannot be read; no live fallback was attempted") from None
        self._validate(key, entry)
        return entry

    def put(self, key: str, entry: dict) -> None:
        record = dict(entry)
        record.update(cache_schema=CACHE_SCHEMA_VERSION, cache_key=key)
        record["content_sha256"] = hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
        record["entry_sha256"] = digest({name: value for name, value in record.items() if name != "entry_sha256"})
        self._validate(key, record)
        atomic_json(self._path(key), record)

    def complete(self, settings: Settings, document: Document, *, allow_live: bool = True,
                 max_tokens=4096, temperature=0, prompt_text: str | None = None,
                 prompt_version: str | None = None, model_revision: str | None = None,
                 json_schema: dict | None = None,
                 transport: httpx.BaseTransport | None = None) -> tuple[str, dict, str, bool]:
        request = request_identity(document, settings, max_tokens=max_tokens, temperature=temperature,
            prompt_text=prompt_text, prompt_version=prompt_version, model_revision=model_revision,
            json_schema=json_schema)
        key = digest(request)
        entry = self.get(key)
        if entry is not None:
            self.hits += 1
            return entry["content"], entry["usage"], key, True
        self.misses += 1
        if not allow_live:
            raise CacheMiss("No recorded response matches this exact request; offline replay makes no model calls")
        payload = request["payload"]
        self.http_calls += 1
        started = time.monotonic()
        content, usage = complete(settings, payload["messages"], max_tokens=payload["max_tokens"],
            temperature=payload["temperature"], json_schema=payload["response_format"]["json_schema"]["schema"],
            transport=transport)
        self.put(key, {"request": request, "content": content, "usage": usage,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "latency_seconds": time.monotonic() - started})
        return content, usage, key, False

    def stats(self) -> dict:
        return {"hits": self.hits, "misses": self.misses, "http_calls": self.http_calls}
