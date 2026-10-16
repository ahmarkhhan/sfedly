import unittest

from src.skony.citations import citation
from src.skony.contracts import (EvidenceSegment, LayerPage, PROJECTION_VERSION, SERIALIZATION_VERSION,
                                 TextSnapshot, identity)
from src.skony.research_report import cross_body_report, cross_body_report_markdown
from src.skony.review_contracts import ComparisonSpec


def snapshot_fixture():
    objects, scope_versions, rows, scope_ids, decision_ids = {}, {}, [], [], []
    for index, (body, level, role, value) in enumerate((
            ("body-de", "municipal", "submission", "Anfrage"),
            ("body-fr", "cantonal", "executive_response", "Réponse"))):
        affair_id = "affair-" + str(index)
        scope_id = "scope-" + str(index)
        artifact_id = (str(index + 1) * 64)
        source_record = {"artifact_id": artifact_id, "provider_namespace": "fixture"}
        source_version = identity(source_record)
        affair = {"internal_id": affair_id, "provider_namespace": "fixture", "body_id": body,
            "body_key": body, "official_affair_id": str(index), "jurisdiction_level": level,
            "source_ids": [source_version]}
        text = TextSnapshot(artifact_id=artifact_id, parser_name="fixture", parser_version="1",
            configuration={"fixture": True}, origin="recorded",
            pages=[LayerPage(page=1, layer_id="native", text=value)])
        scope = {"binding": {"scope_id": scope_id, "subject_id": affair_id, "artifact_id": artifact_id,
            "text_snapshot_id": text.id, "membership": "reviewed", "role": role,
            "windows": [{"page": 1, "layer_id": "native", "start": 0, "end": len(value)}]},
            "source_ids": [source_version], "mapping_ids": []}
        evidence = EvidenceSegment(artifact_id=artifact_id, text_snapshot_id=text.id, page=1, layer_id="native",
            start=0, end=len(value), quote=value, match_method="exact")
        claim = {"scope_id": scope_id, "subject_id": affair_id, "predicate": "title", "value": value,
            "source_assessment": "present", "evidence": [evidence.model_dump()]}
        claim_id = identity(claim)
        decision = {"schema_version": "skony.decision.v0.2",
            "request": {"action": "accepted", "claim_id": claim_id}}
        decision_id = identity(decision)
        affair_version, scope_version = identity(affair), identity(scope)
        objects[affair_version] = {"kind": "affair", "value": affair}
        objects[scope_version] = {"kind": "scope", "value": scope}
        objects[source_version] = {"kind": "source", "value": source_record}
        objects[text.id] = {"kind": "text", "value": text.model_dump()}
        objects[claim_id] = {"kind": "claim", "value": claim}
        objects[decision_id] = {"kind": "review", "value": decision}
        scope_ids.append(scope_id)
        decision_ids.append(decision_id)
        scope_versions[scope_id] = scope_version
        rows.append({"scope_id": scope_id, "subject_id": affair_id, "predicate": "title", "value": value,
            "source_assessment": "present", "decision_id": decision_id, "citations": [citation(evidence, text)]})
    snapshot = {"schema_version": "skony.snapshot.v0.2", "projection_version": PROJECTION_VERSION,
        "serialization_version": SERIALIZATION_VERSION, "query_version": "skony.query.v0.2",
        "scope_ids": sorted(scope_ids), "scope_versions": scope_versions, "decisions": decision_ids, "rows": rows,
        "exclusions": [], "objects": objects}
    spec = ComparisonSpec(question="How are the records titled?", snapshot_id=identity(snapshot),
        scope_ids=scope_ids, columns=["title"], permitted_mapping_relations=[])
    return snapshot, spec


class CrossBodyReportTests(unittest.TestCase):
    def test_report_preserves_raw_values_citations_and_body_context(self):
        snapshot, spec = snapshot_fixture()
        report = cross_body_report(snapshot, spec)
        markdown = cross_body_report_markdown(report)

        self.assertEqual(report["bodies"], ["body-de", "body-fr"])
        self.assertEqual([row["value"] for row in report["rows"]], ["Anfrage", "Réponse"])
        self.assertEqual(len(report["rows"][0]["citations"]), 1)
        self.assertIn("Anfrage", markdown)
        self.assertIn("Réponse", markdown)
        self.assertIn("Source-cited reviewed records grouped by body", markdown)
        self.assertIn("Historical withdrawal or supersession status", markdown)

    def test_one_body_or_unreviewed_membership_cannot_claim_cross_body(self):
        snapshot, spec = snapshot_fixture()
        single_spec = spec.model_copy(update={"scope_ids": [spec.scope_ids[0]]})
        single_snapshot = {**snapshot, "scope_ids": [spec.scope_ids[0]]}
        single_snapshot["scope_versions"] = {spec.scope_ids[0]: snapshot["scope_versions"][spec.scope_ids[0]]}
        single_spec.snapshot_id = identity(single_snapshot)
        with self.assertRaisesRegex(ValueError, "at least two bodies"):
            cross_body_report(single_snapshot, single_spec)

        scope_id = spec.scope_ids[0]
        scope_version = snapshot["scope_versions"][scope_id]
        snapshot["objects"][scope_version]["value"]["binding"]["membership"] = "unresolved"
        snapshot["scope_versions"][scope_id] = identity(snapshot["objects"][scope_version]["value"])
        snapshot["objects"][snapshot["scope_versions"][scope_id]] = snapshot["objects"].pop(scope_version)
        spec.snapshot_id = identity(snapshot)
        with self.assertRaisesRegex(ValueError, "membership"):
            cross_body_report(snapshot, spec)


if __name__ == "__main__":
    unittest.main()
