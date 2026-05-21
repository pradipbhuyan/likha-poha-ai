from fastapi import APIRouter

from app.models.schemas import QuizRequest, QuizResponse
from app.services.quiz_service import generate_quiz

router = APIRouter()


@router.post("/generate", response_model=QuizResponse)
def create_quiz(data: QuizRequest):
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
