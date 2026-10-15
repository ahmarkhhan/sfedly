"""Small local v2 service adapter; business rules live outside HTTP handlers."""

import hashlib
import json
import re

from pydantic import Field

from .affairs import AffairStore
from .completeness import ChunkManifest, ChunkOutcome
from .contracts import (CandidateV2, FIELD_DICTIONARY, RunEnvelope, StrictModel,
                        TextSnapshot, QuoteSegment, EvidenceSegment, ScopeBinding, identity)
from .citations import citation
from .evidence_v2 import _locate
from .gold import GoldUnit, Prediction, score
from .pipeline_v2 import candidate_schema, verify_recording
from .review import ReviewError
from .migration import get_object, head
from .review_contracts import (AffairRecord, Claim, ComparisonSpec, MappingRule,
                               ReviewInput, ScopeRecord, SourceAssessment)


class ScopeUpdate(StrictModel):
    scope: ScopeRecord
    revision: int = Field(ge=0)
    reviewer: str
    note: str


class AffairUpdate(StrictModel):
    affair: AffairRecord
    revision: int = Field(ge=0)


class MappingUpdate(StrictModel):
    mapping: MappingRule
    revision: int = Field(ge=0)


class SourceInput(StrictModel):
    document_id: str
    metadata: dict


class RecordedInput(StrictModel):
    run: RunEnvelope
    manifest: ChunkManifest
    chunk_id: str
    content: str
    finish_reason: str | None


class SnapshotInput(StrictModel):
    decision_ids: list[str]
    scope_ids: list[str]
    exclusions: list[dict] = Field(default_factory=list)


class StatusInput(StrictModel):
    status: str
    reason: str
    successor_id: str | None = None


class ComparisonInput(StrictModel):
    spec: ComparisonSpec
    current: bool = False


class EvaluationInput(StrictModel):
    gold: list[GoldUnit]
    predictions: list[Prediction]
    frozen_unit_ids: list[str]


class CorrectionInput(StrictModel):
    scope_id: str
    predicate: str
    assessment: SourceAssessment = "present"
    segments: list[QuoteSegment] = Field(default_factory=list)
    image_segments: list[EvidenceSegment] = Field(default_factory=list)


class V2API:
    def __init__(self, store):
        self.domain = AffairStore(store)

    def sync_sources(self):
        with self.domain.store.db() as db:
            known = {(s["artifact_id"], s["metadata_digest"]) for r in db.execute("SELECT body_json FROM v2_objects WHERE kind='source'")
                     for s in [json.loads(r[0])]}
            rows = list(db.execute("SELECT d.id,d.sha256,d.source_json FROM documents d"))
            histories = list(db.execute("SELECT d.id,d.sha256,s.source_json FROM document_sources s JOIN documents d ON d.id=s.document_id"))
        for row in rows + histories:
            metadata = json.loads(row["source_json"])
            key = (row["sha256"], identity(metadata))
            if key not in known:
                self.domain.register_document(row["id"], metadata)
                known.add(key)

    def artifact(self, digest):
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ReviewError("Artifact not found", 404)
        with self.domain.store.db() as db:
            record = head(db, "artifact", digest)
            if not record:
                raise ReviewError("Artifact not found", 404)
            return get_object(db, record["object_id"], "artifact")

    def artifact_path(self, digest):
        self.artifact(digest)
        path = self.domain.store.directory / "artifacts" / (digest + ".pdf")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ReviewError("Pinned PDF is unavailable or failed its digest check", 409)
        return path

    def get(self, parts):
        if parts == ["schemas"]:
            return {"candidate": candidate_schema(), "run": RunEnvelope.model_json_schema(),
                    "review": ReviewInput.model_json_schema(), "gold": GoldUnit.model_json_schema(),
                    "field_dictionary": FIELD_DICTIONARY,
                    "scoring_unit": "artifact_id + target scope_id",
                    "structural_automation": "proposals supported; human relation review and accuracy untested"}
        if parts == ["scopes"]:
            self.sync_sources()
            return self.domain.scopes()
        if len(parts) == 2 and parts[0] == "artifacts":
            return self.artifact(parts[1])
        if parts == ["affairs"]:
            return self.domain.versions("affair")
        if parts == ["snapshots"]:
            return [{"id": s["id"], "scope_ids": s["value"]["scope_ids"], "reviewed_fields": len(s["value"]["rows"])}
                    for s in self.domain.versions("snapshot")]
        if parts == ["reviews"]:
            return self.domain.current_reviews()
        if len(parts) == 3 and parts[0] == "scopes" and parts[2] == "claims":
            claims = self.domain.claims(parts[1])
            return [{**c, "review_revision": self.domain.review_revision(c["id"]),
                     "citations": [citation(EvidenceSegment.model_validate(e),
                        TextSnapshot.model_validate(self.domain.get(e["text_snapshot_id"], "text")) if e["basis"] == "text" else None)
                        for e in c["evidence"]]} for c in claims]
        if len(parts) == 2 and parts[0] == "snapshots":
            return self.domain.snapshot(parts[1])
        if len(parts) == 2 and parts[0] == "eligibility":
            return self.domain.eligibility(parts[1])
        if len(parts) == 2 and parts[0] == "objects":
            return self.domain.get(parts[1])
        raise ReviewError("Versioned resource not found", 404)

    def post(self, parts, data):
        if parts == ["sources"]:
            request = SourceInput.model_validate(data)
            return self.domain.register_document(request.document_id, request.metadata)
        if parts == ["affairs"]:
            request = AffairUpdate.model_validate(data)
            return self.domain.put_affair(request.affair, revision=request.revision)
        if parts == ["scopes"]:
            request = ScopeUpdate.model_validate(data)
            return self.domain.put_scope(request.scope, revision=request.revision, reviewer=request.reviewer, note=request.note)
        if parts == ["mappings"]:
            request = MappingUpdate.model_validate(data)
            return self.domain.put_mapping(request.mapping, revision=request.revision)
        if parts == ["text-snapshots"]:
            return {"text_snapshot_id": self.domain.register_text(TextSnapshot.model_validate(data))}
        if parts == ["claims"]:
            return {"claim_id": self.domain.put_claim(Claim.model_validate(data))}
        if parts == ["corrections"]:
            request = CorrectionInput.model_validate(data)
            scope = next((s for s in self.domain.scopes() if s["id"] == request.scope_id), None)
            if scope is None:
                raise ReviewError("Scope not found", 404)
            binding = ScopeBinding.model_validate(scope["binding"])
            text = TextSnapshot.model_validate(self.domain.get(binding.text_snapshot_id, "text"))
            if request.segments and request.image_segments:
                raise ReviewError("Record text and visual transcriptions as separate claims", 422)
            evidence = list(request.image_segments)
            if any(e.basis != "image" for e in evidence):
                raise ReviewError("Visual transcriptions must have an image basis", 422)
            for segment in request.segments:
                located, reason = _locate(segment, text, binding)
                if located is None:
                    raise ReviewError("Passage could not be located uniquely in its selected scope: " + reason, 422)
                evidence.append(located)
            claim = Claim(scope_id=request.scope_id, subject_id=binding.subject_id, predicate=request.predicate,
                          source_assessment=request.assessment, value="\n\n".join(e.quote for e in evidence) if evidence else None,
                          evidence=evidence)
            return {"claim_id": self.domain.put_claim(claim)}
        if parts == ["reviews"]:
            return self.domain.review(ReviewInput.model_validate(data))
        if parts == ["snapshots"]:
            request = SnapshotInput.model_validate(data)
            return self.domain.freeze(request.decision_ids, scope_ids=request.scope_ids, exclusions=request.exclusions)
        if len(parts) == 3 and parts[0] == "snapshots" and parts[2] == "status":
            request = StatusInput.model_validate(data)
            self.domain.mark_snapshot(parts[1], **request.model_dump())
            return {"recorded": True}
        if parts == ["comparisons"]:
            request = ComparisonInput.model_validate(data)
            return self.domain.compare(request.spec, current=request.current)
        if parts == ["evaluations"]:
            request = EvaluationInput.model_validate(data)
            return score(request.gold, request.predictions, frozen_unit_ids=request.frozen_unit_ids)
        if parts == ["extractions"]:
            request = RecordedInput.model_validate(data)
            text = TextSnapshot.model_validate(self.domain.get(request.run.text_snapshot_id, "text"))
            scopes = {s["id"]: s for s in self.domain.scopes()}
            for binding in request.run.scopes:
                current = scopes.get(binding.scope_id, {}).get("binding")
                proposed = binding.model_dump()
                if (current is None or {k: v for k, v in current.items() if k != "windows"} !=
                        {k: v for k, v in proposed.items() if k != "windows"}
                        or any(not any(w["page"] == window.page and w["layer_id"] == window.layer_id
                                      and w["start"] <= window.start <= window.end <= w["end"]
                                      for w in current["windows"]) for window in binding.windows)):
                    raise ReviewError("Run references a stale or unregistered scope", 409)
            known_affairs = {a["id"] for a in self.domain.versions("affair")}
            for endpoint in request.run.allowed_endpoints:
                if not ((endpoint.kind == "affair" and endpoint.id in known_affairs) or
                        (endpoint.kind == "affair_document" and endpoint.id in scopes)):
                    raise ReviewError("External relation endpoint is unregistered or unsupported", 422)
            record = verify_recording(text, request.run, request.manifest,
                chunk_id=request.chunk_id, content=request.content, finish_reason=request.finish_reason)
            oid = self.domain.save_extraction(record)
            claim_ids = []
            if record["result"]:
                for target in record["result"]["targets"]:
                    for predicate, slot in target["fields"].items():
                        for item in slot["items"]:
                            if item["value"] is not None:
                                claim = Claim.model_validate({"scope_id": target["scope_id"],
                                    "subject_id": scopes[target["scope_id"]]["binding"]["subject_id"],
                                    "predicate": predicate, "value": item["value"], "evidence": item["evidence"],
                                    "origin_id": oid, "chunk_manifest": request.manifest.model_dump(),
                                    "chunk_outcomes": [record["outcome"]]})
                                claim_ids.append(self.domain.put_claim(claim))
            # Raw output is recorded even on schema/generation failure. Repeated
            # imports are idempotent and never make a model call.
            return {"extraction_id": oid, "claim_ids": claim_ids, **record}
        raise ReviewError("Versioned operation not found", 404)
