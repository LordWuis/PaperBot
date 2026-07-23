# PaperBot Payment Wall

## User flow

1. A logged-in user with active access goes to `/app`.
2. An expired or inactive user is redirected to `/pay`.
3. PaperBot creates one Razorpay Payment Link for Rs. 999 and reuses it in that
   browser session for up to 23 hours. Razorpay expires the link after 24 hours.
4. A signed `payment_link.paid` webhook activates the PaperBot user identified in
   the Payment Link notes.
5. Access lasts for 30 calendar days, including the payment date. For example, a
   payment on July 23 grants access through August 21; access is blocked on
   August 22.
6. Razorpay redirects web customers back to `/pay`. They can also use
   `I've Paid - Check Status`, which bypasses the local status cache.
7. Starting, generating, or sending a letter (including bulk sending) bypasses
   the cache and checks Google Sheets again, so administrative status changes
   apply on the next operation.

Google Apps Script currently serializes the Sheet's date-only cells one day
behind their displayed India calendar date. PaperBot normalizes that response
before caching and enforcing expiry so users retain access through the date
shown in the Sheet.

New accounts do not receive paid access automatically. Invalid signatures,
partial or wrong-amount payments, non-INR payments, malformed events, and
unrelated webhook events cannot activate a user. Duplicate or delayed webhook
deliveries cannot extend or shorten an existing later expiry.

## Production setup

Set all variables shown in `.env.example`. `FLASK_SECRET_KEY` and
`RAZORPAY_WEBHOOK_SECRET` must be separate, long random values.

In the Razorpay **Live Mode** dashboard, create a webhook with:

- URL: `https://YOUR_APP_DOMAIN/webhooks/razorpay`
- Event: `payment_link.paid`
- Secret: exactly the deployed `RAZORPAY_WEBHOOK_SECRET`

Set `APP_BASE_URL` to `https://YOUR_APP_DOMAIN`. Vercel's `VERCEL_URL` is used as
a fallback, but an explicit production domain is preferred.

## Verification

Run the focused suite:

```powershell
python -m unittest discover -s tests -v
```

Before accepting a real payment, perform one Razorpay test-mode transaction
against a staging deployment and confirm:

- Razorpay reports HTTP 200 for the webhook.
- The Google Sheet changes the user to `active`.
- The expiry is the payment date plus 29 days.
- `/pay/check` redirects to `/app`.
