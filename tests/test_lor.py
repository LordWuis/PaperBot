import unittest
from pathlib import Path

import fitz

from paperbot import documents, db
import test_application


class LORTests(unittest.TestCase):
    setUp = test_application.AppTests.setUp
    tearDown = test_application.AppTests.tearDown

    def form(self, pronouns="she"):
        return {
            "name": "Neha R Girachh",
            "email": "neha@example.com",
            "domain": "Finance",
            "from_date": "25 June 2026",
            "to_date": "31 July 2026",
            "pronouns": pronouns,
        }

    def test_lor_uses_supplied_template_and_consistent_candidate(self):
        draft = documents.build_draft(self.engine, self.owner, "lor", self.form())
        with self.engine.connect() as connection:
            row = (
                connection.execute(db.drafts.select().where(db.drafts.c.id == draft["id"]))
                .mappings()
                .one()
            )
        with fitz.open(stream=row["pdf"], filetype="pdf") as result:
            self.assertEqual(len(result), 1)
            text = result[0].get_text()
            self.assertIn("Ms. Neha R Girachh", text)
            self.assertIn("Intern - Finance", text)
            self.assertIn("25 June 2026 to 31 July 2026", text)
            self.assertNotIn("Govind Pradip Deshmukh", text)
            self.assertIn("her graduate application", text)
            self.assertEqual(tuple(result[0].rect), (0.0, 0.0, 595.5, 842.25))

    def test_lor_pronouns_and_bulk_csv(self):
        for value, phrase in (
            ("he", "his graduate"),
            ("she", "her graduate"),
            ("they", "their graduate"),
        ):
            with self.subTest(pronouns=value):
                path, _ = documents.render_document("lor", self.form(value))
                try:
                    with fitz.open(path) as pdf:
                        self.assertIn(phrase, pdf[0].get_text())
                finally:
                    Path(path).unlink(missing_ok=True)
        form = self.form()
        csv = ",".join(form) + "\n" + ",".join(form.values()) + "\n"
        self.assertEqual(documents.parse_csv("lor", csv.encode()), [form])
