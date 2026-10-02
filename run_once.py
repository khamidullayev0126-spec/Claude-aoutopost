"""
GitHub Actions uchun bir martalik skript.

Bitta ishga tushirishda:
  1. Post tayyorlanadi (matn + QC, kerak bo'lsa rasm va audio).
  2. Admin (ADMIN_CHAT_ID) ga "Qayta qilish" tugmasi bilan preview yuboriladi.
  3. WAIT_MINUTES (default 10) daqiqa tugma bosilishi kutiladi.
       - bosilmasa  -> asl post kanalga chiqadi
       - bosilsa    -> post qayta tayyorlanadi va darhol kanalga chiqadi
  4. Adminga natija haqida xabar beriladi.

Holat (hisoblagich) saqlanmaydi, shuning uchun:
  - har 3-kundan biri matn-only (sana asosida hisoblanadi)
  - audio haftada bir marta, AUDIO_WEEKDAY kunida (0=dushanba ... 6=yakshanba)
"""
import html
import json
import logging
import os
import re
import time
from datetime import date, datetime

import pytz
import requests

from config import (ADMIN_CHAT_ID, CHANNEL_ID, GEMINI_IMAGE_MODEL, PREVIEW_MINUTES_BEFORE,
                    TELEGRAM_BOT_TOKEN, TIMEZONE)
from content_gen import generate_post
from image_gen import generate_image
from audio_gen import generate_audio
from qc import check_post

logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger("autopost")

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
MAX_GENERATION_ATTEMPTS = 3
EPOCH = date(2026, 1, 1)
AUDIO_WEEKDAY = int(os.environ.get("AUDIO_WEEKDAY", "6"))


# ---------------------------------------------------------------- Telegram
def tg(method: str, data: dict | None = None, files: dict | None = None, timeout: int = 60):
    response = requests.post(f"{API}/{method}", data=data, files=files, timeout=timeout)
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method} xatosi: {body}")
    return body["result"]


def send_text(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", data)


def send_photo(chat_id, image_bytes, caption=None, reply_markup=None):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return tg("sendPhoto", data, files={"photo": ("post.png", image_bytes)})


def send_audio(chat_id, audio_bytes, title, caption=None):
    data = {"chat_id": chat_id, "title": title[:60]}
    if caption:
        data["caption"] = caption
    return tg("sendAudio", data, files={"audio": ("maslahat.mp3", audio_bytes)})



# ---------------------------------------------------------------- Qayta urinish
_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "504", "timed out", "Timeout", "Connection")


def with_retry(fn, *args, label: str = "", attempts: int = 6, base_delay: int = 10):
    """Vaqtincha xatolarda (503 'model band', 429, tarmoq) qayta uriniladi."""
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args)
        except Exception as error:
            text = str(error)
            transient = (any(marker in text for marker in _TRANSIENT_MARKERS)
                         and "limit: 0" not in text
                         and "PerDay" not in text)
            if not transient or attempt == attempts:
                raise
            delay = base_delay * attempt
            log.warning("%s vaqtincha xato (%s/%s): %s | %s soniyadan keyin qayta uriniladi",
                        label, attempt, attempts, text[:160], delay)
            time.sleep(delay)

IMAGE_MODELS = list(dict.fromkeys([GEMINI_IMAGE_MODEL, "gemini-3.1-flash-lite-image"]))


def make_image(prompt: str) -> bytes:
    """Avval asosiy rasm modeli, bo'lmasa zaxira model sinab ko'riladi."""
    last_error = None
    for model in IMAGE_MODELS:
        try:
            return with_retry(generate_image, prompt, model, label=f"Rasm ({model})")
        except Exception as error:
            last_error = error
            log.warning("Rasm modeli %s ishlamadi: %s", model, str(error)[:160])
    raise last_error


# ---------------------------------------------------------------- Kontent
def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def build_package(text_only: bool, want_audio: bool) -> dict:
    passed, last_reason, post, plain = False, "", None, ""
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        post = with_retry(generate_post, label="Matn")
        plain = strip_html(post["post_html"])
        passed, reason = with_retry(check_post, plain, label="QC")
        if passed:
            break
        last_reason = reason
        log.warning("QC rad etdi (%s/%s): %s", attempt, MAX_GENERATION_ATTEMPTS, reason)

    package = {
        "topic": post["topic"],
        "post_html": post["post_html"],
        "image_bytes": None,
        "audio_bytes": None,
        "qc_note": "" if passed else last_reason,
    }
    if not text_only:
        try:
            package["image_bytes"] = make_image(post["image_prompt"])
        except Exception:
            log.exception("Rasm generatsiya qilinmadi, rasmsiz davom etiladi")
    if want_audio:
        try:
            package["audio_bytes"] = with_retry(generate_audio, post["audio_script"], label="Audio")
        except Exception:
            log.exception("Audio generatsiya qilinmadi, audiosiz davom etiladi")
    return package


def plan_today(now: datetime) -> tuple[bool, bool]:
    day_index = (now.date() - EPOCH).days
    text_only = day_index % 3 == 2
    want_audio = now.weekday() == AUDIO_WEEKDAY
    if os.environ.get("FORCE_TEXT_ONLY", "").lower() == "true":
        text_only = True
    if os.environ.get("FORCE_AUDIO", "").lower() == "true":
        want_audio = True
    return text_only, want_audio


# ---------------------------------------------------------------- Yuborish
def send_preview(pkg: dict, run_id: str, wait_minutes: int) -> dict:
    caption = f"🕐 Bugungi post ({wait_minutes} daqiqadan keyin chiqadi):\n\n{pkg['post_html']}"
    if pkg["qc_note"]:
        caption += f"\n\n⚠️ QC eslatmasi: {html.escape(pkg['qc_note'])}"
    keyboard = {"inline_keyboard": [[{"text": "🔁 Qayta qilish", "callback_data": f"regen:{run_id}"}]]}

    if pkg["image_bytes"] and len(caption) <= 1024:
        message = send_photo(ADMIN_CHAT_ID, pkg["image_bytes"], caption, keyboard)
    else:
        if pkg["image_bytes"]:
            send_photo(ADMIN_CHAT_ID, pkg["image_bytes"])
        message = send_text(ADMIN_CHAT_ID, caption, keyboard)
    if pkg["audio_bytes"]:
        send_audio(ADMIN_CHAT_ID, pkg["audio_bytes"], pkg["topic"],
                   "🔊 Shu haftaning audio varianti (kanalga ham shu chiqadi)")
    return message


def publish(pkg: dict) -> None:
    caption = pkg["post_html"]
    if pkg["image_bytes"] and len(caption) <= 1024:
        send_photo(CHANNEL_ID, pkg["image_bytes"], caption)
    else:
        if pkg["image_bytes"]:
            send_photo(CHANNEL_ID, pkg["image_bytes"])
        send_text(CHANNEL_ID, caption)
    if pkg["audio_bytes"]:
        send_audio(CHANNEL_ID, pkg["audio_bytes"], pkg["topic"])
    log.info("Post kanalga chiqarildi: %s", pkg["topic"])


def remove_keyboard(message: dict) -> None:
    try:
        tg("editMessageReplyMarkup", {
            "chat_id": message["chat"]["id"],
            "message_id": message["message_id"],
            "reply_markup": json.dumps({"inline_keyboard": []}),
        })
    except Exception:
        log.warning("Tugmani olib tashlab bo'lmadi (muhim emas)")


# ---------------------------------------------------------------- Kutish
def latest_offset() -> int:
    updates = tg("getUpdates", {"offset": -1, "timeout": 0})
    return updates[-1]["update_id"] + 1 if updates else 0


def wait_for_regen(run_id: str, minutes: int, offset: int) -> bool:
    """True qaytarsa — admin 'Qayta qilish'ni bosgan."""
    deadline = time.time() + minutes * 60
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            return False
        updates = tg(
            "getUpdates",
            {
                "offset": offset,
                "timeout": int(min(25, max(1, remaining))),
                "allowed_updates": json.dumps(["callback_query"]),
            },
            timeout=45,
        )
        for update in updates:
            offset = update["update_id"] + 1
            query = update.get("callback_query")
            if not query or query.get("from", {}).get("id") != ADMIN_CHAT_ID:
                continue
            if query.get("data") == f"regen:{run_id}":
                tg("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Qayta ishlanmoqda..."})
                return True
            tg("answerCallbackQuery", {"callback_query_id": query["id"], "text": "Bu tugma eskirgan."})


# ---------------------------------------------------------------- Asosiy
def main() -> None:
    now = datetime.now(pytz.timezone(TIMEZONE))
    text_only, want_audio = plan_today(now)
    wait_minutes = int(os.environ.get("WAIT_MINUTES") or PREVIEW_MINUTES_BEFORE)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    log.info("Boshlandi: text_only=%s, audio=%s, kutish=%s daqiqa", text_only, want_audio, wait_minutes)

    tg("deleteWebhook", {})

    bot_info = tg("getMe", {})
    log.info("Bot: @%s (ID: %s) | ADMIN_CHAT_ID (secret): %s",
              bot_info.get("username"), bot_info["id"], ADMIN_CHAT_ID)
    if ADMIN_CHAT_ID == bot_info["id"]:
        raise RuntimeError(
            f"ADMIN_CHAT_ID ({ADMIN_CHAT_ID}) aynan bu botning o'z ID'siga teng — bu noto'g'ri. "
            f"GitHub Secret'da hali ham eski/bot ID saqlanyapti, u yangilanmagan. "
            f"@userinfobot'dan olingan SHAXSIY ID'ni qayta kiritib, 'Update secret'ni bosganingizga "
            f"ishonch hosil qiling."
        )

    try:
        send_text(ADMIN_CHAT_ID, "⏳ Post tayyorlanmoqda, taxminan 1-3 daqiqa kuting...")
    except RuntimeError as error:
        if "bot" in str(error) and "403" in str(error):
            raise RuntimeError(
                f"Telegram ADMIN_CHAT_ID={ADMIN_CHAT_ID}'ga yoza olmadi (bot ID: {bot_info['id']}). "
                f"Ehtimol siz botga hali /start bosmagansiz, yoki ADMIN_CHAT_ID guruh/kanal ID'si "
                f"(bunday holda manfiy raqam bo'ladi), sizning shaxsiy ID'ingiz emas."
            ) from error
        raise
    offset = latest_offset()

    package = build_package(text_only, want_audio)
    preview = send_preview(package, run_id, wait_minutes)

    regenerate = wait_for_regen(run_id, wait_minutes, offset)
    remove_keyboard(preview)

    if regenerate:
        log.info("Admin qayta qilishni so'radi")
        package = build_package(text_only, want_audio)

    publish(package)
    note = "✅ Yangilangan post kanalga chiqarildi." if regenerate else "✅ Post kanalga chiqarildi."
    send_text(ADMIN_CHAT_ID, note)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log.exception("Pipeline xatosi")
        try:
            send_text(ADMIN_CHAT_ID, f"❌ Autopost xatosi, post chiqmadi:\n<code>{html.escape(str(error))[:800]}</code>")
        except Exception:
            pass
        raise SystemExit(1)
