from fastapi import APIRouter
from app.data.syllabus import SYLLABUS, LESSON_STEPS

router = APIRouter()


@router.get("")
def get_syllabus():
    return {
        "success": True,
        "syllabus": SYLLABUS,
        "lesson_steps": LESSON_STEPS
    }