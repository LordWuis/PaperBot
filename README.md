# PaperBot

PaperBot generates letters and certificates through Flask web interfaces and a Telegram bot, with Razorpay payment integration.

## Setup

1. Install Python 3.12 or newer.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and configure the required services.
4. Start the web app with `python web_app.py` or the bot with `python telegram_bot.py`.

Document templates are stored in `templates/`. Local credentials, databases, and generated documents are excluded from version control.
