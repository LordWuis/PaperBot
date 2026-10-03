import os
import tempfile
import unittest
import hashlib
import hmac
import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch, Mock
from sqlalchemy import select, insert, update

os.environ["APP_SECRET"] = "test-secret-not-for-deployment-123456789"
os.environ["RESEND_API_KEY"] = "re_test_fake"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["ONBOARDING_SHEET_ID"] = ""
from app import create_app
from paperbot import db, core, auth, documents, sending, bulk


class AppTests(unittest.TestCase):
    def setUp(self):
        registry = patch("paperbot.certificate_registry.register", return_value={"status": "test"})
        registry.start()
        self.addCleanup(registry.stop)
        self.generated_ids = iter(f"ai12{i:07d}26" for i in range(10000))
        identifier = patch(
            "paperbot.certificate_registry.generate_unique_id",
            side_effect=lambda engine: next(self.generated_ids),
        )
        identifier.start()
        self.addCleanup(identifier.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.pg_schema = None
        if os.getenv("TEST_DATABASE_URL"):
            from sqlalchemy import text

            self.pg_schema = "test_" + core.uid().replace("-", "")
            base = db.make_engine(os.environ["TEST_DATABASE_URL"])
            with base.begin() as c:
                c.execute(text("CREATE SCHEMA " + self.pg_schema))
            self.engine = base.execution_options(schema_translate_map={None: self.pg_schema})
        else:
            self.engine = db.make_engine("sqlite:///" + str(Path(self.tmp.name) / "test.db"))
        db.init_schema(self.engine)
        self.app = create_app(self.engine)
        self.app.testing = True
        self.client = self.app.test_client()
        self.owner = core.user_id("admin@example.com")
        with self.engine.begin() as c:
            c.execute(
                insert(db.users).values(
                    id=self.owner,
                    name="Admin",
                    email="admin@example.com",
                    status="active",
                    expiry="2099-01-01",
                    created=core.now(),
                )
            )
            c.execute(
                insert(db.sessions).values(
                    token=core.digest("session"), user_id=self.owner, expires=core.now() + 3600
                )
            )
        self.client.set_cookie("pb_session", "session")

    def tearDown(self):
        if self.pg_schema:
            from sqlalchemy import text

            with self.engine.begin() as c:
                c.execute(text("DROP SCHEMA " + self.pg_schema + " CASCADE"))
        self.engine.dispose()
        self.tmp.cleanup()

    def post(self, url, data=None):
        return self.client.post(url, json=data or {}, headers={"X-PaperBot": "1"})

    def draft(self, kind="ca_letter", form=None):
        return documents.build_draft(
            self.engine,
            self.owner,
            kind,
            form or {"name": "Test Candidate", "email": "candidate@example.com"},
        )

    def test_neon_integration_url_precedes_manual_placeholder(self):
        with patch.dict(
            os.environ,
            {
                "PAPERBOT_DATABASE_URL": "postgresql://example:password@localhost/paperbot",
                "DATABASE_URL": "invalid-placeholder",
            },
        ):
            engine = db.make_engine()
            self.assertEqual(engine.url.drivername, "postgresql+psycopg")
            self.assertEqual(engine.url.database, "paperbot")
            engine.dispose()

    def test_health_without_configuration(self):
        self.assertEqual(create_app().test_client().get("/api/health").status_code, 200)

    def test_anonymous_rejected(self):
        self.client.delete_cookie("pb_session")
        self.assertEqual(self.client.get("/api/drafts").status_code, 401)

    def test_csrf_header_and_origin(self):
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/auth/logout",
                headers={"X-PaperBot": "1", "Origin": "https://attacker.example"},
            ).status_code,
            403,
        )

    def test_json_array_rejected(self):
        r = self.client.post("/api/drafts", json=[], headers={"X-PaperBot": "1"})
        self.assertEqual(r.status_code, 400)

    def test_invalid_payment_and_unrelated_events(self):
        for raw, sig, expected in [
            (b"{}", "bad", 401),
            (b"[]", hmac.new(b"test-webhook-secret", b"[]", hashlib.sha256).hexdigest(), 400),
        ]:
            self.assertEqual(
                self.client.post(
                    "/webhooks/razorpay", data=raw, headers={"X-Razorpay-Signature": sig}
                ).status_code,
                expected,
            )
        event = json.dumps({"event": "payment.authorized"}).encode()
        r = self.client.post(
            "/webhooks/razorpay",
            data=event,
            headers={
                "X-Razorpay-Signature": hmac.new(
                    b"test-webhook-secret", event, hashlib.sha256
                ).hexdigest()
            },
        )
        self.assertTrue(r.json["ignored"])

    def test_fresh_revocation_blocks_generation_send_and_step(self):
        d = self.draft()
        with self.engine.begin() as c:
            c.execute(update(db.users).values(status="inactive"))
        for url, data in [
            ("/api/drafts", {"kind": "ca_letter", "form": {}}),
            ("/api/drafts/" + d["id"] + "/send", {"sha256": d["sha256"]}),
            ("/api/jobs/test/step", {}),
        ]:
            self.assertEqual(self.post(url, data).status_code, 402)

    def test_other_owner_cannot_read_or_send(self):
        d = self.draft()
        with self.engine.begin() as c:
            c.execute(update(db.drafts).values(owner=99))
        for suffix in ("", "/pdf", "/preview/0"):
            self.assertEqual(self.client.get("/api/drafts/" + d["id"] + suffix).status_code, 404)
        self.assertEqual(
            self.post("/api/drafts/" + d["id"] + "/send", {"sha256": d["sha256"]}).status_code, 404
        )

    def test_preview_download_all_pages_and_immutable_pdf(self):
        d = self.draft(
            "offer_letter",
            {
                "name": "Test Candidate",
                "email": "candidate@example.com",
                "training_from": "31-01-2026",
            },
        )
        response = self.client.get("/api/drafts/" + d["id"] + "/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(hashlib.sha256(response.data).hexdigest(), d["sha256"])
        self.assertEqual(
            self.client.get("/api/drafts/" + d["id"] + "/preview/0").mimetype, "image/png"
        )
        self.assertEqual(self.client.get("/api/drafts/" + d["id"] + "/preview/99").status_code, 404)

    @patch("paperbot.sending.requests.post")
    def test_send_requires_exact_approval_and_is_idempotent(self, post):
        post.return_value = Mock(json=lambda: {"id": "email_123"})
        d = self.draft()
        with self.assertRaises(core.Problem):
            sending.send_draft(self.engine, self.owner, d["id"], "wrong")
        self.assertEqual(
            sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])["state"], "submitted"
        )
        self.assertEqual(
            sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])["provider_id"],
            "email_123",
        )
        self.assertEqual(post.call_count, 1)
        self.assertEqual(
            post.call_args.kwargs["headers"]["Idempotency-Key"], "paperbot-draft-" + d["id"]
        )
        import base64

        self.assertEqual(
            hashlib.sha256(
                base64.b64decode(post.call_args.kwargs["json"]["attachments"][0]["content"])
            ).hexdigest(),
            d["sha256"],
        )

    @patch("paperbot.sending.rate_limit")
    @patch("paperbot.sending.requests.post")
    def test_uncertain_send_retry_same_payload_and_key(self, post, limit):
        post.side_effect = [requests_timeout(), Mock(json=lambda: {"id": "email_retry"})]
        d = self.draft()
        with self.assertRaises(core.Problem):
            sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])
        sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])
        self.assertEqual(post.call_args_list[0], post.call_args_list[1])

    @patch("paperbot.sending.requests.post")
    def test_expired_retry_window_and_lease_block_provider(self, post):
        d = self.draft()
        with self.engine.begin() as c:
            c.execute(update(db.drafts).values(first_attempt=core.now() - 24 * 3600, state="retry"))
        with self.assertRaises(core.Problem):
            sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])
        with self.engine.begin() as c:
            c.execute(update(db.drafts).values(first_attempt=None, lease=core.now() + 60))
        with self.assertRaises(core.Problem):
            sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])
        post.assert_not_called()

    def test_otp_attempts_are_persisted_and_bounded(self):
        with self.engine.begin() as c:
            c.execute(
                insert(db.otps).values(
                    id=core.digest("challenge"),
                    email="new@example.com",
                    name="New",
                    digest=core.keyed("challenge:123456"),
                    expires=core.now() + 600,
                    attempts=0,
                )
            )
        for i in range(5):
            with self.assertRaises(core.Problem):
                auth.verify_otp(self.engine, "challenge", "000000")
        with self.assertRaises(core.Problem):
            auth.verify_otp(self.engine, "challenge", "123456")
        with self.engine.connect() as c:
            self.assertEqual(c.execute(select(db.otps.c.attempts)).scalar_one(), 5)

    def test_otp_single_use_and_new_accounts_inactive(self):
        with self.engine.begin() as c:
            c.execute(
                insert(db.otps).values(
                    id=core.digest("challenge"),
                    email="new@example.com",
                    name="New",
                    digest=core.keyed("challenge:123456"),
                    expires=core.now() + 600,
                    attempts=0,
                )
            )
        token = auth.verify_otp(self.engine, "challenge", "123456")
        self.assertGreater(len(token), 40)
        with self.assertRaises(core.Problem):
            auth.verify_otp(self.engine, "challenge", "123456")
        with self.engine.connect() as c:
            self.assertEqual(
                c.execute(
                    select(db.users.c.status).where(db.users.c.email == "new@example.com")
                ).scalar_one(),
                "inactive",
            )

    def test_rate_limit_shared_between_app_instances(self):
        core.rate_limit(self.engine, "test", 1, 600)
        with self.assertRaises(core.Problem):
            core.rate_limit(self.engine, "test", 1, 600)

    def test_csv_aliases_bom_and_validation(self):
        records = documents.parse_csv(
            "ca_letter", b"\xef\xbb\xbfCandidate Name,Email Address\nAlice,alice@example.com\n"
        )
        self.assertEqual(records, [{"name": "Alice", "email": "alice@example.com"}])
        for raw in (
            b"name\nAlice\n",
            b"name,email\nAlice,broken\n",
            b"name,email\nAlice,a@b.com,extra\n",
            b"name,email,Email Address\nA,a@b.com,b@c.com\n",
        ):
            with self.assertRaises(core.Problem):
                documents.parse_csv("ca_letter", raw)

    def test_onboarding_duplicates_fail_closed(self):
        with self.engine.begin() as c:
            for email in ("a@example.com", "b@example.com"):
                c.execute(
                    insert(db.students).values(
                        id=core.uid(),
                        name_key="alice",
                        data={
                            "name": "Alice",
                            "email": email,
                            "month": "January",
                            "domain": "Web Development",
                        },
                    )
                )
        with self.assertRaises(core.Problem):
            documents.find_student(self.engine, "Alice")

    def test_certificate_registration_conflicts_and_public_privacy(self):
        form = {
            "name": "Alice",
            "email": "a@example.com",
            "domain": "Web Development",
            "date": "18 September, 2026",
        }
        first = self.draft("course_certificate", form)
        second = self.draft("course_certificate", form)
        self.assertRegex(first["form"]["cert_id"], r"^ai12[a-z0-9]{7}26$")
        self.assertNotEqual(first["form"]["cert_id"], second["form"]["cert_id"])
        result = self.client.get("/api/verification/" + first["form"]["cert_id"])
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("email", result.json)

    def test_html_inputs_escaped_in_email(self):
        d = self.draft(form={"name": "<b>Alice</b>", "email": "a@example.com"})
        self.assertIn("&lt;b&gt;", d["email"]["html"])

    def test_bad_date_and_domain_rejected(self):
        with self.assertRaises(ValueError):
            documents.render_document(
                "offer_letter", {"name": "Test", "training_from": "31-02-2026"}
            )
        with self.assertRaises(ValueError):
            documents.render_document(
                "internship_letter", {"name": "Test", "month": "January", "domain": "Unknown"}
            )

    @patch("paperbot.sending.requests.post")
    def test_bulk_prepare_review_approve_send_and_resume(self, post):
        post.return_value = Mock(json=lambda: {"id": "bulk_email"})
        job_id = bulk.create_job(
            self.engine, self.owner, "ca_letter", [{"name": "Alice", "email": "a@example.com"}]
        )
        job = bulk.step(self.engine, self.owner, job_id)
        self.assertEqual(job["state"], "review")
        post.assert_not_called()
        # GET must have no side effects.
        self.client.get("/api/jobs/" + job_id)
        post.assert_not_called()
        self.assertEqual(
            self.post("/api/jobs/" + job_id + "/approve", {"confirm": True}).status_code, 200
        )
        # Another application instance reads durable progress.
        other = create_app(self.engine).test_client()
        other.set_cookie("pb_session", "session")
        result = other.post("/api/jobs/" + job_id + "/step", headers={"X-PaperBot": "1"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["submitted"], 1)
        self.assertEqual(result.json["state"], "completed")
        self.assertEqual(post.call_count, 1)

    def test_bulk_cannot_access_other_owner(self):
        job = bulk.create_job(
            self.engine, 55, "ca_letter", [{"name": "Alice", "email": "a@example.com"}]
        )
        self.assertEqual(self.client.get("/api/jobs/" + job).status_code, 404)
        self.assertEqual(
            self.post("/api/jobs/" + job + "/approve", {"confirm": True}).status_code, 404
        )

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires real Postgres")
    @patch("paperbot.sending.rate_limit")
    @patch("paperbot.sending.requests.post")
    def test_concurrent_sends_only_one_provider_call(self, post, limit):
        from concurrent.futures import ThreadPoolExecutor
        import threading

        d = self.draft()
        entered = threading.Event()
        release = threading.Event()

        def provider(*args, **kwargs):
            entered.set()
            release.wait(5)
            return Mock(json=lambda: {"id": "concurrent_email"})

        post.side_effect = provider
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(sending.send_draft, self.engine, self.owner, d["id"], d["sha256"])
            self.assertTrue(entered.wait(5))
            try:
                with self.assertRaises(core.Problem):
                    sending.send_draft(self.engine, self.owner, d["id"], d["sha256"])
            finally:
                release.set()
            self.assertEqual(first.result()["state"], "submitted")
        self.assertEqual(post.call_count, 1)

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires real Postgres")
    def test_concurrent_otp_consumption_is_single_use(self):
        from concurrent.futures import ThreadPoolExecutor

        with self.engine.begin() as c:
            c.execute(
                insert(db.otps).values(
                    id=core.digest("race"),
                    email="race@example.com",
                    name="Race",
                    digest=core.keyed("race:123456"),
                    expires=core.now() + 600,
                    attempts=0,
                )
            )

        def verify(_):
            try:
                return auth.verify_otp(self.engine, "race", "123456")
            except core.Problem:
                return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(verify, range(4)))
        self.assertEqual(sum(bool(r) for r in results), 1)

    def test_no_admin_routes(self):
        self.assertEqual(self.client.get("/api/admin").status_code, 404)
        self.assertEqual(self.post("/api/admin/users/123", {}).status_code, 404)
        self.assertEqual(self.post("/api/admin/import/users", {}).status_code, 404)


def requests_timeout():
    import requests

    return requests.Timeout("synthetic timeout")


if __name__ == "__main__":
    unittest.main()
