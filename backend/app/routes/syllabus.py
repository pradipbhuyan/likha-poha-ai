from fastapi import APIRouter
from app.data.syllabus import SYLLABUS, LESSON_STEPS

router = APIRouter()


@router.get("")
def get_syllabus():
    """Return the static Grade 9 syllabus tree and lesson-step sequence."""
    return {
        "success": True,
        "syllabus": SYLLABUS,
        "lesson_steps": LESSON_STEPS
    }
