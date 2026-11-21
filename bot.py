import os
import sys
import time
import logging
import secrets
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
        log.error("Set them in Render → Environment tab.")
        sys.exit(1)
    log.info("Env OK — BASE_URL=%s", BASE_URL)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.effective_chat:
            log.warning("start: no message/chat in update")
            return
        token = secrets.token_urlsafe(8)
        link = f"{BASE_URL}/v/{token}"
        await update.message.reply_text(
            f"🔗 Your verification link:\n{link}\n\n"
            f"Share it — captures will land here."
        )
        log.info("start: issued token %s to chat %s", token, update.effective_chat.id)
    except TelegramError as e:
        log.error("start: TelegramError — %s", e)
    except Exception as e:
        log.exception("start: unexpected error — %s", e)


async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Listening for captures... 🎣")
        log.info("status: replied to chat %s", update.effective_chat.id)
    except Exception as e:
        log.exception("status: error — %s", e)


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error("Update caused error:", exc_info=ctx.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await ctx.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Something went wrong. Try /start again.",
            )
        except Exception:
            pass


def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_error_handler(error_handler)
    return app


def main():
    validate_env()

    attempt = 0
    while True:
        attempt += 1
        try:
            log.info("Starting bot (attempt %d)...", attempt)
            app = build_app()
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False,
            )
        except InvalidToken:
            log.error("BOT_TOKEN invalid — check BotFather. Exiting.")
            sys.exit(1)
        except NetworkError as e:
            log.warning("Network error: %s — retrying in 5s", e)
            time.sleep(5)
        except KeyboardInterrupt:
            log.info("Shutdown requested.")
            sys.exit(0)
        except Exception as e:
            backoff = min(60, 5 * attempt)
            log.exception("Bot crashed — restarting in %ds", backoff)
            time.sleep(backoff)


if __name__ == "__main__":
    main()
