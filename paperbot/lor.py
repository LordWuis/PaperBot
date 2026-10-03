"""Fill the variable body of the supplied Persevex LOR template."""

from pathlib import Path

import fitz

from . import renderer

PRONOUNS = {
    "he": {
        "subject": "he",
        "subject_cap": "He",
        "object": "him",
        "possessive": "his",
        "title": "Mr.",
    },
    "she": {
        "subject": "she",
        "subject_cap": "She",
        "object": "her",
        "possessive": "her",
        "title": "Ms.",
    },
    "they": {
        "subject": "they",
        "subject_cap": "They",
        "object": "them",
        "possessive": "their",
        "title": "Mx.",
    },
}


def generate(data, create_preview=False):
    pronouns = PRONOUNS[data["pronouns"]]
    verb = "choose" if data["pronouns"] == "they" else "chooses"
    name = data["name"]
    paragraphs = [
        (
            f'I am pleased to recommend {pronouns["title"]} {name} for {pronouns["possessive"]} '
            "graduate application. I am Shanmukh Shekar K C, Administrator at Persevex LLP, and I "
            f'had the opportunity to closely observe {pronouns["possessive"]} performance during '
            f'{pronouns["possessive"]} time with our organization.'
        ),
        (
            f'{pronouns["subject_cap"]} worked with us as an Intern - {data["domain"]} from '
            f'{data["from_date"]} to {data["to_date"]}. During this period, '
            f'{pronouns["subject"]} demonstrated strong communication skills, confidence in '
            f'presentations, and effective planning abilities. {pronouns["subject_cap"]} carried '
            f'out {pronouns["possessive"]} responsibilities with dedication and professionalism '
            "and maintained a positive attitude toward learning and growth."
        ),
        (
            f'{pronouns["title"]} {name} is hardworking, disciplined, and capable of applying '
            f'{pronouns["possessive"]} knowledge in practical situations. '
            f'{pronouns["subject_cap"]} contributed well to the team and showed good potential '
            "for future growth."
        ),
        (
            f'I am confident that {pronouns["subject"]} will excel in {pronouns["possessive"]} '
            f'higher studies and professional career. I strongly recommend {pronouns["object"]} '
            f'for any opportunity {pronouns["subject"]} {verb} to pursue.'
        ),
    ]
    root = Path(renderer.BASE_DIR)
    template = root / "templates" / "letter-of-recommendation.pdf"
    font_path = root / "fonts" / "opensans.ttf"
    with fitz.open(template) as document:
        page = document[0]
        body = fitz.Rect(62, 280, 528, 620)
        page.add_redact_annot(body, fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        page.insert_font(fontname="PaperBotOpenSans", fontfile=str(font_path))
        boxes = [
            fitz.Rect(68, 289, 521, 359),
            fitz.Rect(68, 379, 521, 468),
            fitz.Rect(68, 505, 521, 561),
            fitz.Rect(68, 577, 521, 620),
        ]
        for paragraph, box in zip(paragraphs, boxes):
            size = 12
            while size >= 9:
                shape = page.new_shape()
                spare = shape.insert_textbox(
                    box,
                    paragraph,
                    fontsize=size,
                    fontname="PaperBotOpenSans",
                    color=(0, 0, 0),
                    lineheight=1.32,
                )
                if spare >= 0:
                    shape.commit()
                    break
                size -= 0.25
            else:
                raise ValueError("LOR details are too long to fit legibly.")
        output = renderer._make_output_path("Letter_of_Recommendation.pdf")
        document.subset_fonts()
        document.save(output, garbage=4, deflate=True)
    return output, renderer._create_preview_from_pdf(output) if create_preview else ""
