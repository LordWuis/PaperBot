# PaperBot — Vercel edition

A separate rebuild of the PaperBot web application for a small team (1–100 users). The UI, authentication, subscription enforcement, Razorpay webhook, PDF generation, batch processing, and verification API all run in **one Vercel deployment**. No PythonAnywhere or Google Apps Script backend is used.

The new interface is lightweight HTML/CSS/JavaScript served from Vercel's CDN. Python runs inside Vercel Functions because retaining the proven PyMuPDF renderer avoids layout and font drift. Durable Postgres storage is provisioned through **Vercel Marketplace → Neon**. This is a managed database integration, not a database hosted inside an ephemeral function. Razorpay and Resend remain the payment and email providers.

## Deploy manually on Vercel

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for the prepared local env file, Neon Postgres, direct onboarding-sheet connection and Razorpay webhook setup. No existing user import or administration UI is required.

## Access and invitations

Exactly two verified email accounts are reserved globally through `DEVELOPER_EMAIL` and `FREE_USER_EMAIL`. Reservations are persisted at initialization and cannot silently move to different addresses. They are not first-come offers and do not multiply per user.

The main account sees an optional monthly popup: **₹1,000 to support Aman, ₹349 for a burger, or ₹0 with identical full access**. The popup starts 48 hours after the main account first opens the app. Choosing support saves a pledge without checkout; an in-app payment reminder appears on or after the 5th of the next month (India time), on the next visit. Checkout is blocked before then. Paid reminders stop after the verified webhook. Free access never expires. The card remains under Access & support. Developer access is also free. Other accounts pay **₹1,000 before access**, for one calendar month from confirmed payment, at the same India-local time. Month-end dates clamp to the next month's last day. There is no eighth-day deadline or automatic debit.

The main account can pay for additional people and share a single-use invitation after payment. The month starts when paid. The main account renews each expired invited person; invited people cannot reuse the invitation for another account. Everyone has isolated documents and history.

## Internship onboarding and stipend choice

Choose **Without stipend** (the original domain-specific two-month templates) or **With stipend** (the supplied NARAYANI PDF with a three-month period and its unchanged performance-based stipend up to ₹25,000 wording). Both start on the 10th of the onboarding month in the current India year. The choice is available for individual generation and a whole CSV batch; existing name-only CSVs default to non-stipend.

A prepared draft freezes the choice, student lookup, dates, PDF and email. The stipend renderer replaces only variable lines, preserves artwork and wording, and fits long names/domains without clipping. Unsupported characters or text too long to remain legible fail explicitly.

Connect the onboarding sheet directly with a read-only Google service account. `ONBOARDING_SHEET_GID` resolves the selected tab title; `ONBOARDING_COLUMNS` maps its headers. Name matching ignores case and repeated spaces; missing/duplicate names stop generation instead of guessing the recipient. Database student records remain supported internally for tests/previous data, but there is no import screen or Apps Script dependency.

## What stays identical

- All **22 template PDFs and both font files** are copied byte for byte.
- Five document types: campus ambassador letter, internship acceptance, offer letter, course completion certificate, campus ambassador certificate.
- Existing coordinates, typography, document wording, page counts, sender selection, email subjects/bodies, and Bcc default.
- Original non-stipend dates: the 10th of the supplied month in the current India year, ending two calendar months later, including November/December rollover.
- Offer dates: training start +10 days, internship beginning the next day, ending six calendar months later.
- Signed `payment_link.paid` events only. Payment must match a stored order, provider link, exact amount and INR currency. Donations and access purchases are separate. Duplicates cannot create multiple seats or extend access twice; delayed events cannot shorten a later expiry. Links expire after 24 hours and are reused while pending.

Two unusual existing email choices are preserved intentionally: the campus ambassador certificate shares the appointment-letter email, and course completion certificates use the generic “A Letter from Persevex” email. Edit `paperbot/email_templates.py` only if you intend to change that behavior.

## Sending and small-team concurrency

A prepared draft freezes its PDF bytes, resolved recipient, sender, Bcc, subject and HTML. The approval contains that draft's PDF hash. Sending never regenerates a different PDF or repeats an onboarding lookup. You can review the first page inline and open **all pages** before approval.

Every draft and batch is owner-scoped. Postgres row locks and durable leases prevent concurrent operations on a draft. Email requests use a stable Resend idempotency key, and uncertain requests can be retried with exactly the same payload. After 23 hours from the first attempt, automatic retry stops for manual Resend reconciliation, avoiding duplicates outside Resend's 24-hour idempotency window. “Submitted” means Resend returned an email ID, not that the message was delivered. This version does not synchronize delivery/read events; use the displayed provider ID in Resend to reconcile them.

Bulk CSVs are prepared one row per bounded request, then explicitly approved. One ready row is sent per subsequent request. **Keep the app open while processing.** Closing it pauses work; reopen the batch and resume. No polling GET sends an email. There are no background threads, local job files, or serverless lifetime assumptions. Each native PDF operation runs in a short-lived, awaited child process inside its Vercel request; this follows [PyMuPDF’s process-isolation guidance](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html) and avoids sharing its non-thread-safe native state between concurrent requests. Requests have bounded provider timeouts. A shared database rate limiter caps outbound email requests at one per second across users to respect a small-account provider quota; account plan limits still apply.

## Certificate verification

New course certificates and saved certificate designs encode **https://www.persevex.com/verification?id=CERTIFICATE_ID**. They are registered in the existing Google Sheet `1rd6QKi9cexc0H2lPpF3jPU3DRgCv3SjyNjRe46vsB10`, tab gid `550131035`: G = name, K = domain, N = certificate ID, O = issue date (DD-MM-YYYY). Other cells in the appended row remain blank; no existing rows are edited. The existing Google service account needs Editor access.

Registration uses the Sheets API directly from Vercel, checks existing IDs, appends using RAW values, and reads back the row. A failed or uncertain registration does not release a draft. Retrying the same ID checks for a completed previous write. PostgreSQL serializes this app's registration writers. External writers must enforce their own ID uniqueness. There is no distributed transaction with Google: a successful sheet write can survive a failed database commit and is recovered on retry.

The existing Persevex website retains its own verification backend; PaperBot does not change it. The local public verification page/API remains available as a secondary registry. The old CERTIFICATE_VERIFY_URL setting no longer overrides the required QR destination. Existing PDFs are immutable: regenerate old drafts to update their QR and register them before sending. Campus ambassador certificates retain their original design without a QR.

## Development and verification

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
# Copy .env.example to .env and enter local values.
# A local-only DB can use DATABASE_URL=sqlite:///paperbot-local.db
.venv/Scripts/python app.py
.venv/Scripts/python -m unittest discover -s tests -v
node --check public/assets/app.js
```

Production rejects SQLite when `VERCEL` is set. The test suite uses an isolated temporary SQLite database by default. Set `TEST_DATABASE_URL` to a disposable Postgres database to run real row-lock/concurrency tests; each test creates and drops a uniquely named schema. Never point tests at a production database.

GitHub Actions runs the complete suite on Python 3.12 and Postgres 16. The original-renderer baselines cover **34 cases / 37 pages**, checking exact pixel hashes, extracted text, dimensions and all template/font hashes. Frozen time makes date-dependent tests reproducible. Tests use fake credentials/provider mocks and send no real email or payment requests. The baseline capture helper needs the original checkout beside this repo; normal tests do not.

No real sending, payment transaction, live onboarding-sheet lookup, Vercel production deployment or migration was performed during the initial local build. Those are deployment acceptance checks, not implied by passing isolated tests. Performance depends on your Vercel/Neon region, cold starts, Google Sheets latency and provider quotas; there is no unmeasured “blazing fast” guarantee.

## Operations

- Keep a stable `APP_BASE_URL`; redeploy after changing environment settings. Use separate credentials/database for Vercel Preview deployments.
- Durable audit events are stored in `audit`; email IDs and immutable snapshots are in `drafts`. Monitor storage usage and enable database backups appropriate to your plan. PDFs are kept until an administrator deliberately prunes them; no silent document deletion is scheduled.
- Periodically run the documented cleanup command in `scripts/maintenance.py` for expired login challenges/sessions and old rate-limit buckets. PDF cleanup is optional and preserves audit metadata, payment history and certificate records.
- Credentials, local databases, logs, QA artifacts and downloaded dependencies are excluded from Git. No production database contents are committed.
- This rebuild replaces the **web application**. It does not run Telegram polling or import the old Telegram conversations. The PDF/template behaviors used by the web application are preserved.

Reference: [Flask on Vercel](https://vercel.com/docs/frameworks/backend/flask), [Vercel Marketplace storage](https://vercel.com/docs/marketplace-storage), [Resend idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).


## Saved certificate library

Create includes a separate picker for all nine JSON designs from certificate_generator/Templates. The same designs are available in Batch, with template-specific CSV headers. Each generated certificate registers its ID and QR verification record before any email can be approved. Registration conflicts fail closed; all sends retain preview approval.

Original background images and template JSON files are retained byte-for-byte. The JSON format omits editor canvas dimensions; rendering uses the visually verified 860 px reference width. Portable PDF Times fonts replace desktop-only Times New Roman; variable text fits within bounds or fails explicitly if too long. This is not a pixel-identical reproduction of the old browser renderer. The existing 500-row batch limit is unchanged.

Certificate IDs are generated automatically for every course/saved certificate as `ai12` + seven lowercase alphanumeric characters + the current India year suffix, for example `ai1239djf3d26`. PaperBot checks both PostgreSQL and the verification sheet before using an ID. Manual certificate-ID fields are intentionally absent from single and CSV workflows.

## Letter of recommendation

The supplied `Neha R Girachh.pdf` is included as the LOR template. The app replaces the inconsistent sample names with one candidate and fills internship domain, dates, and selected pronouns throughout. The original header, signature, stamp, contact details, artwork, and A4 page geometry are preserved. LORs support single preparation, preview approval, email sending, and CSV batches.
