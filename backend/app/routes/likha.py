import base64
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth_service import admin_client, get_current_user
from app.services.tts_service import clean_text_for_tts, generate_speech_file

router = APIRouter()

MAX_SPOKEN_CHARACTERS = 1800
SUPPORTED_LANGUAGES = {
    "en-IN": "en-IN",
    "en": "en-IN",
    "hi-IN": "hi-IN",
    "hi": "hi-IN",
}
VOICE_BY_LANGUAGE = {
    "en-IN": "en-IN-NeerjaNeural",
    "hi-IN": "hi-IN-SwaraNeural",
}
UNSPEAKABLE_SOURCE_TYPES = {"ERROR"}


class SpeakDoubtAnswerRequest(BaseModel):
    """Request playback only for an answer the server has already stored."""

    history_id: str = Field(min_length=1, max_length=128)
    language: str = Field(default="en-IN", max_length=16)
    reply_style: Literal["full", "concise", "full_follow_up"] = "full"


def _get_profile(user_id: str) -> dict:
    """Load the caller profile used to verify answer ownership and role."""
    response = (
        admin_client
        .table("profiles")
        .select("id, role, account_status")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return response.data or {}


def _load_owned_history_answer(history_id: str, profile_id: str) -> dict | None:
    """Load a doubt history record only when it belongs to the signed-in user."""
    response = (
        admin_client
        .table("doubt_history")
        .select("id, answer, source_type")
        .eq("id", history_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _normalize_language(language: str) -> str:
    """Normalize supported browser language values to the configured voice."""
    normalized = SUPPORTED_LANGUAGES.get(str(language or "").strip())
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Choose English or Hindi for Likha's voice.",
        )
    return normalized


def _spoken_text(answer: str, reply_style: str) -> str:
    """Clean server-owned answer text and enforce predictable speech limits."""
    cleaned = clean_text_for_tts(answer or "").strip()
    if not cleaned:
        return ""

    limit = 700 if reply_style == "concise" else MAX_SPOKEN_CHARACTERS
    if len(cleaned) > limit:
        cleaned = f"{cleaned[:limit].rsplit(' ', 1)[0].strip()}."

    if reply_style == "full_follow_up":
        cleaned = f"{cleaned} Do you have a follow-up question? Tap Speak follow-up to continue with Likha."

    return cleaned


def _generate_audio_data_url(text: str, voice: str) -> str:
    """Generate an ephemeral MP3 data URL; no personalized answer is shared."""
    mp3_path = generate_speech_file(
        text,
        voice=voice,
        rate="+5%",
        pitch="+5Hz",
    )
    try:
        with open(mp3_path, "rb") as audio_file:
            encoded = base64.b64encode(audio_file.read()).decode("ascii")
    finally:
        try:
            os.remove(mp3_path)
        except OSError:
            pass
    return f"data:audio/mpeg;base64,{encoded}"


@router.post("/speak-doubt-answer")
def speak_doubt_answer(
    data: SpeakDoubtAnswerRequest,
    user=Depends(get_current_user),
):
    """
    Generate speech for an answer owned by the caller.

    The endpoint intentionally accepts only a history ID, never answer text.
    This prevents it from becoming a general arbitrary-text TTS service and
    guarantees the displayed written answer remains the source of truth.
    """
    profile = _get_profile(user.id)
    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found")

    if profile.get("role") != "student":
        raise HTTPException(
            status_code=403,
            detail="Likha Voice Tutor is available to student accounts only.",
        )

    if profile.get("account_status") not in (None, "active", "trial"):
        raise HTTPException(
            status_code=403,
            detail="Your account is not currently active.",
        )

    language = _normalize_language(data.language)
    history = _load_owned_history_answer(data.history_id, profile["id"])
    if not history:
        raise HTTPException(
            status_code=404,
            detail="That answer is unavailable for voice playback.",
        )

    if str(history.get("source_type") or "").upper() in UNSPEAKABLE_SOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="This answer is unavailable for voice playback.",
        )

    spoken_text = _spoken_text(history.get("answer") or "", data.reply_style)
    if not spoken_text:
        raise HTTPException(
            status_code=400,
            detail="There is no answer available to read aloud.",
        )

    voice = VOICE_BY_LANGUAGE[language]
    try:
        audio_url = _generate_audio_data_url(spoken_text, voice)
    except Exception:
        # Browser Speech Synthesis is the intentional client fallback.
        return {
            "success": False,
            "audio_url": None,
            "voice": voice,
            "spoken_text": spoken_text,
            "cached": False,
            "message": "Likha's neural voice is temporarily unavailable.",
        }

    return {
        "success": True,
        "audio_url": audio_url,
        "voice": voice,
        "spoken_text": spoken_text,
        "cached": False,
    }
