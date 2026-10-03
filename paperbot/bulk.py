from sqlalchemy import select, insert, update
from . import db
from .core import Problem, now, uid
from .documents import build_draft
from .sending import send_draft


def create_job(engine, owner, kind, forms):
    job_id = uid()
    with engine.begin() as c:
        c.execute(
            insert(db.jobs).values(
                id=job_id, owner=owner, kind=kind, state="preparing", created=now()
            )
        )
        c.execute(
            insert(db.rows),
            [
                {
                    "id": uid(),
                    "job_id": job_id,
                    "position": i + 2,
                    "form": form,
                    "state": "pending",
                    "lease": 0,
                }
                for i, form in enumerate(forms)
            ],
        )
    return job_id


def snapshot(engine, owner, job_id):
    with engine.connect() as c:
        job = (
            c.execute(select(db.jobs).where(db.jobs.c.id == job_id, db.jobs.c.owner == owner))
            .mappings()
            .first()
        )
        if not job:
            raise Problem("Batch not found.", 404)
        rows = [
            dict(r)
            for r in c.execute(
                select(db.rows).where(db.rows.c.job_id == job_id).order_by(db.rows.c.position)
            ).mappings()
        ]
        draft_ids = [r["draft_id"] for r in rows if r["draft_id"]]
        recipients = (
            {
                r["id"]: r["recipient"]
                for r in c.execute(
                    select(db.drafts.c.id, db.drafts.c.recipient).where(
                        db.drafts.c.id.in_(draft_ids)
                    )
                ).mappings()
            }
            if draft_ids
            else {}
        )
    for row in rows:
        row["recipient"] = recipients.get(row["draft_id"])
    return {
        **dict(job),
        "rows": rows,
        "total": len(rows),
        "submitted": sum(r["state"] == "submitted" for r in rows),
        "failed": sum(r["state"] in ("error", "retry") for r in rows),
    }


def step(engine, owner, job_id):
    job = snapshot(engine, owner, job_id)
    preparing = job["state"] == "preparing"
    if job["state"] not in ("preparing", "sending"):
        return job
    eligible = ("pending", "working") if preparing else ("ready", "sending")
    with engine.begin() as c:
        row = (
            c.execute(
                select(db.rows)
                .where(
                    db.rows.c.job_id == job_id,
                    db.rows.c.state.in_(eligible),
                    db.rows.c.lease <= now(),
                )
                .order_by(db.rows.c.position)
                .with_for_update(skip_locked=True)
            )
            .mappings()
            .first()
        )
        if row:
            claimed = c.execute(
                update(db.rows)
                .where(db.rows.c.id == row["id"], db.rows.c.lease <= now())
                .values(lease=now() + 120, state="working" if preparing else "sending")
            )
            if not claimed.rowcount:
                return job
    if row:
        try:
            if preparing:
                draft = build_draft(engine, owner, job["kind"], row["form"])
                values = {"draft_id": draft["id"], "state": "ready", "lease": 0, "error": None}
            else:
                with engine.connect() as c:
                    sha = c.execute(
                        select(db.drafts.c.sha256).where(
                            db.drafts.c.id == row["draft_id"], db.drafts.c.owner == owner
                        )
                    ).scalar_one()
                send_draft(engine, owner, row["draft_id"], sha)
                values = {"state": "submitted", "lease": 0, "error": None}
        except Problem as exc:
            values = {
                "state": (
                    ("pending" if preparing else "ready")
                    if exc.status in (429, 402)
                    else ("error" if preparing else "retry")
                ),
                "lease": 0,
                "error": str(exc),
            }
        except Exception:
            values = {
                "state": "error" if preparing else "retry",
                "lease": 0,
                "error": "Operation failed. Check configuration or retry.",
            }
        with engine.begin() as c:
            c.execute(update(db.rows).where(db.rows.c.id == row["id"]).values(**values))
    result = snapshot(engine, owner, job_id)
    if not any(r["state"] in eligible for r in result["rows"]):
        state = "review" if preparing else "completed"
        with engine.begin() as c:
            c.execute(update(db.jobs).where(db.jobs.c.id == job_id).values(state=state))
        result["state"] = state
    return result
