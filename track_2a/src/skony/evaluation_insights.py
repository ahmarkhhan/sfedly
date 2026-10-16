"""B3/B6: saved metadata baselines and separate schema/mapping/recovery findings."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import EvidenceSegment, FIELDS, StrictModel, TextSnapshot, identity
from .evaluation_common import checked, ratio, seal, timestamp, unique, verify_citations
from .gold import GoldUnit, Prediction, label_eligibility
from .study import load_cohort

BASELINE_SCHEMA = "skony.metadata-baseline.v1"
CORPUS_COVERAGE_SCHEMA = "skony.corpus-coverage.v1"


def corpus_coverage(cohort: dict, structure_census: dict | None = None):
    """Describe actual frozen cohort coverage while keeping hints separate from review."""
    units = load_cohort(cohort)

    def label(unit, dimension):
        review = unit.review
        if dimension == "body":
            return (unit.body_id, "human_checked" if review and review.kind == "human" else "metadata_or_unreviewed")
        if dimension == "language":
            if review and review.kind == "human":
                return (review.language, "human_checked")
            return ("unverified:" + (unit.language_hint or "unknown"), "metadata_hint")
        if dimension == "jurisdiction_level":
            if review and review.kind == "human":
                return (review.jurisdiction_level, "human_checked")
            return ("unverified:" + unit.level, "metadata_hint")
        if dimension == "document_role":
            if review and review.kind == "human":
                return (review.role, "human_checked")
            return ("unverified:" + (unit.role_hint or "unknown"), "metadata_hint")
        if dimension == "suspected_scan":
            return ("flagged" if unit.hard_case else "not_flagged", "intake_hint_only")
        if dimension == "split":
            return (unit.split, "frozen_cohort")
        if dimension == "source_status":
            return (unit.source_status, "source_intake")
        if dimension == "intake_review":
            if review is None:
                return ("unreviewed", "no_review")
            return (review.kind, "recorded_review")
        raise ValueError("Unsupported corpus coverage dimension")

    dimensions = ("body", "language", "jurisdiction_level", "document_role", "suspected_scan",
                  "split", "source_status", "intake_review")
    slices = {}
    for dimension in dimensions:
        groups = {}
        for unit in units:
            value, basis = label(unit, dimension)
            bucket = groups.setdefault((value, basis), {"units": [], "artifacts": set(), "failed_units": 0,
                                                        "verified_units": 0})
            bucket["units"].append(unit.unit_id)
            if unit.artifact_id:
                bucket["artifacts"].add(unit.artifact_id)
            bucket["failed_units"] += unit.source_status == "failed"
            bucket["verified_units"] += unit.verified
        slices[dimension] = [
            {"value": value, "basis": basis, "unit_count": len(bucket["units"]),
             "artifact_count": len(bucket["artifacts"]), "failed_unit_count": bucket["failed_units"],
             "verified_unit_count": bucket["verified_units"], "unit_ids": sorted(bucket["units"])}
            for (value, basis), bucket in sorted(groups.items())
        ]

    joint_groups = {}
    for unit in units:
        body, body_basis = label(unit, "body")
        language, language_basis = label(unit, "language")
        level, level_basis = label(unit, "jurisdiction_level")
        role, role_basis = label(unit, "document_role")
        key = (body, body_basis, language, language_basis, level, level_basis, role, role_basis)
        bucket = joint_groups.setdefault(key, {"units": [], "artifacts": set(), "verified_units": 0})
        bucket["units"].append(unit.unit_id)
        if unit.artifact_id:
            bucket["artifacts"].add(unit.artifact_id)
        bucket["verified_units"] += unit.verified

    counts = {
        "unit_count": len(units),
        "ready_unit_count": sum(u.source_status == "ready" for u in units),
        "failed_unit_count": sum(u.source_status == "failed" for u in units),
        "distinct_artifact_count": len({u.artifact_id for u in units if u.artifact_id}),
        "human_intake_review_count": sum(u.review is not None and u.review.kind == "human" for u in units),
        "verified_intake_count": sum(u.verified for u in units),
        "unreviewed_ready_count": sum(u.source_status == "ready" and u.review is None for u in units),
        "test_unit_count": sum(u.split == "test" for u in units),
        "development_unit_count": sum(u.split == "development" for u in units),
        "unassigned_unit_count": sum(u.split == "unassigned" for u in units),
        "suspected_scan_hint_count": sum(u.hard_case for u in units),
    }
    structural = None
    if structure_census is not None:
        if structure_census.get("schema_version") != "skony.structure-census.v0.1":
            raise ValueError("Unsupported structural census version")
        documents = structure_census.get("documents")
        if not isinstance(documents, list):
            raise ValueError("Structural census must include document rows")
        document_ids = [row.get("document_id") for row in documents if isinstance(row, dict)]
        if len(document_ids) != len(documents) or any(not isinstance(v, str) or not v for v in document_ids):
            raise ValueError("Structural census contains malformed document identities")
        unique(document_ids, "structural census document")
        cohort_artifacts = {u.artifact_id for u in units if u.artifact_id}
        if set(document_ids) - cohort_artifacts:
            raise ValueError("Structural census includes artifacts outside the frozen cohort")

        numeric = ("pages", "textless_pages", "annexes", "images", "table_hints")
        totals = {name: 0 for name in numeric}
        by_body = {}
        by_language = {}
        for row in documents:
            if any(not isinstance(row.get(name), int) or row[name] < 0 for name in numeric):
                raise ValueError("Structural census has invalid count values")
            for name in numeric:
                totals[name] += row[name]
            for dimension, source_key in ((by_body, "body"), (by_language, "language")):
                key = str(row.get(source_key) or "unknown")
                bucket = dimension.setdefault(key, {"documents": 0, **{name: 0 for name in numeric},
                                                    "documents_with_textless_pages": 0,
                                                    "documents_with_images": 0,
                                                    "documents_with_annexes": 0,
                                                    "documents_with_table_hints": 0})
                bucket["documents"] += 1
                for name in numeric:
                    bucket[name] += row[name]
                bucket["documents_with_textless_pages"] += row["textless_pages"] > 0
                bucket["documents_with_images"] += row["images"] > 0
                bucket["documents_with_annexes"] += row["annexes"] > 0
                bucket["documents_with_table_hints"] += row["table_hints"] > 0
        census_counts = structure_census.get("counts")
        if not isinstance(census_counts, dict) or census_counts.get("processed") != len(documents):
            raise ValueError("Structural census summary does not match its document rows")
        summary_checks = {
            "total_pages": totals["pages"], "total_annexes": totals["annexes"],
            "total_images": totals["images"],
            "docs_with_textless_pages": sum(row["textless_pages"] > 0 for row in documents),
            "docs_with_images": sum(row["images"] > 0 for row in documents),
            "docs_with_annexes": sum(row["annexes"] > 0 for row in documents),
            "docs_with_table_hints": sum(row["table_hints"] > 0 for row in documents),
        }
        if any(name in census_counts and census_counts[name] != value for name, value in summary_checks.items()):
            raise ValueError("Structural census summary counts do not match its document rows")
        structural = {
            "census_digest": identity(structure_census),
            "processed_document_count": len(documents),
            "joined_document_count": len(set(document_ids) & cohort_artifacts),
            "cohort_artifacts_without_structural_inventory": len(cohort_artifacts - set(document_ids)),
            "failed_source_count_without_artifact": sum(u.source_status == "failed" for u in units),
            "totals": totals,
            "documents_with_textless_pages": sum(row["textless_pages"] > 0 for row in documents),
            "documents_with_images": sum(row["images"] > 0 for row in documents),
            "documents_with_annexes": sum(row["annexes"] > 0 for row in documents),
            "documents_with_table_hints": sum(row["table_hints"] > 0 for row in documents),
            "by_body": dict(sorted(by_body.items())),
            "by_language": dict(sorted(by_language.items())),
            "method_note": structure_census.get("method_note", ""),
        }
    return seal({
        "schema_version": CORPUS_COVERAGE_SCHEMA,
        "cohort_digest": cohort["digest"],
        "counts": counts,
        "dimensions": slices,
        "joint_body_language_level_role": [
            {"body": k[0], "body_basis": k[1], "language": k[2], "language_basis": k[3],
             "jurisdiction_level": k[4], "level_basis": k[5], "document_role": k[6], "role_basis": k[7],
             "unit_count": len(v["units"]), "artifact_count": len(v["artifacts"]),
             "verified_unit_count": v["verified_units"], "unit_ids": sorted(v["units"])}
            for k, v in sorted(joint_groups.items())
        ],
        "structural_inventory": structural,
        "interpretation": {
            "language_level_role_hints_are_not_human_verified": True,
            "suspected_scan_values_are_unverified_intake_hints_not_visual_review": True,
            "verified_intake_does_not_establish_extraction_accuracy": True,
            "unit_counts_are_not_independent_affair_counts": True,
        },
    })


def corpus_coverage_markdown(report: dict):
    checked(report, CORPUS_COVERAGE_SCHEMA)
    counts = report["counts"]
    lines = ["# Frozen cohort coverage", "",
             f"Cohort digest: `{report['cohort_digest']}`", "",
             "These are source and intake counts, not model accuracy. Values marked `unverified:` come from metadata hints.", "",
             "## Overall", "",
             "| Measure | Count |", "|---|---:|"]
    labels = {
        "unit_count": "Source units", "ready_unit_count": "Sources ready", "failed_unit_count": "Failed sources retained",
        "distinct_artifact_count": "Distinct pinned PDFs", "human_intake_review_count": "Human intake reviews",
        "verified_intake_count": "Verified intake units", "unreviewed_ready_count": "Ready units without review",
        "test_unit_count": "Test units", "development_unit_count": "Development units",
        "unassigned_unit_count": "Units without a split", "suspected_scan_hint_count": "Suspected scan hints",
    }
    lines.extend(f"| {labels[key]} | {counts[key]} |" for key in labels)
    for dimension, title in (("body", "Bodies"), ("language", "Languages"),
                             ("jurisdiction_level", "Government levels"), ("document_role", "Document roles"),
                             ("suspected_scan", "Suspected scan hints"), ("split", "Split"),
                             ("source_status", "Source status"), ("intake_review", "Intake review")):
        lines.extend(["", "## " + title, "", "| Value | Basis | Units | PDFs | Verified intake |", "|---|---|---:|---:|---:|"])
        for row in report["dimensions"][dimension]:
            value = str(row["value"]).replace("|", "\\|").replace("\n", " ")
            basis = str(row["basis"]).replace("|", "\\|")
            lines.append(f"| {value} | {basis} | {row['unit_count']} | {row['artifact_count']} | {row['verified_unit_count']} |")
    lines.extend(["", "## Joint body, language, level and role coverage", "",
                  "| Body | Language | Level | Role | Units | PDFs | Verified intake |", "|---|---|---|---|---:|---:|---:|"])
    for row in report["joint_body_language_level_role"]:
        values = [row["body"], row["language"], row["jurisdiction_level"], row["document_role"]]
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(values) + f" | {row['unit_count']} | {row['artifact_count']} | {row['verified_unit_count']} |")
    structural = report["structural_inventory"]
    lines.extend(["", "## Structural hard-case inventory", ""])
    if structural is None:
        lines.append("No structural census was supplied. Suspected-scan flags above are intake hints only.")
    else:
        lines.extend([f"Structural census digest: `{structural['census_digest']}`", "",
            "These counts come from the versioned inventory heuristics. They identify document features; they do not establish that the feature content was interpreted.", "",
            "| Measure | Count |", "|---|---:|"])
        structural_counts = [
            ("Processed documents", structural["processed_document_count"]),
            ("Joined to frozen cohort", structural["joined_document_count"]),
            ("Cohort PDFs without inventory", structural["cohort_artifacts_without_structural_inventory"]),
            ("Documents with textless pages", structural["documents_with_textless_pages"]),
            ("Textless pages", structural["totals"]["textless_pages"]),
            ("Documents with images", structural["documents_with_images"]),
            ("Embedded images", structural["totals"]["images"]),
            ("Documents with annex markers", structural["documents_with_annexes"]),
            ("Annex markers", structural["totals"]["annexes"]),
            ("Documents with table hints", structural["documents_with_table_hints"]),
            ("Table hints", structural["totals"]["table_hints"]),
        ]
        lines.extend(f"| {name} | {count} |" for name, count in structural_counts)
        for key, title in (("by_body", "By source body"), ("by_language", "By source language")):
            lines.extend(["", "### " + title, "", "| Group | Documents | Textless | Images | Annex markers | Table hints |", "|---|---:|---:|---:|---:|---:|"])
            for group, values in structural[key].items():
                group = str(group).replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {group} | {values['documents']} | {values['textless_pages']} | {values['images']} | {values['annexes']} | {values['table_hints']} |")
        if structural["method_note"]:
            lines.extend(["", "Inventory method: " + str(structural["method_note"]).replace("\n", " ")])
    return "\n".join(lines) + "\n"


def feasibility_review_packet(cohort: dict, texts: list[TextSnapshot], body_ids: list[str], concepts: list[str],
                              selected_unit_ids: list[str], reviewer_id: str):
    """Prepare source-only human tasks without creating feasibility findings."""
    units = load_cohort(cohort)
    unique(body_ids, "schema review body")
    unique(concepts, "schema review concept")
    unique(selected_unit_ids, "schema review unit")
    if not reviewer_id.strip() or not body_ids or not concepts or not selected_unit_ids:
        raise ValueError("Schema review packet needs a reviewer, bodies, concepts and selected units")
    if len(body_ids) * len(concepts) > 10000 or len(selected_unit_ids) * len(concepts) > 10000:
        raise ValueError("Schema review packet exceeds the bounded task limit")
    by_id = {unit.unit_id: unit for unit in units}
    if set(selected_unit_ids) - set(by_id):
        raise ValueError("Schema review packet selects units outside the frozen cohort")
    if set(body_ids) - {unit.body_id for unit in units}:
        raise ValueError("Schema review packet requests a body outside the frozen cohort")
    selected = [by_id[unit_id] for unit_id in selected_unit_ids]
    if {unit.body_id for unit in selected} != set(body_ids):
        raise ValueError("Every requested body must have at least one selected review unit")
    if any(not unit.verified for unit in selected):
        raise ValueError("Schema review requires human-verified language, role and affair intake")
    by_artifact = {}
    for text in texts:
        if text.artifact_id in by_artifact:
            raise ValueError("Schema review source texts must be unique by artifact")
        by_artifact[text.artifact_id] = text
    tasks = []
    for unit in sorted(selected, key=lambda value: value.unit_id):
        text = by_artifact.get(unit.artifact_id)
        if text is None:
            raise ValueError("Every selected schema review unit needs its pinned source text")
        for concept in concepts:
            tasks.append({
                "unit_id": unit.unit_id,
                "artifact_id": unit.artifact_id,
                "scope_id": unit.scope_id,
                "body_id": unit.body_id,
                "language": unit.review.language,
                "jurisdiction_level": unit.review.jurisdiction_level,
                "document_role": unit.review.role,
                "checked_pages": unit.review.checked_pages,
                "concept": concept,
                "text_snapshot": text.model_dump(),
                "judgment": None,
            })
    return seal({
        "schema_version": "skony.schema-review-packet.v1",
        "cohort_digest": cohort["digest"],
        "reviewer_id": reviewer_id.strip(),
        "body_ids": sorted(body_ids),
        "concepts": concepts,
        "selected_unit_ids": sorted(selected_unit_ids),
        "model_outputs_included": False,
        "human_findings_created": 0,
        "tasks": tasks,
        "instruction": "Review the pinned source only. Record an evidence-backed FeasibilityJudgment separately; unknown or absent from this source is not proof of schema-wide absence.",
    })


def pointer(document, path: str):
    """RFC 6901-style local lookup; an absent path stays explicitly unavailable."""
    if path == "":
        return {"available": True, "value": document}
    if not path.startswith("/"):
        raise ValueError("Metadata query paths must be JSON pointers")
    current = document
    for raw in path[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and str(int(part)) == part and int(part) < len(current):
            current = current[int(part)]
        else:
            return {"available": False, "value": None}
    return {"available": True, "value": current}


def metadata_baseline(snapshot, *, question: str, source_reference: str, queries: dict[str, str], recorded_at: str):
    timestamp(recorded_at)
    if not question.strip() or not source_reference.strip() or not queries:
        raise ValueError("Baseline needs a question, saved source and reproducible local queries")
    return seal({"schema_version": BASELINE_SCHEMA, "question": question,
        "source_reference": source_reference, "recorded_at": recorded_at, "metadata_snapshot": snapshot,
        "snapshot_digest": identity(snapshot), "queries": queries,
        "facts": {name: pointer(snapshot, path) for name, path in sorted(queries.items())}})


def load_baseline(value):
    body = checked(value, BASELINE_SCHEMA)
    rebuilt = metadata_baseline(body["metadata_snapshot"], question=body["question"],
        source_reference=body["source_reference"], queries=body["queries"], recorded_at=body["recorded_at"])
    if rebuilt != value:
        raise ValueError("Saved baseline answers do not match the pinned metadata/query")
    return body


class PDFAddition(StrictModel):
    fact_key: str
    value: str = Field(min_length=1)
    contribution: Literal["additional_detail", "corrected_link", "changed_conclusion"]
    explanation: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reviewer_kind: Literal["human", "automated", "synthetic"]
    reviewed_at: str
    snapshot_id: str = Field(min_length=1)
    review_decision_id: str = Field(min_length=1)
    evidence: list[EvidenceSegment] = Field(min_length=1)


def novelty_report(baseline, additions: list[PDFAddition], texts: list[TextSnapshot], cohort: dict | None = None):
    body = load_baseline(baseline)
    unique([a.fact_key for a in additions], "demonstration fact")
    findings = []
    def strings(value):
        if isinstance(value, str):
            yield " ".join(value.split())
        elif isinstance(value, dict):
            for child in value.values():
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)
    metadata_strings = list(strings(body["metadata_snapshot"]))
    artifacts = {u.artifact_id for u in load_cohort(cohort)} if cohort else None
    for addition in additions:
        if addition.fact_key not in body["facts"]:
            raise ValueError("PDF contribution has no predeclared metadata baseline query")
        verify_citations(addition.evidence, texts)
        if artifacts is not None and any(e.artifact_id not in artifacts for e in addition.evidence):
            raise ValueError("Demonstration evidence is outside its frozen corpus")
        if timestamp(addition.reviewed_at) <= timestamp(body["recorded_at"]):
            raise ValueError("Save the metadata baseline before reviewing PDF information gain")
        prior = body["facts"][addition.fact_key]
        already_available = prior["available"] and isinstance(prior["value"], str) and (
            " ".join(prior["value"].split()) == " ".join(addition.value.split()))
        in_existing_text = any(" ".join(addition.value.split()) in value for value in metadata_strings)
        gain = (addition.reviewer_kind == "human" and not already_available
                and not (in_existing_text and addition.contribution == "additional_detail"))
        findings.append({**addition.model_dump(), "baseline": prior,
                         "accepted_information_gain": gain, "value_found_in_saved_metadata_text": in_existing_text,
                         "already_available_in_baseline": already_available})
    return seal({"schema_version": "skony.novelty-report.v1", "baseline_digest": baseline["digest"],
        "cohort_digest": cohort["digest"] if cohort else None,
        "question": body["question"], "passed": any(f["accepted_information_gain"] for f in findings),
        "findings": findings, "semantic_novelty_is_a_recorded_human_judgment": True,
        "missing_gate": None if any(f["accepted_information_gain"] for f in findings) else "no_demonstrated_human_reviewed_pdf_information_gain"})


class FeasibilityJudgment(StrictModel):
    body_id: str
    concept: str
    expressivity: Literal["faithful", "partial", "not_representable", "untested"]
    harmonization: Literal["exact_in_reviewed_scope", "conditional_with_mapping", "semantic_collision", "unmapped"]
    reviewer_id: str = Field(min_length=1)
    reviewer_kind: Literal["human", "automated", "synthetic"]
    rationale: str = Field(min_length=1)
    evidence: list[EvidenceSegment]
    counterexamples: list[EvidenceSegment]

    @model_validator(mode="after")
    def supported(self):
        if (self.expressivity != "untested" or self.harmonization != "unmapped") and not self.evidence:
            raise ValueError("Schema/mapping conclusions require cited source examples")
        if (self.expressivity in {"partial", "not_representable"}
                or self.harmonization in {"conditional_with_mapping", "semantic_collision"}) and not self.counterexamples:
            raise ValueError("Conditional/negative conclusions need a source-backed counterexample")
        return self


def feasibility_matrix(body_ids: list[str], concepts: list[str], judgments: list[FeasibilityJudgment],
                       texts: list[TextSnapshot], gold: list[GoldUnit], predictions: list[Prediction], cohort: dict | None = None):
    unique(body_ids, "matrix body")
    unique(concepts, "matrix concept")
    if not body_ids or not concepts or len(body_ids) * len(concepts) > 10000:
        raise ValueError("Feasibility matrix needs a bounded nonempty body/concept inventory")
    unique([(j.body_id, j.concept) for j in judgments], "matrix judgment")
    unique([g.unit_id for g in gold], "matrix gold unit")
    unique([p.unit_id for p in predictions], "matrix prediction")
    people = {(j.body_id, j.concept): j for j in judgments}
    if any(j.body_id not in body_ids or j.concept not in concepts for j in judgments):
        raise ValueError("Feasibility judgment is outside the declared matrix")
    by_pred = {p.unit_id: p for p in predictions}
    if cohort:
        units = load_cohort(cohort)
        if set(body_ids) - {u.body_id for u in units} or {g.unit_id for g in gold} - {u.unit_id for u in units}:
            raise ValueError("Feasibility inputs are outside their frozen corpus")
        artifacts = {u.artifact_id for u in units}
        if any(e.artifact_id not in artifacts for j in judgments for e in j.evidence + j.counterexamples):
            raise ValueError("Schema counterexample belongs to another corpus")
    if set(by_pred) - {g.unit_id for g in gold}:
        raise ValueError("Recovery predictions lack their declared gold units")
    cells = []
    for body in sorted(body_ids):
        for concept in concepts:
            judgment = people.get((body, concept))
            if judgment:
                verify_citations(judgment.evidence + judgment.counterexamples, texts)
            human = judgment is not None and judgment.reviewer_kind == "human"
            counts = {"known_present": 0, "recovered_exact": 0, "failed_inputs": 0, "unknown_or_excluded": 0}
            for unit in gold:
                if unit.body_id != body or concept not in unit.fields:
                    continue
                label = unit.fields[concept]
                if unit.synthetic or not label_eligibility(label)[0]:
                    counts["unknown_or_excluded"] += 1
                    continue
                prediction = by_pred.get(unit.unit_id)
                completed = prediction and prediction.outcome == "completed"
                counts["failed_inputs"] += not completed
                if label.assessment == "present":
                    counts["known_present"] += 1
                    value = prediction.fields[concept] if completed else None
                    counts["recovered_exact"] += value is not None and " ".join(value.split()) in {
                        " ".join(v.split()) for v in label.acceptable_values}
            cells.append({"body_id": body, "concept": concept,
                "expressivity": judgment.expressivity if human else "untested",
                "harmonization": judgment.harmonization if human else "unmapped",
                "judgment": judgment.model_dump() if judgment else None,
                "pipeline_recovery": {**counts, "recall": ratio(counts["recovered_exact"], counts["known_present"])}})
    return seal({"schema_version": "skony.feasibility-matrix.v1", "cells": cells,
                 "cohort_digest": cohort["digest"] if cohort else None,
                 "schema_conclusions_are_not_inferred_from_pipeline_errors": True})


def matrix_markdown(matrix):
    checked(matrix, "skony.feasibility-matrix.v1")
    lines = ["| Body | Concept | Expressivity | Harmonization | Recovery |",
             "|---|---|---|---|---|"]
    for cell in matrix["cells"]:
        p = cell["pipeline_recovery"]
        values = [cell["body_id"], cell["concept"], cell["expressivity"], cell["harmonization"],
                  f"{p['recovered_exact']}/{p['known_present']} known-present; {p['failed_inputs']} failed"]
        lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    return "\n".join(lines) + "\n"
