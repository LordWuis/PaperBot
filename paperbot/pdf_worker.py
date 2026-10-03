"""Internal binary-stdio worker. No HTTP routes, credentials or database access."""

import json
import sys
from pathlib import Path
from . import renderer


def main():
    path = None
    try:
        operation = sys.argv[1]
        raw = sys.stdin.buffer.read()
        if operation == "preview":
            import fitz

            with fitz.open(stream=raw, filetype="pdf") as document:
                page = int(sys.argv[2])
                if page < 0 or page >= len(document):
                    raise ValueError("Page not found.")
                result = document[page].get_pixmap(dpi=110).tobytes("png")
        else:
            request = json.loads(raw)
            kind, data = request["kind"], request["data"]
            if kind.startswith("saved_"):
                from .saved_certificates import generate

                sys.stdout.buffer.write(generate(kind, data))
                return
            if kind == "ca_letter":
                path, _ = renderer.generate_campus_ambassador_pdf_with_preview(data["name"], False)
            elif kind == "internship_letter" and data.get("internship_variant") == "with_stipend":
                from .stipend import generate

                path, _ = generate(data["name"], data["month"], data["domain"])
            elif kind == "internship_letter":
                path, _ = renderer.generate_internship_acceptance_pdf_with_preview(
                    data["name"], data["month"], data["domain"], False
                )
            elif kind == "offer_letter":
                path, _ = renderer.generate_offer_letter_pdf_with_preview(
                    data["name"], data["training_from"], False
                )
            elif kind == "course_certificate":
                path, _ = renderer.generate_completion_certificate(
                    data["name"], data["date"], data["domain"], data["cert_id"], False
                )
            elif kind == "ca_certificate":
                path, _ = renderer.ca_certificate(data["name"], data["date"], False)
            elif kind == "lor":
                from .lor import generate

                path, _ = generate(data, False)
            else:
                raise ValueError("Unknown document type.")
            result = Path(path).read_bytes()
        sys.stdout.buffer.write(result)
    except ValueError as exc:
        sys.stderr.write(str(exc))
        sys.exit(2)
    except Exception:
        sys.stderr.write("PDF processing failed. Check template assets.")
        sys.exit(1)
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
