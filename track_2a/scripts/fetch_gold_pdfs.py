"""Download selected gold-set PDFs and write per-document manifests.

Reads the candidate manifest from select_gold_corpus.py, downloads each PDF
from its OpenParlData files-server URL, verifies bytes, and records source,
hash and licence status. Downloaded files stay under data/private/gold/ until
redistribution rights are confirmed per document; see docs/16 (W01).

No model calls. Idempotent: an existing file with a matching hash is kept.

Usage:
    python scripts/fetch_gold_pdfs.py [--candidates data/private/gold_candidates.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skony.cache import atomic_bytes, atomic_json
ALLOWED_HOSTS = {"files.openparldata.ch", "www.nidau.ch", "nidau.ch"}
MAX_BYTES = 25 * 1024 * 1024  # matches the pipeline's per-PDF limit
TIMEOUT = 40


def fetch_one(client: httpx.Client, entry: dict, dest_dir: Path) -> dict:
    doc_id = entry["openparldata_document_id"]
    body_key = entry["body_key"]
    url = entry.get("retrieved_url") or entry.get("source_url")
    manifest = {
        "openparldata_document_id": doc_id,
        "body_key": body_key,
        "body_id": entry.get("body_id"),
        "body_label": entry.get("body_label"),
        "affair_id": entry.get("affair_id"),
        "role": entry.get("role"),
        "role_origin": entry.get("role_origin") or "unverified_selection_hint",
        "role_review_required": entry.get("role_review_required", True),
        "level": entry.get("level", "unknown"),
        "category": entry.get("category"),
        "language": entry.get("language"),
        "date": entry.get("date"),
        "name": entry.get("name"),
        "source_url": entry.get("source_url"),
        "retrieved_url": url,
        "likely_scanned": entry.get("likely_scanned", False),
        "retrieved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "licence_status": "officially published by the parliament; per-item "
                          "redistribution right not yet verified (W01)",
    }
    if not url:
        manifest.update(status="failed", error="no download URL in metadata")
        return manifest

    if any(re.fullmatch(r"[A-Za-z0-9_-]+", str(part)) is None for part in (body_key, doc_id)):
        manifest.update(status="failed", error="invalid source identifier")
        return manifest

    filename = f"{body_key}_{doc_id}.pdf"
    dest = dest_dir / filename
    manifest["document_file"] = filename

    # Skip a previously fetched, hash-verified file.
    hash_path = dest_dir / f"{body_key}_{doc_id}.sha256"
    if dest.is_file() and hash_path.is_file():
        recorded = hash_path.read_text(encoding="utf-8").strip()
        actual = hashlib.sha256(dest.read_bytes()).hexdigest()
        if recorded == actual:
            manifest.update(status="cached", sha256=actual, bytes=dest.stat().st_size)
            return manifest

    try:
        for redirect in range(6):
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username
                    or parsed.password or parsed.port not in {None, 443}):
                manifest.update(status="failed", error="download URL is outside the HTTPS allow-list")
                return manifest
            with client.stream("GET", url, follow_redirects=False) as response:
                if response.is_redirect:
                    if redirect == 5 or not response.headers.get("location"):
                        manifest.update(status="failed", error="redirect limit or missing location")
                        return manifest
                    url = urljoin(url, response.headers["location"])
                    continue
                if response.status_code != 200:
                    manifest.update(status="failed", error=f"HTTP {response.status_code}")
                    return manifest
                contents = bytearray()
                for chunk in response.iter_bytes():
                    contents.extend(chunk)
                    if len(contents) > MAX_BYTES:
                        manifest.update(status="failed", error="exceeds 25 MB limit")
                        return manifest
                break
    except (httpx.HTTPError, ValueError) as error:
        manifest.update(status="failed", error=type(error).__name__)
        return manifest

    if not contents.startswith(b"%PDF-"):
        manifest.update(status="failed", error="response was not a PDF")
        return manifest

    atomic_bytes(dest, bytes(contents))
    digest = hashlib.sha256(bytes(contents)).hexdigest()
    atomic_bytes(hash_path, (digest + "\n").encode("ascii"))
    manifest.update(status="fetched", sha256=digest, bytes=len(contents),
                    content_type="application/pdf", final_download_url=url)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default=str(ROOT / "data" / "private" / "gold_candidates.json"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "private" / "gold"))
    parser.add_argument("--only-body", default=None, help="fetch one body_key only")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    docs = candidates.get("documents", [])
    if args.only_body:
        docs = [d for d in docs if d["body_key"] == args.only_body]
    if args.limit:
        docs = docs[: args.limit]

    dest_dir = Path(args.out_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    fetched = cached = failed = 0
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT,
                      headers={"User-Agent": "skony-gold-fetcher/0.1"}) as client:
        for entry in docs:
            result = fetch_one(client, entry, dest_dir)
            results.append(result)
            status = result["status"]
            if status == "fetched":
                fetched += 1
            elif status == "cached":
                cached += 1
            else:
                failed += 1
                print(f"  FAIL {result['body_key']}_{result['openparldata_document_id']}: "
                      f"{result.get('error')}", file=sys.stderr)
            print(f"[{len(results)}/{len(docs)}] {result['document_file'] if 'document_file' in result else result['openparldata_document_id']}: {status}", flush=True)

    # A partial retry must not erase the other corpus entries.
    manifest_path = dest_dir / "fetch_manifest.json"
    previous = json.loads(manifest_path.read_bytes()).get("documents", []) if manifest_path.is_file() else []
    merged = merge_documents(previous, results)
    manifest_out = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidates_file": str(Path(args.candidates).name),
        "counts": {**{status: sum(row.get("status") == status for row in merged)
                       for status in ("fetched", "cached", "failed")}, "total": len(merged)},
        "attempt_counts": {"fetched": fetched, "cached": cached, "failed": failed, "total": len(results)},
        "documents": merged,
    }
    atomic_json(manifest_path, manifest_out)
    print(json.dumps(manifest_out["counts"], indent=2))
    print(f"wrote {manifest_path}")
    return 0 if failed == 0 else 1


def merge_documents(previous: list, results: list) -> list:
    merged = {(str(row["body_key"]), str(row["openparldata_document_id"])): row for row in previous}
    for row in results:
        merged[(str(row["body_key"]), str(row["openparldata_document_id"]))] = row
    return list(merged.values())


if __name__ == "__main__":
    raise SystemExit(main())
