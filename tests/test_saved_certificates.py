import unittest
import fitz
from sqlalchemy import select
from paperbot import saved_certificates as saved, documents, db
from paperbot.core import Problem
import test_application


class SavedCertificateTests(unittest.TestCase):
    setUp = test_application.AppTests.setUp
    tearDown = test_application.AppTests.tearDown

    def form(self, kind):
        values = {
            "name": "Test Student",
            "email": "test@example.com",
            "domain": "Web Development",
            "date": "21 September 2026",
            "from_date": "1 June 2026",
            "to_date": "31 August 2026",
            "title": "Mr.",
            "usn": "TEST123",
            "course": "B.Tech",
            "college_name": "Example College",
            "university_name": "Example University",
            "his_her": "his",
            "he_she": "he",
            "capital_he_she": "He",
            "him_her": "him",
            "internship_hours": "120",
            "mentor_name": "Test Mentor",
            "registration_no": "REG123",
            "department": "Engineering",
            "intern_designation": "Developer",
            "project_name": "Student Portal",
        }
        return {f["name"]: values[f["name"]] for f in saved.schemas()[kind]["fields"]}

    def test_all_templates_generate_and_register_without_sending(self):
        from pathlib import Path

        output = Path("output/certificate-qa")
        output.mkdir(parents=True, exist_ok=True)
        for kind in saved.schemas():
            with self.subTest(kind=kind):
                form = self.form(kind)
                draft = documents.build_draft(self.engine, self.owner, kind, form)
                identifier = draft["form"]["cert_id"]
                with self.engine.connect() as c:
                    row = (
                        c.execute(select(db.drafts).where(db.drafts.c.id == draft["id"]))
                        .mappings()
                        .one()
                    )
                    cert = (
                        c.execute(select(db.certificates).where(db.certificates.c.id == identifier))
                        .mappings()
                        .one()
                    )
                self.assertEqual(cert["data"]["template"], kind)
                self.assertEqual(row["state"], "ready")
                with fitz.open(stream=row["pdf"], filetype="pdf") as pdf:
                    self.assertEqual(len(pdf), 1)
                    text = pdf[0].get_text()
                    self.assertIn("Test Student", text)
                    self.assertNotIn("{", text)
                    self.assertEqual(len(pdf[0].get_images()), 2)
                    pdf[0].get_pixmap(matrix=fitz.Matrix(1, 1)).save(output / (kind + ".png"))
                csv = ",".join(form) + "\n" + ",".join(form.values()) + "\n"
                self.assertEqual(documents.parse_csv(kind, csv.encode()), [form])
                self.assertRegex(identifier, r"^ai12[a-z0-9]{7}26$")

    def test_long_details_fail_without_clipping(self):
        form = self.form("saved_adv-ic-temp")
        form["college_name"] = "Long college name " * 30
        with self.assertRaises(ValueError):
            saved.generate("saved_adv-ic-temp", form)
