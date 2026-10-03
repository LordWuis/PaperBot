from typing import Dict

LETTER_TYPE_OPTIONS = [
    ("ca_letter", "Campus Ambassador Letter"),
    ("internship_letter", "Internship Acceptance Letter"),
    ("offer_letter", "Offer Letter"),
    ("course_certificate", "Course Completion Certificate"),
    ("ca_certificate", "Campus Ambassador Certificate"),
    ("lor", "Letter of Recommendation"),
]


def get_letter_type_map() -> Dict[str, str]:
    return dict(LETTER_TYPE_OPTIONS)


def get_letter_schema() -> Dict[str, Dict[str, object]]:
    from .saved_certificates import schemas

    return {
        **schemas(),
        "lor": {
            "label": "Letter of Recommendation",
            "short_label": "LOR",
            "description": "Create a recommendation letter from the supplied Persevex template.",
            "helper_text": "The candidate name, internship details and pronouns are applied consistently throughout the letter.",
            "sender_label": "Persevex Support",
            "fields": [
                {
                    "name": "name",
                    "label": "Candidate Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter full name",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "name@example.com",
                },
                {
                    "name": "domain",
                    "label": "Internship Domain",
                    "type": "text",
                    "required": True,
                    "placeholder": "Finance",
                },
                {
                    "name": "from_date",
                    "label": "Internship Start Date",
                    "type": "text",
                    "required": True,
                    "placeholder": "25 June 2026",
                },
                {
                    "name": "to_date",
                    "label": "Internship End Date",
                    "type": "text",
                    "required": True,
                    "placeholder": "31 July 2026",
                },
                {
                    "name": "pronouns",
                    "label": "Pronouns",
                    "type": "select",
                    "required": True,
                    "options": [["he", "He / him"], ["she", "She / her"], ["they", "They / them"]],
                    "placeholder": "",
                },
            ],
        },
        "ca_letter": {
            "label": "Campus Ambassador Letter",
            "short_label": "CA Letter",
            "description": "Create and preview a campus ambassador appointment letter, then send it by email.",
            "helper_text": "Use this when you already know the candidate's name and email address.",
            "sender_label": "Persevex Support",
            "fields": [
                {
                    "name": "name",
                    "label": "Candidate Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter full name",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "name@example.com",
                },
            ],
        },
        "internship_letter": {
            "label": "Internship Acceptance Letter",
            "short_label": "Internship Letter",
            "description": "Look up the intern in the onboarding sheet, generate the correct domain template, and send it.",
            "helper_text": "Only the intern name is needed here. Email and domain are fetched from the onboarding sheet.",
            "sender_label": "Persevex Support",
            "fields": [
                {
                    "name": "name",
                    "label": "Intern Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter name as stored in OB",
                },
            ],
        },
        "offer_letter": {
            "label": "Offer Letter",
            "short_label": "Offer Letter",
            "description": "Generate the offer letter with training dates and send it from the HR account.",
            "helper_text": "Training start date must stay in DD-MM-YYYY format to match the PDF logic.",
            "sender_label": "Persevex HR",
            "fields": [
                {
                    "name": "name",
                    "label": "Candidate Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter full name",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "name@example.com",
                },
                {
                    "name": "training_from",
                    "label": "Training Start Date",
                    "type": "text",
                    "required": True,
                    "placeholder": "DD-MM-YYYY",
                },
            ],
        },
        "course_certificate": {
            "label": "Course Completion Certificate",
            "short_label": "Course Certificate",
            "description": "Generate a completion certificate with course details and QR verification ID.",
            "helper_text": "Fill all fields exactly as they should appear in the certificate and QR record.",
            "sender_label": "Persevex Support",
            "fields": [
                {
                    "name": "name",
                    "label": "Student Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter student name",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "name@example.com",
                },
                {
                    "name": "domain",
                    "label": "Domain / Course Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Artificial Intelligence",
                },
                {
                    "name": "date",
                    "label": "Issue Date",
                    "type": "text",
                    "required": True,
                    "placeholder": "15 November, 2025",
                },
            ],
        },
        "ca_certificate": {
            "label": "Campus Ambassador Certificate",
            "short_label": "CA Certificate",
            "description": "Generate the campus ambassador certificate and email it after preview approval.",
            "helper_text": "Use the exact issue date text you want printed on the certificate.",
            "sender_label": "Persevex Support",
            "fields": [
                {
                    "name": "name",
                    "label": "Candidate Name",
                    "type": "text",
                    "required": True,
                    "placeholder": "Enter full name",
                },
                {
                    "name": "email",
                    "label": "Email Address",
                    "type": "email",
                    "required": True,
                    "placeholder": "name@example.com",
                },
                {
                    "name": "date",
                    "label": "Issue Date",
                    "type": "text",
                    "required": True,
                    "placeholder": "15 November, 2025",
                },
            ],
        },
    }
