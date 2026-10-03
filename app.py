"""Vercel entrypoint: the entire application runs in this deployment."""

import csv
import io
import os
import threading
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, g, request, jsonify, send_file, send_from_directory
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from paperbot import db, auth, bulk, billing
from paperbot.core import (
    Problem,
    now,
    digest,
    active,
    rate_limit,
    record,
)
from paperbot.documents import build_draft, public_draft, parse_csv
from paperbot.sending import send_draft
from paperbot.schema import get_letter_schema

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def create_app(engine=None):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
    app.config["ENGINE"] = engine
    app.config["SCHEMA_READY"] = False
    schema_lock = threading.Lock()

    def database():
        if not app.config["SCHEMA_READY"]:
            with schema_lock:
                if not app.config["SCHEMA_READY"]:
                    app.config["ENGINE"] = app.config["ENGINE"] or db.make_engine()
                    db.init_schema(app.config["ENGINE"])
                    app.config["SCHEMA_READY"] = True
        return app.config["ENGINE"]

    def protected(paid=False):
        def decorator(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                token = request.cookies.get("pb_session", "")
                with database().connect() as c:
                    user = (
                        c.execute(
                            select(db.users)
                            .join(db.sessions, db.sessions.c.user_id == db.users.c.id)
                            .where(
                                db.sessions.c.token == digest(token), db.sessions.c.expires > now()
                            )
                        )
                        .mappings()
                        .first()
                    )
                    user = billing.resolve(c, user)
                if not user:
                    raise Problem("Please sign in.", 401)
                g.user = dict(user)
                if paid and not active(user):
                    raise Problem("Your subscription is inactive or expired.", 402)
                return fn(*args, **kwargs)

            return wrapped

        return decorator

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise Problem("Expected a JSON object.")
        return value

    def owned_draft(draft_id):
        with database().connect() as c:
            result = (
                c.execute(
                    select(db.drafts).where(
                        db.drafts.c.id == draft_id, db.drafts.c.owner == g.user["id"]
                    )
                )
                .mappings()
                .first()
            )
        if not result:
            raise Problem("Draft not found.", 404)
        return result

    @app.before_request
    def csrf():
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.path not in (
            "/webhooks/razorpay",
        ):
            # Browser mutations require a non-simple header; no CORS is enabled.
            if request.headers.get("X-PaperBot") != "1":
                raise Problem("Missing request protection header.", 403)
            origin = request.headers.get("Origin")
            if origin:
                trusted = {request.host_url.rstrip("/")}
                base = os.getenv("APP_BASE_URL", "").rstrip("/")
                if base:
                    trusted.add(base)
                if origin not in trusted:
                    raise Problem("Untrusted request origin.", 403)

    @app.after_request
    def secure(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        if request.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    @app.errorhandler(Problem)
    def problem(exc):
        return jsonify(error=str(exc)), exc.status

    @app.errorhandler(413)
    def too_large(exc):
        return jsonify(error="Upload must be smaller than 3 MB."), 413

    @app.errorhandler(IntegrityError)
    def conflict(exc):
        return (
            jsonify(
                error="This record already exists or was changed concurrently. Refresh and try again."
            ),
            409,
        )

    @app.errorhandler(Exception)
    def unexpected(exc):
        from werkzeug.exceptions import HTTPException

        if isinstance(exc, HTTPException):
            return jsonify(error=exc.description), exc.code
        # Do not log SQL bound values, email addresses, credentials or PDF contents.
        app.logger.error("Request failed: %s", type(exc).__name__)
        return jsonify(error="Operation unavailable. Check configuration and try again."), 503

    @app.get("/")
    @app.get("/app")
    @app.get("/login")
    @app.get("/join")
    @app.get("/pay")
    @app.get("/verification")
    def index():
        return send_file(ROOT / "public/index.html")

    @app.get("/assets/<path:name>")
    def assets(name):
        return send_from_directory(ROOT / "public/assets", name)

    @app.get("/favicon.svg")
    def favicon():
        return send_file(ROOT / "public/favicon.svg")

    @app.get("/api/health")
    def health():
        return {"ok": True, "application": "paperbot-vercel"}

    @app.get("/api/session")
    @protected()
    def session_info():
        return {
            "user": g.user,
            "active": active(g.user),
            "seats": billing.list_seats(database(), g.user),
            "offer_due": billing.offer_due(database(), g.user),
            "support": billing.support_status(database(), g.user),
            "schema": get_letter_schema(),
        }

    @app.post("/api/auth/request")
    def request_code():
        if len(os.getenv("APP_SECRET", "")) < 32:
            raise Problem("APP_SECRET must contain at least 32 characters.", 503)
        data = payload()
        # Vercel overwrites x-real-ip. Local requests use remote_addr.
        ip = (
            request.headers.get("X-Real-IP", request.remote_addr or "")
            if os.getenv("VERCEL")
            else request.remote_addr or ""
        )
        token = auth.request_otp(database(), data.get("name"), data.get("email"), ip)
        response = jsonify(ok=True)
        response.set_cookie(
            "pb_challenge",
            token,
            httponly=True,
            secure=bool(os.getenv("VERCEL")),
            samesite="Lax",
            max_age=600,
        )
        return response

    @app.post("/api/auth/verify")
    def verify_code():
        token = auth.verify_otp(
            database(), request.cookies.get("pb_challenge"), payload().get("code")
        )
        response = jsonify(ok=True)
        response.set_cookie(
            "pb_session",
            token,
            httponly=True,
            secure=bool(os.getenv("VERCEL")),
            samesite="Lax",
            max_age=45 * 86400,
        )
        response.delete_cookie("pb_challenge")
        return response

    @app.post("/api/auth/logout")
    def logout():
        with database().begin() as c:
            c.execute(
                delete(db.sessions).where(
                    db.sessions.c.token == digest(request.cookies.get("pb_session", ""))
                )
            )
        response = jsonify(ok=True)
        response.delete_cookie("pb_session")
        return response

    @app.post("/api/payment-link")
    @protected()
    def payment_link():
        rate_limit(database(), "payment:" + str(g.user["id"]), 5, 60)
        return billing.payment_link(
            database(), g.user, payload(), os.getenv("APP_BASE_URL") or request.host_url
        )

    @app.post("/api/support/choice")
    @protected()
    def support_choice():
        return billing.dismiss_offer(database(), g.user, payload().get("amount", 0))

    @app.post("/api/invitations/claim")
    @protected()
    def claim_invitation():
        billing.claim(database(), g.user, payload().get("token"))
        return {"ok": True}

    @app.post("/webhooks/razorpay")
    def webhook():
        handled = billing.webhook(
            database(),
            request.get_data(),
            request.headers.get("X-Razorpay-Signature", ""),
            os.getenv("RAZORPAY_WEBHOOK_SECRET", ""),
        )
        return {"ok": True, "ignored": not handled}

    @app.post("/api/drafts")
    @protected(paid=True)
    def prepare():
        rate_limit(database(), "prepare:" + str(g.user["id"]), 60, 60)
        data = payload()
        return build_draft(database(), g.user["id"], data.get("kind"), data.get("form"))

    @app.get("/api/drafts")
    @protected()
    def history():
        with database().connect() as c:
            records = c.execute(
                select(
                    db.drafts.c.id,
                    db.drafts.c.kind,
                    db.drafts.c.recipient,
                    db.drafts.c.created,
                    db.drafts.c.state,
                    db.drafts.c.provider_id,
                    db.drafts.c.error,
                )
                .where(db.drafts.c.owner == g.user["id"])
                .order_by(db.drafts.c.created.desc())
                .limit(100)
            ).mappings()
            return {"drafts": [dict(r) for r in records]}

    @app.get("/api/drafts/<draft_id>")
    @protected(paid=True)
    def get_draft(draft_id):
        return public_draft(owned_draft(draft_id))

    @app.get("/api/drafts/<draft_id>/pdf")
    @protected(paid=True)
    def pdf(draft_id):
        draft = owned_draft(draft_id)
        if not draft["pdf"]:
            raise Problem("Document expired.", 410)
        return send_file(
            io.BytesIO(draft["pdf"]),
            mimetype="application/pdf",
            download_name=draft["recipient"]["letter_type"].replace(" ", "_") + ".pdf",
            as_attachment=request.args.get("download") == "1",
        )

    @app.get("/api/drafts/<draft_id>/preview/<int:page>")
    @protected(paid=True)
    def preview(draft_id, page):
        from paperbot.pdf_runtime import preview as render_preview

        draft = owned_draft(draft_id)
        if not draft["pdf"]:
            raise Problem("Document expired.", 410)
        try:
            data = render_preview(draft["pdf"], page)
        except Problem as exc:
            if str(exc) == "Page not found.":
                raise Problem(str(exc), 404)
            raise
        return send_file(io.BytesIO(data), mimetype="image/png")

    @app.post("/api/drafts/<draft_id>/send")
    @protected(paid=True)
    def send(draft_id):
        return send_draft(database(), g.user["id"], draft_id, payload().get("sha256"))

    @app.get("/api/jobs")
    @protected()
    def jobs():
        with database().connect() as c:
            return {
                "jobs": [
                    dict(r)
                    for r in c.execute(
                        select(db.jobs)
                        .where(db.jobs.c.owner == g.user["id"])
                        .order_by(db.jobs.c.created.desc())
                        .limit(30)
                    ).mappings()
                ]
            }

    @app.post("/api/jobs")
    @protected(paid=True)
    def new_job():
        rate_limit(database(), "batch:" + str(g.user["id"]), 10, 3600)
        upload = request.files.get("file")
        if not upload:
            raise Problem("Upload a CSV file.")
        kind = request.form.get("kind")
        rows = parse_csv(kind, upload.read())
        if kind == "internship_letter":
            from paperbot.documents import clean_form

            rows = [
                clean_form(
                    kind,
                    {
                        **row,
                        "internship_variant": request.form.get(
                            "internship_variant", "without_stipend"
                        ),
                    },
                )
                for row in rows
            ]
        return {"id": bulk.create_job(database(), g.user["id"], kind, rows)}

    @app.get("/api/jobs/<job_id>")
    @protected()
    def job_status(job_id):
        return bulk.snapshot(database(), g.user["id"], job_id)

    @app.post("/api/jobs/<job_id>/step")
    @protected(paid=True)
    def job_step(job_id):
        return bulk.step(database(), g.user["id"], job_id)

    @app.post("/api/jobs/<job_id>/approve")
    @protected(paid=True)
    def job_approve(job_id):
        job = bulk.snapshot(database(), g.user["id"], job_id)
        if payload().get("confirm") is not True:
            raise Problem("Confirm the reviewed recipient list.")
        if job["state"] != "review":
            raise Problem("Prepare the batch before approving it.", 409)
        if not any(r["state"] == "ready" for r in job["rows"]):
            raise Problem("No valid documents to send.")
        with database().begin() as c:
            c.execute(
                update(db.jobs)
                .where(db.jobs.c.id == job_id, db.jobs.c.state == "review")
                .values(state="sending")
            )
            record(
                c,
                g.user["id"],
                "batch.approved",
                {
                    "id": job_id,
                    "drafts": [r["draft_id"] for r in job["rows"] if r["state"] == "ready"],
                },
            )
        return {"ok": True}

    @app.post("/api/jobs/<job_id>/retry")
    @protected(paid=True)
    def retry_job(job_id):
        job = bulk.snapshot(database(), g.user["id"], job_id)
        if job["state"] != "completed":
            raise Problem("Wait for the batch to finish.", 409)
        with database().begin() as c:
            c.execute(
                update(db.rows)
                .where(db.rows.c.job_id == job_id, db.rows.c.state == "retry")
                .values(state="ready")
            )
            c.execute(update(db.jobs).where(db.jobs.c.id == job_id).values(state="sending"))
        return {"ok": True}

    @app.get("/api/jobs/<job_id>/failed.csv")
    @protected()
    def failed_csv(job_id):
        job = bulk.snapshot(database(), g.user["id"], job_id)
        output = io.StringIO()
        fields = [f["name"] for f in get_letter_schema()[job["kind"]]["fields"]] + ["row", "error"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in job["rows"]:
            if row["state"] not in ("error", "retry"):
                continue
            values = {**row["form"], "row": row["position"], "error": row["error"]}
            # Spreadsheet formula injection protection.
            values = {
                k: (
                    "'" + v
                    if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                )
                for k, v in values.items()
            }
            writer.writerow(values)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            download_name="failed-" + job_id + ".csv",
            as_attachment=True,
        )

    @app.get("/api/verification/<cert_id>")
    def verification(cert_id):
        with database().connect() as c:
            cert = c.execute(
                select(db.certificates.c.data).where(db.certificates.c.id == cert_id)
            ).scalar_one_or_none()
        if not cert:
            raise Problem("Certificate not found.", 404)
        return {k: cert[k] for k in ("name", "domain", "date")}

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
