import os
import secrets
import requests
from sqlalchemy import select, insert, update, delete
from . import db
from .core import Problem, now, uid, keyed, digest, user_id, email_address, rate_limit


def request_otp(engine, name, email, ip):
    name = str(name or "").strip()
    if not name or len(name) > 150:
        raise Problem("Enter your name (up to 150 characters).")
    email = email_address(email)
    rate_limit(engine, "otp-email:" + email, 3, 600)
    rate_limit(engine, "otp-ip:" + ip, 10, 600)
    rate_limit(engine, "resend-outbound", 1, 1)
    key = os.getenv("RESEND_API_KEY")
    if not key:
        raise Problem("Email login is not configured.", 503)
    token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1000000):06d}"
    with engine.begin() as c:
        c.execute(delete(db.otps).where(db.otps.c.email == email))
        c.execute(
            insert(db.otps).values(
                id=digest(token),
                email=email,
                name=name,
                digest=keyed(token + ":" + code),
                expires=now() + 600,
                attempts=0,
            )
        )
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + key, "Idempotency-Key": "otp-" + digest(token)},
            json={
                "from": f"PaperBot <{os.getenv('DEFAULT_EMAIL','support@persevex.com')}>",
                "to": [email],
                "subject": "Your PaperBot login code",
                "html": f"<p>Your PaperBot login code is <strong>{code}</strong>.</p><p>This code expires in 10 minutes.</p>",
            },
            timeout=20,
        )
        response.raise_for_status()
        if not response.json().get("id"):
            raise ValueError()
    except Exception as exc:
        with engine.begin() as c:
            c.execute(delete(db.otps).where(db.otps.c.id == digest(token)))
        raise Problem("Could not send code. Try again shortly.", 502) from exc
    return token


def verify_otp(engine, token, code):
    import hmac

    if not token or not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise Problem("Enter the six-digit code.")
    error = None
    session_token = None
    with engine.begin() as c:
        otp = (
            c.execute(select(db.otps).where(db.otps.c.id == digest(token)).with_for_update())
            .mappings()
            .first()
        )
        if not otp or otp["expires"] < now() or otp["attempts"] >= 5:
            raise Problem("Code expired or too many attempts. Request a new code.")
        c.execute(
            update(db.otps).where(db.otps.c.id == otp["id"]).values(attempts=db.otps.c.attempts + 1)
        )
        if not hmac.compare_digest(otp["digest"], keyed(token + ":" + code)):
            error = "Incorrect code."
        else:
            consumed = c.execute(delete(db.otps).where(db.otps.c.id == otp["id"]))
            if not consumed.rowcount:
                raise Problem("Code has already been used.")
            owner = user_id(otp["email"])
            user = c.execute(select(db.users).where(db.users.c.id == owner)).mappings().first()
            if user and user["email"] and user["email"] != otp["email"]:
                raise Problem("Account ID conflict. Contact the administrator.", 409)
            if not user:
                c.execute(
                    insert(db.users).values(
                        id=owner,
                        email=otp["email"],
                        name=otp["name"],
                        status="inactive",
                        created=now(),
                    )
                )
            else:
                c.execute(
                    update(db.users)
                    .where(db.users.c.id == owner)
                    .values(email=otp["email"], name=otp["name"])
                )
            session_token = secrets.token_urlsafe(48)
            c.execute(
                insert(db.sessions).values(
                    token=digest(session_token), user_id=owner, expires=now() + 45 * 86400
                )
            )
    if error:
        raise Problem(error)
    return session_token
