"""Source-cited Markdown for cross-body comparisons over frozen review snapshots."""

from .comparison import query_snapshot
from .citations import citation
from .contracts import EvidenceSegment, TextSnapshot, identity
from .evaluation_common import seal
from .review_contracts import Claim, ComparisonSpec

REPORT_SCHEMA = "skony.cross-body-report.v1"


def cross_body_report(snapshot: dict, spec: ComparisonSpec):
    """Render a frozen evidence table; never infer an aggregate semantic result."""
    wrapped_snapshot = "snapshot" in snapshot
    historical_warning = snapshot.get("historical_warning") if wrapped_snapshot else None
    snapshot_body = snapshot.get("snapshot", snapshot)
    comparison = query_snapshot(snapshot_body, spec)
    objects = snapshot_body["objects"]
    if wrapped_snapshot and type(historical_warning) is not bool:
        raise ValueError("Snapshot historical warning must be a boolean")
    saved_rows = {}
    decisions = set(snapshot_body.get("decisions", []))
    scope_bindings = {}
    for scope_id in spec.scope_ids:
        scope_version = snapshot_body["scope_versions"][scope_id]
        scope_obj = objects.get(scope_version)
        if not scope_obj or scope_obj.get("kind") != "scope":
            raise ValueError("Frozen comparison scope has no pinned scope record")
        scope_bindings[scope_id] = scope_obj["value"]["binding"]
    texts = {key: TextSnapshot.model_validate(item["value"]) for key, item in objects.items()
             if item.get("kind") == "text"}
    for saved in snapshot_body["rows"]:
        if saved["scope_id"] not in set(spec.scope_ids):
            continue
        key = (saved["scope_id"], saved["predicate"])
        if key in saved_rows:
            raise ValueError("Frozen snapshot contains duplicate scope/field decisions")
        decision_id = saved.get("decision_id")
        decision_obj = objects.get(decision_id)
        if decision_id not in decisions or not decision_obj or decision_obj.get("kind") != "review":
            raise ValueError("Frozen comparison values need their pinned human review decisions")
        decision = decision_obj["value"]
        request = decision.get("request", {})
        if request.get("action") not in {"accepted", "corrected"}:
            raise ValueError("Frozen comparison values must come from accepted review decisions")
        claim_obj = objects.get(request.get("claim_id"))
        if not claim_obj or claim_obj.get("kind") != "claim":
            raise ValueError("Frozen review decision has no pinned claim")
        claim = Claim.model_validate(claim_obj["value"])
        if (claim.scope_id != saved["scope_id"] or claim.subject_id != saved["subject_id"]
                or claim.predicate != saved["predicate"] or claim.value != saved["value"]
                or claim.source_assessment != saved["source_assessment"]):
            raise ValueError("Frozen comparison row differs from its reviewed claim")
        binding = scope_bindings.get(claim.scope_id)
        if not binding or claim.subject_id != binding["subject_id"]:
            raise ValueError("Reviewed claim differs from its frozen scope subject")
        verified_citations = []
        for evidence in claim.evidence:
            if evidence.artifact_id != binding["artifact_id"]:
                raise ValueError("Reviewed evidence belongs to another source artifact")
            text = texts.get(evidence.text_snapshot_id) if evidence.basis == "text" else None
            if evidence.basis == "text":
                if evidence.text_snapshot_id != binding["text_snapshot_id"] or text is None:
                    raise ValueError("Reviewed evidence does not use the frozen scope text")
                if not any(window["page"] == evidence.page and window["layer_id"] == evidence.layer_id
                           and window["start"] <= evidence.start < evidence.end <= window["end"]
                           for window in binding["windows"]):
                    raise ValueError("Reviewed evidence lies outside the frozen scope window")
            elif evidence.page not in {window["page"] for window in binding["windows"]}:
                raise ValueError("Image evidence lies outside the frozen scope")
            verified_citations.append(citation(evidence, text))
        if verified_citations != saved.get("citations", []):
            raise ValueError("Frozen comparison citations differ from their reviewed evidence")
        saved_rows[key] = saved
    affairs = [obj["value"] for obj in objects.values() if obj.get("kind") == "affair"]
    source_objects = {key: item["value"] for key, item in objects.items() if item.get("kind") == "source"}
    by_affair = {}
    for affair in affairs:
        by_affair.setdefault(affair["internal_id"], []).append(affair)
    scopes = {}
    for scope_id in spec.scope_ids:
        binding = scope_bindings[scope_id]
        if binding["membership"] != "reviewed":
            raise ValueError("Cross-body reports require human-reviewed affair membership")
        candidates = by_affair.get(binding["subject_id"], [])
        if len(candidates) != 1:
            raise ValueError("Cross-body reports need one frozen namespaced affair identity per scope")
        affair = candidates[0]
        scope_value = objects[snapshot_body["scope_versions"][scope_id]]["value"]
        source_ids = set(scope_value["source_ids"])
        if not source_ids or not source_ids.issubset(set(affair["source_ids"])):
            raise ValueError("Cross-body reports need source records attached to the reviewed affair")
        if any(source_id not in source_objects or source_objects[source_id]["artifact_id"] != binding["artifact_id"]
               for source_id in source_ids):
            raise ValueError("Reviewed scope source records do not match its PDF artifact")
        scopes[scope_id] = {
            "scope_id": scope_id,
            "subject_id": binding["subject_id"],
            "body_id": affair["body_id"],
            "body_key": affair["body_key"],
            "jurisdiction_level": affair["jurisdiction_level"],
            "document_role": binding["role"],
            "membership": binding["membership"],
        }
    body_ids = {scope["body_id"] for scope in scopes.values()}
    if len(body_ids) < 2:
        raise ValueError("A cross-body report needs reviewed scopes from at least two bodies")

    rows = []
    for result_row in comparison["result"]["rows"]:
        scope = scopes[result_row["scope_id"]]
        for predicate, field in result_row["fields"].items():
            assessment = field.get("source_assessment", "not_assessed")
            value = field.get("value")
            citations = field.get("citations", [])
            if assessment == "present" and (not isinstance(value, str) or not value.strip() or not citations):
                raise ValueError("Present comparison values require source text and citations")
            if assessment != "present" and (value is not None or citations):
                raise ValueError("Non-present comparison values cannot carry text or citations")
            rows.append({**scope, "predicate": predicate, "source_assessment": assessment,
                         "value": value, "citations": citations,
                         "compatible_for_aggregation": result_row["compatible_for_aggregation"],
                         "mapping_categories": result_row["categories"],
                         "mapping_caveats": result_row["caveats"]})
            frozen = saved_rows.get((result_row["scope_id"], predicate))
            if frozen is None:
                if assessment != "not_assessed" or value is not None or citations:
                    raise ValueError("Unreviewed comparison fields must remain explicitly unassessed")
            elif any(field.get(name) != frozen.get(name) for name in ("value", "source_assessment", "citations")):
                raise ValueError("Comparison projection differs from its frozen reviewed row")

    body = {"schema_version": REPORT_SCHEMA, "question": spec.question,
        "snapshot_id": spec.snapshot_id, "comparison_result_id": comparison["result_id"],
        "bodies": sorted(body_ids), "scope_count": len(scopes), "fields": list(spec.columns),
        "rows": rows, "exclusions": comparison["result"]["exclusions"],
        "interpretation": "Source-cited reviewed records grouped by body. No aggregate semantic conclusion, rate or transfer claim is inferred.",
        "historical_warning": historical_warning,
        "historical_status_checked": historical_warning is not None}
    return seal(body)


def cross_body_report_markdown(report: dict):
    body = {key: value for key, value in report.items() if key != "digest"}
    if report.get("schema_version") != REPORT_SCHEMA or report.get("digest") != identity(body):
        raise ValueError("Cross-body report failed its identity check")

    def cell(value):
        if value is None:
            value = "—"
        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")

    lines = ["# Source-cited cross-body comparison", "", "Research question: " + cell(report["question"]), "",
        f"Snapshot: `{cell(report['snapshot_id'])}`  ",
        f"Comparison result: `{cell(report['comparison_result_id'])}`  ",
        "Bodies: " + ", ".join(cell(value) for value in report["bodies"]), "",
        report["interpretation"], ""]
    if not report["historical_status_checked"]:
        lines.extend(["Historical withdrawal or supersession status was not present in the input snapshot wrapper; check it before publication.", ""])
    elif report["historical_warning"]:
        lines.extend(["Warning: the snapshot has recorded withdrawal, supersession or current-eligibility warnings.", ""])
    for field in report["fields"]:
        lines.extend(["## " + cell(field), "",
            "| Body | Level | Affair | Role | Assessment | Reviewed value | Source citation | Mapping status |",
            "|---|---|---|---|---|---|---|---|"])
        for row in report["rows"]:
            if row["predicate"] != field:
                continue
            cite = "<br>".join(f"`{cell(item.get('artifact_id'))}` p. {cell(item.get('page'))}: {cell(item.get('quote'))}"
                               for item in row["citations"])
            if row["mapping_caveats"]:
                mapping = "not grouped: " + "; ".join(cell(item["reason"]) for item in row["mapping_caveats"])
            elif row["compatible_for_aggregation"]:
                mapping = ", ".join(f"{cell(item.get('destination'))} ({cell(item.get('relation'))})"
                                     for item in row["mapping_categories"])
            else:
                mapping = "raw value only"
            value = cell(row["value"])
            lines.append("| " + " | ".join((cell(row["body_id"]), cell(row["jurisdiction_level"]),
                cell(row["subject_id"]), cell(row["document_role"]), cell(row["source_assessment"]),
                value, cite or "—", mapping)) + " |")
        lines.append("")
    if report["exclusions"]:
        lines.extend(["## Mapping exclusions", "", "| Scope | Reason |", "|---|---|"])
        lines.extend(f"| {cell(row['scope_id'])} | {cell(row['reason'])} |" for row in report["exclusions"])
        lines.append("")
    lines.extend(["## Scope", "", f"The report contains {report['scope_count']} reviewed document scopes from {len(report['bodies'])} bodies. It preserves per-source dispositions and does not treat missing text as proof that a parliament did not respond.", ""])
    return "\n".join(lines)
