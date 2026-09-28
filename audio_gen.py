"""
ElevenLabs Text-to-Speech API orqali post matnini audio (MP3) ko'rinishiga
o'giradi.
"""
import requests

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"


def generate_audio(script_text: str) -> bytes:
    response = requests.post(
        _TTS_URL,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": script_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.content
