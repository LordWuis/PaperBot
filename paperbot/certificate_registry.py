"""Register QR certificates in the existing Persevex verification sheet."""

import json
import os
import secrets
import string
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlencode
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
from sqlalchemy import text
from sqlalchemy import select
from . import db
from .core import Problem

VERIFY_URL = "https://www.persevex.com/verification"
SHEET_ID = "1rd6QKi9cexc0H2lPpF3jPU3DRgCv3SjyNjRe46vsB10"
SHEET_GID = 550131035
# Zero-based columns G, K, N, O. Never include email/payment/student contact data.
COLUMNS = (6, 10, 13, 14)
ID_ALPHABET = string.ascii_lowercase + string.digits


def verification_url(identifier):
    return VERIFY_URL + "?" + urlencode({"id": identifier})


def generate_unique_id(engine):
    """Create ai12 + seven lowercase alphanumerics + current India year."""
    year = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%y")
    for _ in range(20):
        identifier = "ai12" + "".join(secrets.choice(ID_ALPHABET) for _ in range(7)) + year
        with engine.connect() as connection:
            if connection.execute(
                select(db.certificates.c.id).where(db.certificates.c.id == identifier)
            ).first():
                continue
        if not _sheet_contains(identifier):
            return identifier
    raise Problem("Could not allocate a unique certificate ID. Please retry.", 503)


def _sheet_contains(identifier):
    try:
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        with AuthorizedSession(credentials) as client:
            base = "https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID
            response = client.get(base, params={"fields": "sheets.properties"}, timeout=10)
            response.raise_for_status()
            title = next(
                sheet["properties"]["title"]
                for sheet in response.json()["sheets"]
                if sheet["properties"]["sheetId"] == SHEET_GID
            )
            target = "'" + title.replace("'", "''") + "'!N:N"
            response = client.get(base + "/values/" + quote(target, safe=""), timeout=10)
            response.raise_for_status()
            return any(
                row and str(row[0]).strip().casefold() == identifier.casefold()
                for row in response.json().get("values", [])
            )
    except Exception as exc:
        raise Problem("Could not check certificate ID uniqueness in Google Sheets.", 503) from exc


def issue_date(value):
    value = str(value).strip().replace(",", "")
    for pattern in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(value, pattern).strftime("%d-%m-%Y")
        except ValueError:
            pass
    raise Problem("Enter a full issue date, for example 21-09-2026 or 21 September 2026.")


def registration_values(data):
    return [data["name"].strip(), data["domain"].strip(), data["cert_id"], issue_date(data["date"])]


def register(connection, data):
    """Called inside the certificate/draft transaction. Fail closed on uncertainty.

    The DB lock serializes this app's writers. Retrying an uncertain append first
    searches the sheet by ID, recovering a completed append without duplicating it.
    Other applications writing this sheet must enforce their own ID uniqueness.
    """
    expected = registration_values(data)
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(7294015821)"))
    try:
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        with AuthorizedSession(credentials) as client:
            return _register(client, expected)
    except Problem:
        raise
    except Exception as exc:
        raise Problem(
            "Certificate registration could not be confirmed in Google Sheets. No new draft was released. Retry with the same certificate ID.",
            503,
        ) from exc


def _register(client, expected):
    base = "https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID
    response = client.get(base, params={"fields": "sheets.properties"}, timeout=10)
    response.raise_for_status()
    title = next(
        s["properties"]["title"]
        for s in response.json()["sheets"]
        if s["properties"]["sheetId"] == SHEET_GID
    )
    sheet = "'" + title.replace("'", "''") + "'"
    response = client.get(base + "/values/" + quote(sheet + "!A:O", safe=""), timeout=10)
    response.raise_for_status()
    rows = response.json().get("values", [])
    matches = [
        row
        for row in rows
        if len(row) > 13 and str(row[13]).strip().casefold() == expected[2].casefold()
    ]
    if matches:
        if len(matches) != 1 or not _matches(matches[0], expected):
            raise Problem(
                "Certificate ID already exists in Google Sheets with different details or duplicate rows. Use a unique ID or correct the existing record.",
                409,
            )
        return {"status": "existing", "sheet_id": SHEET_ID, "gid": SHEET_GID}
    row = [""] * 15
    for column, value in zip(COLUMNS, expected):
        row[column] = value
    response = client.post(
        base + "/values/" + quote(sheet + "!A:O", safe="") + ":append",
        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
        json={"values": [row]},
        timeout=10,
    )
    response.raise_for_status()
    written_range = response.json()["updates"]["updatedRange"]
    response = client.get(base + "/values/" + quote(written_range, safe=""), timeout=10)
    response.raise_for_status()
    written = response.json().get("values", [])
    if len(written) != 1 or not _matches(written[0], expected):
        raise Problem(
            "Google Sheets registration could not be verified. Retry with the same certificate ID.",
            503,
        )
    return {"status": "registered", "sheet_id": SHEET_ID, "gid": SHEET_GID, "range": written_range}


def _matches(row, expected):
    if len(row) < 15:
        return False
    try:
        actual = [str(row[i]).strip() for i in COLUMNS]
        actual[3] = issue_date(actual[3])
        return actual == expected
    except Problem:
        return False
