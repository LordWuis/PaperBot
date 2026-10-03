"""Awaited, isolated PDF operations inside the current Vercel request.

PyMuPDF does not support multithreaded use. Each operation gets its own short-lived
process; no MuPDF objects or global contexts are shared by concurrent requests.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from .core import Problem


def execute(operation, payload, page=0):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "paperbot.pdf_worker", operation, str(page)],
            input=payload,
            capture_output=True,
            timeout=30,
            cwd=Path(__file__).resolve().parents[1],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise Problem("PDF processing timed out or was unavailable. Try again.", 503) from exc
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace")[:300]
        raise Problem(message or "PDF processing failed.", 400 if result.returncode == 2 else 503)
    if not result.stdout:
        raise Problem("PDF processing produced no output.", 503)
    return result.stdout


def generate(kind, data):
    return execute("generate", json.dumps({"kind": kind, "data": data}).encode())


def preview(pdf, page):
    return execute("preview", pdf, page)
