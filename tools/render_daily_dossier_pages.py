from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
pdf = ROOT / "reports" / "daily-intelligence" / "2026-07-01-daily-internet-intelligence-dossier.pdf"
out_dir = ROOT / "tmp" / "pdfs"
out_dir.mkdir(parents=True, exist_ok=True)

doc = fitz.open(pdf)
for page_no in [0, 1, 2, 10, doc.page_count - 1]:
    page = doc[page_no]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    out = out_dir / f"dossier-2026-07-01-page-{page_no + 1:02d}.png"
    pix.save(out)
    print(out)
