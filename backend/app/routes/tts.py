from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.models.schemas import TTSRequest
from app.services.tts_service import generate_speech_file

router = APIRouter()


@router.post("/generate")
def generate_tts(data: TTSRequest):
    """Generate an MP3 file for lesson read-aloud playback."""
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
