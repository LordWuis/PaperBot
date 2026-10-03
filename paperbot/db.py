"""Shared durable storage. SQLite is allowed only for explicit local/test use."""

import os
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    BigInteger,
    Text,
    LargeBinary,
    JSON,
    Index,
)
from sqlalchemy.pool import NullPool

meta = MetaData()
users = Table(
    "users",
    meta,
    Column("id", BigInteger, primary_key=True),
    Column("email", String(254), unique=True),
    Column("name", Text, nullable=False),
    Column("status", String(20), nullable=False, default="inactive"),
    Column("expiry", String(10)),
    Column("created", BigInteger, nullable=False),
)
sessions = Table(
    "sessions",
    meta,
    Column("token", String(64), primary_key=True),
    Column("user_id", BigInteger, nullable=False),
    Column("expires", BigInteger, nullable=False),
)
otps = Table(
    "otps",
    meta,
    Column("id", String(64), primary_key=True),
    Column("email", String(254), nullable=False),
    Column("name", Text, nullable=False),
    Column("digest", String(64), nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("expires", BigInteger, nullable=False),
)
limits = Table(
    "rate_limits",
    meta,
    Column("key", String(128), primary_key=True),
    Column("count", Integer, nullable=False),
)
payments = Table(
    "payments",
    meta,
    Column("id", String(100), primary_key=True),
    Column("user_id", BigInteger, nullable=False),
    Column("url", Text),
    Column("expires", BigInteger, nullable=False),
    Column("paid", Integer, default=0),
)
events = Table(
    "payment_events",
    meta,
    Column("id", String(100), primary_key=True),
    Column("user_id", BigInteger, nullable=False),
    Column("expiry", String(10), nullable=False),
)
drafts = Table(
    "drafts",
    meta,
    Column("id", String(36), primary_key=True),
    Column("owner", BigInteger, nullable=False),
    Column("kind", String(40), nullable=False),
    Column("form", JSON, nullable=False),
    Column("recipient", JSON, nullable=False),
    Column("email_payload", JSON, nullable=False),
    Column("pdf", LargeBinary),
    Column("sha256", String(64), nullable=False),
    Column("created", BigInteger, nullable=False),
    Column("state", String(20), nullable=False, default="ready"),
    Column("lease", BigInteger, nullable=False, default=0),
    Column("first_attempt", BigInteger),
    Column("provider_id", Text),
    Column("error", Text),
)
jobs = Table(
    "jobs",
    meta,
    Column("id", String(36), primary_key=True),
    Column("owner", BigInteger, nullable=False),
    Column("kind", String(40), nullable=False),
    Column("state", String(20), nullable=False),
    Column("created", BigInteger, nullable=False),
)
rows = Table(
    "job_rows",
    meta,
    Column("id", String(36), primary_key=True),
    Column("job_id", String(36), nullable=False),
    Column("position", Integer, nullable=False),
    Column("form", JSON, nullable=False),
    Column("draft_id", String(36)),
    Column("state", String(20), nullable=False),
    Column("lease", BigInteger, nullable=False, default=0),
    Column("error", Text),
)
students = Table(
    "students",
    meta,
    Column("id", String(36), primary_key=True),
    Column("name_key", Text, nullable=False),
    Column("data", JSON, nullable=False),
)
certificates = Table(
    "certificates",
    meta,
    Column("id", String(100), primary_key=True),
    Column("owner", BigInteger, nullable=False),
    Column("data", JSON, nullable=False),
    Column("created", BigInteger, nullable=False),
)
audit = Table(
    "audit",
    meta,
    Column("id", String(36), primary_key=True),
    Column("owner", BigInteger, nullable=False),
    Column("action", String(60), nullable=False),
    Column("data", JSON, nullable=False),
    Column("created", BigInteger, nullable=False),
)
Index("drafts_owner_created", drafts.c.owner, drafts.c.created)
Index("job_rows_job_position", rows.c.job_id, rows.c.position, unique=True)
Index("jobs_owner_created", jobs.c.owner, jobs.c.created)
Index("students_name_key", students.c.name_key)


def make_engine(url=None):
    url = url or os.getenv("PAPERBOT_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("Connect Postgres and set DATABASE_URL. See README.")
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    if os.getenv("VERCEL") and not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Production requires durable Postgres storage.")
    options = {"poolclass": NullPool}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 30}
    return create_engine(url, **options)


def init_schema(engine):
    # Serialize simultaneous cold-start schema checks across serverless instances.
    with engine.begin() as c:
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text

            c.execute(text("SELECT pg_advisory_xact_lock(718391024)"))
        meta.create_all(c)
        from .billing import seed

        seed(c)


free_accounts = Table(
    "free_accounts",
    meta,
    Column("slot", String(20), primary_key=True),
    Column("email", String(254), unique=True, nullable=False),
)
seats = Table(
    "seats",
    meta,
    Column("id", String(36), primary_key=True),
    Column("sponsor_id", BigInteger, nullable=False),
    Column("beneficiary_id", BigInteger, unique=True),
    Column("expires_at", BigInteger),
    Column("created", BigInteger, nullable=False),
)
billing_orders = Table(
    "billing_orders",
    meta,
    Column("id", String(36), primary_key=True),
    Column("payer_id", BigInteger, nullable=False),
    Column("purpose", String(20), nullable=False),
    Column("seat_id", String(36)),
    Column("amount", Integer, nullable=False),
    Column("provider_id", String(100), unique=True),
    Column("url", Text),
    Column("expires", BigInteger, nullable=False),
    Column("paid", Integer, nullable=False, default=0),
    Column("access_until", BigInteger),
    Column("created", BigInteger, nullable=False),
)

support_choices = Table(
    "support_choices",
    meta,
    Column("id", String(80), primary_key=True),
    Column("user_id", BigInteger, nullable=False),
    Column("created", BigInteger, nullable=False),
)


support_schedule = Table(
    "support_schedule",
    meta,
    Column("user_id", BigInteger, primary_key=True),
    Column("first_seen", BigInteger, nullable=False),
    Column("amount", Integer),
    Column("selected_at", BigInteger),
    Column("due_at", BigInteger),
    Column("paid_at", BigInteger),
)
