"""Run one CSCS smoke prompt or one PDF extraction, preserving pilot evidence."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.__main__ import load_env
from skony.client import Settings, complete
from skony.pdf import read_pdf
from skony.pipeline import PROMPT_VERSION, messages_for, verify_response
from skony.schema import CandidateExtraction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--run-name", default="nidau-8b-v01")
    parser.add_argument("--model", choices=["swiss-ai/Apertus-v1.5-8B", "swiss-ai/Apertus-v1.5-70B"])
    args = parser.parse_args()
    if not args.run_name.replace("-", "").replace("_", "").isalnum():
        print("Invalid run name")
        return 2
    load_env(ROOT / ".env")
    try:
        settings = Settings.from_environment()
        if settings.base_url != "https://api.inference.cscs.ch/v1":
            raise ValueError("This pilot is restricted to the configured CSCS endpoint")
        if args.model:
            settings = Settings(args.model, settings.base_url, settings.api_key)
        if settings.model not in {"swiss-ai/Apertus-v1.5-8B", "swiss-ai/Apertus-v1.5-70B"}:
            raise ValueError("Select an official non-thinking Apertus 1.5 model for this pilot")
        if args.smoke_only:
            started = time.monotonic()
            answer, usage = complete(settings, [{"role": "user", "content": "Reply with exactly APERTUS_READY."}], max_tokens=32)
            if answer.strip() != "APERTUS_READY":
                raise ValueError("Endpoint responded but the smoke prompt was not satisfied")
            report = {"provider": "CSCS", "model": settings.model, "smoke_passed": True,
                      "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                      "latency_seconds": round(time.monotonic() - started, 3), "usage": usage}
            directory = ROOT / "output" / "live_pilot"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report))
            return 0
        if args.pdf is None:
            raise ValueError("Supply a real public PDF for extraction")
        document = read_pdf(args.pdf)
        messages = messages_for(document)
        directory = ROOT / "output" / "live_pilot" / args.run_name
        if directory.exists():
            raise ValueError("Run directory already exists; use a new name to preserve evidence")
        directory.mkdir(parents=True)
        (directory / "document.json").write_text(document.model_dump_json(indent=2), encoding="utf-8")
        (directory / "messages.json").write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
        started = time.monotonic()
        content, usage = complete(settings, messages, json_schema=CandidateExtraction.model_json_schema())
        elapsed = time.monotonic() - started
        (directory / "model_response.txt").write_text(content, encoding="utf-8")
        run = {"provider": "CSCS", "model": settings.model, "prompt_version": PROMPT_VERSION,
               "timestamp_utc": datetime.now(timezone.utc).isoformat(), "input_sha256": document.sha256,
               "usage": usage, "latency_seconds": round(elapsed, 3)}
        try:
            result = verify_response(document, content, settings.model, elapsed, usage)
        except ValidationError as error:
            run["schema_valid"] = False
            run["errors"] = error.errors(include_input=False, include_context=False, include_url=False)
            (directory / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
            print(json.dumps({"schema_valid": False, "errors": run["errors"], "run_name": args.run_name}))
            return 4
        run["schema_valid"] = True
        run["verifier_version"] = result.verifier_version
        run["field_states"] = {name: {"status": field.status, "reason": field.reason}
                               for name, field in result.fields.items()}
        (directory / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        (directory / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
        print(json.dumps(run))
        return 0
    except ValueError as error:
        print(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
