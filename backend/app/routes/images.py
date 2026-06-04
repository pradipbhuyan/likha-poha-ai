from fastapi import APIRouter
from pydantic import BaseModel
from app.services.image_service import generate_educational_image

router = APIRouter()


class ImageRequest(BaseModel):
    prompt: str
    username: str = "unknown"
    grade: str = ""
    mode: str = "CBSE"
    subject: str = ""
    chapter: str = ""


@router.post("/generate")
def generate_image(data: ImageRequest):
    """Generate an educational image for a lesson visual prompt."""
    return generate_educational_image(
        prompt=data.prompt,
        username=data.username,
        grade=data.grade,
        mode=data.mode,
        subject=data.subject,
        chapter=data.chapter,
    )
