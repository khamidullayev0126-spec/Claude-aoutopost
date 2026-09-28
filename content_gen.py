"""
Gemini API orqali "Claude maslahatlar" rubrikasi uchun post matnini yozadi.
Natija Telegram HTML formatida qaytariladi (parse_mode="HTML" bilan yuboriladi).
"""
import json
import re
from google import genai

from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, RUBRIC_TOPIC_PROMPT

_client = genai.Client(api_key=GEMINI_API_KEY)

# Namuna kanal stilidan olingan yo'l-yo'riq: qalin sarlavha, emoji bilan
# ajratilgan qisqa abzatslar, aniq va foydali ohang, ortiqcha suv gapsiz.
_STYLE_GUIDE = """
STIL TALABLARI (Telegram HTML formatida yoz, faqat <b>, <i>, <a href="">, va \\n\\n dan foydalan):
- Til: o'zbek tili, tabiiy va samimiy ohang, lekin professional.
- Sarlavha: 1-qator, <b>qalin</b> va bitta mos emoji bilan boshlansin.
- Keyingi 2-4 ta qisqa abzats: har biri 1-3 gapdan, orasida bo'sh qator.
- Kerak bo'lsa muhim so'z yoki iboralarni <b>qalin</b> qilib ajrat.
- Post oxirida 1 ta amaliy xulosa yoki "buni sinab ko'ring" tarzidagi chaqiriq bo'lsin (link shart emas).
- Umumiy uzunlik: 600-1000 belgi (Telegram post uchun qulay uzunlik), ortiqcha cho'zma.
- Hech qanday o'ylab topilgan statistika, mualliflik, yoki tekshirilmagan "fakt" yozma —
  faqat umumiy tan olingan, ishonchli ma'lumotlardan foydalan.
- Hashtag yoki reklama matni qo'shma.
"""

_PROMPT_TEMPLATE = """
Sen "{rubric}" mavzusida ishlaydigan "Claude maslahatlar" nomli Telegram rubrikasi
uchun kontent yozuvchisan.

Vazifa: shu mavzu doirasida BITTA aniq, foydali va qiziqarli sub-mavzu tanla
(masalan: bitta AI vositasi, bitta dasturlash texnikasi, bitta amaliy maslahat yoki
bitta yangi tendensiya) va shu haqda post yoz.

{style}

Javobni FAQAT quyidagi JSON formatida qaytar, boshqa hech narsa yozma:
{{
  "topic": "tanlangan sub-mavzu nomi (o'zbekcha, qisqa)",
  "post_html": "Telegram HTML formatidagi to'liq post matni",
  "image_prompt": "shu post uchun rasm generatsiya qilish uchun ingliz tilida qisqa, aniq tavsif (odam yuzlari, matn, logotip bo'lmasin, minimalist/flat-illustration uslubida)",
  "audio_script": "post_html dagi HTML teglarsiz, ovozli o'qish uchun toza o'zbekcha matn"
}}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Model ba'zan ```json ... ``` bilan o'rab yuborishi mumkin
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Gemini javobidan JSON topilmadi: {text[:300]}")
    return json.loads(match.group(0))


def generate_post() -> dict:
    """
    Qaytaradi: {"topic", "post_html", "image_prompt", "audio_script"}
    """
    prompt = _PROMPT_TEMPLATE.format(rubric=RUBRIC_TOPIC_PROMPT, style=_STYLE_GUIDE)
    response = _client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
    )
    data = _extract_json(response.text)
    for key in ("topic", "post_html", "image_prompt", "audio_script"):
        if key not in data or not data[key]:
            raise ValueError(f"Gemini javobida '{key}' maydoni yo'q: {data}")
    return data
