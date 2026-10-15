"""Prove bounded real-data extraction and offline replay; this is not an accuracy evaluation.

Selects one usable DE and FR source, preserves an existing failed-fetch row,
and writes private inputs, raw-response cache references and both run ledgers.
Live calls require --live. The second run explicitly has no API credential and
uses a transport that rejects any attempted HTTP request.
"""

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.__main__ import load_env
from skony.batch import _input, load_manifest, run_batch
from skony.cache import ResponseCache, atomic_json
from skony.client import Settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-dir", type=Path, default=ROOT / "data/private/gold")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "output/cache")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--live", action="store_true", help="allow at most two uncached model requests")
    args = parser.parse_args(argv)
    output = args.out or ROOT / "output" / ("pipeline-proof-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6])
    if output.exists() and any(output.iterdir()):
        parser.error("Choose a new, empty output directory")
    if args.live:
        load_env(ROOT / ".env")
        settings = Settings.from_environment()
    else:
        settings = Settings("swiss-ai/Apertus-v1.5-70B", "https://api.inference.cscs.ch/v1", "")
    entries = load_manifest(args.fetch_dir)
    chosen = []
    for language in ("de", "fr"):
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("language") != language:
                continue
            try:
                document = _input(args.fetch_dir, entry)
                if 0 < sum(len(page.text) for page in document.pages) <= 50000:
                    chosen.append(entry)
                    break
            except (ValueError, OSError):
                continue
        else:
            raise ValueError("Corpus has no supported, hash-verified source for " + language)
    inputs = output / "input"
    inputs.mkdir(parents=True)
    for entry in chosen:
        destination = inputs / entry["document_file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.fetch_dir / entry["document_file"], destination)
    failed = next((entry for entry in entries if isinstance(entry, dict) and entry.get("status") == "failed"), None)
    manifest = {"purpose": "bounded engineering proof, not a representative quality benchmark",
                "documents": chosen + ([failed] if failed else [])}
    atomic_json(inputs / "fetch_manifest.json", manifest)
    before = (inputs / "fetch_manifest.json").read_bytes()
    first = run_batch("live" if args.live else "replay", inputs, output / "first", ResponseCache(args.cache_dir), settings)

    def forbidden(request):
        raise AssertionError("Offline proof attempted an HTTP request")

    replay_settings = Settings(settings.model, settings.base_url, "")
    second = run_batch("replay", inputs, output / "replay", ResponseCache(args.cache_dir), replay_settings,
                       transport=httpx.MockTransport(forbidden))
    successful = first["counts"]["processed"] == second["counts"]["processed"] == len(chosen)
    same_results = successful and all(
        old.get("cache_key") == new.get("cache_key") and
        json.loads((output / "first" / old["result_file"]).read_bytes()) ==
        json.loads((output / "replay" / new["result_file"]).read_bytes())
        for old, new in zip(first["items"][:len(chosen)], second["items"][:len(chosen)]))
    preserved_failure = not failed or (first["items"][-1]["error"]["reason"] ==
                                     second["items"][-1]["error"]["reason"] == "source_fetch_failed")
    unchanged = (inputs / "fetch_manifest.json").read_bytes() == before
    passed = same_results and preserved_failure and unchanged and second["counts"]["live_calls"] == 0
    report = {"kind": "engineering_pipeline_proof_not_accuracy", "status": "passed" if passed else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(), "model": settings.model, "endpoint": settings.base_url,
        "source_languages": [entry["language"] for entry in chosen], "first": first["counts"], "replay": second["counts"],
        "first_usage": first["usage"], "same_results": same_results, "failure_preserved": bool(preserved_failure),
        "manifest_unchanged": unchanged, "replay_api_credential": "empty", "gold_labels_created": 0,
        "model_latency_seconds": [item.get("model_latency_seconds") for item in first["items"][:len(chosen)]]}
    atomic_json(output / "proof.json", report)
    print(json.dumps(report, indent=2))
    print(f"Evidence: {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
