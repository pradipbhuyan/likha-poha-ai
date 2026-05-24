from fastapi import APIRouter
from pydantic import BaseModel
from app.services.image_service import generate_educational_image

router = APIRouter()


class ImageRequest(BaseModel):
    prompt: str
    username: str = "unknown"


@router.post("/generate")
def generate_image(data: ImageRequest):
    return generate_educational_image(
        prompt=data.prompt,
        username=data.username,
    )
