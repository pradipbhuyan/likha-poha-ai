from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from app.models.schemas import TTSRequest
from app.services.tts_service import generate_speech_file

router = APIRouter()


@router.post("/generate")
def generate_tts(data: TTSRequest):
    """
    Generate an MP3 file for lesson read-aloud playback.

    Performance path: caller should first check GET /tts/cached-url to see
    if a pre-warmed audio URL exists (instant, no TTS cost). This endpoint is
    the fallback when no cached audio is available.
    """
    audio_path = generate_speech_file(
        text=data.text,
        voice=data.voice,
        rate=data.rate,
        pitch=data.pitch,
    )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename="lesson.mp3",
    )


@router.get("/cached-url")
def get_cached_audio_url(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    voice: str = "en-IN-NeerjaNeural",
    rate: str = "+0%",
):
    """
    Check if pre-warmed audio exists for this lesson step.

    Returns { cached: true, url: "https://..." } if found — frontend plays
    directly from Supabase CDN (instant, no generation delay).
    Returns { cached: false } if not found — frontend falls back to /tts/generate.

    Called by the frontend Listen button BEFORE calling /tts/generate.
    """
    try:
        from app.services.audio_cache_service import get_cached_audio_url as _get_url  # noqa: PLC0415
        url = _get_url(grade, subject, chapter, step_title, voice, rate)
        if url:
            return JSONResponse({"cached": True, "url": url})
        return JSONResponse({"cached": False})
    except Exception:
        # audio_cache table may not exist yet during migration — fail gracefully
        return JSONResponse({"cached": False})


@router.get("/audio-cache/overview")
def get_audio_cache_overview(grade: str | None = None):
    """
    Admin endpoint: summary of pre-warmed audio cache.
    Shows total files, MB, and breakdown by grade.
    """
    try:
        from app.services.audio_cache_service import get_audio_cache_overview as _overview  # noqa: PLC0415
        return JSONResponse(_overview(grade))
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)})
