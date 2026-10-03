"""Fill only the variable lines in the supplied stipend acceptance template."""

from pathlib import Path
import fitz
from dateutil.relativedelta import relativedelta
from . import renderer


def generate(name, month, domain, create_preview=False):
    start = renderer.datetime.strptime(
        f"10 {month.strip().title()} {renderer.datetime.now().year}", "%d %B %Y"
    )
    period = f"{start:%d-%m-%Y} to {start + relativedelta(months=3):%d-%m-%Y}"
    root = Path(renderer.BASE_DIR)
    font = fitz.Font(fontfile=str(root / "fonts/opensans.ttf"))
    replacements = {"{{name}}": name, "{{domain}}": domain, "{{fromtodate}}": period}
    with fitz.open(root / "templates/internship-stipend.pdf") as doc:
        page = doc[0]
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"]
                    if not any(k in text for k in replacements):
                        continue
                    for key, value in replacements.items():
                        text = text.replace(key, value)
                    if any(not font.has_glyph(ord(ch)) for ch in text):
                        raise ValueError(
                            "The stipend font cannot display a character in the name or domain."
                        )
                    x, y = span["origin"]
                    size = min(span["size"], (550 - x) / font.text_length(text, fontsize=1))
                    if size < 9:
                        raise ValueError(
                            "Name or domain is too long for this letter. Shorten it before generating."
                        )
                    lines.append((text, (x, y), size))
                    page.add_redact_annot(fitz.Rect(span["bbox"]), fill=(1, 1, 1))
        if len(lines) != 3:
            raise ValueError("The stipend template placeholders have changed.")
        page.apply_redactions(images=0, graphics=0)
        page.insert_font(fontname="PaperBotOpenSans", fontfile=str(root / "fonts/opensans.ttf"))
        for text, point, size in lines:
            page.insert_text(
                point, text, fontsize=size, fontname="PaperBotOpenSans", color=(0, 0, 0)
            )
        path = renderer._make_output_path("stipend.pdf")
        doc.subset_fonts()
        doc.save(path, garbage=4, deflate=True)
    return path, renderer._create_preview_from_pdf(path) if create_preview else ""
