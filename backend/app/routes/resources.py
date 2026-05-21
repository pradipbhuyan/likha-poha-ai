from fastapi import APIRouter
from app.data.resources import get_learning_resources

router = APIRouter()


@router.get("")
def get_resources(subject: str, chapter: str):
    return {
        "success": True,
        "resources": get_learning_resources(subject, chapter)
    }