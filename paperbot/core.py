import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from sqlalchemy import select, insert, update
from . import db


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return int(time.time())


def uid():
    return str(uuid.uuid4())


def today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def user_id(email):
    return (
        int(hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12], 16) % 9000000000
        + 1000000000
    )


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def keyed(value):
    return hmac.new(os.environ["APP_SECRET"].encode(), value.encode(), hashlib.sha256).hexdigest()


def email_address(value):
    value = str(value or "").strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
        raise Problem("Enter a valid email address.")
    return value


def active(user, day=None):
    if user and user.get("free_role"):
        return True
    if user and user.get("access_until") is not None:
        return user["access_until"] > now()
    if not user or user["status"] != "active" or not user["expiry"]:
        return False
    try:
        return date.fromisoformat(user["expiry"]) >= (day or today())
    except ValueError:
        return False


def record(c, owner, action, data):
    c.execute(
        insert(db.audit).values(id=uid(), owner=owner, action=action, data=data, created=now())
    )


def rate_limit(engine, key, maximum, seconds):
    """Atomic upsert works across instances; retain only hashes, never IP/email."""
    bucket = f"{digest(key)}:{seconds}:{now() // seconds}"
    table = db.limits
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    statement = (pg_insert if engine.dialect.name == "postgresql" else sqlite_insert)(table).values(
        key=bucket, count=1
    )
    statement = statement.on_conflict_do_update(
        index_elements=[table.c.key], set_={"count": table.c.count + 1}
    ).returning(table.c.count)
    with engine.begin() as c:
        count = c.execute(statement).scalar_one()
    if count > maximum:
        raise Problem("Please wait a moment before trying again.", 429)
