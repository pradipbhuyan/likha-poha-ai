"""Generate and upload shared, instant-play Likha welcome MP3 assets.

Run from backend/ with configured Supabase and Edge TTS environment variables:
    python3 scripts/prewarm_likha_welcome_audio.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from app.services.audio_cache_service import store_likha_welcome_audio
from app.services.tts_service import generate_speech_file

WELCOME_ASSETS = (
    (
        "en-IN-NeerjaNeural",
        "Hello! I’m Likha. I can read this lesson aloud, one chapter path at a time.",
    ),
    (
        "hi-IN-SwaraNeural",
        "नमस्ते! मैं लिखा हूँ। मैं इस पाठ को एक-एक भाग करके आपको पढ़कर सुना सकती हूँ।",
    ),
)


def main() -> None:
    for voice, text in WELCOME_ASSETS:
        mp3_path = generate_speech_file(
            text=text,
            voice=voice,
            rate="+5%",
            pitch="+5Hz",
        )
        try:
            with open(mp3_path, "rb") as audio_file:
                url = store_likha_welcome_audio(voice, audio_file.read())
        finally:
            try:
                os.remove(mp3_path)
            except OSError:
                pass

        print(f"Uploaded {voice} welcome audio: {url}")


if __name__ == "__main__":
    main()
