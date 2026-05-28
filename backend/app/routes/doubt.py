from fastapi import APIRouter, HTTPException

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt

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


@router.post("/answer")
def answer_student_doubt(data: DoubtRequest):
    """
    Answer a student's doubt.

    Required fields:
    - username
    - question

    subject and chapter are allowed to be empty for now because some existing
    tests and flows may ask a general question without selecting a chapter.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.question, "question")

    try:
        result = answer_doubt(
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            question=data.question,
            username=data.username,
        )

        return {
            "success": True,
            "answer": result.get("answer"),
            "source_type": result.get("source_type", "LLM"),
            "sources": result.get("sources", []),
            "mentor_suggestions": result.get("mentor_suggestions", []),
            "message": "Doubt answered successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "answer": None,
            "source_type": "ERROR",
            "sources": [],
            "mentor_suggestions": [],
            "message": f"Doubt answering failed: {str(e)}",
        }