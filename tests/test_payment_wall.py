import hashlib
import hmac
import json
import os
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from flask import Flask, session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database_handler
import razorpay_handler
import web_auth


class SubscriptionTimingTests(unittest.TestCase):
    def test_access_period_is_30_calendar_days_inclusive(self):
        self.assertEqual(
            database_handler.get_subscription_access_through(date(2026, 7, 23)),
            "2026-08-21",
        )

    def test_access_period_handles_year_and_leap_month_boundaries(self):
        self.assertEqual(
            database_handler.get_subscription_access_through(date(2027, 12, 20)),
            "2028-01-18",
        )
        self.assertEqual(
            database_handler.get_subscription_access_through(date(2028, 2, 1)),
            "2028-03-01",
        )

    def test_access_is_valid_through_expiry_date_then_fails_closed(self):
        status = {"status": "active", "expiry_date": "2026-08-21"}
        self.assertEqual(
            database_handler._apply_local_expiry(status, date(2026, 8, 21))["status"],
            "active",
        )
        self.assertEqual(
            database_handler._apply_local_expiry(status, date(2026, 8, 22))["status"],
            "expired",
        )

    def test_invalid_active_expiry_fails_closed(self):
        status = database_handler._apply_local_expiry(
            {"status": "active", "expiry_date": "not-a-date"},
            date(2026, 7, 23),
        )
        self.assertEqual(status["status"], "error")

    @patch("database_handler._fetch_from_sheet")
    def test_activation_sends_deterministic_access_through_date(self, fetch):
        fetch.return_value = {"status": "success"}
        self.assertTrue(
            database_handler.update_user_subscription(123, activation_date=date(2026, 7, 23))
        )
        self.assertEqual(fetch.call_args.args[0]["expiry_date"], "2026-08-21")

    @patch("database_handler.update_user_subscription")
    @patch("database_handler.get_user_status")
    @patch("database_handler.clear_user_cache")
    def test_late_or_duplicate_event_cannot_shorten_access(
        self,
        _clear_cache,
        get_status,
        update,
    ):
        get_status.return_value = {
            "status": "active",
            "expiry_date": "2026-09-15",
        }

        result = database_handler.activate_paid_subscription(
            123,
            activation_date=date(2026, 7, 23),
        )

        self.assertTrue(result)
        update.assert_not_called()


class PaymentLinkTests(unittest.TestCase):
    @patch("razorpay_handler.requests.post")
    @patch("razorpay_handler.time.time", return_value=1_700_000_000)
    def test_link_has_exact_price_identity_expiry_and_callback(self, _time, post):
        response = Mock()
        response.json.return_value = {
            "id": "plink_test",
            "short_url": "https://rzp.io/test",
        }
        post.return_value = response

        env = {
            "RAZORPAY_KEY_ID": "key_test",
            "RAZORPAY_KEY_SECRET": "secret_test",
            "APP_BASE_URL": "https://paperbot.example/",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(
                razorpay_handler.create_payment_link(456),
                "https://rzp.io/test",
            )

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 99900)
        self.assertEqual(payload["currency"], "INR")
        self.assertFalse(payload["accept_partial"])
        self.assertEqual(payload["expire_by"], 1_700_086_400)
        self.assertEqual(payload["notes"]["paperbot_user_id"], "456")
        self.assertEqual(payload["callback_url"], "https://paperbot.example/pay")
        self.assertEqual(payload["callback_method"], "get")

    def test_missing_credentials_returns_actionable_failure(self):
        with patch.dict(
            os.environ,
            {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""},
            clear=False,
        ):
            self.assertIsNone(razorpay_handler.create_payment_link(456))
        self.assertIn("credentials are missing", razorpay_handler.get_last_error())


class PaymentWallWebTests(unittest.TestCase):
    def setUp(self):
        app = Flask(
            __name__,
            template_folder=str(ROOT / "web_templates"),
            static_folder=str(ROOT / "static"),
        )
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        web_auth.register_auth_routes(app)

        @app.route("/app")
        def web_dashboard():
            return "dashboard"

        self.app = app
        self.client = app.test_client()

    def login(self, user_id=123):
        with self.client.session_transaction() as client_session:
            client_session["web_user"] = {
                "id": user_id,
                "name": "Test User",
                "email": "test@example.com",
            }

    @patch("web_auth.database_handler.get_user_status")
    @patch("razorpay_handler.create_payment_link")
    def test_expired_user_sees_paywall_and_link_is_reused(self, create_link, get_status):
        self.login()
        get_status.return_value = {"status": "expired", "expiry_date": "2026-07-01"}
        create_link.return_value = "https://rzp.io/test"

        first = self.client.get("/pay")
        second = self.client.get("/pay")

        self.assertEqual(first.status_code, 200)
        self.assertIn(b"30 calendar days", first.data)
        self.assertIn(b"https://rzp.io/test", first.data)
        self.assertEqual(second.status_code, 200)
        create_link.assert_called_once_with(123)

    @patch("web_auth.database_handler.get_user_status")
    @patch("razorpay_handler.create_payment_link")
    def test_active_user_cannot_create_another_payment_link(self, create_link, get_status):
        self.login()
        get_status.return_value = {"status": "active", "expiry_date": "2026-08-21"}

        response = self.client.get("/pay")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/app"))
        create_link.assert_not_called()

    @patch("web_auth.database_handler.get_user_status")
    @patch("web_auth.database_handler.clear_user_cache")
    def test_check_status_unlocks_only_active_user(self, clear_cache, get_status):
        self.login()
        get_status.return_value = {"status": "active", "expiry_date": "2026-08-21"}

        response = self.client.post("/pay/check")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        clear_cache.assert_called_once_with(123)

    @patch("web_auth.database_handler.get_user_status")
    @patch("web_auth.database_handler.clear_user_cache")
    def test_check_status_keeps_expired_user_blocked(self, _clear_cache, get_status):
        self.login()
        get_status.return_value = {"status": "expired", "expiry_date": "2026-07-01"}

        response = self.client.post("/pay/check")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["ok"])

    @patch("web_auth.database_handler.get_user_status")
    @patch("razorpay_handler.create_payment_link")
    def test_backend_error_never_offers_a_charge(self, create_link, get_status):
        self.login()
        get_status.return_value = {"status": "error", "message": "Status service unavailable."}

        response = self.client.get("/pay")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Payment unavailable", response.data)
        self.assertIn(b"Status service unavailable.", response.data)
        create_link.assert_not_called()

    @patch("web_auth.database_handler.update_user_subscription")
    @patch("web_auth.database_handler.get_user_status")
    @patch("web_auth.database_handler.clear_user_cache")
    @patch("web_auth.database_handler.register_new_user")
    def test_new_web_account_does_not_bypass_payment(
        self,
        register,
        _clear_cache,
        get_status,
        update_subscription,
    ):
        register.return_value = {"status": "success"}
        get_status.side_effect = [
            {"status": "not_found"},
            {"status": "expired", "expiry_date": ""},
        ]
        with self.app.test_request_context("/"):
            session["pending_login"] = {
                "name": "New User",
                "email": "new@example.com",
                "otp_hash": web_auth._hash_otp("123456"),
                "expires_at": 4_000_000_000,
            }
            result = web_auth.complete_login("123456")

        self.assertTrue(result["ok"])
        self.assertFalse(result["active"])
        update_subscription.assert_not_called()


class RazorpayWebhookTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        web_auth.register_auth_routes(app)

        @app.route("/app")
        def web_dashboard():
            return "dashboard"

        self.client = app.test_client()
        self.secret = "webhook-test-secret"
        paid_at = datetime(2026, 7, 23, 12, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.event = {
            "event": "payment_link.paid",
            "created_at": int(paid_at.timestamp()),
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test",
                        "status": "paid",
                        "amount": 99900,
                        "amount_paid": 99900,
                        "currency": "INR",
                        "notes": {"paperbot_user_id": "789"},
                    }
                }
            },
        }

    def post_event(self, event=None, signature=None):
        raw = json.dumps(event or self.event, separators=(",", ":")).encode("utf-8")
        if signature is None:
            signature = hmac.new(
                self.secret.encode("utf-8"),
                raw,
                hashlib.sha256,
            ).hexdigest()
        with patch.dict(
            os.environ,
            {"RAZORPAY_WEBHOOK_SECRET": self.secret},
            clear=False,
        ):
            return self.client.post(
                "/webhooks/razorpay",
                data=raw,
                content_type="application/json",
                headers={"X-Razorpay-Signature": signature},
            )

    @patch("web_auth.database_handler.activate_paid_subscription", return_value=True)
    def test_valid_paid_event_activates_user_for_event_date(self, update):
        response = self.post_event()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["access_through"], "2026-08-21")
        update.assert_called_once_with(789, activation_date=date(2026, 7, 23))

    @patch("web_auth.database_handler.activate_paid_subscription")
    def test_invalid_signature_is_rejected_without_activation(self, update):
        response = self.post_event(signature="invalid")

        self.assertEqual(response.status_code, 401)
        update.assert_not_called()

    @patch("web_auth.database_handler.activate_paid_subscription")
    def test_wrong_amount_is_rejected_without_activation(self, update):
        self.event["payload"]["payment_link"]["entity"]["amount_paid"] = 99800

        response = self.post_event()

        self.assertEqual(response.status_code, 400)
        update.assert_not_called()

    @patch("web_auth.database_handler.activate_paid_subscription")
    def test_unrelated_signed_event_is_acknowledged_and_ignored(self, update):
        self.event["event"] = "payment_link.expired"

        response = self.post_event()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ignored"])
        update.assert_not_called()

    @patch("web_auth.database_handler.activate_paid_subscription", return_value=False)
    def test_sheet_update_failure_requests_webhook_retry(self, _update):
        response = self.post_event()

        self.assertEqual(response.status_code, 500)


if __name__ == "__main__":
    unittest.main()
