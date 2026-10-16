"""B2: fixed typed candidate universes, independent relation review and scoring."""

from collections import Counter
from itertools import product
from typing import Literal

from pydantic import Field, model_validator

from .contracts import EvidenceSegment, StrictModel, TextSnapshot, identity
from .evaluation_common import checked, link_metrics, ratio, seal, timestamp, unique, verify_citations
from .gold import Adjudication
from .study import load_cohort

RelationKind = Literal["affair_document", "question_response", "response_decision"]
RelationDisposition = Literal["positive", "negative", "unknown"]
UNIVERSE_SCHEMA = "skony.relation-universe.v1"
ENDPOINTS = {"affair_document": ("affair", "affair_document"),
             "question_response": ("question", "response"), "response_decision": ("response", "decision")}


class RelationNode(StrictModel):
    id: str = Field(min_length=1)
    kind: Literal["affair", "affair_document", "question", "response", "decision"]
    body_id: str = Field(min_length=1)
    affair_key: str = Field(min_length=1)
    unit_id: str | None = None
    evidence: list[EvidenceSegment] = Field(default_factory=list)

    @model_validator(mode="after")
    def supported(self):
        if self.kind != "affair" and (not self.unit_id or not self.evidence):
            raise ValueError("Document, item and decision inventories need a unit and pinned source evidence")
        return self


class RelationPair(StrictModel):
    kind: RelationKind
    source_id: str
    target_id: str

    @property
    def id(self):
        return identity(self.model_dump())


def freeze_universe(nodes: list[RelationNode], texts: list[TextSnapshot], *, kinds: list[RelationKind], frozen_at: str,
                    inventory_note: str, maximum_pairs=100000, cohort: dict | None = None):
    timestamp(frozen_at)
    if not inventory_note.strip() or not kinds:
        raise ValueError("A frozen universe needs an inventory/eligibility description and claimed kinds")
    unique([(n.kind, n.id) for n in nodes], "typed relation endpoint")
    unique(kinds, "relation kind")
    unique([t.id for t in texts], "source text")
    if cohort:
        units = [u for u in load_cohort(cohort) if u.split == "test" and u.verified]
        by_unit = {u.unit_id: u for u in units}
        affairs = {(u.body_id, u.affair_key) for u in units}
        if timestamp(frozen_at) < timestamp(cohort["frozen_at"]):
            raise ValueError("Freeze the cohort before the relation universe")
        for node in nodes:
            if (node.body_id, node.affair_key) not in affairs:
                raise ValueError("Relation inventory is outside the verified test affairs")
            if node.kind != "affair":
                unit = by_unit.get(node.unit_id)
                if unit is None or unit.body_id != node.body_id or unit.affair_key != node.affair_key:
                    raise ValueError("Relation endpoint has an unverified/different source unit")
                if any(e.artifact_id != unit.artifact_id for e in node.evidence):
                    raise ValueError("Relation endpoint evidence belongs to another source unit")
        if "affair_document" in kinds and (
            {(n.body_id, n.affair_key) for n in nodes if n.kind == "affair"} != affairs or
            {n.unit_id for n in nodes if n.kind == "affair_document"} != set(by_unit)):
            raise ValueError("Membership universe must include every verified held-out affair and document scope")
    for node in nodes:
        verify_citations(node.evidence, texts)
    candidates = []
    for kind in sorted(kinds):
        if kind not in ENDPOINTS:
            raise ValueError("Unsupported relation capability")
        left, right = ENDPOINTS[kind]
        for source, target in product([n for n in nodes if n.kind == left], [n for n in nodes if n.kind == right]):
            # Membership includes cross-body/same-number decoys. Q/A and
            # response/decision are within the independently inventoried affair.
            if kind != "affair_document" and (source.affair_key != target.affair_key or source.body_id != target.body_id):
                continue
            pair = RelationPair(kind=kind, source_id=source.id, target_id=target.id)
            candidates.append({"candidate_id": pair.id, **pair.model_dump()})
            if len(candidates) > maximum_pairs:
                raise ValueError("Candidate universe exceeds the declared capacity")
    if not candidates or any(not any(p["kind"] == kind for p in candidates) for kind in kinds):
        raise ValueError("Every claimed relation needs a nonempty fixed candidate inventory")
    return seal({"schema_version": UNIVERSE_SCHEMA, "frozen_at": frozen_at, "inventory_note": inventory_note,
        "eligibility_policy": "membership:all-inventory-cross-product;QA/decision:same-namespaced-affair-and-body",
        "kinds": sorted(kinds), "nodes": [n.model_dump() for n in sorted(nodes, key=lambda n: (n.kind, n.id))],
        "cohort": cohort, "engineering_only": cohort is None or not cohort["experiment_committed"],
        "texts": [t.model_dump() for t in sorted(texts, key=lambda t: t.id)],
        "candidates": sorted(candidates, key=lambda p: p["candidate_id"])})


def load_universe(value):
    body = checked(value, UNIVERSE_SCHEMA)
    rebuilt = freeze_universe([RelationNode.model_validate(n) for n in body["nodes"]],
        [TextSnapshot.model_validate(t) for t in body["texts"]], kinds=body["kinds"],
        frozen_at=body["frozen_at"], inventory_note=body["inventory_note"], cohort=body["cohort"])
    if rebuilt != value:
        raise ValueError("Universe candidate list does not match its frozen eligibility rules")
    return body


class RelationAnnotation(StrictModel):
    annotator_id: str = Field(min_length=1)
    kind: Literal["human", "automated", "synthetic"]
    mode: Literal["blind", "assisted"]
    independent: bool
    language_competence: str = Field(min_length=1)
    procedural_competence: str = Field(min_length=1)
    locked_at: str
    label: RelationDisposition
    checked_node_ids: list[str] = Field(min_length=2)
    evidence: list[EvidenceSegment]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid(self):
        timestamp(self.locked_at)
        if self.label != "unknown" and not self.evidence:
            raise ValueError("Scored positive/negative relations need source-backed review evidence")
        return self


class RelationGold(StrictModel):
    universe_digest: str
    candidate_id: str
    label: RelationDisposition
    status: Literal["single_annotator_final", "independently_agreed", "adjudicated", "unresolved"]
    annotations: list[RelationAnnotation]
    adjudication: Adjudication | None = None

    @model_validator(mode="after")
    def quality(self):
        ids = [a.annotator_id for a in self.annotations]
        unique(ids, "relation reviewer")
        if self.status != "unresolved" and not self.annotations:
            raise ValueError("Final relation labels need original annotations")
        if self.status == "single_annotator_final" and len(ids) != 1:
            raise ValueError("Single relation annotation must remain explicitly single")
        if self.status in {"independently_agreed", "adjudicated"} and (len(ids) < 2 or any(not a.independent for a in self.annotations)):
            raise ValueError("Scored relations require independent review")
        if self.status in {"single_annotator_final", "independently_agreed"} and any(a.label != self.label for a in self.annotations):
            raise ValueError("Final agreement differs from its original annotations")
        if self.status == "adjudicated":
            if not self.adjudication or self.adjudication.adjudicator_id in ids:
                raise ValueError("Relation adjudication needs a separate recorded adjudicator")
            timestamp(self.adjudication.locked_at)
        elif self.adjudication:
            raise ValueError("Only adjudicated labels may carry adjudication")
        return self


class RelationPrediction(StrictModel):
    candidate_id: str
    label: RelationDisposition


def relation_packet(universe, annotator_id: str):
    body = load_universe(universe)
    return {"schema_version": "skony.relation-review-packet.v1", "universe_digest": universe["digest"],
            "annotator_id": annotator_id, "mode": "blind", "model_proposals_included": False,
            "nodes": body["nodes"], "texts": body["texts"],
            "tasks": [{**p, "annotation": None} for p in body["candidates"]]}


def score_relations(universe, labels: list[RelationGold], predictions: list[RelationPrediction]):
    body = load_universe(universe)
    candidates = {p["candidate_id"]: p for p in body["candidates"]}
    unique([g.candidate_id for g in labels], "relation gold candidate")
    unique([p.candidate_id for p in predictions], "predicted candidate (one-to-one link scoring)")
    if any(g.candidate_id not in candidates or g.universe_digest != universe["digest"] for g in labels):
        raise ValueError("Relation gold belongs to a different candidate universe")
    if any(p.candidate_id not in candidates for p in predictions):
        raise ValueError("Prediction is outside the frozen relation universe")
    texts = [TextSnapshot.model_validate(t) for t in body["texts"]]
    for gold in labels:
        pair = candidates[gold.candidate_id]
        for annotation in gold.annotations:
            if not {pair["source_id"], pair["target_id"]}.issubset(annotation.checked_node_ids):
                raise ValueError("Relation review did not check both endpoints")
            if timestamp(annotation.locked_at) < timestamp(body["frozen_at"]):
                raise ValueError("Relation annotations predate the frozen candidate inventory")
            verify_citations(annotation.evidence, texts)
        if gold.adjudication and timestamp(gold.adjudication.locked_at) < max(timestamp(a.locked_at) for a in gold.annotations):
            raise ValueError("Relation adjudication predates its original annotations")
    by_gold, by_pred = {g.candidate_id: g for g in labels}, {p.candidate_id: p.label for p in predictions}
    per_kind = {}
    for kind in body["kinds"]:
        counts = Counter()
        for cid, pair in candidates.items():
            if pair["kind"] != kind:
                continue
            counts["candidates"] += 1
            gold = by_gold.get(cid)
            prediction = by_pred.get(cid, "unknown")
            counts["predicted_" + prediction] += 1
            if not gold:
                counts["unlabelled"] += 1
                continue
            counts["gold_" + gold.label] += 1
            eligible = (gold.status in {"independently_agreed", "adjudicated"} and gold.label != "unknown"
                        and all(a.kind == "human" and a.mode == "blind" for a in gold.annotations))
            if not eligible:
                counts["excluded"] += 1
                continue
            counts["scorable"] += 1
            if gold.label == "positive":
                counts["tp" if prediction == "positive" else "fn"] += 1
            else:
                counts["known_negative"] += 1
                if prediction == "positive":
                    counts["fp"] += 1
                else:
                    counts["correct_negative"] += prediction == "negative"
        per_kind[kind] = {**dict(counts), **link_metrics(counts["tp"], counts["fp"], counts["fn"]),
                          "scorable_fraction": ratio(counts["scorable"], counts["candidates"])}
    all_labelled = len(labels) == len(candidates)
    independently_checked = all(g.status in {"independently_agreed", "adjudicated"}
        and all(a.kind == "human" and a.mode == "blind" for a in g.annotations) for g in labels)
    gate = all_labelled and independently_checked and all(v.get("scorable", 0) for v in per_kind.values())
    return seal({"schema_version": "skony.relation-score.v1", "universe_digest": universe["digest"],
        "cohort_digest": body["cohort"]["digest"] if body["cohort"] else None,
        "engineering_only": body["engineering_only"],
        "gold_digest": identity([g.model_dump() for g in sorted(labels, key=lambda g: g.candidate_id)]),
        "prediction_digest": identity([p.model_dump() for p in sorted(predictions, key=lambda p: p.candidate_id)]),
        "gate_passed": bool(gate), "research_ready": bool(gate and not body["engineering_only"]),
        "unknowns_are_excluded_not_negative": True, "per_kind": per_kind,
        "candidates": len(candidates), "unlabelled": len(candidates) - len(labels)})


def merge_relation_packets(universe, packets: list[dict], adjudications: dict | None = None):
    """Keep original independent annotations; disagreements remain unresolved."""
    body = load_universe(universe)
    adjudications = adjudications or {}
    candidates = {p["candidate_id"]: p for p in body["candidates"]}
    unique([p["annotator_id"] for p in packets], "packet reviewer")
    collected = {cid: [] for cid in candidates}
    if set(adjudications) - set(candidates):
        raise ValueError("Adjudication is outside the frozen universe")
    for packet in packets:
        if (packet.get("universe_digest") != universe["digest"] or packet.get("mode") != "blind"
                or packet.get("model_proposals_included") is not False):
            raise ValueError("Relation packet is not the matching independent blind task")
        tasks = packet["tasks"]
        if Counter(t["candidate_id"] for t in tasks) != Counter(candidates.keys()):
            raise ValueError("Review packet silently dropped or duplicated fixed candidates")
        for task in tasks:
            pair = candidates[task["candidate_id"]]
            if any(task[k] != pair[k] for k in ("kind", "source_id", "target_id")):
                raise ValueError("Review packet changed candidate endpoints")
            if task["annotation"] is not None:
                annotation = RelationAnnotation.model_validate(task["annotation"])
                if annotation.annotator_id != packet["annotator_id"] or annotation.mode != "blind":
                    raise ValueError("Annotation identity/mode differs from its packet")
                collected[pair["candidate_id"]].append(annotation)
    labels = []
    for cid, annotations in collected.items():
        status, disposition, adjudication = "unresolved", "unknown", None
        if cid in adjudications:
            disposition = adjudications[cid]["label"]
            adjudication = Adjudication.model_validate(adjudications[cid]["adjudication"])
            status = "adjudicated"
        elif annotations and len({a.label for a in annotations}) == 1:
            disposition = annotations[0].label
            status = "independently_agreed" if len(annotations) >= 2 and all(a.independent for a in annotations) else "single_annotator_final"
            if len(annotations) >= 2 and not all(a.independent for a in annotations):
                status = "unresolved"
        labels.append(RelationGold(universe_digest=universe["digest"], candidate_id=cid, label=disposition,
                                  status=status, annotations=annotations, adjudication=adjudication))
    # This validates checked endpoints, original citations and review chronology.
    score_relations(universe, labels, [])
    return {"schema_version": "skony.relation-gold.v1", "universe_digest": universe["digest"],
            "labels": [g.model_dump() for g in sorted(labels, key=lambda g: g.candidate_id)]}
