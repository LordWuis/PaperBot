# Deploy PaperBot on Vercel

The private repository is https://github.com/Wuiserous/PaperBot-Vercel. You do not need to upload old users. Everyone signs in afresh using an email code.

The existing production project is `paper-bot-vercel`, at https://paper-bot-vercel.vercel.app. Neon is connected with the `PAPERBOT` prefix; `PAPERBOT_DATABASE_URL` takes precedence over a manually configured `DATABASE_URL`.

## 1. Import the repository

In Vercel, choose Add New → Project and import PaperBot-Vercel. Use the repository root and Flask preset. Leave Build Command and Output Directory at their defaults. The project declares Python 3.12.

## 2. Connect Postgres

Open the project's Storage tab → Create Database / Browse Marketplace → Neon. Create a database, choose a region near your Vercel functions, and connect it to this project for Production. Neon supplies connection environment variables. Ensure `DATABASE_URL` is the pooled Postgres URL with TLS (`sslmode=require`). If the integration uses a prefix, copy its pooled URL into `DATABASE_URL`. The application creates its own tables on first use; no manual SQL or account import is needed.

## 3. Import the prepared environment file

Aman has a local `.env.vercel` file beside this guide. It is deliberately excluded from GitHub. In Vercel → Project Settings → Environment Variables, use Import .env (or paste its key/value entries), selecting Production. It contains the existing Resend/Razorpay credentials, sender settings, newly generated application/webhook secrets, both reserved email addresses, and the onboarding sheet ID/tab ID.

These remaining values cannot be prepared until you create/connect the services:

| Variable                      | What to enter                                                                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                | Neon's pooled connection string; do not replace an integration-provided working value with a placeholder    |
| `APP_BASE_URL`                | Your stable production URL, e.g. `https://paperbot-vercel.vercel.app`, without a trailing slash             |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The service account JSON, compacted to one line; see below                                                  |
| Certificate QR destination | Fixed to `https://www.persevex.com/verification?id=...`; no environment override needed |

The live onboarding connection was verified on 2026-09-20. `ONBOARDING_COLUMNS` is `{"name":"Student Name","email":"Student Email ID","month":"Month Selection- According to your preference","domain":"Selected Domain"}`. The prepared env file includes the existing service-account credential. `ONBOARDING_SHEET_GID=1699871834` identifies the tab from the supplied URL; the app resolves its title automatically.

### Google Sheets connection

1. In Google Cloud Console, create/select a project and enable the **Google Sheets API**.
2. Open IAM & Admin → Service Accounts, create a service account for PaperBot, then Keys → Add key → Create new key → JSON. Keep the downloaded key private.
3. Share the onboarding spreadsheet with the JSON file's `client_email`, with **Viewer** access. No Google Cloud project-wide role is needed for reading this shared sheet.
4. Convert the JSON to one line using this PowerShell command (substitute the downloaded key's path), then paste the result into `GOOGLE_SERVICE_ACCOUNT_JSON` in Vercel:

   ```powershell
   Get-Content -Raw -LiteralPath 'C:\path\service-account.json' | ConvertFrom-Json | ConvertTo-Json -Compress -Depth 20 | Set-Clipboard
   ```

   Paste only into the Vercel secret field. Never commit the key. This enables direct Google Sheets access from Vercel; there is no Apps Script backend.

## 4. Configure payment confirmation

In Razorpay Dashboard → Webhooks, add `https://YOUR-PRODUCTION-URL/webhooks/razorpay`, select `payment_link.paid`, and use the exact `RAZORPAY_WEBHOOK_SECRET` from the local env file. Ensure the webhook URL is reachable through Vercel Deployment Protection. Configure test/live webhooks in the same mode as the corresponding Razorpay keys. Existing credentials are copied as provided; use test-mode credentials in a separate Preview project/database for payment testing.

A return from checkout never activates access. The signed webhook must match a locally created order, link ID, amount, and INR currency. Neither the optional ₹1,000 support contribution nor the ₹349 burger contribution purchases access or an additional seat.

## 5. Redeploy and verify

Redeploy after environment changes. Sign in as the developer or main user and check one letter of each type, both internship choices, a small batch, and the QR verification URL. In a test environment, check an ordinary ₹1,000 payment and a paid invitation. Real email sends, payments, Google credentials, and production deployment still need your acceptance test.

- Developer and designated main account: permanent free access, reserved globally by verified email.
- Main account: monthly optional ₹1,000 support, ₹349 burger, or ₹0 popup, identical access either way. The popup is delayed 48 hours from first use. A paid choice schedules an in-app reminder for the 5th of next month, without immediate checkout or automatic charging. Choices persist across devices. The support card remains available under Access & support.
- Others: ₹1,000 paid first, expiring at the same India-local time one calendar month later. January 31 ends February 28/29. No 8th-of-month rule, no automatic debit.
- Invitations: main user pays first and shares a one-person link. Their paid month starts at payment, not link redemption. The main user renews expired invited accounts. Invited users have separate documents/history.
- No administration screen or user import.

Vercel Hobby is for personal non-commercial use. This paid-seat application must use a suitable Vercel plan; free user access is not a promise of zero infrastructure costs. Neon, Resend and payment-provider limits/fees also depend on your plans.

Official references: [Vercel environment variables](https://vercel.com/docs/environment-variables), [Vercel Marketplace storage](https://vercel.com/docs/marketplace-storage), [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines), [Google service accounts](https://cloud.google.com/iam/docs/service-accounts-create), [Google Sheets API](https://developers.google.com/workspace/sheets/api/guides/concepts).

Certificate registration uses GOOGLE_SERVICE_ACCOUNT_JSON with Editor access to the existing verification sheet (gid 550131035). The live account has confirmed edit permission. No new environment variables are required.
