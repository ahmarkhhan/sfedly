"""Build labelled synthetic contract/UI examples; never annotation or model gold."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skony.affairs import AffairStore
from skony.cache import atomic_json
from skony.comparison import query_snapshot
from skony.contracts import (FIELDS, CandidateV2, EvidenceSegment, LayerPage, PDFRegion, RunEnvelope,
                            ScopeBinding, ScopeWindow, TextSnapshot, identity)
from skony.evidence_v2 import verify_v2
from skony.pipeline_v2 import PROMPT_ID, candidate_schema, chunk_manifest
from skony.review_contracts import AffairRecord, Claim, ComparisonSpec, ReviewInput, ScopeRecord
from skony.server import Workbench


def candidate(scopes):
    return {"schema_version": "skony.candidate.v0.2", "targets": [{"scope_id": scope,
        "fields": {f: {"outcome": "abstained", "items": [], "abstention_reason": "synthetic_fixture_unsupported"} for f in FIELDS},
        "actors": None, "question_items": None, "response_items": None, "events": None, "relations": None} for scope in scopes]}


def propose(target, predicate, identifier, segments):
    target["fields"][predicate] = {"outcome": "proposed", "abstention_reason": None, "items": [
        {"proposal_id": identifier, "segments": [{"page": page, "layer_id": "fixture", "quote": quote, "context_anchor": None}
                                                   for page, quote in segments]}]}


def build_examples(out):
    examples = {}
    for name, pages in {
        "multi-page-response": ["Request", "The executive agrees in principle.", "Subject to funding approval; no unconditional commitment."],
        "two-submitters": ["Alice Example; Bob Exemple"],
        "minutes-two-affairs": ["Affair A: approved.\nAffair B: rejected."]}.items():
        text = TextSnapshot(artifact_id=identity(["synthetic", name]), parser_name="authored-fixture", parser_version="1",
                            configuration={"synthetic": True}, origin="recorded",
                            pages=[LayerPage(page=i + 1, layer_id="fixture", text=p) for i, p in enumerate(pages)])
        windows = [[ScopeWindow(page=p.page, layer_id=p.layer_id, start=0, end=len(p.text)) for p in text.pages]]
        if name == "minutes-two-affairs":
            split = pages[0].index("Affair B")
            windows = [[ScopeWindow(page=1, layer_id="fixture", start=0, end=split)],
                       [ScopeWindow(page=1, layer_id="fixture", start=split, end=len(pages[0]))]]
        scopes = [ScopeBinding(scope_id=f"fixture-s{i+1}", subject_id=f"fictional-body:affair-{i+1}",
            artifact_id=text.artifact_id, text_snapshot_id=text.id, association_version="authored-fixture",
            role_version="authored-fixture", role="minutes" if len(windows) == 2 else "combined", membership="reviewed", windows=w)
            for i, w in enumerate(windows)]
        data = candidate([s.scope_id for s in scopes])
        if name == "multi-page-response":
            propose(data["targets"][0], "answer_text", "response", [(2, pages[1]), (3, pages[2])])
        elif name == "two-submitters":
            propose(data["targets"][0], "submitter_raw", "block", [(1, pages[0])])
            data["targets"][0]["actors"] = [{"proposal_id": f"actor-{i}", "name": {"item_id": "block", "segment_index": 0,
                "quote": actor}, "role": None} for i, actor in enumerate(["Alice Example", "Bob Exemple"])]
        else:
            for i, word in enumerate(["approved.", "rejected."]):
                propose(data["targets"][i], "decision_raw", f"decision-{i}", [(1, word)])
        manifest = chunk_manifest(text)
        run = RunEnvelope(artifact_id=text.artifact_id, text_snapshot_id=text.id, model_identity="synthetic-not-model-output",
            prompt_identity=PROMPT_ID, schema_identity=identity(candidate_schema()), chunk_manifest_id=manifest.id, scopes=scopes)
        record = {"kind": "synthetic_engineering_fixture_not_gold", "text": text.model_dump(), "run": run.model_dump(),
                  "manifest": manifest.model_dump(), "candidate": data,
                  "resolved": verify_v2(CandidateV2.model_validate(data), run, text).model_dump()}
        atomic_json(out / (name + ".json"), record)
        examples[name] = identity(record)
    atomic_json(out / "manifest.json", {"kind": "synthetic_engineering_fixtures_not_gold", "examples": examples})


def build_ui(store_dir):
    if (store_dir / "review.sqlite3").exists():
        raise ValueError("Use a new isolated UI fixture directory")
    app = Workbench(store_dir, mode="replay")
    domain = AffairStore(app.store)
    scope = domain.scopes()[0]
    record = ScopeRecord.model_validate({k: scope[k] for k in ("binding", "source_ids", "mapping_ids")})
    domain.put_affair(AffairRecord(internal_id="synthetic-practice-affair", provider_namespace="synthetic-fixture", body_id="fictional-body",
        body_key="DEMO", official_affair_id=None, jurisdiction_level="unknown", source_ids=record.source_ids))
    record.binding.subject_id = "synthetic-practice-affair"; record.binding.membership = "reviewed"; record.binding.role = "submission"
    domain.put_scope(record, revision=scope["revision"], reviewer="Automated UI QA — not gold labels", note="Authored synthetic fixture association")
    text = TextSnapshot.model_validate(domain.get(record.binding.text_snapshot_id, "text"))
    png = app.image(app.store.list()[0]["id"], 1)
    width, height = struct.unpack(">II", png[16:24])
    sx, sy = width / 595, height / 842
    # The public fixture is generated at (36,804), 15-point leading. This is
    # a recorded rectangle around the known, authored submitter line (index 7).
    region = PDFRegion(x=30*sx, y=(842-804+15*7-12)*sy, width=530*sx, height=20*sy,
                       render_width=width, render_height=height, transform=[sx,0.0,0.0,-sy,0.0,float(height)],
                       render_identity="pdftoppm-scale1600;authored-fixture-coordinate-system")
    quotes = {"title": "Motion: Sichere Schulwege", "submitter_raw": "Eingereicht von Anna Beispiel",
              "question_text": "Der Gemeinderat wird gebeten, sichere Schulwege zu pruefen.\nDie Verwaltung soll bis Ende 2026 einen Bericht vorlegen."}
    decisions = []
    for predicate, quote in quotes.items():
        if predicate == "title":
            start = text.pages[0].text.index(quote)
            evidence = EvidenceSegment(artifact_id=text.artifact_id, text_snapshot_id=text.id, page=1, layer_id="legacy",
                start=start, end=start+len(quote), quote=quote, match_method="exact")
        else:
            evidence = EvidenceSegment(artifact_id=text.artifact_id, text_snapshot_id=None, page=1, layer_id=None,
                quote=quote, basis="image", region=region if predicate=="submitter_raw" else None,
                note="Authored synthetic visual-evidence fixture for automated UI QA; not a human annotation.")
        claim = domain.put_claim(Claim(scope_id=record.binding.scope_id, subject_id=record.binding.subject_id,
                                      predicate=predicate, value=quote, evidence=[evidence]))
        review = domain.review(ReviewInput(claim_id=claim, revision=0, action="accepted", reviewer="Automated UI QA — not gold labels",
            note="Synthetic citation-capability check only; no human gold or extraction quality claim.", checked_scope={record.binding.scope_id:[1]}))
        decisions.append(review["decision_id"])
    frozen = domain.freeze(decisions, scope_ids=[record.binding.scope_id])
    spec = ComparisonSpec(question="Synthetic citation capability demonstration, not a research finding", snapshot_id=frozen["snapshot_id"],
        scope_ids=[record.binding.scope_id], columns=list(quotes), permitted_mapping_relations=[])
    proof = {"kind": "synthetic_engineering_fixture_not_gold", "snapshot_id": frozen["snapshot_id"],
             "comparison_id": query_snapshot(frozen["snapshot"], spec)["result_id"],
             "capabilities": [r["citations"][0]["capability"] for r in frozen["snapshot"]["rows"]], "model_calls": 0}
    atomic_json(store_dir / "snapshot.json", frozen)
    atomic_json(store_dir / "comparison-spec.json", spec.model_dump())
    atomic_json(store_dir / "fixture-proof.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=Path)
    parser.add_argument("--ui-store", type=Path)
    args = parser.parse_args()
    if args.examples:
        build_examples(args.examples)
    if args.ui_store:
        print(json.dumps(build_ui(args.ui_store), indent=2))


if __name__ == "__main__":
    main()
