"""B4/B5: competent independent annotation and non-circular review studies."""

from collections import Counter, defaultdict
from math import ceil
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StrictModel, identity
from .evaluation_common import ratio, seal, timestamp, unique
from .gold import GoldUnit, Prediction, score
from .study import load_cohort


class Calibration(StrictModel):
    development_unit_ids: list[str] = Field(min_length=1)
    guide_digest: str = Field(min_length=1)
    completed_at: str
    resolution_note: str = Field(min_length=1)


class Reviewer(StrictModel):
    id: str = Field(min_length=1)
    kind: Literal["human", "automated", "synthetic"]
    languages: list[str] = Field(min_length=1)
    body_ids: list[str] = Field(min_length=1)
    procedural_competence: str = Field(min_length=1)
    calibration: list[Calibration]


class ReviewSession(StrictModel):
    id: str = Field(min_length=1)
    reviewer_id: str
    mode: Literal["blind", "assisted"]
    unit_ids: list[str] = Field(min_length=1)
    capabilities: list[Literal["fields", "roles", "relations"]] = Field(min_length=1)
    independent: bool
    exposure_disclosed: bool
    exposed_gold_unit_ids: list[str]
    saw_model_output: bool
    started_at: str
    finished_at: str
    active_seconds: float = Field(ge=0, allow_inf_nan=False)
    actions: int = Field(ge=0)
    corrections: int = Field(ge=0)
    reversals: int = Field(ge=0)
    unresolved_fields: int = Field(ge=0)
    predictions: list[Prediction] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid(self):
        elapsed = (timestamp(self.finished_at) - timestamp(self.started_at)).total_seconds()
        if elapsed < self.active_seconds or self.corrections + self.reversals > self.actions:
            raise ValueError("Review time or action accounting is inconsistent")
        unique(self.unit_ids, "session unit")
        unique(self.capabilities, "session capability")
        unique([p.unit_id for p in self.predictions], "session prediction")
        if any(p.unit_id not in self.unit_ids for p in self.predictions):
            raise ValueError("Review outputs do not belong to this task")
        if self.mode == "blind" and (self.saw_model_output or set(self.unit_ids) & set(self.exposed_gold_unit_ids)):
            raise ValueError("Exposed sessions cannot be labelled blind")
        return self


def review_protocol(cohort, reviewers: list[Reviewer], sessions: list[ReviewSession], *, claimed_relations=False):
    units = load_cohort(cohort)
    unique([r.id for r in reviewers], "reviewer")
    unique([s.id for s in sessions], "review session")
    by_id, people = {u.unit_id: u for u in units}, {r.id: r for r in reviewers}
    required_capabilities = {"fields", "roles"} | ({"relations"} if claimed_relations else set())
    eligible_sessions = defaultdict(set)
    issues = []
    for reviewer in reviewers:
        for calibration in reviewer.calibration:
            timestamp(calibration.completed_at)
            if any(uid not in by_id or by_id[uid].split != "development" for uid in calibration.development_unit_ids):
                raise ValueError("Calibration must use development examples, never held-out test units")
    for session in sessions:
        if session.reviewer_id not in people or set(session.unit_ids) - set(by_id):
            raise ValueError("Review session has an unknown reviewer or unit")
        if timestamp(session.started_at) < timestamp(cohort["frozen_at"]):
            raise ValueError("Held-out review sessions must follow the cohort freeze")
        person = people[session.reviewer_id]
        calibrated_languages = set()
        for calibration in person.calibration:
            if timestamp(calibration.completed_at) < timestamp(session.started_at):
                calibrated_languages.update(by_id[uid].review.language for uid in calibration.development_unit_ids
                                            if by_id[uid].verified)
        for uid in session.unit_ids:
            unit = by_id[uid]
            language = unit.review.language if unit.verified else unit.language_hint
            competent = (person.kind == "human" and unit.verified and language in person.languages
                         and unit.body_id in person.body_ids and language in calibrated_languages)
            independent = (session.mode == "blind" and session.independent and session.exposure_disclosed
                           and required_capabilities.issubset(session.capabilities))
            prior_exposure = any(other.id != session.id and other.reviewer_id == session.reviewer_id
                and timestamp(other.started_at) < timestamp(session.started_at)
                and (uid in other.exposed_gold_unit_ids or
                     (uid in other.unit_ids and (other.mode == "assisted" or other.saw_model_output))) for other in sessions)
            independent = independent and not prior_exposure
            if competent and independent:
                eligible_sessions[uid].add(person.id)
            elif unit.split == "test" and session.mode == "blind":
                issues.append("ineligible_review:" + session.id + ":" + uid)
    test = [u for u in units if u.split == "test"]
    affairs = defaultdict(list)
    for u in test:
        affairs[u.affair_key or "unresolved:" + u.unit_id].append(u)
    independent_affairs, single = [], []
    for key, group in sorted(affairs.items()):
        reviewers_for_every_unit = set.intersection(*(eligible_sessions[u.unit_id] for u in group))
        if len(reviewers_for_every_unit) >= 2:
            independent_affairs.append(key)
        else:
            single.append({"affair_key": key, "body_ids": sorted({u.body_id for u in group}),
                           "languages": sorted({u.review.language if u.verified else u.language_hint for u in group}),
                           "competent_blind_reviewers_on_every_unit": sorted(reviewers_for_every_unit)})
    independent_units = [u for u in test if (u.affair_key or "unresolved:" + u.unit_id) in independent_affairs]
    tested_bodies = {u.body_id for u in test}
    required = max(ceil(len(affairs) * .25), len(tested_bodies))
    reasons = []
    if not test:
        reasons.append("no_frozen_test_affairs")
    if not cohort["experiment_committed"]:
        reasons.append("acquisition_or_split_gate_open")
    if len(independent_affairs) < required:
        reasons.append(f"insufficient_independent_affairs:{len(independent_affairs)}/{required}")
    for body in sorted(tested_bodies - {u.body_id for u in independent_units}):
        reasons.append("body_without_independent_review:" + body)
    languages = {u.review.language for u in independent_units if u.verified}
    for language in cohort["policy"]["required_languages"]:
        if language not in languages:
            reasons.append("language_without_independent_review:" + language)
    if any(u.hard_case for u in test) and not any(u.hard_case for u in independent_units):
        reasons.append("no_independently_reviewed_hard_case")
    required_roles = {u.review.role for u in test if u.verified}
    reviewed_roles = {u.review.role for u in independent_units if u.verified}
    for role in sorted(required_roles - reviewed_roles):
        reasons.append("role_without_independent_review:" + role)
    if any(not eligible_sessions[u.unit_id] for u in test):
        reasons.append("test_units_without_competent_blind_primary_review")
    return seal({"schema_version": "skony.review-protocol.v1", "cohort_digest": cohort["digest"],
        "passed": not reasons and not issues, "reasons": reasons + issues,
        "required_independent_affairs": required, "independently_reviewed_affairs": independent_affairs,
        "singly_or_unreviewed_strata": single, "test_affairs": len(affairs),
        "reviewers_digest": identity([r.model_dump() for r in reviewers]),
        "sessions_digest": identity([s.model_dump() for s in sessions]),
        "workload": {mode: {"sessions": sum(s.mode == mode for s in sessions),
            **{field: sum(getattr(s, field) for s in sessions if s.mode == mode)
               for field in ("active_seconds", "actions", "corrections", "reversals", "unresolved_fields")}}
            for mode in ("blind", "assisted")}, "accuracy_uplift_claim": False})


class UpliftDesign(StrictModel):
    design: Literal["matched_tasks_independent_reviewers"]
    predeclared_at: str
    frozen_gold_at: str
    frozen_gold_digest: str
    control_session_ids: list[str] = Field(min_length=1)
    assisted_session_ids: list[str] = Field(min_length=1)
    memory_effects_policy: Literal["disjoint_reviewers_no_prior_task_exposure"]


def review_uplift(cohort, reviewers: list[Reviewer], sessions: list[ReviewSession], gold: list[GoldUnit], design: UpliftDesign):
    """Optional independent field-agreement study; default workflow reports no uplift."""
    units = load_cohort(cohort)
    ids = [u.unit_id for u in units if u.split == "test"]
    report = review_protocol(cohort, reviewers, sessions)
    if not report["passed"]:
        raise ValueError("Human review protocol has not passed")
    expected_gold_digest = identity([g.model_dump() for g in sorted(gold, key=lambda g: g.unit_id)])
    if design.frozen_gold_digest != expected_gold_digest or {g.unit_id for g in gold} != set(ids):
        raise ValueError("Uplift needs the exact frozen blind gold for every matched test task")
    by_session, people = {s.id: s for s in sessions}, {r.id: r for r in reviewers}
    unique(design.control_session_ids + design.assisted_session_ids, "uplift session")
    if any(sid not in by_session for sid in design.control_session_ids + design.assisted_session_ids):
        raise ValueError("Unknown uplift session")
    control = [by_session[sid] for sid in design.control_session_ids]
    assisted = [by_session[sid] for sid in design.assisted_session_ids]
    gold_reviewers = {a.annotator_id for g in gold for f in g.fields.values() for a in f.annotations}
    gold_reviewers |= {f.adjudication.adjudicator_id for g in gold for f in g.fields.values() if f.adjudication}
    control_people, assisted_people = {s.reviewer_id for s in control}, {s.reviewer_id for s in assisted}
    if control_people & assisted_people or (control_people | assisted_people) & gold_reviewers:
        raise ValueError("Uplift participants overlap gold authors/adjudicators or the other condition")
    predictions = {}
    for condition, group, mode in [("control", control, "blind"), ("assisted", assisted, "assisted")]:
        predictions[condition] = []
        for session in group:
            if (session.mode != mode or people[session.reviewer_id].kind != "human" or not session.exposure_disclosed
                    or set(session.exposed_gold_unit_ids) & set(ids)
                    or timestamp(session.started_at) <= max(timestamp(design.predeclared_at), timestamp(design.frozen_gold_at))):
                raise ValueError("Uplift session violates its frozen independent protocol")
            # A participant who already saw a task in any earlier session has a
            # memory advantage, including a participant in unrelated gold work.
            if any(other.id != session.id and other.reviewer_id == session.reviewer_id
                   and timestamp(other.started_at) < timestamp(session.started_at)
                   and set(other.unit_ids) & set(session.unit_ids) for other in sessions):
                raise ValueError("Prior task exposure prevents an independent uplift estimate")
            predictions[condition].extend(session.predictions)
        if Counter(p.unit_id for p in predictions[condition]) != Counter(ids):
            raise ValueError("Both conditions require exactly one recorded output for every matched task")
    results = {name: score(gold, pred, frozen_unit_ids=ids) for name, pred in predictions.items()}
    if any(r["primary"]["micro"]["scorable"] == 0 for r in results.values()):
        raise ValueError("Uplift requires scorable independent blind human gold")
    a, b = [results[name]["primary"]["micro"]["f1"] for name in ("assisted", "control")]
    return seal({"schema_version": "skony.review-uplift.v1", "design": design.model_dump(),
        "cohort_digest": cohort["digest"], "results": results, "field_agreement_f1_difference": a - b if a is not None and b is not None else None,
        "semantic_accuracy_claim": False, "time_saving_claim": False,
        "workload": report["workload"]})
