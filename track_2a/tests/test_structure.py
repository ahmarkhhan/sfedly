"""Deterministic tests for the structural inventory layer. No network."""

import unittest

from skony import structure
from skony.schema import Document, Page


def doc(pages: list[str], textless: list[int] | None = None) -> Document:
    return Document(
        document_id="d" * 64,
        filename="test.pdf",
        sha256="d" * 64,
        pages=[Page(number=i + 1, text=t) for i, t in enumerate(pages)],
        textless_pages=textless or [],
    )


class TestAnnexes(unittest.TestCase):
    def test_numbered_marker_de(self):
        d = doc(["Antrag\n...\nBeilage 1: Budget 2027\n"])
        items = structure.annex_inventory(d)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].label, "Beilage 1: Budget 2027")
        self.assertEqual(items[0].quote, d.pages[0].text[items[0].start:items[0].end])

    def test_marker_fr(self):
        d = doc(["Rapport\n\nAnnexe 2 - Compte de gestion\n"])
        items = structure.annex_inventory(d)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].label.startswith("Annexe 2"))

    def test_bare_word_rejected(self):
        d = doc(["Les annexes\nsont disponibles\n"])
        self.assertEqual(structure.annex_inventory(d), [])

    def test_inline_mention_rejected(self):
        d = doc(["voir Beilage 3 pour details du budget\n"])
        self.assertEqual(structure.annex_inventory(d), [])

    def test_textless_flag(self):
        d = doc(["", ], textless=[1])
        self.assertEqual(structure.annex_inventory(d), [])
        d2 = doc(["Anhang 1\n"], textless=[1])
        self.assertTrue(structure.annex_inventory(d2)[0].textless_page)

    def test_multiple_pages(self):
        d = doc(["Antrag\n", "Beilage 1\n", "Beilage 2: Kosten\n"])
        self.assertEqual([i.page for i in structure.annex_inventory(d)], [2, 3])


class TestImages(unittest.TestCase):
    def test_no_bytes_empty(self):
        self.assertEqual(structure.image_inventory(doc(["x"]), None), [])

    def test_invalid_bytes_no_crash(self):
        self.assertEqual(structure.image_inventory(doc(["x"]), b"not a pdf"), [])


class TestTableHints(unittest.TestCase):
    def test_grid_detected(self):
        page = (
            "Voranschlag 2027\n"
            "Personalaufwand        1 250 000\n"
            "Sachaufwand              340 000\n"
            "Abschreibungen            85 000\n"
            "Total                  1 675 000\n"
        )
        hints = structure.table_hints(doc([page]))
        self.assertEqual(len(hints), 1)
        self.assertIn("digit-dense", hints[0].reason)

    def test_prose_not_flagged(self):
        page = ("Der Stadtrat beantragt die Genehmigung des Budgets. "
                "Die Kosten belaufen sich auf mehrere Posten. "
                "Einzelheiten sind im Bericht beschrieben worden.")
        self.assertEqual(structure.table_hints(doc([page])), [])

    def test_two_line_run_too_short(self):
        page = "Aufwand    100\nErtrag     200\n"
        self.assertEqual(structure.table_hints(doc([page])), [])


class TestBuild(unittest.TestCase):
    def test_schema_and_limitations(self):
        inv = structure.build_inventory(doc(["Beilage 1\n", ""]))
        self.assertEqual(inv.schema_version, "skony.structure-inventory.v0.1")
        self.assertEqual(len(inv.limitations), 4)
        payload = structure.inventory_json(inv)
        self.assertIn('"document_id"', payload)

    def test_deterministic(self):
        d = doc(["Beilage 1\nAufwand    100\nErtrag     200\nSaldo      300\n"])
        a = structure.inventory_json(structure.build_inventory(d))
        b = structure.inventory_json(structure.build_inventory(d))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
