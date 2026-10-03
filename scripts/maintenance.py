"""Explicit maintenance. Dry-run by default; optional PDF pruning preserves audit."""

import argparse, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from sqlalchemy import select, delete, update, func
from paperbot import db
from paperbot.core import now

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
p = argparse.ArgumentParser()
p.add_argument("--apply", action="store_true", help="Apply the displayed cleanup")
p.add_argument(
    "--pdf-days",
    type=int,
    help="Optional retention; only submitted PDF bytes older than this are pruned (minimum 30)",
)
a = p.parse_args()
if a.pdf_days is not None and a.pdf_days < 30:
    p.error("--pdf-days must be at least 30")
engine = db.make_engine()
with engine.begin() as c:
    for table in (db.otps, db.sessions):
        where = table.c.expires < now()
        count = c.execute(select(func.count()).select_from(table).where(where)).scalar_one()
        print(f"{table.name}: {count} expired records")
        if a.apply:
            c.execute(delete(table).where(where))
    keys = []
    for (key,) in c.execute(select(db.limits.c.key)):
        try:
            _, seconds, bucket = key.split(":")
            if (int(bucket) + 2) * int(seconds) < now():
                keys.append(key)
        except ValueError:
            pass
    print(f"rate_limits: {len(keys)} expired buckets")
    if a.apply and keys:
        c.execute(delete(db.limits).where(db.limits.c.key.in_(keys)))
    if a.pdf_days:
        where = (
            (db.drafts.c.created < now() - a.pdf_days * 86400)
            & (db.drafts.c.state == "submitted")
            & (db.drafts.c.pdf.is_not(None))
        )
        count = c.execute(select(func.count()).select_from(db.drafts).where(where)).scalar_one()
        print(f"drafts: {count} old submitted PDFs (metadata retained)")
        if a.apply:
            c.execute(update(db.drafts).where(where).values(pdf=None))
print("Applied." if a.apply else "Dry-run only. Add --apply to commit cleanup.")
