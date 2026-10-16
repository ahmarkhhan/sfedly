"""Strict offline evaluation service operations shared by CLI and local HTTP."""

from pydantic import Field

from .contracts import StrictModel, TextSnapshot
from .evaluation_insights import (FeasibilityJudgment, PDFAddition, corpus_coverage, feasibility_matrix,
                                  metadata_baseline, novelty_report)
from .evaluation_protocol import Reviewer, ReviewSession, UpliftDesign, review_protocol, review_uplift
from .experiments import ExperimentInput, freeze_experiment, score_experiment
from .gold import GoldUnit, Prediction
from .relations import (RelationGold, RelationKind, RelationNode, RelationPrediction,
                        freeze_universe, merge_relation_packets, score_relations)
from .study import SplitLink, StudyPolicy, StudyUnit, freeze_cohort
from .evaluation_status import research_readiness


class CohortInput(StrictModel):
    units: list[StudyUnit]
    policy: StudyPolicy
    links: list[SplitLink] = Field(default_factory=list)
    frozen_at: str


class RelationUniverseInput(StrictModel):
    nodes: list[RelationNode]
    texts: list[TextSnapshot]
    kinds: list[RelationKind]
    frozen_at: str
    inventory_note: str
    cohort: dict | None = None


class RelationScoreInput(StrictModel):
    universe: dict
    labels: list[RelationGold]
    predictions: list[RelationPrediction]


class RelationMergeInput(StrictModel):
    universe: dict
    packets: list[dict]
    adjudications: dict = Field(default_factory=dict)


class ProtocolInput(StrictModel):
    cohort: dict
    reviewers: list[Reviewer]
    sessions: list[ReviewSession]
    claimed_relations: bool = False


class UpliftInput(StrictModel):
    cohort: dict
    reviewers: list[Reviewer]
    sessions: list[ReviewSession]
    gold: list[GoldUnit]
    design: UpliftDesign


class BaselineInput(StrictModel):
    snapshot: dict | list
    question: str
    source_reference: str
    queries: dict[str, str]
    recorded_at: str


class NoveltyInput(StrictModel):
    baseline: dict
    additions: list[PDFAddition]
    texts: list[TextSnapshot]
    cohort: dict | None = None


class MatrixInput(StrictModel):
    body_ids: list[str]
    concepts: list[str]
    judgments: list[FeasibilityJudgment]
    texts: list[TextSnapshot]
    gold: list[GoldUnit]
    predictions: list[Prediction]
    cohort: dict | None = None


class ExperimentFreezeInput(StrictModel):
    cohort: dict
    inputs: list[ExperimentInput]
    calibration: dict
    frozen_at: str
    engineering_only: bool = False


class ExperimentScoreInput(StrictModel):
    run: dict
    gold: list[GoldUnit]
    cohort: dict


class ReadinessInput(StrictModel):
    cohort: dict
    protocol: dict | None = None
    relation_scores: list[dict] = Field(default_factory=list)
    novelty: dict | None = None
    matrix: dict | None = None
    experiment: dict | None = None


class CoverageInput(StrictModel):
    cohort: dict
    structure_census: dict | None = None


OPERATIONS = {
    "cohort": (CohortInput, freeze_cohort),
    "relation-universe": (RelationUniverseInput, freeze_universe),
    "relation-score": (RelationScoreInput, score_relations),
    "relation-merge": (RelationMergeInput, merge_relation_packets),
    "review-protocol": (ProtocolInput, review_protocol),
    "review-uplift": (UpliftInput, review_uplift),
    "metadata-baseline": (BaselineInput, metadata_baseline),
    "novelty": (NoveltyInput, novelty_report),
    "feasibility": (MatrixInput, feasibility_matrix),
    "experiment-freeze": (ExperimentFreezeInput, freeze_experiment),
    "experiment-score": (ExperimentScoreInput, score_experiment),
    "readiness": (ReadinessInput, research_readiness),
    "coverage": (CoverageInput, corpus_coverage),
}


def evaluate(operation, payload):
    if operation not in OPERATIONS:
        raise ValueError("Unsupported offline evaluation operation")
    model, function = OPERATIONS[operation]
    request = model.model_validate(payload)
    # Preserve validated domain objects; model_dump would erase their types.
    try:
        return function(**{key: getattr(request, key) for key in model.model_fields})
    except (KeyError, TypeError, IndexError, StopIteration) as error:
        raise ValueError("Malformed frozen evaluation artifact") from error


def schemas():
    return {name: model.model_json_schema() for name, (model, _) in OPERATIONS.items()}
