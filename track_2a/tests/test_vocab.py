"""Deterministic tests for the controlled-vocabulary layer. No network, no API key."""

import unittest

from skony import vocab
from skony.review_contracts import MappingRule


class TestLoad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocabs = vocab.load_all()

    def test_all_four_kinds_load(self):
        self.assertEqual(set(self.vocabs), {"affair_type", "actor_role",
                                            "procedural_state", "decision_outcome"})

    def test_versions_pinned(self):
        for v in self.vocabs.values():
            self.assertTrue(v.version.startswith("v0.1"), v.version)
            self.assertTrue(v.id.startswith("skony.vocab."), v.id)

    def test_term_ids_unique_and_namespaced(self):
        for kind, v in self.vocabs.items():
            ids = [t.id for t in v.terms]
            self.assertEqual(len(ids), len(set(ids)))
            prefixes = {"affair_type": "at.", "actor_role": "role.",
                        "procedural_state": "state.", "decision_outcome": "outcome."}
            for tid in ids:
                self.assertTrue(tid.startswith(prefixes[kind]), tid)

    def test_broader_references_resolve(self):
        for v in self.vocabs.values():
            for t in v.terms:
                if t.broader:
                    self.assertIn(t.broader, v.index)

    def test_alias_table_no_collisions(self):
        # load_all would already raise on collision; assert counts are sane
        total = sum(len(v.alias_table()) for v in self.vocabs.values())
        self.assertGreater(total, 150)


class TestNormalize(unittest.TestCase):
    def test_diacritics_and_case(self):
        self.assertEqual(vocab.normalize("Pris acte"), vocab.normalize("PRIS ACTE"))
        self.assertEqual(vocab.normalize("Uberwiesen"), vocab.normalize("überwiesen"))

    def test_punctuation_collapses(self):
        self.assertEqual(vocab.normalize("pris-acte"), vocab.normalize("pris acte"))
        self.assertEqual(vocab.normalize("  Motion  urgente "), "motion urgente")


class TestMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocabs = vocab.load_all()

    def test_exact_alias_de(self):
        m = vocab.map_label(self.vocabs["affair_type"], "Motion")
        self.assertEqual(m.destination, "at.motion")
        self.assertEqual(m.relation, "exact_in_scope")
        self.assertEqual(m.rule, "alias-exact")

    def test_exact_alias_fr(self):
        m = vocab.map_label(self.vocabs["decision_outcome"], "Adopté")
        self.assertEqual(m.destination, "outcome.adopted")

    def test_generic_vorstoss_maps_to_family(self):
        m = vocab.map_label(self.vocabs["affair_type"], "Parlamentarischer Vorstoss")
        self.assertEqual(m.destination, "at.motion-family")

    def test_unknown_is_unmapped_not_guessed(self):
        m = vocab.map_label(self.vocabs["affair_type"], "Dringliche Interpellation (VI)")
        self.assertIsNone(m.destination)
        self.assertEqual(m.relation, "unmapped")
        self.assertEqual(m.rule, "no-alias")

    def test_empty_is_unmapped(self):
        for empty in (None, "", "   "):
            m = vocab.map_label(self.vocabs["affair_type"], empty)
            self.assertIsNone(m.destination)
            self.assertEqual(m.rule, "empty")

    def test_deterministic(self):
        a = vocab.map_label(self.vocabs["procedural_state"], "beantwortet")
        b = vocab.map_label(self.vocabs["procedural_state"], "beantwortet")
        self.assertEqual(a, b)

    def test_mapping_rule_contract_compatible(self):
        m = vocab.map_label(self.vocabs["affair_type"], "Postulat")
        rule = MappingRule(**m.as_mapping_rule(body_id="nidau"))
        self.assertEqual(rule.destination, "at.postulate")
        self.assertEqual(rule.relation, "exact_in_scope")
        self.assertIn("nidau", rule.body_id)

    def test_map_fields_routes_known_fields(self):
        out = vocab.map_fields(self.vocabs,
                               {"affair_type_raw": "Motion", "decision_raw": "abgelehnt",
                                "title": "ignored"})
        self.assertEqual(out["affair_type_raw"].destination, "at.motion")
        self.assertEqual(out["decision_raw"].destination, "outcome.rejected")
        self.assertNotIn("title", out)


if __name__ == "__main__":
    unittest.main()
