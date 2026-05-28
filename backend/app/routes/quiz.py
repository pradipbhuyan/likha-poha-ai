from fastapi import APIRouter, HTTPException

from app.models.schemas import QuizRequest, QuizResponse
from app.services.quiz_service import generate_quiz

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


@router.post("/generate", response_model=QuizResponse)
def create_quiz(data: QuizRequest):
    """
    Generate quiz questions for a selected chapter.

    Required fields:
    - grade
    - subject
    - chapter
    - mode
    - difficulty

    question_count should also be a positive number.
    """
    validate_required_text(data.grade, "grade")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.difficulty, "difficulty")

    if data.question_count <= 0:
        raise HTTPException(
            status_code=400,
            detail="question_count must be greater than 0",
        )

    try:
        questions = generate_quiz(
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            mode=data.mode,
            difficulty=data.difficulty,
            count=data.question_count,
        )

        return QuizResponse(
            success=True,
            questions=questions,
            message="Quiz generated successfully",
        )

    except Exception as e:
        return QuizResponse(
            success=False,
            questions=[],
            message=f"Quiz generation failed: {str(e)}",
        )