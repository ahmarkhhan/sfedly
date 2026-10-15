"""Re-check a recorded real Apertus output locally; makes no inference request."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skony.pipeline import verify_response
from skony.schema import Document


def main():
    directory = ROOT / "output" / "live_pilot" / "nidau-70b-v02"
    document = Document.model_validate_json((directory / "document.json").read_text(encoding="utf-8"))
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if document.sha256 != run["input_sha256"]:
        print("Recorded input identity does not match the original run")
        return 2
    result = verify_response(document, (directory / "model_response.txt").read_text(encoding="utf-8"),
                             run["model"], run["latency_seconds"], run["usage"])
    result.prompt_version = run["prompt_version"]
    (directory / "result-evidence-v02.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    report = {"mode": "recorded_model_output_replay", "new_inference_calls": 0,
              "original_model": run["model"], "original_prompt_version": run["prompt_version"],
              "verifier_version": result.verifier_version,
              "field_states": {name: {"status": field.status, "reason": field.reason}
                               for name, field in result.fields.items()}}
    (directory / "replay-evidence-v02.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
