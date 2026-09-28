"""
Barcha sozlamalar environment variable'lardan o'qiladi.
Render Dashboard -> Environment bo'limida shu nomlar bilan qo'shiladi.
Hech qanday kalit/token kodda hardcode qilinmaydi.
"""
import os

# --- Majburiy kalitlar ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]

# Post chiqadigan kanal (masalan: @AbdulhamidDasturchi_kundaligi yoki -100... ID)
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@AbdulhamidDasturchi_kundaligi")

# Sizning shaxsiy Telegram chat ID'ingiz — bot preview va "Qayta qilish"
# tugmasini shu chatga yuboradi. Buni qanday topish README.md'da yozilgan.
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])

# ElevenLabs ovoz ID (default: ElevenLabs'ning tayyor ovozlaridan biri,
# xohlasangiz o'zingizning tanlagan voice_id'ingizga almashtiring)
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# Gemini modellari
GEMINI_TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Vaqt mintaqasi va jadval
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Tashkent")
PUBLISH_HOUR = int(os.environ.get("PUBLISH_HOUR", "17"))
PUBLISH_MINUTE = int(os.environ.get("PUBLISH_MINUTE", "0"))
PREVIEW_MINUTES_BEFORE = int(os.environ.get("PREVIEW_MINUTES_BEFORE", "10"))

# Rubrika mavzusi
RUBRIC_TOPIC_PROMPT = os.environ.get(
    "RUBRIC_TOPIC_PROMPT",
    "Sun'iy intellekt (AI)dan foydalanish va dasturlash sohasidagi so'nggi "
    "yangiliklar, foydali faktlar va amaliy maslahatlar",
)

# Holat fayli (Render Persistent Disk ulangan bo'lsa shu yerga yoziladi,
# aks holda /tmp'ga yoziladi va deploy/restart'da hisoblagichlar nollanadi)
STATE_FILE = os.environ.get("STATE_FILE_PATH", "/tmp/autopost_state.json")
