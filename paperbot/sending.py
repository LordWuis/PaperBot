import base64
import os
import requests
from sqlalchemy import select, update
from . import db, billing
from .core import Problem, now, active, rate_limit, record


def send_draft(engine, owner, draft_id, approved_hash):
    with engine.begin() as c:
        user = c.execute(select(db.users).where(db.users.c.id == owner)).mappings().first()
        user = billing.resolve(c, user)
        if not active(user):
            raise Problem("An active subscription is required.", 402)
        draft = (
            c.execute(
                select(db.drafts)
                .where(db.drafts.c.id == draft_id, db.drafts.c.owner == owner)
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if not draft:
            raise Problem("Draft not found.", 404)
        if not approved_hash or approved_hash != draft["sha256"]:
            raise Problem("Review and approve this exact preview before sending.", 409)
        if draft["state"] == "submitted":
            return {"state": "submitted", "provider_id": draft["provider_id"]}
        if draft["kind"] == "course_certificate" or draft["kind"].startswith("saved_"):
            from .certificate_registry import VERIFY_URL

            if (
                not draft["form"].get("_sheet_registered")
                or draft["form"].get("_verification_url") != VERIFY_URL
            ):
                raise Problem(
                    "Regenerate this certificate to use the Persevex QR link and register it in Google Sheets before sending.",
                    409,
                )
        if not draft["pdf"]:
            raise Problem("Document has expired. Generate a new preview.", 410)
        if draft["first_attempt"] and now() - draft["first_attempt"] >= 23 * 3600:
            raise Problem(
                "Send outcome requires manual reconciliation in Resend; automatic retries have stopped.",
                409,
            )
        if draft["lease"] > now():
            raise Problem("This document is already being processed.", 409)
        if not os.getenv("RESEND_API_KEY"):
            raise Problem("Email is not configured.", 503)
        # Compare-and-set also prevents concurrent sends on local SQLite.
        claimed = c.execute(
            update(db.drafts)
            .where(
                db.drafts.c.id == draft_id,
                db.drafts.c.lease <= now(),
                db.drafts.c.state != "submitted",
            )
            .values(
                lease=now() + 90, state="sending", first_attempt=draft["first_attempt"] or now()
            )
        )
        if not claimed.rowcount:
            raise Problem("This document is already being processed.", 409)
    try:
        rate_limit(engine, "resend-outbound", 1, 1)
        payload = dict(draft["email_payload"])
        payload["attachments"] = [
            {
                "filename": draft["recipient"]["letter_type"].replace(" ", "_") + ".pdf",
                "content": base64.b64encode(draft["pdf"]).decode(),
            }
        ]
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": "Bearer " + os.environ["RESEND_API_KEY"],
                "Idempotency-Key": "paperbot-draft-" + draft_id,
            },
            json=payload,
            timeout=25,
        )
        response.raise_for_status()
        provider_id = response.json().get("id")
        if not provider_id:
            raise ValueError("Missing provider ID")
    except Exception as exc:
        with engine.begin() as c:
            c.execute(
                update(db.drafts)
                .where(db.drafts.c.id == draft_id)
                .values(
                    state="retry",
                    lease=0,
                    error="Not confirmed. Retry uses the same provider idempotency key.",
                )
            )
        if isinstance(exc, Problem):
            raise
        raise Problem(
            "Email submission was not confirmed. Retry safely within 23 hours; check Resend if it remains unresolved.",
            502,
        ) from exc
    with engine.begin() as c:
        c.execute(
            update(db.drafts)
            .where(db.drafts.c.id == draft_id)
            .values(state="submitted", lease=0, error=None, provider_id=provider_id)
        )
        record(c, owner, "email.submitted", {"draft_id": draft_id, "provider_id": provider_id})
    return {"state": "submitted", "provider_id": provider_id}
