import unittest
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path
from sqlalchemy import select, func
from paperbot import certificate_registry as registry, documents, db, renderer, saved_certificates
from paperbot.core import Problem
import test_application


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.expected = ["Test Student", "Artificial Intelligence", "TEST-ONLY", "21-09-2026"]
        self.row = [""] * 15
        for col, value in zip(registry.COLUMNS, self.expected):
            self.row[col] = value

    def response(self, data):
        return Mock(json=lambda: data)

    def client(self, rows):
        client = Mock()
        client.get.side_effect = [
            self.response(
                {
                    "sheets": [
                        {
                            "properties": {
                                "sheetId": registry.SHEET_GID,
                                "title": "Artificial Intelligence (paid)",
                            }
                        }
                    ]
                }
            ),
            self.response({"values": rows}),
            self.response({"values": [self.row]}),
        ]
        client.post.return_value = self.response(
            {"updates": {"updatedRange": "'Artificial Intelligence (paid)'!A100:O100"}}
        )
        return client

    def test_append_exact_columns_raw_and_read_back(self):
        client = self.client([])
        result = registry._register(client, self.expected)
        self.assertEqual(result["status"], "registered")
        args = client.post.call_args.kwargs
        self.assertEqual(args["json"]["values"], [self.row])
        written = args["json"]["values"][0]
        self.assertEqual(written[6], "Test Student")
        self.assertEqual(written[1], "")
        self.assertEqual([written[10], written[13], written[14]], self.expected[1:])
        self.assertEqual(args["params"]["valueInputOption"], "RAW")
        self.assertEqual(client.get.call_count, 3)

    def test_idempotent_retry_and_conflicting_or_duplicate_ids(self):
        client = self.client([self.row])
        self.assertEqual(registry._register(client, self.expected)["status"], "existing")
        client.post.assert_not_called()
        changed = self.row.copy()
        changed[6] = "Someone Else"
        for rows in [[changed], [self.row, self.row]]:
            client = self.client(rows)
            with self.assertRaises(Problem):
                registry._register(client, self.expected)
            client.post.assert_not_called()

    def test_uncertain_append_and_failed_readback_are_errors(self):
        client = self.client([])
        client.post.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            registry._register(client, self.expected)
        client = self.client([])
        client.get.side_effect = [
            self.response(
                {"sheets": [{"properties": {"sheetId": registry.SHEET_GID, "title": "Registry"}}]}
            ),
            self.response({"values": []}),
            self.response({"values": []}),
        ]
        with self.assertRaises(Problem):
            registry._register(client, self.expected)

    def test_dates_are_explicit_and_qr_destination_is_exact(self):
        for date in ["21-9-2026", "21 September, 2026", "2026-09-21"]:
            self.assertEqual(registry.issue_date(date), "21-09-2026")
        for date in ["September 2026", "21 September", "2026", "31-02-2026"]:
            with self.assertRaises(Problem):
                registry.issue_date(date)
        self.assertEqual(
            registry.verification_url("ai12fkcgbe726"),
            "https://www.persevex.com/verification?id=ai12fkcgbe726",
        )

    def test_generated_id_format_and_collision_retry(self):
        connection = Mock()
        connection.execute.return_value.first.return_value = None
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        characters = iter("aaaaaaa" "39djf3d")
        with (
            patch(
                "paperbot.certificate_registry.secrets.choice",
                side_effect=lambda _: next(characters),
            ),
            patch("paperbot.certificate_registry._sheet_contains", side_effect=[True, False]),
        ):
            identifier = registry.generate_unique_id(engine)
        self.assertEqual(identifier, "ai1239djf3d26")
        self.assertRegex(identifier, r"^ai12[a-z0-9]{7}26$")
        self.assertEqual(connection.execute.call_count, 2)

    def test_both_renderers_use_new_qr_url(self):
        import qrcode

        original = qrcode.QRCode.add_data
        urls = []

        def capture(obj, data, *args, **kwargs):
            if isinstance(data, str):
                urls.append(data)
            return original(obj, data, *args, **kwargs)

        with patch.object(qrcode.QRCode, "add_data", capture):
            path, _ = renderer.generate_completion_certificate(
                "Test", "21-09-2026", "AI", "TEST-ONLY", False
            )
            Path(path).unlink()
            saved_certificates.generate(
                "saved_ic",
                {
                    "name": "Test",
                    "domain": "AI",
                    "date": "21-09-2026",
                    "cert_id": "TEST-ONLY",
                    "from_date": "1 June 2026",
                    "to_date": "1 August 2026",
                },
            )
        self.assertEqual(urls, [registry.verification_url("TEST-ONLY")] * 2)


class RegistrationGateTests(unittest.TestCase):
    setUp = test_application.AppTests.setUp
    tearDown = test_application.AppTests.tearDown

    def test_registration_failure_rolls_back_draft_and_local_record(self):
        with patch(
            "paperbot.certificate_registry.register", side_effect=Problem("Sheet unavailable", 503)
        ):
            with self.assertRaises(Problem):
                documents.build_draft(
                    self.engine,
                    self.owner,
                    "course_certificate",
                    {
                        "name": "Test",
                        "email": "test@example.com",
                        "domain": "AI",
                        "date": "21-09-2026",
                    },
                )
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(db.drafts)), 0)
            self.assertEqual(c.scalar(select(func.count()).select_from(db.certificates)), 0)

    def test_old_unregistered_certificate_cannot_be_sent(self):
        from sqlalchemy import update
        from paperbot import sending

        form = {
            "name": "Test",
            "email": "test@example.com",
            "domain": "AI",
            "date": "21-09-2026",
        }
        draft = documents.build_draft(self.engine, self.owner, "course_certificate", form)
        form = {key: value for key, value in draft["form"].items() if not key.startswith("_")}
        with self.engine.begin() as c:
            c.execute(update(db.drafts).where(db.drafts.c.id == draft["id"]).values(form=form))
        with patch("paperbot.sending.requests.post") as post:
            with self.assertRaisesRegex(Problem, "Regenerate"):
                sending.send_draft(self.engine, self.owner, draft["id"], draft["sha256"])
            post.assert_not_called()
