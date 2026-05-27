from fastapi import APIRouter

from app.models.schemas import AnswerEvaluationRequest
from app.services.evaluation_service import evaluate_student_answer
from app.services.evaluation_service import (
    evaluate_student_answer,
    generate_practice_questions,
)

router = APIRouter()


@router.post("/evaluate")
def evaluate_answer(data: AnswerEvaluationRequest):

    try:

        result = evaluate_student_answer(
            question=data.question,
            student_answer=data.student_answer,
            ideal_context=data.ideal_context,
            username=data.username,
        )

        return {
            "success": True,
            "evaluation": result.get("evaluation"),
            "score": result.get("score", 0),
            "passed": result.get("passed", False),
            "message": "Answer evaluated successfully",
        }

    except Exception as e:

        return {
            "success": False,
            "evaluation": None,
            "score": 0,
            "passed": False,
            "message": f"Evaluation failed: {str(e)}",
        }
        
@router.post("/practice-questions")
def create_practice_questions(data: AnswerEvaluationRequest):

    try:

        result = generate_practice_questions(
            lesson=data.ideal_context,
            chapter=data.question,
            step_title="Current lesson step",
            username=data.username,
        )

        return {
            "success": True,
            "questions": result.get("questions", []),
            "message": "Practice questions generated successfully",
        }

    except Exception as e:

        return {
            "success": False,
            "questions": [],
            "message": f"Practice question generation failed: {str(e)}",
        }