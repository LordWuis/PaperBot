"""Globally reserved free accounts and payment-bound monthly access."""

import hashlib
import hmac
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from dateutil.relativedelta import relativedelta
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy import select, insert, update
from . import db
from .core import Problem, now, uid, active, email_address, record


def seed(c):
    configured = {
        "developer": os.getenv("DEVELOPER_EMAIL", ""),
        "main": os.getenv("FREE_USER_EMAIL", ""),
    }
    configured = {k: email_address(v) for k, v in configured.items() if v}
    if len(set(configured.values())) != len(configured):
        raise RuntimeError("The two free accounts must be different.")
    for slot, email in configured.items():
        prior = c.execute(
            select(db.free_accounts.c.email).where(db.free_accounts.c.slot == slot)
        ).scalar()
        if prior and prior != email:
            raise RuntimeError("Reserved free account differs from the stored account.")
        if not prior:
            c.execute(insert(db.free_accounts).values(slot=slot, email=email))


def resolve(c, user):
    if not user:
        return None
    result = dict(user)
    role = c.execute(
        select(db.free_accounts.c.slot).where(db.free_accounts.c.email == user["email"])
    ).scalar()
    result["free_role"] = role
    if role:
        result.update(status="active", expiry=None, access_until=None)
        return result
    seat = (
        c.execute(select(db.seats).where(db.seats.c.beneficiary_id == user["id"]))
        .mappings()
        .first()
    )
    if seat:
        until = seat["expires_at"] or 0
        result["sponsored"] = True
    else:
        until = c.execute(
            select(db.billing_orders.c.access_until)
            .where(
                db.billing_orders.c.payer_id == user["id"],
                db.billing_orders.c.purpose == "access",
                db.billing_orders.c.paid == 1,
            )
            .order_by(db.billing_orders.c.access_until.desc())
        ).scalar()
        if until is None:
            return result  # Historical paid records remain usable; fresh logins are inactive.
    result.update(
        access_until=until,
        status="active" if until > now() else "expired",
        expiry=datetime.fromtimestamp(until, ZoneInfo("Asia/Kolkata")).isoformat(),
    )
    return result


def month_after(stamp):
    return int(
        (
            datetime.fromtimestamp(stamp, ZoneInfo("Asia/Kolkata")) + relativedelta(months=1)
        ).timestamp()
    )


def signer():
    return URLSafeSerializer(os.environ["APP_SECRET"], salt="paperbot-paid-invitation")


def list_seats(engine, user):
    if user.get("free_role") != "main":
        return []
    with engine.connect() as c:
        rows = (
            c.execute(
                select(db.seats, db.users.c.email)
                .outerjoin(db.users, db.users.c.id == db.seats.c.beneficiary_id)
                .where(db.seats.c.sponsor_id == user["id"])
                .order_by(db.seats.c.created)
            )
            .mappings()
            .all()
        )
    return [
        {
            **dict(r),
            "token": (
                signer().dumps(r["id"])
                if not r["beneficiary_id"] and (r["expires_at"] or 0) > now()
                else None
            ),
        }
        for r in rows
    ]


def claim(engine, user, token):
    try:
        seat_id = signer().loads(token)
        if not isinstance(seat_id, str):
            raise BadSignature("Invalid")
    except (BadSignature, TypeError):
        raise Problem("This invitation is invalid.")
    with engine.begin() as c:
        account = (
            c.execute(select(db.users).where(db.users.c.id == user["id"]).with_for_update())
            .mappings()
            .one()
        )
        current = resolve(c, account)
        seat = (
            c.execute(select(db.seats).where(db.seats.c.id == seat_id).with_for_update())
            .mappings()
            .first()
        )
        if not seat or (seat["expires_at"] or 0) <= now():
            raise Problem("This invitation needs payment from its owner before you can join.", 402)
        if seat["beneficiary_id"] == user["id"]:
            return
        if seat["beneficiary_id"] is not None:
            raise Problem("This invitation has already been used.", 409)
        if current.get("free_role") or current.get("sponsored") or active(current):
            raise Problem("This account already has access or belongs to another invitation.", 409)
        changed = c.execute(
            update(db.seats)
            .where(db.seats.c.id == seat_id, db.seats.c.beneficiary_id.is_(None))
            .values(beneficiary_id=user["id"])
        )
        if not changed.rowcount:
            raise Problem("This invitation has already been used.", 409)
        record(c, user["id"], "invitation.claimed", {"seat_id": seat_id})


def payment_link(engine, user, data, base):
    purpose = data.get("purpose", "access")
    seat_id = data.get("seat_id")
    if purpose not in ("access", "donation", "support", "seat"):
        raise Problem("Choose a valid payment type.")
    with engine.begin() as c:
        account = (
            c.execute(select(db.users).where(db.users.c.id == user["id"]).with_for_update())
            .mappings()
            .one()
        )
        user = resolve(c, account)
        if purpose in ("donation", "support", "seat") and user.get("free_role") != "main":
            raise Problem("This option belongs to the reserved main account.", 403)
        if purpose in ("donation", "support"):
            schedule = _support_row(c, user)
            expected = 349 if purpose == "donation" else 1000
            if (
                schedule["amount"] != expected
                or schedule["paid_at"]
                or not schedule["due_at"]
                or now() < schedule["due_at"]
            ):
                raise Problem(
                    "Your support choice is saved for the 5th of next month. Payment is not due yet.",
                    409,
                )
        if purpose == "access" and (active(user) or user.get("sponsored")):
            raise Problem(
                "Your account does not need a personal payment. Invited access is renewed by its owner.",
                409,
            )
        if purpose != "seat" and seat_id:
            raise Problem("Invalid payment details.")
        if purpose == "seat" and seat_id:
            seat = (
                c.execute(
                    select(db.seats)
                    .where(db.seats.c.id == seat_id, db.seats.c.sponsor_id == user["id"])
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not seat:
                raise Problem("Person not found.", 404)
            if (seat["expires_at"] or 0) > now():
                raise Problem("This person's access is still active.", 409)
        order = (
            c.execute(
                select(db.billing_orders)
                .where(
                    db.billing_orders.c.payer_id == user["id"],
                    db.billing_orders.c.purpose == purpose,
                    db.billing_orders.c.seat_id == seat_id,
                    db.billing_orders.c.paid == 0,
                    db.billing_orders.c.expires > now() + 300,
                    db.billing_orders.c.created
                    >= (schedule["selected_at"] if purpose in ("donation", "support") else 0),
                )
                .order_by(db.billing_orders.c.created.desc())
            )
            .mappings()
            .first()
        )
        if order and order["url"]:
            return {"url": order["url"]}
        key, secret = os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")
        if not key or not secret or not base:
            raise Problem("Payment setup is incomplete.", 503)
        order_id = uid()
        amount = 34900 if purpose == "donation" else 100000
        body = {
            "amount": amount,
            "currency": "INR",
            "accept_partial": False,
            "description": (
                "Optional burger for Aman"
                if purpose == "donation"
                else (
                    "Optional support for Aman"
                    if purpose == "support"
                    else "One calendar month of PaperBot access"
                )
            ),
            "notes": {"paperbot_order_id": order_id},
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "expire_by": now() + 86400,
            "callback_url": base.rstrip("/") + "/pay",
            "callback_method": "get",
        }
        response = requests.post(
            "https://api.razorpay.com/v1/payment_links", auth=(key, secret), json=body, timeout=20
        )
        response.raise_for_status()
        link = response.json()
        if not str(link.get("id", "")).startswith("plink_") or not str(
            link.get("short_url", "")
        ).startswith("https://"):
            raise Problem("Payment link was not returned.", 502)
        c.execute(
            insert(db.billing_orders).values(
                id=order_id,
                payer_id=user["id"],
                purpose=purpose,
                seat_id=seat_id,
                amount=amount,
                provider_id=link["id"],
                url=link["short_url"],
                expires=body["expire_by"],
                paid=0,
                created=now(),
            )
        )
        return {"url": link["short_url"]}


def webhook(engine, raw, signature, secret):
    if not secret:
        raise Problem("Payment webhook is not configured.", 503)
    if not signature or not hmac.compare_digest(
        signature, hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    ):
        raise Problem("Invalid signature.", 401)
    try:
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError()
        if event.get("event") != "payment_link.paid":
            return False
        entity = event["payload"]["payment_link"]["entity"]
        order_id = entity["notes"]["paperbot_order_id"]
        if not isinstance(order_id, str) or len(order_id) != 36:
            raise ValueError()
        stamp = event["created_at"]
        if type(stamp) is not int or stamp <= 0 or stamp > now() + 300:
            raise ValueError()
        if entity["status"] != "paid" or entity["currency"] != "INR":
            raise ValueError()
        if any(type(entity[k]) is not int for k in ("amount", "amount_paid")):
            raise ValueError()
    except (KeyError, ValueError, TypeError, AttributeError):
        raise Problem("Malformed or mismatched payment event.")
    with engine.begin() as c:
        order = (
            c.execute(
                select(db.billing_orders)
                .where(db.billing_orders.c.id == order_id)
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if (
            not order
            or entity.get("id") != order["provider_id"]
            or entity["amount"] != order["amount"]
            or entity["amount_paid"] != order["amount"]
        ):
            raise Problem("Payment does not match a PaperBot order.")
        if order["paid"]:
            return True
        until = month_after(stamp) if order["purpose"] not in ("donation", "support") else None
        changed = c.execute(
            update(db.billing_orders)
            .where(db.billing_orders.c.id == order_id, db.billing_orders.c.paid == 0)
            .values(paid=1, access_until=until)
        )
        if not changed.rowcount:
            return True
        if order["purpose"] == "seat":
            if order["seat_id"]:
                seat = (
                    c.execute(
                        select(db.seats).where(db.seats.c.id == order["seat_id"]).with_for_update()
                    )
                    .mappings()
                    .one()
                )
                c.execute(
                    update(db.seats)
                    .where(db.seats.c.id == seat["id"])
                    .values(expires_at=max(until, seat["expires_at"] or 0))
                )
            else:
                seat_id = uid()
                c.execute(
                    insert(db.seats).values(
                        id=seat_id, sponsor_id=order["payer_id"], expires_at=until, created=now()
                    )
                )
                c.execute(
                    update(db.billing_orders)
                    .where(db.billing_orders.c.id == order_id)
                    .values(seat_id=seat_id)
                )
        if order["purpose"] in ("donation", "support"):
            c.execute(
                update(db.support_schedule)
                .where(
                    db.support_schedule.c.user_id == order["payer_id"],
                    db.support_schedule.c.amount == order["amount"] // 100,
                    db.support_schedule.c.selected_at <= order["created"],
                )
                .values(paid_at=now())
            )
        record(
            c,
            order["payer_id"],
            "billing." + order["purpose"],
            {"order_id": order_id, "access_until": until},
        )
    return True


def _support_row(c, user):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    c.execute(
        (pg_insert if c.dialect.name == "postgresql" else sqlite_insert)(db.support_schedule)
        .values(user_id=user["id"], first_seen=now())
        .on_conflict_do_nothing()
    )
    return (
        c.execute(select(db.support_schedule).where(db.support_schedule.c.user_id == user["id"]))
        .mappings()
        .one()
    )


def support_status(engine, user):
    if user.get("free_role") != "main":
        return {"phase": "hidden", "offer_due": False}
    with engine.begin() as c:
        row = _support_row(c, user)
        stamp = now()
        month = lambda t: datetime.fromtimestamp(t, ZoneInfo("Asia/Kolkata")).strftime("%Y-%m")
        phase = "choose"
        if row["amount"] and not row["paid_at"]:
            phase = "due" if stamp >= row["due_at"] else "scheduled"
        elif row["selected_at"] and month(row["paid_at"] or row["selected_at"]) == month(stamp):
            phase = "thanks" if row["paid_at"] else "free"
        elif stamp < row["first_seen"] + 2 * 86400:
            phase = "waiting"
        return {
            "phase": phase,
            "amount": row["amount"],
            "due_at": row["due_at"],
            "offer_due": phase in ("choose", "due"),
        }


def offer_due(engine, user):
    return support_status(engine, user)["offer_due"]


def dismiss_offer(engine, user, amount=0):
    if user.get("free_role") != "main":
        raise Problem("This offer belongs to the reserved main account.", 403)
    if type(amount) is not int or amount not in (0, 349, 1000):
        raise Problem("Choose ₹0, ₹349 or ₹1,000.")
    stamp = now()
    date = datetime.fromtimestamp(stamp, ZoneInfo("Asia/Kolkata"))
    due = int(
        (
            date.replace(day=5, hour=0, minute=0, second=0, microsecond=0) + relativedelta(months=1)
        ).timestamp()
    )
    with engine.begin() as c:
        row = _support_row(c, user)
        # Repeated clicks must not postpone an existing commitment.
        if row["amount"] and amount and not row["paid_at"]:
            due = row["due_at"]
            if row["amount"] == amount:
                stamp = row["selected_at"]
        c.execute(
            update(db.support_schedule)
            .where(db.support_schedule.c.user_id == user["id"])
            .values(amount=amount, selected_at=stamp, due_at=due if amount else None, paid_at=None)
        )
    return support_status(engine, user)
