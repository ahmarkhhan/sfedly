"""Load an explicitly synthetic public fixture, never a claimed model run."""

import json
from hashlib import sha256
from pathlib import Path

from .pdf import read_pdf
from .schema import CandidateExtraction, ExtractionResult
from .verify import locate

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"


def load_demo(directory: Path = SAMPLE):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("kind") != "synthetic_engineering_fixture":
        raise ValueError("The bundled demonstration must be labelled synthetic")
    pdf = directory / "synthetic-request.pdf"
    candidate_path = directory / "candidate.json"
    for name, path in (("pdf_sha256", pdf), ("candidate_sha256", candidate_path)):
        if sha256(path.read_bytes()).hexdigest() != manifest.get(name):
            raise ValueError("Bundled demonstration checksum mismatch")
    document = read_pdf(pdf)
    candidate = CandidateExtraction.model_validate_json(candidate_path.read_text(encoding="utf-8"))
    result = ExtractionResult(
        document=document,
        model_name="synthetic_fixture_not_model_inference",
        prompt_version="synthetic-demo-v1-not-a-model-prompt",
        fields={name: locate(getattr(candidate, name), document, name)
                for name in CandidateExtraction.model_fields},
        latency_seconds=0.0,
    )
    source = {
        "body_label": "Practice document · fictional parliament",
        "language_label": "German",
        "synthetic": True,
        "fixture_id": manifest["fixture_id"],
        "model_generated": False,
        "gold_annotation": False,
        "licence": "CDLA-Permissive-2.0",
    }
    return pdf, result, source
