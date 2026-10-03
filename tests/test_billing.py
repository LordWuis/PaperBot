import os
import json
import hmac
import hashlib
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, Mock
from sqlalchemy import select, insert, update
import test_application
from paperbot import db, core, billing, documents, bulk


class BillingTests(unittest.TestCase):
    setUp = test_application.AppTests.setUp
    tearDown = test_application.AppTests.tearDown
    post = test_application.AppTests.post

    def account(self, email):
        user = dict(
            id=core.user_id(email),
            email=email,
            name="Test",
            status="inactive",
            expiry=None,
            created=core.now(),
        )
        with self.engine.begin() as c:
            c.execute(insert(db.users).values(**user))
        return user

    def free(self):
        with patch.dict(
            os.environ,
            {"DEVELOPER_EMAIL": "dev@example.com", "FREE_USER_EMAIL": "main@example.com"},
        ):
            db.init_schema(self.engine)
        return self.account("main@example.com")

    def resolved(self, user):
        with self.engine.connect() as c:
            return billing.resolve(c, user)

    def order(self, user, purpose="access", seat_id=None):
        if purpose in ("donation", "support") and self.resolved(user).get("free_role") == "main":
            billing.dismiss_offer(
                self.engine, self.resolved(user), 349 if purpose == "donation" else 1000
            )
            with self.engine.begin() as c:
                c.execute(
                    update(db.support_schedule)
                    .where(db.support_schedule.c.user_id == user["id"])
                    .values(due_at=core.now() - 1)
                )
        with (
            patch.dict(os.environ, {"RAZORPAY_KEY_ID": "fake", "RAZORPAY_KEY_SECRET": "fake"}),
            patch("paperbot.billing.requests.post") as post,
        ):
            link = "plink_" + core.uid()
            post.return_value = Mock(json=lambda: {"id": link, "short_url": "https://rzp.io/test"})
            billing.payment_link(
                self.engine, user, {"purpose": purpose, "seat_id": seat_id}, "https://example.com"
            )
        with self.engine.connect() as c:
            return dict(
                c.execute(select(db.billing_orders).where(db.billing_orders.c.provider_id == link))
                .mappings()
                .one()
            )

    def event(self, order, stamp=None, **changes):
        entity = dict(
            id=order["provider_id"],
            notes={"paperbot_order_id": order["id"]},
            amount=order["amount"],
            amount_paid=order["amount"],
            status="paid",
            currency="INR",
        )
        entity.update(changes)
        raw = json.dumps(
            {
                "event": "payment_link.paid",
                "created_at": stamp or core.now(),
                "payload": {"payment_link": {"entity": entity}},
            }
        ).encode()
        return raw, hmac.new(b"test-webhook-secret", raw, hashlib.sha256).hexdigest()

    def pay(self, order, **changes):
        raw, sig = self.event(order, **changes)
        return billing.webhook(self.engine, raw, sig, "test-webhook-secret")

    def test_free_accounts_global_and_not_first_come(self):
        main = self.free()
        self.assertTrue(core.active(self.resolved(main)))
        self.assertTrue(core.active(self.resolved(self.account("dev@example.com"))))
        for i in range(3):
            self.assertFalse(core.active(self.resolved(self.account(f"new{i}@example.com"))))
        with (
            patch.dict(os.environ, {"FREE_USER_EMAIL": "other@example.com"}),
            self.assertRaises(RuntimeError),
        ):
            db.init_schema(self.engine)
        self.assertTrue(core.active(self.resolved(main)))

    def test_free_access_enforced_on_real_routes_and_sender(self):
        from paperbot import sending

        main = self.free()
        with self.engine.begin() as c:
            c.execute(
                update(db.sessions)
                .where(db.sessions.c.token == core.digest("session"))
                .values(user_id=main["id"])
            )
        session = self.client.get("/api/session")
        self.assertTrue(session.json["active"])
        self.assertFalse(session.json["offer_due"])
        response = self.post(
            "/api/drafts",
            {"kind": "ca_letter", "form": {"name": "Test", "email": "test@example.com"}},
        )
        self.assertEqual(response.status_code, 200)
        draft = response.json
        with patch(
            "paperbot.sending.requests.post", return_value=Mock(json=lambda: {"id": "mock-email"})
        ):
            self.assertEqual(
                sending.send_draft(self.engine, main["id"], draft["id"], draft["sha256"])["state"],
                "submitted",
            )
        self.assertEqual(self.post("/api/support/choice").status_code, 200)
        self.assertFalse(self.client.get("/api/session").json["offer_due"])
        self.assertTrue(self.client.get("/api/session").json["active"])

    def test_pay_first_and_exact_calendar_month(self):
        user = self.account("paid@example.com")
        order = self.order(user)
        self.assertEqual(order["amount"], 100000)
        self.assertFalse(core.active(self.resolved(user)))
        self.pay(order)
        resolved = self.resolved(user)
        self.assertTrue(core.active(resolved))
        self.assertGreater(resolved["access_until"], core.now())
        self.pay(order)
        self.assertEqual(self.resolved(user)["access_until"], resolved["access_until"])
        with patch("paperbot.core.now", return_value=resolved["access_until"]):
            self.assertFalse(core.active(resolved))
        for year, expected in [(2028, 29), (2027, 28)]:
            start = datetime(year, 1, 31, 14, 25, tzinfo=ZoneInfo("Asia/Kolkata"))
            end = datetime.fromtimestamp(
                billing.month_after(int(start.timestamp())), ZoneInfo("Asia/Kolkata")
            )
            self.assertEqual((end.month, end.day, end.hour, end.minute), (2, expected, 14, 25))

    def test_donation_is_optional_and_not_an_access_payment(self):
        main = self.free()
        order = self.order(main, "donation")
        self.assertEqual(order["amount"], 34900)
        self.assertTrue(billing.offer_due(self.engine, self.resolved(main)))
        billing.dismiss_offer(self.engine, self.resolved(main))
        self.assertFalse(billing.offer_due(self.engine, self.resolved(main)))
        self.pay(order)
        self.assertTrue(core.active(self.resolved(main)))
        self.assertIsNone(self.resolved(main)["access_until"])
        self.assertEqual(billing.list_seats(self.engine, self.resolved(main)), [])
        with self.assertRaises(core.Problem):
            self.order(self.account("stranger@example.com"), "donation")

    def test_support_is_optional_and_never_buys_access_or_seats(self):
        main = self.free()
        order = self.order(main, "support")
        self.assertEqual(order["amount"], 100000)
        with self.assertRaises(core.Problem):
            self.pay(order, amount_paid=34900)
        self.pay(order)
        self.assertTrue(core.active(self.resolved(main)))
        self.assertIsNone(self.resolved(main)["access_until"])
        self.assertEqual(billing.list_seats(self.engine, self.resolved(main)), [])
        with self.assertRaises(core.Problem):
            self.order(self.account("stranger@example.com"), "support")

    def test_invite_paid_single_use_and_sponsor_renewal(self):
        main = self.free()
        order = self.order(main, "seat")
        self.pay(order)
        seat = billing.list_seats(self.engine, self.resolved(main))[0]
        invited = self.account("guest@example.com")
        billing.claim(self.engine, invited, seat["token"])
        self.assertTrue(core.active(self.resolved(invited)))
        with self.assertRaises(core.Problem):
            billing.claim(self.engine, self.account("other@example.com"), seat["token"])
        with self.engine.begin() as c:
            c.execute(update(db.seats).values(expires_at=core.now() - 1))
        self.assertFalse(core.active(self.resolved(invited)))
        with self.assertRaises(core.Problem):
            self.order(invited)
        renewal = self.order(main, "seat", seat["id"])
        self.pay(renewal)
        self.assertTrue(core.active(self.resolved(invited)))
        self.assertIsNone(billing.list_seats(self.engine, self.resolved(main))[0]["token"])

    def test_payment_binding_amount_and_signature(self):
        order = self.order(self.account("paid@example.com"))
        for changes in [
            dict(amount=34900),
            dict(amount_paid=99900),
            dict(id="plink_wrong"),
            dict(currency="USD"),
            dict(status="created"),
            dict(amount=True),
            dict(notes={"paperbot_order_id": core.uid()}),
            dict(notes=[]),
            dict(notes={"paperbot_order_id": {}}),
        ]:
            with self.subTest(changes=changes), self.assertRaises(core.Problem):
                self.pay(order, **changes)
        raw, _ = self.event(order)
        with self.assertRaises(core.Problem):
            billing.webhook(self.engine, raw, "bad", "test-webhook-secret")

    def test_payment_link_reused_and_no_charge_while_active(self):
        user = self.account("paid@example.com")
        order = self.order(user)
        with patch("paperbot.billing.requests.post") as post:
            self.assertEqual(
                billing.payment_link(self.engine, user, {}, "https://example.com")["url"],
                order["url"],
            )
            post.assert_not_called()
        self.pay(order)
        with self.assertRaises(core.Problem):
            self.order(user)

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires real Postgres")
    def test_concurrent_webhook_creates_only_one_seat(self):
        from concurrent.futures import ThreadPoolExecutor

        main = self.free()
        order = self.order(main, "seat")
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.pay(order), range(8)))
        self.assertEqual(len(billing.list_seats(self.engine, self.resolved(main))), 1)

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Requires real Postgres")
    def test_concurrent_invitation_claim_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor

        main = self.free()
        order = self.order(main, "seat")
        self.pay(order)
        token = billing.list_seats(self.engine, self.resolved(main))[0]["token"]
        people = [self.account(f"race{i}@example.com") for i in range(4)]

        def attempt(user):
            try:
                billing.claim(self.engine, user, token)
                return True
            except core.Problem:
                return False

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(attempt, people)), 1)

    def test_stipend_single_and_bulk_preserve_choice(self):
        import io, fitz

        with self.engine.begin() as c:
            c.execute(
                insert(db.students).values(
                    id=core.uid(),
                    name_key="test intern",
                    data={
                        "name": "Test Intern",
                        "email": "intern@example.com",
                        "month": "November",
                        "domain": "Logistics and Supply Chain Management",
                    },
                )
            )
        draft = documents.build_draft(
            self.engine,
            self.owner,
            "internship_letter",
            {"name": "Test Intern", "internship_variant": "with_stipend"},
        )
        with self.engine.connect() as c:
            pdf = c.execute(
                select(db.drafts.c.pdf).where(db.drafts.c.id == draft["id"])
            ).scalar_one()
        with fitz.open(stream=pdf, filetype="pdf") as doc:
            text = doc[0].get_text()
            self.assertNotIn("{{", text)
            self.assertIn("25,000", text)
            self.assertIn("Test Intern", text)
            self.assertIn("10-02-", text)
            self.assertIn("Logistics and Supply Chain Management", text)
        response = self.client.post(
            "/api/jobs",
            data={
                "kind": "internship_letter",
                "internship_variant": "with_stipend",
                "file": (io.BytesIO(b"name\nTest Intern\n"), "list.csv"),
            },
            headers={"X-PaperBot": "1"},
        )
        self.assertEqual(response.status_code, 200)
        job = bulk.step(self.engine, self.owner, response.json["id"])
        self.assertEqual(job["rows"][0]["form"]["internship_variant"], "with_stipend")
        self.assertEqual(
            documents.clean_form("internship_letter", {"name": "Test Intern"})[
                "internship_variant"
            ],
            "without_stipend",
        )
        with self.assertRaises(core.Problem):
            documents.clean_form(
                "internship_letter", {"name": "Test", "internship_variant": "forged"}
            )


class SupportScheduleTests(unittest.TestCase):
    setUp = BillingTests.setUp
    tearDown = BillingTests.tearDown
    account = BillingTests.account
    free = BillingTests.free
    resolved = BillingTests.resolved
    order = BillingTests.order
    pay = BillingTests.pay
    event = BillingTests.event

    def test_two_day_delay_and_next_month_fifth(self):
        user = self.resolved(self.free())
        zone = ZoneInfo("Asia/Kolkata")
        first = int(datetime(2026, 9, 22, 10, tzinfo=zone).timestamp())
        with patch("paperbot.billing.now", return_value=first):
            self.assertFalse(billing.offer_due(self.engine, user))
        with patch("paperbot.billing.now", return_value=first + 86400):
            self.assertFalse(billing.offer_due(self.engine, user))
        with patch("paperbot.billing.now", return_value=first + 2 * 86400):
            self.assertTrue(billing.offer_due(self.engine, user))
            choice = billing.dismiss_offer(self.engine, user, 349)
            self.assertEqual(choice["phase"], "scheduled")
            due = int(datetime(2026, 10, 5, tzinfo=zone).timestamp())
            self.assertEqual(choice["due_at"], due)
            with self.assertRaises(core.Problem), patch("paperbot.billing.requests.post") as post:
                billing.payment_link(
                    self.engine, user, {"purpose": "donation"}, "https://example.com"
                )
            post.assert_not_called()
        with patch("paperbot.billing.now", return_value=due - 1):
            self.assertFalse(billing.offer_due(self.engine, user))
        with patch("paperbot.billing.now", return_value=due):
            self.assertEqual(billing.support_status(self.engine, user)["phase"], "due")
            self.assertTrue(core.active(self.resolved(user)))
            billing.dismiss_offer(self.engine, user, 0)
            self.assertFalse(billing.offer_due(self.engine, user))

    def test_december_rollover_and_paid_reminder_stops(self):
        user = self.resolved(self.free())
        with patch(
            "paperbot.billing.now",
            return_value=int(datetime(2026, 12, 31, tzinfo=ZoneInfo("Asia/Kolkata")).timestamp()),
        ):
            choice = billing.dismiss_offer(self.engine, user, 1000)
            self.assertEqual(
                datetime.fromtimestamp(choice["due_at"], ZoneInfo("Asia/Kolkata")).strftime(
                    "%Y-%m-%d"
                ),
                "2027-01-05",
            )
        with patch("paperbot.billing.now", return_value=choice["due_at"]):
            order = self.order(user, "support")
            self.pay(order, stamp=choice["due_at"])
            self.assertEqual(billing.support_status(self.engine, user)["phase"], "thanks")
            self.assertFalse(billing.offer_due(self.engine, user))
