"""Invented evaluation fixtures. These simulate records and are never human gold."""

import json

import httpx

from src.skony.client import Settings
from src.skony.contracts import FIELDS, EvidenceSegment, LayerPage, ScopeBinding, ScopeWindow, TextSnapshot, identity
from src.skony.experiments import ExperimentInput
from src.skony.gold import GoldLabel, GoldUnit
from src.skony.study import IntakeReview, StudyPolicy, StudyUnit, freeze_cohort
from v2_helpers import envelope, wire, propose
from test_gold_v2 import label

AT = "2026-10-15T08:00:00Z"


def study_unit(name="test", *, body="body1", affair=None, language="de", role="submission", split="test", verified=True):
    artifact, scope = "artifact-" + name, "scope-" + name
    review = IntakeReview(reviewer_id="simulated-intake-reviewer", kind="human", locked_at="2026-10-15T07:00:00Z",
        artifact_id=artifact, body_id=body, affair_id=affair or name, language=language, role=role,
        jurisdiction_level="municipal", checked_pages=[1], note="Invented engineering fixture, not a real human annotation") if verified else None
    return StudyUnit(unit_id=artifact + ":" + scope, source_id="source-" + name, artifact_id=artifact, scope_id=scope,
        body_id=body, body_key=body, level="municipal", affair_id=affair or name, language_hint=language,
        role_hint=role, source_status="ready", available_pages=[1], split=split, review=review)


def cohort_for(units=None):
    return freeze_cohort(units or [study_unit("dev", split="development"), study_unit()],
        StudyPolicy(mode="bounded", minimum_documents=1, maximum_documents=None, minimum_bodies=1,
                    minimum_levels=1, required_languages=["de"]), frozen_at=AT)


def source(name="test", content="Motion\nAnswer."):
    return TextSnapshot(artifact_id="artifact-" + name, origin="recorded", parser_name="invented-fixture",
        parser_version="1", configuration={"synthetic": True}, pages=[LayerPage(page=1, layer_id="native", text=content)])


def citation(text=None, quote="Motion"):
    text = text or source()
    start = text.pages[0].text.index(quote)
    return EvidenceSegment(artifact_id=text.artifact_id, text_snapshot_id=text.id, page=1, layer_id="native",
                           start=start, end=start + len(quote), quote=quote, match_method="exact")


def extraction_input(name="test"):
    text = source(name)
    scope = ScopeBinding(scope_id="scope-" + name, subject_id="affair-" + name, artifact_id=text.artifact_id,
        text_snapshot_id=text.id, association_version="fixture", role_version="fixture", role="combined",
        membership="reviewed", windows=[ScopeWindow(page=1, layer_id="native", start=0, end=len(text.pages[0].text))])
    run = envelope(text, [scope])
    from src.skony.pipeline_v2 import chunk_manifest
    return ExperimentInput(unit_id=text.artifact_id + ":" + scope.scope_id, text=text,
                           manifest=chunk_manifest(text), runs=[run])


def gold_for(unit, cohort):
    group = next(gid for gid, ids in cohort["split_groups"].items() if unit.unit_id in ids)
    fields = {field: GoldLabel.model_validate(label(assessment="absent_in_reviewed_scope", scope=unit.scope_id)) for field in FIELDS}
    fields["title"] = GoldLabel.model_validate(label(value="Motion", scope=unit.scope_id))
    return GoldUnit(artifact_id=unit.artifact_id, scope_id=unit.scope_id, split_group=group,
                    body_id=unit.body_id, language=unit.language_hint, fields=fields)


def settings():
    return Settings("synthetic-not-model", "https://model.invalid/v1", "test-secret-never-in-artifacts")


def transport(*, finish="stop", wrong_answer=False):
    def complete(request):
        data = json.loads(request.content)
        if data.get("response_format", {}).get("type") == "json_schema":
            sid = json.loads(data["messages"][1]["content"])["targets"][0]["scope_id"]
            result = propose(wire([sid]), field="title", segments=[(1, "Motion")], pid="t")
            if wrong_answer:
                propose(result, field="answer_text", segments=[(1, "Invented answer")], pid="a")
            tokens = 100
        else:
            result = {field: "Motion" if field == "title" else None for field in FIELDS}
            tokens = 40
        return httpx.Response(200, json={"model": "synthetic-not-model", "choices": [{"finish_reason": finish,
            "message": {"content": json.dumps(result)}}], "usage": {"prompt_tokens": 50, "completion_tokens": tokens,
                                                                      "total_tokens": 50 + tokens}})
    return httpx.MockTransport(complete)
