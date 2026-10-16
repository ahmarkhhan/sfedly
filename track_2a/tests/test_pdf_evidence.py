"""Synthetic PDF geometry and evidence API checks; not extraction accuracy."""

import tempfile
import shutil
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import pymupdf

from src.skony.pdf import read_pdf
from src.skony.pdf_evidence import passage_regions
from src.skony.review import ReviewAction, ReviewError
from src.skony.server import Workbench, make_handler


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "synthetic.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=400, height=600)
            page.insert_text((50, 80), "Motion pour Genève\nSupporting passage on two lines\ncontinues here.", fontsize=12)
            page.insert_text((50, 180), "Repeated phrase\nRepeated phrase", fontsize=12)
            page.insert_text((50, 230), "Same wrapped phrase\nSame wrapped\nphrase", fontsize=12)
            rotated = pdf.new_page(width=400, height=600)
            rotated.insert_text((50, 80), "Rotated passage", fontsize=12)
            rotated.set_cropbox(pymupdf.Rect(20, 30, 380, 560))
            rotated.set_rotation(90)
            pdf.new_page(width=400, height=600)
            pdf.save(self.path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_wrapped_passage_has_separate_line_regions(self):
        result = passage_regions(self.path, 1, "Supporting passage on two lines\ncontinues here.")
        self.assertEqual(result["status"], "located")
        self.assertEqual(len(result["regions"]), 2)
        first, second = result["regions"]
        self.assertAlmostEqual(first["x"], 50 / 400, places=4)
        self.assertGreater(second["y"], first["y"])
        self.assertLess(second["width"], first["width"])

    def test_whitespace_and_accents_are_supported_without_word_changes(self):
        self.assertEqual(passage_regions(self.path, 1, "Motion pour Genève")["status"], "located")
        self.assertEqual(passage_regions(self.path, 1, "two lines   continues here.")["status"], "located")
        self.assertEqual(passage_regions(self.path, 1, "Motion pour Geneve")["regions"], [])

    def test_ambiguous_missing_blank_and_out_of_range_stay_unavailable(self):
        for page, quote in [(1, "Repeated phrase"), (1, "Same wrapped phrase"), (1, "Invented value"), (3, "Motion"), (9, "Motion"), (0, "Motion"), (1, "")]:
            with self.subTest(page=page, quote=quote):
                self.assertEqual(passage_regions(self.path, page, quote)["regions"], [])

    def test_rotated_cropped_coordinates_match_display_orientation(self):
        result = passage_regions(self.path, 2, "Rotated passage")
        self.assertEqual(result["status"], "located")
        region = result["regions"][0]
        self.assertGreater(region["x"], .85)
        self.assertLess(region["y"], .1)
        self.assertGreater(region["height"], region["width"])
        for axis, size in [("x", "width"), ("y", "height")]:
            self.assertGreaterEqual(region[axis], 0)
            self.assertLessEqual(region[axis] + region[size], 1.00001)

    def test_effective_review_geometry_and_image_transcription(self):
        app = Workbench(Path(self.temporary.name) / "store", seed_pilot=False)
        identifier = app.store.add(read_pdf(self.path), self.path, {"synthetic": True})
        self.assertEqual(app.evidence(identifier, "title")["regions"], [])
        app.store.review(identifier, ReviewAction(field="title", action="correct", revision=0,
            reviewer="Synthetic geometry QA", value="Genève", page=1, quote="Motion pour Genève", basis="text"))
        result = app.evidence(identifier, "title")
        self.assertEqual(result["status"], "located")
        self.assertEqual(result["revision"], 1)
        app.store.review(identifier, ReviewAction(field="title", action="correct", revision=1,
            reviewer="Synthetic geometry QA", value="Visual transcription", page=1,
            quote="Visual transcription", basis="image", note="Read the page header visually."))
        result = app.evidence(identifier, "title")
        self.assertEqual(result["regions"], [])
        self.assertIn("transcription", result["reason"])
        with self.assertRaises(ReviewError):
            app.evidence(identifier, "not-a-field")
        self.assertEqual(app.store.get(identifier)["revision"], 2)

    @unittest.skipUnless(shutil.which("pdftoppm"), "Page renderer is unavailable")
    def test_page_preview_and_geometry_use_the_same_rotated_crop_box(self):
        app = Workbench(Path(self.temporary.name) / "render-store", seed_pilot=False)
        rendered = app.render_image(self.path, "synthetic", 2)
        image = pymupdf.Pixmap(rendered)
        self.assertAlmostEqual(image.width / image.height, 530 / 360, delta=.002)

    def test_http_endpoint_serves_revision_bound_geometry(self):
        app = Workbench(Path(self.temporary.name) / "http-store", mode="replay")
        identifier = app.store.list()[0]["id"]
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False) as client:
                result = client.get(f"/api/documents/{identifier}/fields/title/evidence")
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["status"], "located")
                self.assertEqual(result.json()["revision"], 0)
                self.assertEqual(client.get(f"/api/documents/{identifier}/fields/unknown/evidence").status_code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
