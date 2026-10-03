import csv
import io
import json
import os
import re
from pathlib import Path
from html import escape
from sqlalchemy import select, insert
from . import db, renderer
from .core import Problem, uid, now, digest, email_address, record
from .schema import get_letter_schema
from .email_templates import get_email_templates


def name_key(value):
    return " ".join(value.split()).casefold()


def find_student(engine, name):
    sheet = os.getenv("ONBOARDING_SHEET_ID")
    if sheet:
        from google.oauth2.service_account import Credentials
        from google.auth.transport.requests import AuthorizedSession
        from urllib.parse import quote

        try:
            creds = Credentials.from_service_account_info(
                json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            with AuthorizedSession(creds) as client:
                sheet_range = os.getenv("ONBOARDING_RANGE", "OB!A:ZZ")
                gid = os.getenv("ONBOARDING_SHEET_GID")
                if gid:
                    metadata = client.get(
                        f'https://sheets.googleapis.com/v4/spreadsheets/{quote(sheet, safe="")}',
                        params={"fields": "sheets.properties"},
                        timeout=20,
                    )
                    metadata.raise_for_status()
                    title = next(
                        s["properties"]["title"]
                        for s in metadata.json()["sheets"]
                        if str(s["properties"]["sheetId"]) == gid
                    )
                    sheet_range = "'" + title.replace("'", "''") + "'!A:ZZ"
                response = client.get(
                    f'https://sheets.googleapis.com/v4/spreadsheets/{quote(sheet, safe="")}/values/{quote(sheet_range, safe="")}',
                    timeout=20,
                )
                response.raise_for_status()
                values = response.json().get("values", [])
            columns = json.loads(
                os.getenv(
                    "ONBOARDING_COLUMNS",
                    '{"name":"Name","email":"Email","month":"Month","domain":"Domain"}',
                )
            )
            headers = [str(v).strip().casefold() for v in values[0]]
            positions = {
                k: headers.index(columns[k].strip().casefold())
                for k in ("name", "email", "month", "domain")
            }
            matches = []
            for row in values[1:]:
                data = {
                    k: str(row[i]).strip() if i < len(row) else "" for k, i in positions.items()
                }
                if name_key(data["name"]) == name_key(name):
                    matches.append(data)
        except Exception as exc:
            raise Problem(
                "Could not read onboarding sheet. Check its access, range and column mapping.", 503
            ) from exc
    else:
        with engine.connect() as c:
            matches = [
                r[0]
                for r in c.execute(
                    select(db.students.c.data).where(db.students.c.name_key == name_key(name))
                )
            ]
    if not matches:
        raise Problem(f"Could not find '{name}' in onboarding records.")
    if len(matches) > 1:
        raise Problem(
            "Multiple onboarding records have that name. Resolve the duplicate before sending."
        )
    result = matches[0]
    if any(not result.get(k) for k in ("name", "email", "month", "domain")):
        raise Problem("Onboarding record is missing name, email, month or domain.")
    result["email"] = email_address(result["email"])
    return result


def clean_form(kind, data):
    schema = get_letter_schema().get(kind)
    if not schema or not isinstance(data, dict):
        raise Problem("Select a valid document type.")
    result = {f["name"]: str(data.get(f["name"], "")).strip() for f in schema["fields"]}
    for f in schema["fields"]:
        if not result[f["name"]]:
            raise Problem(f"Missing {f['label']}.")
        if len(result[f["name"]]) > 250 or any(ord(ch) < 32 for ch in result[f["name"]]):
            raise Problem(f"Invalid {f['label']}.")
    if "email" in result:
        result["email"] = email_address(result["email"])
    if kind == "course_certificate" or kind.startswith("saved_"):
        from .certificate_registry import issue_date

        issue_date(result["date"])
    if kind == "internship_letter":
        result["internship_variant"] = data.get("internship_variant", "without_stipend")
        if result["internship_variant"] not in ("without_stipend", "with_stipend"):
            raise Problem("Choose a valid internship letter type.")
    if kind == "lor" and result["pronouns"] not in ("he", "she", "they"):
        raise Problem("Choose valid pronouns.")
    return result


def render_document(kind, data):
    options = {"create_preview": False}
    if kind == "ca_letter":
        return renderer.generate_campus_ambassador_pdf_with_preview(data["name"], **options)
    if kind == "internship_letter" and data.get("internship_variant") == "with_stipend":
        from .stipend import generate

        return generate(data["name"], data["month"], data["domain"], **options)
    if kind == "internship_letter":
        return renderer.generate_internship_acceptance_pdf_with_preview(
            data["name"], data["month"], data["domain"], **options
        )
    if kind == "offer_letter":
        return renderer.generate_offer_letter_pdf_with_preview(
            data["name"], data["training_from"], **options
        )
    if kind == "course_certificate":
        return renderer.generate_completion_certificate(
            data["name"], data["date"], data["domain"], data["cert_id"], **options
        )
    if kind == "lor":
        from .lor import generate

        return generate(data, **options)
    return renderer.ca_certificate(data["name"], data["date"], **options)


def build_draft(engine, owner, kind, form):
    data = clean_form(kind, form)
    if kind == "course_certificate" or kind.startswith("saved_"):
        from .certificate_registry import generate_unique_id

        data["cert_id"] = generate_unique_id(engine)
    if kind == "internship_letter":
        data = {
            **find_student(engine, data["name"]),
            "internship_variant": data["internship_variant"],
        }
    labels = {
        "ca_letter": "Campus Ambassador",
        "internship_letter": "Internship Acceptance",
        "offer_letter": "Offer Letter",
        "course_certificate": "Course Completion Certificate",
        "ca_certificate": "Campus Ambassador Certificate",
        "lor": "Letter of Recommendation",
    }
    recipient = {
        "name": data["name"],
        "email": data["email"],
        "domain": data.get("domain", "General" if kind == "offer_letter" else "Community"),
        "letter_type": labels.get(kind, get_letter_schema()[kind]["label"]),
    }
    subject, html = get_email_templates(
        labels.get(kind, get_letter_schema()[kind]["label"]),
        escape(recipient["name"]),
        escape(recipient["domain"]),
    )
    if kind.startswith("saved_"):
        subject = "Your " + get_letter_schema()[kind]["label"] + " certificate"
        html = f"<p>Dear {escape(data['name'])},</p><p>Please find your {escape(get_letter_schema()[kind]['label'])} certificate attached.</p><p>Best regards,<br>Persevex Support</p>"
    sender = (
        f"Persevex HR <{os.getenv('HR_EMAIL','hr@persevex.com')}>"
        if kind == "offer_letter"
        else f"Persevex Support <{os.getenv('DEFAULT_EMAIL','support@persevex.com')}>"
    )
    email = {"from": sender, "to": [recipient["email"]], "subject": subject, "html": html}
    bcc = os.getenv("BCC_EMAIL", "startling550@gmail.com").strip()
    if bcc:
        email["bcc"] = [email_address(bcc)]
    from .pdf_runtime import generate

    pdf = generate(kind, data)
    import hashlib

    result = {
        "id": uid(),
        "owner": owner,
        "kind": kind,
        "form": data,
        "recipient": recipient,
        "email_payload": email,
        "pdf": pdf,
        "sha256": hashlib.sha256(pdf).hexdigest(),
        "created": now(),
        "state": "ready",
        "lease": 0,
    }
    with engine.begin() as c:
        if kind == "course_certificate" or kind.startswith("saved_"):
            cert_data = {k: data[k] for k in ("name", "email", "domain", "date")}
            if kind.startswith("saved_"):
                cert_data.update({"template": kind, "details": data})
            prior = (
                c.execute(
                    select(db.certificates)
                    .where(db.certificates.c.id == data["cert_id"])
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if prior and (prior["data"] != cert_data or prior["owner"] != owner):
                raise Problem(
                    "Certificate ID already belongs to a different record. Use a unique ID.", 409
                )
            if not prior:
                c.execute(
                    insert(db.certificates).values(
                        id=data["cert_id"], owner=owner, data=cert_data, created=now()
                    )
                )
            from .certificate_registry import register

            registration = register(c, data)
            from .certificate_registry import VERIFY_URL

            result["form"] = {**data, "_verification_url": VERIFY_URL, "_sheet_registered": True}
            record(
                c,
                owner,
                "certificate.sheet_registered",
                {"cert_id": data["cert_id"], **registration},
            )
        c.execute(insert(db.drafts).values(**result))
        record(
            c,
            owner,
            "document.prepared",
            {"id": result["id"], "sha256": result["sha256"], "kind": kind},
        )
    return public_draft(result)


def public_draft(row):
    result = {
        k: row.get(k)
        for k in (
            "id",
            "kind",
            "form",
            "recipient",
            "sha256",
            "created",
            "state",
            "provider_id",
            "error",
        )
    }
    result["email"] = {k: v for k, v in row["email_payload"].items() if k != "attachments"}
    return result


def parse_csv(kind, raw):
    schema = get_letter_schema().get(kind)
    if not schema:
        raise Problem("Select a document type.")
    if len(raw) > 2_000_000:
        raise Problem("CSV must be smaller than 2 MB.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeError:
        raise Problem("Use a UTF-8 CSV file.")
    norm = lambda value: re.sub(r"[^a-z0-9]+", "_", value.lower().strip()).strip("_")
    aliases = {
        norm(label): f["name"] for f in schema["fields"] for label in (f["name"], f["label"])
    }
    headers = reader.fieldnames or []
    canonical = {h: aliases.get(norm(h)) for h in headers}
    known = [v for v in canonical.values() if v]
    if len(set(known)) != len(known):
        raise Problem("CSV has duplicate columns.")
    missing = [f["name"] for f in schema["fields"] if f["name"] not in known]
    if missing:
        raise Problem("CSV missing headers: " + ", ".join(missing))
    result = []
    for position, row in enumerate(reader, 2):
        if None in row:
            raise Problem(f"Row {position} has extra columns.")
        data = {canonical[h]: (v or "").strip() for h, v in row.items() if canonical.get(h)}
        if not any(data.values()):
            continue
        try:
            data = clean_form(kind, data)
        except Problem as exc:
            raise Problem(f"Row {position}: {exc}")
        result.append(data)
        if len(result) > 500:
            raise Problem("Maximum 500 rows per upload.")
    if not result:
        raise Problem("CSV has no rows.")
    return result
