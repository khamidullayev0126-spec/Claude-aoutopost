"""
Gemini rasm modeli (Nanobanana / gemini-2.5-flash-image) orqali post uchun
rasm generatsiya qiladi va PNG bayt sifatida qaytaradi.
"""
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)


def generate_image(image_prompt: str, model: str | None = None) -> bytes:
    full_prompt = (
        f"{image_prompt}. Style: clean, modern, minimalist flat illustration, "
        "soft color palette suitable for a tech/education Telegram channel cover. "
        "No text, no watermark, no logos, no human faces. 16:9 aspect ratio."
    )
    response = _client.models.generate_content(
        model=model or GEMINI_IMAGE_MODEL,
        contents=full_prompt,
    )
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data
    raise ValueError("Gemini javobida rasm (inline_data) topilmadi")
