from fastapi import APIRouter

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


@router.post("/generate")
def generate_lesson(data: LessonRequest):
    try:
        result = generate_step_lesson(
            grade=data.grade,
            mode=data.mode,
            subject=data.subject,
            chapter=data.chapter,
            step_title=data.step_title,
            teacher_persona=data.teacher_persona,
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
    try:
        result = answer_lesson_follow_up(
            grade=data.grade,
            mode=data.mode,
            subject=data.subject,
            chapter=data.chapter,
            step_title=data.step_title,
            lesson=data.lesson,
            question=data.question,
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
    