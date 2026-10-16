"""Evidence-gate status. Passing software tests never substitutes for human research."""

from .evaluation_common import checked, seal
from .study import load_cohort


def research_readiness(cohort, *, protocol=None, relation_scores=None, novelty=None, matrix=None, experiment=None):
    load_cohort(cohort)
    gates = {"B1_acquisition_and_split": bool(cohort["experiment_committed"]),
             "B2_independent_relation_gold": False, "B3_pdf_information_gain": False,
             "B4_non_circular_review": False, "B5_independent_review_allocation": False,
             "B6_source_backed_schema_findings": False, "B7_frozen_experiment_results": False}
    if protocol:
        p = checked(protocol, "skony.review-protocol.v1")
        if p["cohort_digest"] != cohort["digest"]:
            raise ValueError("Review protocol belongs to another cohort")
        gates["B4_non_circular_review"] = p["accuracy_uplift_claim"] is False
        gates["B5_independent_review_allocation"] = p["passed"]
    if relation_scores:
        kinds = set()
        for result in relation_scores:
            r = checked(result, "skony.relation-score.v1")
            if r["cohort_digest"] != cohort["digest"]:
                raise ValueError("Relation results belong to another cohort")
            if r["research_ready"]:
                kinds.update(r["per_kind"])
        gates["B2_independent_relation_gold"] = kinds.issuperset({"affair_document", "question_response", "response_decision"})
    if novelty:
        n = checked(novelty, "skony.novelty-report.v1")
        if n["cohort_digest"] != cohort["digest"]:
            raise ValueError("Novelty evidence belongs to another cohort")
        gates["B3_pdf_information_gain"] = n["passed"]
    if matrix:
        m = checked(matrix, "skony.feasibility-matrix.v1")
        if m["cohort_digest"] != cohort["digest"]:
            raise ValueError("Schema evidence belongs to another cohort")
        cells = m["cells"]
        gates["B6_source_backed_schema_findings"] = any(c["judgment"] and c["judgment"]["reviewer_kind"] == "human"
            and c["expressivity"] != "untested" for c in cells)
    if experiment:
        e = checked(experiment, "skony.experiment-score.v1")
        if e["cohort_digest"] != cohort["digest"]:
            raise ValueError("Experiment scores belong to another cohort")
        gates["B7_frozen_experiment_results"] = (not e["engineering_only"] and all(
            e["results"][v]["primary"]["micro"]["scorable"] > 0 for v in ("B0", "B1", "B2")))
    return seal({"schema_version": "skony.research-readiness.v1", "cohort_digest": cohort["digest"],
        "gates": gates, "research_evidence_ready": all(gates.values()),
        "open_gates": [name for name, passed in gates.items() if not passed],
        "scope": "Recorded evidence checks, not certification of human judgment or a judge score"})
