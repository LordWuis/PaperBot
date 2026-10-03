"""Saved certificate designs, rendered without a browser or external service."""

import base64
import io
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from html import escape
from urllib.parse import urlencode
import fitz
import qrcode

ROOT = Path(__file__).resolve().parents[1] / "templates/certificates"
LABELS = {
    "ic": "Internship completion",
    "internship-completion": "Internship completion (alternate)",
    "ic-120hrs": "Internship completion · 120 hours",
    "offline-ic": "Offline internship completion",
    "adv-ic-temp": "Internship · college & mentor",
    "ic-adv-v2": "Internship · department & project",
    "course-completion": "Course completion (saved design)",
    "project-completion": "Project completion",
    "project-completion-temp": "Project completion (alternate)",
}


@lru_cache(maxsize=9)
def template(slug):
    if slug not in LABELS:
        raise ValueError("Unknown certificate template.")
    return json.loads((ROOT / (slug + ".json")).read_text())


def schemas():
    result = {}
    for slug, label in LABELS.items():
        keys = ["name", "email", "domain", "date"]
        for element in template(slug)["elements"]:
            for key in re.findall(r"\{(\w+)\}", element.get("text", "")):
                key = "capital_he_she" if key == "He_She" else key
                if key not in keys and key != "candidate_name":
                    keys.append(key)
        names = {
            "name": "Student name",
            "email": "Email address",
            "date": "Issue date",
            "capital_he_she": "He / She (capitalized)",
            "his_her": "His / her",
            "he_she": "He / she",
            "him_her": "Him / her",
        }
        result["saved_" + slug] = dict(
            label=label,
            short_label=label,
            group="Saved certificates",
            source=slug + ".json",
            helper_text="Original saved design: "
            + slug
            + ".json. QR verification is registered automatically. Dates print exactly as entered.",
            fields=[
                dict(
                    name=k,
                    label=names.get(k, k.replace("_", " ").capitalize()),
                    type="email" if k == "email" else "text",
                    required=True,
                    placeholder={
                        "date": "21 September 2026",
                        "domain": "Web Development",
                    }.get(k, ""),
                )
                for k in keys
            ],
        )
    return result


def generate(kind, data):
    slug = kind.removeprefix("saved_")
    design = template(slug)
    # Saved files contain editor coordinates but no canvas dimensions. Their
    # artwork/issue-date alignment establishes an 860 px reference canvas.
    width = 860
    height = width * design["image_dimensions"][1] / design["image_dimensions"][0]
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_image(page.rect, stream=base64.b64decode(design["image_data_b64"]))
    values = {
        **data,
        "candidate_name": data["name"],
        "issue_date": data["date"],
        "He_She": data.get("capital_he_she", ""),
    }
    font_names = {False: "Times-Roman", True: "Times-Bold"}
    for e in design["elements"]:
        coords = e["coords"]
        if e["type"] == "image":
            from .certificate_registry import verification_url

            qr = qrcode.make(verification_url(data["cert_id"]))
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            page.insert_image(fitz.Rect(coords), stream=buf.getvalue())
            continue
        text = values[e["name"]] if e["type"] == "text" else e["text"].format_map(values)
        font = fitz.Font(fontname=font_names[bool(e.get("bold"))])
        if any(not font.has_glyph(ord(c)) for c in text if c != "\n"):
            raise ValueError(
                "A certificate field contains characters unsupported by this template font."
            )
        color = tuple(int(e["color"][i : i + 2], 16) / 255 for i in (1, 3, 5))
        size = e["size"] * 4 / 3
        if e["type"] == "text":
            x, y = coords
            anchor = e.get("anchor", "center")
            available = 2 * min(x - 25, width - 25 - x) if anchor == "center" else width - 25 - x
            size = min(size, available / max(font.text_length(text, fontsize=1), 1))
            if size < 10:
                raise ValueError("Name or date is too long to fit legibly.")
            length = font.text_length(text, fontsize=size)
            if anchor == "center":
                x -= length / 2
            elif anchor == "e":
                x -= length
            page.insert_text(
                (x, y + size * 0.34),
                text,
                fontname=font_names[bool(e.get("bold"))],
                fontsize=size,
                color=color,
            )
        else:
            # Keep body above the original issue-date line, even with long values.
            rect = fitz.Rect(coords)
            rect.y1 = min(rect.y1, 438)
            rect.x0 += 1
            rect.x1 -= 1
            while size >= 10:
                shape = page.new_shape()
                spare = shape.insert_textbox(
                    rect,
                    text,
                    fontname=font_names[bool(e.get("bold"))],
                    fontsize=size,
                    color=color,
                    align=1,
                    lineheight=1.4,
                )
                if spare >= 0:
                    shape.commit()
                    break
                size -= 0.25
            else:
                raise ValueError(
                    "Certificate details are too long. Shorten them before generating."
                )
    result = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return result
