from fastapi import APIRouter
from app.data.resources import get_learning_resources

router = APIRouter()


@router.get("")
def get_resources(subject: str, chapter: str, grade: str = "Grade 9"):
    """Return curated learning resources for the selected subject/chapter."""
    return {
        "success": True,
        "resources": get_learning_resources(subject, chapter, grade)
    }
