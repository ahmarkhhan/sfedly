"""Pure offline queries over a frozen closure. No database or model access."""

from .contracts import PROJECTION_VERSION, SERIALIZATION_VERSION, identity
from .review_contracts import ComparisonSpec


def query_snapshot(snapshot: dict, spec: ComparisonSpec):
    if identity(snapshot) != spec.snapshot_id:
        raise ValueError("Snapshot content digest mismatch")
    if (snapshot.get("schema_version") != "skony.snapshot.v0.2"
            or snapshot.get("projection_version") != PROJECTION_VERSION
            or snapshot.get("serialization_version") != SERIALIZATION_VERSION
            or snapshot.get("query_version") != "skony.query.v0.2"):
        raise ValueError("Unsupported historical projection/query policy")
    objects = snapshot["objects"]
    if any(identity(obj["value"]) != oid for oid, obj in objects.items()):
        raise ValueError("Frozen dependency digest mismatch")
    if set(spec.scope_ids) - set(snapshot["scope_ids"]):
        raise ValueError("Comparison requests a scope outside the frozen snapshot")
    rows, exclusions = [], []
    for scope_id in sorted(spec.scope_ids):
        scope = objects[snapshot["scope_versions"][scope_id]]["value"]
        caveats = []
        for mid in scope["mapping_ids"]:
            mapping = objects[mid]["value"]
            if mapping["relation"] not in spec.permitted_mapping_relations:
                caveats.append({"mapping_id": mid, "reason": "incompatible_mapping_relation"})
        fields = {}
        for predicate in spec.columns:
            found = next((r for r in snapshot["rows"] if r["scope_id"] == scope_id and r["predicate"] == predicate), None)
            fields[predicate] = found or {"value": None, "source_assessment": "not_assessed", "citations": []}
        rows.append({"scope_id": scope_id, "subject_id": scope["binding"]["subject_id"], "fields": fields,
                     "categories": [] if caveats else [objects[mid]["value"] for mid in scope["mapping_ids"]],
                     "compatible_for_aggregation": not caveats and bool(scope["mapping_ids"]), "caveats": caveats})
        exclusions.extend({"scope_id": scope_id, **c} for c in caveats)
    result = {"schema_version": "skony.comparison-result.v0.2", "spec": spec.model_dump(),
              "snapshot_id": spec.snapshot_id,
              "rows": sorted(rows, key=lambda r: (r["subject_id"], r["scope_id"])), "exclusions": exclusions}
    return {"result_id": identity(result), "result": result}
