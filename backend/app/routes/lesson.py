from fastapi import APIRouter, HTTPException
from fastapi import Depends
from app.services.auth_service import get_current_user

from app.models.schemas import (
    LessonRequest,
    LessonFollowUpRequest,
    LessonFollowUpResponse,
)

from app.services.tutor_service import (
    generate_step_lesson,
    answer_lesson_follow_up,
)

router = APIRouter()


def validate_required_text(value: str, field_name: str):
    """
    Validate that a required text field is not empty.

    This catches both:
    - empty strings like ""
    - strings with only spaces like "   "

    If the value is empty, FastAPI will return HTTP 400.
    """
    if value is None or not value.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not be empty",
        )


@router.post("/generate")
def generate_lesson(data: LessonRequest):
    """
    Generate a lesson step for a student.

    Required fields:
    - username
    - grade
    - mode
    - subject
    - chapter
    - step_title

    teacher_persona is not validated here because it may be optional
    depending on your frontend flow.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.grade, "grade")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")

    try:
        result = generate_step_lesson(
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            mode=data.mode,
            step_title=data.step_title,
            teacher_persona=data.teacher_persona,
            username=data.username,
        )

        if isinstance(result, dict):
            lesson = result.get("lesson")
            source_type = result.get("source_type", "LLM")
            sources = result.get("sources", [])
        else:
            lesson = result
            source_type = "LLM"
            sources = []

        return {
            "success": True,
            "lesson": lesson,
            "source_type": source_type,
            "sources": sources,
            "message": "Lesson generated successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "lesson": None,
            "source_type": "LLM",
            "sources": [],
            "message": f"Lesson generation failed: {str(e)}",
        }


@router.post("/follow-up", response_model=LessonFollowUpResponse)
def lesson_follow_up(data: LessonFollowUpRequest):
    """
    Answer a student's follow-up question about a lesson.

    Required fields:
    - username
    - grade
    - mode
    - subject
    - chapter
    - step_title
    - lesson
    - question
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.grade, "grade")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")
    validate_required_text(data.lesson, "lesson")
    validate_required_text(data.question, "question")

    try:
        result = answer_lesson_follow_up(
            grade=data.grade,
            mode=data.mode,
            subject=data.subject,
            chapter=data.chapter,
            step_title=data.step_title,
            lesson=data.lesson,
            question=data.question,
            username=data.username,
        )

        return LessonFollowUpResponse(
            success=True,
            answer=result["answer"],
            source_type=result.get("source_type", "LLM"),
            sources=result.get("sources", []),
            message="Follow-up answered successfully",
        )

    except Exception as e:
        return LessonFollowUpResponse(
            success=False,
            answer=None,
            source_type="LLM",
            sources=[],
            message=f"Follow-up failed: {str(e)}",
        )
        

@router.post("/generate")
def generate_lesson(payload: dict, user=Depends(get_current_user)):
    user_id = user.id

    # existing logic here

    return result