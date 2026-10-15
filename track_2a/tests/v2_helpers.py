"""Explicitly synthetic engineering fixtures, never human evaluation labels."""

import hashlib

from src.skony.affairs import AffairStore
from src.skony.contracts import (FIELDS, CandidateV2, LayerPage, RunEnvelope,
                                ScopeBinding, ScopeWindow, TextSnapshot, identity)
from src.skony.pipeline_v2 import PROMPT_ID, candidate_schema, chunk_manifest
from src.skony.review import ReviewStore
from src.skony.review_contracts import AffairRecord, Claim, ReviewInput, ScopeRecord
from src.skony.schema import Document, Page


def text_fixture(pages=None):
    pages = pages or ["😀Motion\nAlice Example; Bob Exemple\nQuestion?", "Réponse: première clause.", "Suite: sous condition de financement."]
    return TextSnapshot(artifact_id="synthetic-artifact", origin="recorded", parser_name="fixture",
                        parser_version="1", configuration={"synthetic": True},
                        pages=[LayerPage(page=i + 1, layer_id="native", text=s) for i, s in enumerate(pages)])


def envelope(text, scopes=None):
    manifest = chunk_manifest(text)
    scopes = scopes or [ScopeBinding(scope_id="s1", subject_id="affair1", artifact_id=text.artifact_id,
        text_snapshot_id=text.id, association_version="a1", role_version="r1", role="combined", membership="reviewed",
        windows=[ScopeWindow(page=p.page, layer_id=p.layer_id, start=0, end=len(p.text)) for p in text.pages])]
    return RunEnvelope(artifact_id=text.artifact_id, text_snapshot_id=text.id, model_identity="synthetic-not-model",
                       prompt_identity=PROMPT_ID, schema_identity=identity(candidate_schema()), chunk_manifest_id=manifest.id,
                       scopes=scopes)


def wire(scope_ids=("s1",)):
    return {"schema_version": "skony.candidate.v0.2", "targets": [
        {"scope_id": sid, "fields": {name: {"outcome": "abstained", "items": [], "abstention_reason": "fixture_no_proposal"}
                                    for name in FIELDS},
         "actors": None, "question_items": None, "response_items": None, "events": None, "relations": None} for sid in scope_ids]}


def propose(data, field="answer_text", segments=None, *, target=0, pid="answer1"):
    segments = segments or [(2, "Réponse: première clause."), (3, "Suite: sous condition de financement.")]
    data["targets"][target]["fields"][field] = {"outcome": "proposed", "abstention_reason": None,
        "items": [{"proposal_id": pid, "segments": [{"page": page, "layer_id": "native", "quote": quote, "context_anchor": None}
                                                     for page, quote in segments]}]}
    return data


def review_fixture(directory):
    pdf = directory / "fixture.pdf"
    data = b"%PDF-synthetic-engineering-fixture; not a parliamentary source"
    pdf.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    document = Document(document_id=sha, filename=pdf.name, sha256=sha,
                        pages=[Page(number=1, text="😀Motion\nQuestion?\nAnswer complete.\nAlternative answer.")])
    legacy = ReviewStore(directory / "store")
    document_id = legacy.add(document, pdf, {"synthetic": True, "source_url": "https://fixture.invalid/a"})
    store = AffairStore(legacy)
    scope_dict = store.scopes()[0]
    scope = ScopeRecord.model_validate({k: v for k, v in scope_dict.items() if k in {"binding", "source_ids", "mapping_ids"}})
    store.put_affair(AffairRecord(internal_id="affair1", provider_namespace="fixture", body_id="body1", body_key="B1",
        official_affair_id="1", jurisdiction_level="municipal", source_ids=scope.source_ids))
    scope.binding.subject_id = "affair1"
    scope.binding.membership = "reviewed"
    scope.binding.role = "combined"
    store.put_scope(scope, revision=scope_dict["revision"], reviewer="Synthetic engineering fixture", note="Fixture association")
    return legacy, store, document_id, document, store.scopes()[0]


def claim_for(store, scope_dict, *, predicate="answer_text", quote="Answer complete.", assessment="present"):
    from src.skony.contracts import EvidenceSegment
    binding = scope_dict["binding"]
    text = TextSnapshot.model_validate(store.get(binding["text_snapshot_id"], "text"))
    page = text.pages[0]
    start = page.text.index(quote) if quote is not None else None
    evidence = [] if quote is None else [EvidenceSegment(artifact_id=text.artifact_id, text_snapshot_id=text.id,
        page=page.page, layer_id=page.layer_id, start=start, end=start + len(quote), quote=quote, match_method="exact")]
    claim = Claim(scope_id=binding["scope_id"], subject_id=binding["subject_id"], predicate=predicate,
                  value=quote, evidence=evidence, source_assessment=assessment)
    return store.put_claim(claim)


def accept(store, claim_id, scope_dict, **overrides):
    checked = {scope_dict["id"]: sorted({w["page"] for w in scope_dict["binding"]["windows"]})}
    payload = dict(claim_id=claim_id, revision=store.review_revision(claim_id, overrides.get("coverage", "document")),
                   action="accepted", reviewer="Synthetic engineering fixture", note="Fixture check, not human gold",
                   checked_scope=checked)
    payload.update(overrides)
    return store.review(ReviewInput(**payload))
