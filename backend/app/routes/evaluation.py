from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import AnswerEvaluationRequest
from app.services.evaluation_service import (
    evaluate_student_answer,
    generate_practice_questions,
)
from app.services.auth_service import get_current_user
from app.services.offer_access_service import is_free_tier_user
from app.services.test_account_service import is_all_access_test_user

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


@router.post("/evaluate")
def evaluate_answer(
    data: AnswerEvaluationRequest,
    user=Depends(get_current_user),
):
    """
    Evaluate a student's answer.

    This endpoint requires:
    - username
    - question
    - student_answer
    - ideal_context

    Empty values are rejected before calling the evaluation service.

    Tier gating for AI feedback (see evaluation_service.evaluate_student_answer
    and offer_access_service.py for the full policy):
    - Both free and paid tiers get instant, zero-cost keyword-scored feedback
      whenever the question has expected_keywords (the GPT-5.5-authored
      subjective_question_bank we ingest offline, or admin-prewarmed lesson
      practice questions).
    - Free tier NEVER reaches a live LLM call -- if a question has no
      expected_keywords, free-tier users see an upgrade prompt instead.
    - Paid tier can fall back to a live LLM call for such questions, capped
      at 10/day (mirrors the Ask Doubt paid-tier LLM cap).
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.question, "question")
    validate_required_text(data.student_answer, "student_answer")
    validate_required_text(data.ideal_context, "ideal_context")

    is_free = is_free_tier_user(user.id) and not is_all_access_test_user(
        {"username": data.username}
    )

    try:
        result = evaluate_student_answer(
            grade=data.grade,
            question=data.question,
            student_answer=data.student_answer,
            ideal_context=data.ideal_context,
            username=data.username,
            mode=data.mode,
            subject=data.subject,
            chapter=data.chapter,
            step_title=data.step_title,
            question_type=data.question_type,
            expected_keywords=data.expected_keywords,
            correct_answer=data.correct_answer,
            is_free=is_free,
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
def create_practice_questions(
    data: AnswerEvaluationRequest,
    user=Depends(get_current_user),
):
    """
    Generate practice questions from lesson context.

    This endpoint uses:
    - ideal_context as the lesson text
    - question as the chapter/topic label

    Empty values are rejected before calling the question generation service.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.question, "question")
    validate_required_text(data.ideal_context, "ideal_context")

    try:
        result = generate_practice_questions(
            grade=data.grade,
            lesson=data.ideal_context,
            chapter=data.chapter or data.question,
            step_title=data.step_title or "Current lesson step",
            username=data.username,
            subject=data.subject,
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
