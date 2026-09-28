"""
Gemini yordamida postni sifat nazoratidan o'tkazadi:
- faktlarning to'g'riligi (shubhali/tekshirilmagan da'volar bormi)
- uzunlik (juda qisqa yoki juda uzun emasmi)
- ton (professional, samimiy, reklama emasmi)
"""
import json
import re

from google import genai

from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

_QC_PROMPT = """
Quyidagi Telegram post matnini tekshir (HTML teglarga e'tibor berma, faqat matnga qara):

---
{post_text}
---

Mezonlar:
1. FAKTLAR: post ichida tekshirilmagan, noaniq yoki noto'g'ri bo'lishi mumkin bo'lgan
   raqam/da'vo bormi?
2. UZUNLIK: matn juda qisqa (100 belgidan kam) yoki juda uzun (1500 belgidan ko'p)mi?
3. TON: matn professional va foydali ohangdami, ortiqcha reklama yoki mos kelmaydigan
   ohang yo'qmi?

Javobni FAQAT shu JSON formatida qaytar:
{{"pass": true yoki false, "reason": "agar pass=false bo'lsa, aniq sabab (o'zbekcha, qisqa)"}}
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"QC javobidan JSON topilmadi: {text[:300]}")
    return json.loads(match.group(0))


def check_post(post_text_plain: str) -> tuple[bool, str]:
    prompt = _QC_PROMPT.format(post_text=post_text_plain)
    response = _client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
    )
    data = _extract_json(response.text)
    return bool(data.get("pass", False)), data.get("reason", "")
