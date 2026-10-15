"""Local CLI for intake, a live extraction and offline verification."""

import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from pypdf.errors import PdfReadError

from .client import Settings, complete
from .pdf import read_pdf
from .pipeline import extract, verify_response
from .schema import Document


def load_env(path: Path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("Invalid .env line; expected NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        if name not in {"LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY"}:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def write_output(path: Path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"Saved {path.name}")


def main():
    parser = argparse.ArgumentParser(description="Skony parliamentary extraction starter")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["ingest", "extract"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("pdf", type=Path)
        cmd.add_argument("--output", type=Path, required=True)
    sub.add_parser("smoke")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--data-dir", type=Path, default=os.environ.get("SKONY_DATA_DIR"))
    serve.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    serve.add_argument("--mode", choices=["replay", "live"], default=os.environ.get("SKONY_MODE", "replay"))
    serve.add_argument("--public-port", type=int)
    verify = sub.add_parser("verify")
    verify.add_argument("document", type=Path)
    verify.add_argument("candidate", type=Path)
    verify.add_argument("--output", type=Path, required=True)
    schema = sub.add_parser("schema")
    schema.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        # Replay never needs a local credential file, even if an unrelated one exists.
        if args.command != "serve" or args.mode == "live":
            load_env(args.env_file)
        if args.command == "serve":
            from .server import run_server
            run_server(args.port, args.data_dir, host=args.host, mode=args.mode, public_port=args.public_port)
        elif args.command == "schema":
            from .schema import CandidateExtraction
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(CandidateExtraction.model_json_schema(), indent=2), encoding="utf-8")
            print("Saved candidate schema")
        elif args.command == "smoke":
            settings = Settings.from_environment()
            answer, _ = complete(settings, [{"role": "user", "content": "Reply with exactly APERTUS_READY."}], max_tokens=32)
            if answer.strip() != "APERTUS_READY":
                raise ValueError("Endpoint responded, but did not pass the smoke prompt")
            print("Endpoint smoke test passed; confirm the served model is Apertus 1.5 with the provider")
        elif args.command == "verify":
            document = Document.model_validate_json(args.document.read_text(encoding="utf-8"))
            result = verify_response(document, args.candidate.read_text(encoding="utf-8"), "offline_fixture_not_model_run")
            write_output(args.output, result)
        else:
            document = read_pdf(args.pdf)
            result = document if args.command == "ingest" else extract(document, Settings.from_environment())
            write_output(args.output, result)
            if document.textless_pages:
                print(f"Pages needing OCR or review: {document.textless_pages}")
        return 0
    except ValidationError:
        print("Input or model output failed the schema; no output accepted", file=sys.stderr)
    except (ValueError, OSError, PdfReadError):
        # Never echo provider response bodies, source text or keys in a traceback.
        print("Operation failed. Check input limits, configuration and model response format. No output accepted.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

