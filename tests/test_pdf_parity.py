"""Regression fixtures captured from the original renderer, all domain aliases/pages."""

import hashlib
import json
import os
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import fitz
from paperbot import renderer

ROOT = Path(__file__).resolve().parents[1]


class Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 18, 12)


class PDFParityTests(unittest.TestCase):
    def test_isolated_worker_preserves_all_five_document_types(self):
        from paperbot.pdf_runtime import generate
        from paperbot.documents import render_document

        cases = [
            ("ca_letter", {"name": "Test Candidate"}),
            (
                "internship_letter",
                {"name": "Test Candidate", "month": "November", "domain": "Web Development"},
            ),
            ("offer_letter", {"name": "Test Candidate", "training_from": "31-01-2026"}),
            (
                "course_certificate",
                {
                    "name": "Test Candidate",
                    "date": "18 September, 2026",
                    "domain": "Web Development",
                    "cert_id": "test-cert-123",
                },
            ),
            ("ca_certificate", {"name": "Test Candidate", "date": "18 September, 2026"}),
        ]
        for kind, data in cases:
            with self.subTest(kind=kind):
                isolated = generate(kind, data)
                path, _ = render_document(kind, data)
                try:
                    with (
                        fitz.open(path) as reference,
                        fitz.open(stream=isolated, filetype="pdf") as actual,
                    ):
                        self.assertEqual(len(reference), len(actual))
                        for left, right in zip(reference, actual):
                            self.assertEqual(
                                left.get_pixmap(dpi=72).samples, right.get_pixmap(dpi=72).samples
                            )
                finally:
                    Path(path).unlink(missing_ok=True)

    def test_simultaneous_workers_keep_names_isolated(self):
        from concurrent.futures import ThreadPoolExecutor
        from paperbot.pdf_runtime import generate

        names = ["Concurrent Alice", "Concurrent Bob", "Concurrent Carol", "Concurrent Dave"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda name: generate("ca_letter", {"name": name}), names))
        for name, pdf in zip(names, results):
            with fitz.open(stream=pdf, filetype="pdf") as doc:
                text = doc[0].get_text()
                self.assertIn(name, text)
                for other in names:
                    if other != name:
                        self.assertNotIn(other, text)

    def test_all_template_and_font_bytes_unchanged(self):
        manifest = json.loads((ROOT / "tests/asset-sha256.json").read_text())
        for name, expected in manifest.items():
            with self.subTest(asset=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_all_original_document_pixels_and_text(self):
        baseline = json.loads((ROOT / "tests/legacy-render-baselines.json").read_text())
        for case in baseline["cases"]:
            with (
                self.subTest(case=case["name"]),
                patch.object(renderer, "datetime", Frozen),
                # Compare historical artwork using its original QR payload.
                # Production QR destination is independently tested in registry tests.
                patch(
                    "paperbot.certificate_registry.verification_url",
                    side_effect=lambda identifier: "https://persevex.com/verification?id="
                    + identifier,
                ),
            ):
                path, _ = getattr(renderer, case["fn"])(*case["args"], create_preview=False)
                try:
                    with fitz.open(path) as doc:
                        self.assertEqual(len(doc), len(case["pages"]))
                        for page, expected in zip(doc, case["pages"]):
                            self.assertEqual(page.rect.width, expected["width"])
                            self.assertEqual(page.rect.height, expected["height"])
                            self.assertEqual(page.get_text(), expected["text"])
                            self.assertEqual(
                                hashlib.sha256(page.get_pixmap(dpi=72).samples).hexdigest(),
                                expected["pixels_sha256"],
                            )
                finally:
                    Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
