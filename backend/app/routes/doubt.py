from fastapi import APIRouter

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt

router = APIRouter()


@router.post("/answer")
def answer_student_doubt(data: DoubtRequest):

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
            "success": True,
            "answer": result.get("answer"),
            "source_type": result.get("source_type", "LLM"),
            "sources": result.get("sources", []),
            "mentor_suggestions": result.get("mentor_suggestions", []),
            "message": "Doubt answered successfully",
        }   