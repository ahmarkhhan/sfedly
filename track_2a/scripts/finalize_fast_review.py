"""Validate an actual fast-review export and produce source-cited study artifacts."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skony.contracts import TextSnapshot, identity
from skony.evaluation_common import seal, timestamp
from skony.study import IntakeReview, StudyPolicy, StudyUnit, freeze_cohort


def score_pilot_records(predictions, annotations, locked_at):
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "reviewed_fields": 0}
    excluded, rows = Counter(), []
    for annotation in annotations:
        doc_id, field = annotation["document_id"], annotation["field"]
        if doc_id not in predictions:
            excluded["no_recorded_production_run"] += 1
            continue
        if not annotation["intake_confirmed"] or annotation["mode"] != "source_only":
            excluded["unconfirmed_intake_or_assisted_annotation"] += 1
            continue
        if timestamp(annotation["updated_at"]) < timestamp(locked_at):
            excluded["annotation_precedes_prediction_freeze"] += 1
            continue
        if annotation["assessment"] not in {"present", "absent_in_reviewed_scope"}:
            excluded["unknown_or_inapplicable_reference"] += 1
            continue
        predicted = predictions[doc_id]["fields"][field]
        value = predicted["value"] if predicted["status"] == "source_located" else None
        expected = annotation["value"]
        cell = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        if expected is None:
            cell["tn" if value is None else "fp"] = 1
        elif value is None:
            cell["fn"] = 1
        elif " ".join(value.split()) == " ".join(expected.split()):
            cell["tp"] = 1
        else:
            cell["fp"] = cell["fn"] = 1
        for name in cell:
            counts[name] += cell[name]
        counts["reviewed_fields"] += 1
        rows.append({"document_id": doc_id, "field": field, "body_id": annotation["body_id"],
            "language": annotation["language"], "level": annotation["level"], **cell})
    def ratio(top, bottom):
        return top / bottom if bottom else None
    return {"description": "Single-reviewer source-first pilot against previously recorded production outputs; not independent adjudicated benchmark accuracy.",
        "matching": "Exact field string after whitespace normalization; wrong nonempty value counts as FP and FN.",
        "counts": counts, "precision": ratio(counts["tp"], counts["tp"] + counts["fp"]),
        "recall": ratio(counts["tp"], counts["tp"] + counts["fn"]),
        "exact_field_agreement": ratio(counts["tp"] + counts["tn"], counts["reviewed_fields"]),
        "exclusions": dict(excluded), "scored_rows": rows}


def production_pilot(pack, annotations, directory):
    path = directory / "locked-predictions.json"
    if not path.is_file():
        return {"status": "No frozen production predictions supplied"}
    lock = json.loads(path.read_text(encoding="utf-8"))
    if (lock.get("schema_version") != "skony.fast-review-predictions.v1" or lock.get("pack_digest") != pack["digest"]
            or lock.get("digest") != identity({k: v for k, v in lock.items() if k != "digest"})):
        raise ValueError("Production prediction lock failed its identity check")
    predictions = {}
    documents = {d["id"]: d for d in pack["documents"]}
    for saved in lock["predictions"]:
        file = (directory / saved["result_file"]).resolve()
        if not file.is_relative_to(directory.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest() != saved["file_sha256"]:
            raise ValueError("Saved production result is missing or modified")
        result = json.loads(file.read_text(encoding="utf-8"))
        doc_id = saved["document_id"]
        if doc_id not in documents or doc_id in predictions or result["document"]["sha256"] != doc_id:
            raise ValueError("Saved production result has invalid or duplicate source membership")
        if ({p["number"]: p["text"] for p in result["document"]["pages"]}
                != {p["page"]: p["text"] for p in documents[doc_id]["text"]["pages"]}
                or set(pack["fields"]) - set(result["fields"])):
            raise ValueError("Production result source projection or field inventory differs")
        if any(result[k] != saved[v] for k, v in (("model_name", "model"), ("prompt_version", "prompt_version"), ("verifier_version", "verifier_version"))):
            raise ValueError("Production model or processing identity differs")
        predictions[doc_id] = result
    return {"prediction_lock_digest": lock["digest"], "recorded_document_count": len(predictions),
        "models": sorted({p["model_name"] for p in predictions.values()}),
        **score_pilot_records(predictions, annotations, lock["locked_at"])}


def validate_review(pack, review):
    if pack.get("schema_version") != "skony.fast-review-pack.v1" or pack.get("digest") != identity({k: v for k, v in pack.items() if k != "digest"}):
        raise ValueError("Review pack failed its identity check")
    if review.get("schema_version") != "skony.fast-review.v1" or review.get("pack_digest") != pack["digest"]:
        raise ValueError("Review export belongs to another pack")
    person = review.get("reviewer", {})
    reviewer = person.get("id", "").strip()
    languages = person.get("languages", [])
    if not reviewer or not person.get("competence_note", "").strip() or not languages or set(languages) - {"de", "fr"}:
        raise ValueError("Actual reviewer ID and declared language/parliamentary competence are required")
    documents = {d["id"]: d for d in pack["documents"]}
    if set(review.get("documents", {})) - set(documents):
        raise ValueError("Review refers to a document outside the frozen pack")
    checked, units, annotations = {}, [], []
    for doc_id, doc in documents.items():
        text = TextSnapshot.model_validate(doc["text"])
        if text.artifact_id != doc_id or text.id != doc["text_snapshot_id"]:
            raise ValueError("Pinned text snapshot identity differs")
        saved = review.get("documents", {}).get(doc_id, {})
        intake = saved.get("intake", {"status": "unreviewed"})
        if intake.get("status") not in {"confirmed", "unreviewed"}:
            raise ValueError("Unsupported intake review status")
        original = dict(doc["unit"])
        original["split"] = "unassigned"
        original["review"] = None
        if intake.get("status") == "confirmed":
            if intake.get("reviewer_id") != reviewer or intake.get("language") not in languages:
                raise ValueError("Intake reviewer or source language differs from declared competence")
            if not str(intake.get("body_id", "")).strip() or not str(intake.get("affair_id", "")).strip():
                raise ValueError("Reviewed body and affair identities are required")
            original.update(body_id=str(intake["body_id"]), affair_id=str(intake["affair_id"]), level=intake["level"])
            record = IntakeReview(reviewer_id=reviewer, kind="human", locked_at=intake["confirmed_at"],
                artifact_id=doc_id, body_id=original["body_id"], affair_id=original["affair_id"],
                language=intake["language"], role=intake["role"], jurisdiction_level=intake["level"],
                checked_pages=intake["checked_pages"], note=intake["note"])
            original["review"] = record.model_dump()
            checked[doc_id] = intake
        unit = StudyUnit.model_validate(original)
        units.append(unit)
        exposure = timestamp(saved["exposure_at"]) if saved.get("exposure_at") else None
        for field, entry in saved.get("fields", {}).items():
            if field not in pack["fields"]:
                raise ValueError("Unknown reviewed field")
            if entry.get("reviewer_id") != reviewer or (intake.get("language") or doc["hints"]["language"]) not in languages:
                raise ValueError("Field annotation lacks the declared competent reviewer")
            mode = "assisted" if exposure is not None and timestamp(entry["updated_at"]) >= exposure else "source_only"
            if entry.get("mode") != mode:
                raise ValueError("Field review exposure status differs from recorded chronology")
            assessment = entry.get("assessment")
            if assessment not in {"present", "absent_in_reviewed_scope", "unknown", "not_applicable"}:
                raise ValueError("Field review assessment is unsupported")
            evidence = entry.get("evidence")
            if assessment == "present":
                if not isinstance(entry.get("value"), str) or not entry["value"].strip() or not isinstance(evidence, dict):
                    raise ValueError("Present field needs a value and exact source quotation")
                page = next((p for p in text.pages if p.page == evidence.get("page") and p.layer_id == evidence.get("layer_id")), None)
                start, end = evidence.get("start"), evidence.get("end")
                if (not page or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(page.text)
                        or page.text[start:end] != evidence.get("quote") or evidence.get("artifact_id") != doc_id
                        or evidence.get("text_snapshot_id") != text.id):
                    raise ValueError("Reviewed quotation does not resolve to the pinned source")
            elif entry.get("value") is not None or evidence is not None or not entry.get("note", "").strip():
                raise ValueError("Non-present assessments need an explanation and no value or quotation")
            if assessment == "absent_in_reviewed_scope" and (doc_id not in checked or set(intake["checked_pages"]) != {p.page for p in text.pages}):
                raise ValueError("Document-level absence needs all source pages human checked")
            annotations.append({**entry, "document_id": doc_id, "unit_id": unit.unit_id, "field": field,
                "intake_confirmed": doc_id in checked, "body_id": unit.body_id,
                "language": intake.get("language") or "unverified:" + doc["hints"]["language"],
                "level": intake.get("level") or "unverified:" + doc["hints"]["level"]})
    tasks = {t["id"]: t for t in pack["schema_tasks"]}
    findings = []
    for task_id, entry in review.get("schema_reviews", {}).items():
        if task_id not in tasks or entry.get("status") not in {"accepted", "corrected", "unclear"}:
            raise ValueError("Unsupported schema judgment")
        task = tasks[task_id]
        task_docs = [d for d in documents.values() if d["manifest_index"] in task["document_indices"]]
        if (set(entry.get("document_ids", [])) != {d["id"] for d in task_docs}
                or any(d["id"] not in checked for d in task_docs)
                or entry.get("reviewer_id") != reviewer or not entry.get("note", "").strip()
                or entry.get("mode") != "assisted"):
            raise ValueError("Schema judgment lacks checked sources, reviewer, or rationale")
        timestamp(entry["updated_at"])
        findings.append({**entry, "task_id": task_id, "draft_statement": task["statement"],
            "citations": [{"document_id": d["id"], "filename": d["filename"], "checked_pages": checked[d["id"]]["checked_pages"]} for d in task_docs]})
    now = datetime.now(timezone.utc).isoformat()
    cohort = freeze_cohort(units, StudyPolicy(mode="bounded", minimum_documents=12, maximum_documents=12,
        minimum_bodies=3, minimum_levels=2, required_languages=["de", "fr"]), frozen_at=now)
    rows = []
    for doc in documents.values():
        intake = checked.get(doc["id"])
        if not intake or intake["role"] != "submission" or doc["unit"]["body_key"] not in {"743", "6621"}:
            continue
        field = next((a for a in annotations if a["document_id"] == doc["id"] and a["field"] == "affair_type_raw" and a["assessment"] == "present"), None)
        if field:
            rows.append({"source_body_key": doc["unit"]["body_key"], "body_id": intake["body_id"], "body_label": doc["body_label"] if intake["body_id"] == str(doc["unit"]["body_id"]) else "Corrected body " + intake["body_id"],
                "affair_id": intake["affair_id"], "filename": doc["filename"], "source_url": doc["source_url"],
                "printed_instrument": field["value"], "evidence": field["evidence"], "review_mode": field["mode"]})
    counts = {"selected_documents": len(documents), "confirmed_intake": len(checked),
        "verified_intake": sum(u.verified for u in units), "field_annotations": len(annotations),
        "source_only_fields": sum(a["mode"] == "source_only" for a in annotations),
        "assisted_fields": sum(a["mode"] == "assisted" for a in annotations),
        "accepted_or_corrected_schema_findings": sum(f["status"] != "unclear" for f in findings)}
    summary = seal({"schema_version": "skony.fast-review-results.v1", "pack_digest": pack["digest"],
        "reviewer_declaration": person, "counts": counts, "cohort_digest": cohort["digest"],
        "reviewed_language_level_cells": [{"language": k[0], "level": k[1], "documents": n} for k, n in sorted(Counter((i["language"], i["level"]) for i in checked.values()).items())],
        "cross_body_question": pack["question"], "cross_body_answer_demonstrated": len({r["body_id"] for r in rows}) >= 2 and {r["source_body_key"] for r in rows} == {"743", "6621"},
        "cross_body_rows": rows, "schema_findings": findings,
        "limitations": ["Purposive convenience sample; no population inference.", "Reviewer identity and competence are declarations, not authentication.", "Source-only annotations here are single-reviewer records; independent annotation and adjudication remain separate.", "Prepared suggestions are not production model predictions. Production pilot comparisons use only the separate previously recorded output lock, confirmed intake and subsequent source-only field annotations."]})
    return summary, cohort, annotations


def markdown(summary):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")
    lines = ["# Checked source-review results", "", "## Actual completed review", "", "| Measure | Count |", "|---|---:|"]
    lines += [f"| {cell(k)} | {v} |" for k, v in summary["counts"].items()]
    lines += ["", "## Comparative question", "", summary["cross_body_question"], ""]
    if not summary["cross_body_answer_demonstrated"]:
        lines += ["Pending: reviewed submission-type records from both cities are still required.", ""]
    else:
        lines += ["The following printed instrument labels occur in the reviewed selected submissions. They are source-specific raw labels; no legal equivalence, prevalence or nationwide claim is inferred.", ""]
    lines += ["| Body | Affair | Printed instrument | Source quotation |", "|---|---|---|---|"]
    for row in summary["cross_body_rows"]:
        e = row["evidence"]
        lines.append(f"| {cell(row['body_label'])} | {cell(row['affair_id'])} | {cell(row['printed_instrument'])} | [{cell(row['filename'])}]({row['source_url']}) p. {e['page']}: {cell(e['quote'])} |")
    lines += ["", "## Human-reviewed schema statements", ""]
    for finding in summary["schema_findings"]:
        lines += ["### " + finding["task_id"] + " · " + finding["status"], "", finding["draft_statement"] if finding["status"] == "accepted" else finding["note"], "", "Reviewer rationale: " + finding["note"], "", "Sources: " + "; ".join(c["filename"] + " pp. " + ",".join(map(str, c["checked_pages"])) for c in finding["citations"]), ""]
    pilot = summary.get("production_pilot", {})
    if "counts" in pilot:
        lines += ["## Recorded production pilot", "", pilot["description"], "", pilot["matching"], "",
            f"Previously recorded documents available: {pilot['recorded_document_count']}. Reviewed field denominator: {pilot['counts']['reviewed_fields']}.", "",
            "| Precision | Recall | Exact field agreement |", "|---|---|---|",
            "| " + " | ".join("not measured" if pilot[k] is None else str(round(pilot[k], 4)) for k in ("precision", "recall", "exact_field_agreement")) + " |", ""]
    lines += ["## Interpretation", ""] + ["- " + value for value in summary["limitations"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        pack = json.loads(args.pack.read_text(encoding="utf-8-sig"))
        review = json.loads(args.review.read_text(encoding="utf-8-sig"))
        result, cohort, fields = validate_review(pack, review)
        result = seal({**{k: v for k, v in result.items() if k != "digest"},
            "production_pilot": production_pilot(pack, fields, args.pack.parent)})
        for doc in pack["documents"]:
            path = (args.pack.parent / doc["pdf"]).resolve()
            if not path.is_relative_to(args.pack.parent.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != doc["id"]:
                raise ValueError("Pinned source PDF is missing or modified")
        args.out.mkdir(parents=True, exist_ok=False)
        for name, value in (("review-results.json", result), ("reviewed-cohort.json", cohort), ("reviewed-fields.json", fields), ("original-human-review.json", review)):
            (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.out / "review-results.md").write_text(markdown(result), encoding="utf-8")
        print(json.dumps({"output": str(args.out), "counts": result["counts"]}))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, "Review rejected: " + str(error) + "\n")
