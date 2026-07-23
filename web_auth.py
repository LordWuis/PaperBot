import hashlib
import hmac
import json
import logging
import os
import random
import time
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

from typing import Optional

from flask import jsonify, redirect, render_template, request, session, url_for

import database_handler
from config_loader import load_project_env


load_project_env()

OTP_TTL_SECONDS = 10 * 60


def web_user_id_from_email(email: str) -> int:
    normalized = email.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % 9000000000) + 1000000000


def send_login_otp(name: str, email: str) -> None:
    import resend

    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")
    resend.api_key = api_key

    otp = f"{random.randint(0, 999999):06d}"
    expires_at = int(time.time()) + OTP_TTL_SECONDS
    pending_login = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "otp_hash": _hash_otp(otp),
        "expires_at": expires_at,
    }

    response = resend.Emails.send(
        {
            "from": f"PaperBot <{os.getenv('DEFAULT_EMAIL', 'support@persevex.com')}>",
            "to": [email],
            "subject": "Your PaperBot login code",
            "html": f"<p>Your PaperBot login code is <strong>{otp}</strong>.</p><p>This code expires in 10 minutes.</p>",
        }
    )
    if not response or not _response_id(response):
        raise RuntimeError("OTP email was not accepted by Resend.")
    session["pending_login"] = pending_login
    session.modified = True


def complete_login(otp: str) -> dict:
    pending = session.get("pending_login")
    if not pending:
        return {"ok": False, "error": "Request a new code."}

    if int(time.time()) > int(pending.get("expires_at", 0)):
        session.pop("pending_login", None)
        return {"ok": False, "error": "Code expired."}

    if _hash_otp(otp.strip()) != pending.get("otp_hash"):
        return {"ok": False, "error": "Incorrect code."}

    user_id = web_user_id_from_email(pending["email"])
    status = database_handler.get_user_status(user_id)
    if status.get("status") == "not_found":
        registration = database_handler.register_new_user(user_id, pending["name"] or pending["email"])
        if registration.get("status") not in {"success", "already_exists"}:
            return {"ok": False, "error": "Could not register this account."}
        database_handler.clear_user_cache(user_id)
        status = database_handler.get_user_status(user_id)

    session.permanent = True
    session["web_user"] = {
        "id": user_id,
        "name": pending["name"],
        "email": pending["email"],
    }
    session.pop("pending_login", None)
    session.modified = True

    return {"ok": True, "active": status.get("status") == "active"}


def current_web_user() -> Optional[dict]:
    return session.get("web_user")


def current_subscription_status(force_refresh: bool = False) -> dict:
    user = current_web_user()
    if not user:
        return {"status": "not_logged_in"}
    try:
        return database_handler.get_user_status(user["id"], force_refresh=force_refresh)
    except Exception as exc:
        logging.exception("Failed to check web subscription status")
        return {"status": "error", "message": str(exc)}


def require_login(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_web_user():
            return redirect(url_for("web_login"))
        return route_func(*args, **kwargs)

    return wrapper


def require_active_subscription(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_web_user():
            return redirect(url_for("web_login"))

        status = current_subscription_status()
        if status.get("status") != "active":
            return redirect(url_for("web_paywall"))

        return route_func(*args, **kwargs)

    return wrapper


def require_fresh_subscription(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_web_user():
            return redirect(url_for("web_login"))

        status = current_subscription_status(force_refresh=True)
        if status.get("status") == "error":
            return "Could not verify subscription status right now. Please try again.", 503
        if status.get("status") != "active":
            return redirect(url_for("web_paywall"))

        return route_func(*args, **kwargs)

    return wrapper


def build_payment_context() -> dict:
    user = current_web_user()
    status = current_subscription_status()
    payment_url = None
    payment_error = None

    if user and status.get("status") in {"expired", "inactive"}:
        try:
            import razorpay_handler

            cached_link = session.get("web_payment_link") or {}
            if (
                cached_link.get("user_id") == user["id"]
                and int(cached_link.get("expires_at", 0)) > int(time.time()) + 60
            ):
                payment_url = cached_link.get("url")
            else:
                payment_url = razorpay_handler.create_payment_link(user["id"])
                if payment_url:
                    session["web_payment_link"] = {
                        "user_id": user["id"],
                        "url": payment_url,
                        "expires_at": int(time.time()) + (23 * 60 * 60),
                    }
            if not payment_url:
                payment_error = razorpay_handler.get_last_error() or "Payment link is not available right now."
        except Exception as exc:
            logging.exception("Failed to create web payment link")
            payment_error = "Payment link is not available right now."
    elif user and status.get("status") != "active":
        payment_error = status.get("message") or "We could not verify your account status. Please try again."

    return {"user": user, "status": status, "payment_url": payment_url, "payment_error": payment_error}


def register_auth_routes(app):
    @app.route("/", methods=["GET"])
    def web_index():
        if not current_web_user():
            return redirect(url_for("web_login"))
        if current_subscription_status().get("status") != "active":
            return redirect(url_for("web_paywall"))
        return redirect(url_for("web_dashboard"))

    @app.route("/login", methods=["GET"])
    def web_login():
        if current_web_user() and current_subscription_status().get("status") == "active":
            return redirect(url_for("web_dashboard"))
        return render_template("login.html")

    @app.route("/auth/request-otp", methods=["POST"])
    def web_request_otp():
        payload = request.get_json(silent=True) or request.form
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        if not name or not email or "@" not in email:
            return jsonify({"ok": False, "error": "Enter name and email."}), 400

        try:
            send_login_otp(name, email)
            return jsonify({"ok": True})
        except Exception:
            app.logger.exception("Failed to send OTP")
            return jsonify({"ok": False, "error": "Could not send code."}), 500

    @app.route("/auth/verify-otp", methods=["POST"])
    def web_verify_otp():
        payload = request.get_json(silent=True) or request.form
        otp = (payload.get("otp") or "").strip()
        if len(otp) != 6:
            return jsonify({"ok": False, "error": "Enter 6 digits."}), 400

        try:
            result = complete_login(otp)
        except Exception:
            app.logger.exception("Failed to verify web OTP")
            return jsonify({"ok": False, "error": "Could not complete login. Try again."}), 500
        if not result.get("ok"):
            return jsonify(result), 400

        return jsonify({"ok": True, "redirect": url_for("web_dashboard") if result.get("active") else url_for("web_paywall")})

    @app.route("/logout")
    def web_logout():
        session.pop("pending_login", None)
        session.pop("web_user", None)
        session.pop("web_draft_id", None)
        session.pop("web_draft_payload", None)
        session.pop("web_form_values_by_type", None)
        session.pop("web_form_values", None)
        session.pop("selected_letter_type", None)
        session.pop("web_payment_link", None)
        return redirect(url_for("web_login"))

    @app.route("/pay", methods=["GET"])
    @require_login
    def web_paywall():
        if current_subscription_status().get("status") == "active":
            return redirect(url_for("web_dashboard"))
        return render_template("paywall.html", **build_payment_context())

    @app.route("/pay/check", methods=["POST"])
    @require_login
    def web_check_payment():
        user = current_web_user()
        try:
            database_handler.clear_user_cache(user["id"])
            status = database_handler.get_user_status(user["id"])
        except Exception:
            app.logger.exception("Failed to refresh web payment status")
            return jsonify({"ok": False, "error": "Could not check payment status right now."}), 500

        if status.get("status") == "active":
            return jsonify({"ok": True, "redirect": url_for("web_dashboard")})
        if status.get("status") == "error":
            return jsonify({"ok": False, "error": "Could not verify payment status right now."}), 503
        return jsonify({"ok": False, "error": "Payment not active yet."})

    @app.route("/webhooks/razorpay", methods=["POST"])
    def razorpay_webhook():
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
        if not webhook_secret:
            app.logger.error("RAZORPAY_WEBHOOK_SECRET is not configured")
            return jsonify({"ok": False, "error": "Webhook is not configured."}), 503

        raw_body = request.get_data(cache=True)
        supplied_signature = request.headers.get("X-Razorpay-Signature", "")
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not supplied_signature or not hmac.compare_digest(supplied_signature, expected_signature):
            return jsonify({"ok": False, "error": "Invalid signature."}), 401

        try:
            event = json.loads(raw_body)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Invalid JSON."}), 400

        if event.get("event") != "payment_link.paid":
            return jsonify({"ok": True, "ignored": True})

        import razorpay_handler

        payment_link = event.get("payload", {}).get("payment_link", {}).get("entity", {})
        notes = payment_link.get("notes") or {}
        if not isinstance(notes, dict):
            return jsonify({"ok": False, "error": "Malformed payment event."}), 400
        user_id_text = notes.get("paperbot_user_id") or notes.get("telegram_user_id")

        try:
            user_id = int(user_id_text)
            amount = int(payment_link.get("amount"))
            amount_paid = int(payment_link.get("amount_paid"))
            paid_at = int(event.get("created_at"))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Malformed payment event."}), 400

        if (
            user_id <= 0
            or payment_link.get("status") != "paid"
            or payment_link.get("currency") != "INR"
            or amount != razorpay_handler.PAYMENT_AMOUNT_PAISE
            or amount_paid != amount
        ):
            return jsonify({"ok": False, "error": "Payment details do not match."}), 400

        activation_date = datetime.fromtimestamp(
            paid_at,
            tz=ZoneInfo("Asia/Kolkata"),
        ).date()
        if not database_handler.activate_paid_subscription(user_id, activation_date=activation_date):
            app.logger.error("Failed to activate subscription for user %s", user_id)
            return jsonify({"ok": False, "error": "Could not activate subscription."}), 500

        return jsonify(
            {
                "ok": True,
                "user_id": user_id,
                "access_through": database_handler.get_subscription_access_through(activation_date),
            }
        )


def _hash_otp(otp: str) -> str:
    secret = os.getenv("FLASK_SECRET_KEY", "paperbot")
    return hashlib.sha256(f"{secret}:{otp}".encode("utf-8")).hexdigest()


def _response_id(response) -> str | None:
    if isinstance(response, dict):
        return response.get("id")
    return getattr(response, "id", None)
