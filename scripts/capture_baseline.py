"""Generate baseline pixel hashes from the original checkout (not shipped to Vercel)."""

import ast, hashlib, importlib.util, json, sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import fitz

root = Path.cwd()
spec = importlib.util.spec_from_file_location("original_renderer", root.parent / "pdf_generator.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


class Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 18, 12, 0, 0)


legacy.datetime = Frozen
source = (root.parent / "pdf_generator.py").read_text(encoding="utf-8")
function = next(
    n
    for n in ast.parse(source).body
    if isinstance(n, ast.FunctionDef)
    and n.name == "generate_internship_acceptance_pdf_with_preview"
)
mapping = next(
    n
    for n in function.body
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "domain_to_template_map"
)
domains = ast.literal_eval(mapping.value)
cases = [
    {
        "name": "campus-ambassador",
        "fn": "generate_campus_ambassador_pdf_with_preview",
        "args": ["Test Candidate"],
    },
    {
        "name": "offer",
        "fn": "generate_offer_letter_pdf_with_preview",
        "args": ["Test Candidate", "31-01-2026"],
    },
    {
        "name": "course-certificate",
        "fn": "generate_completion_certificate",
        "args": ["Test Candidate", "18 September, 2026", "Web Development", "test-cert-123"],
    },
    {
        "name": "ca-certificate",
        "fn": "ca_certificate",
        "args": ["Test Candidate", "18 September, 2026"],
    },
]
for domain in domains:
    cases.append(
        {
            "name": "internship-" + domain,
            "fn": "generate_internship_acceptance_pdf_with_preview",
            "args": ["Test Candidate", "November", domain],
        }
    )
output = root / "output"
output.mkdir(exist_ok=True)
for case in cases:
    with patch.object(
        legacy, "_make_output_path", side_effect=lambda _: str(output / "baseline.pdf")
    ):
        path, _ = getattr(legacy, case["fn"])(*case["args"], create_preview=False)
    with fitz.open(path) as doc:
        case["pages"] = [
            {
                "width": p.rect.width,
                "height": p.rect.height,
                "pixels_sha256": hashlib.sha256(p.get_pixmap(dpi=72).samples).hexdigest(),
                "text": p.get_text(),
            }
            for p in doc
        ]
(root / "tests/legacy-render-baselines.json").write_text(
    json.dumps({"frozen_date": "2026-09-18", "cases": cases}, indent=2), encoding="utf-8"
)
manifest = {
    str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
    for folder in ("templates", "fonts")
    for p in (root / folder).iterdir()
    if p.is_file()
}
(root / "tests/asset-sha256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(
    f'{len(cases)} baseline cases, {sum(len(c["pages"]) for c in cases)} pages, {len(manifest)} assets'
)
