from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    LessonRequest,
    LessonFollowUpRequest,
    LessonFollowUpResponse,
)

from app.services.auth_service import get_current_user, admin_client
from app.services.usage_service import enforce_token_limits

from app.services.tutor_service import (
    generate_step_lesson,
    answer_lesson_follow_up,
)

router = APIRouter()


def validate_required_text(value: str, field_name: str):
    """Reject empty request fields before expensive lesson generation starts."""
    if value is None or not value.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not be empty",
        )


def get_profile_by_user_id(user_id: str):
    """Load access flags and status for the authenticated user profile."""
    response = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data


def normalize_grade(value: str | None):
    """Normalize stored/requested grade values to the app's Grade N label."""
    text = str(value or "Grade 9").strip()
    digits = "".join(char for char in text if char.isdigit())

    if digits:
        return f"Grade {int(digits)}"

    return text


def enforce_profile_grade(profile: dict, requested_grade: str):
    """Prevent students from requesting content outside their onboarded grade."""
    if not profile or profile.get("role") in ["admin", "parent"]:
        return

    profile_grade = normalize_grade(profile.get("grade"))
    request_grade = normalize_grade(requested_grade)

    if profile_grade != request_grade:
        raise HTTPException(
            status_code=403,
            detail=f"This student is onboarded for {profile_grade}.",
        )


def enforce_learning_access(profile: dict, mode: str, subject: str):
    """
    Enforce plan access for CBSE and subject-specific SOF lessons.

    Admins bypass student plan gates; all other users must be active/trial and
    have the exact access flag needed by the requested learning mode.
    """
    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found")

    if profile.get("role") == "admin":
        return

    if profile.get("account_status") not in [None, "active", "trial"]:
        raise HTTPException(
            status_code=403,
            detail="Your account is suspended. Please contact your parent or administrator.",
        )

    if mode == "CBSE":
        if not profile.get("access_cbse"):
            raise HTTPException(
                status_code=403,
                detail="CBSE access is not enabled for this student.",
            )
        return

    if mode == "SOF":
        if subject == "Science Olympiad" and not profile.get("access_sof_science"):
            raise HTTPException(
                status_code=403,
                detail="SOF Science access is not enabled for this student.",
            )

        if subject == "Maths Olympiad" and not profile.get("access_sof_maths"):
            raise HTTPException(
                status_code=403,
                detail="SOF Maths access is not enabled for this student.",
            )

        if subject == "English Olympiad" and not profile.get("access_sof_english"):
            raise HTTPException(
                status_code=403,
                detail="SOF English access is not enabled for this student.",
            )

        return

    raise HTTPException(
        status_code=403,
        detail="Invalid learning mode.",
    )


def enforce_ai_token_limit(username: str):
    """Convert the shared usage-limit service response into route HTTP errors."""
    limit_check = enforce_token_limits(username)

    if not limit_check.get("allowed"):
        raise HTTPException(
            status_code=403,
            detail=limit_check.get("message", "AI token limit reached."),
        )


@router.post("/generate")
def generate_lesson(
    data: LessonRequest,
    user=Depends(get_current_user),
):
    """
    Generate one lesson step for an authenticated user.

    The route validates profile access and token limits before invoking the LLM,
    then returns both the lesson and source metadata for frontend attribution.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.grade, "grade")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")

    profile = get_profile_by_user_id(user.id)
    enforce_profile_grade(profile, data.grade)
    enforce_learning_access(profile, data.mode, data.subject)
    enforce_ai_token_limit(profile.get("username") or data.username)

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

    except HTTPException:
        raise

    except Exception as e:
        return {
            "success": False,
            "lesson": None,
            "source_type": "LLM",
            "sources": [],
            "message": f"Lesson generation failed: {str(e)}",
        }


@router.post("/follow-up", response_model=LessonFollowUpResponse)
def lesson_follow_up(
    data: LessonFollowUpRequest,
    user=Depends(get_current_user),
):
    """
    Answer a student follow-up question about the current lesson step.

    It uses the same access/token gates as lesson generation so follow-up chats
    cannot bypass plan limits.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.grade, "grade")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")
    validate_required_text(data.lesson, "lesson")
    validate_required_text(data.question, "question")

    profile = get_profile_by_user_id(user.id)

    enforce_profile_grade(profile, data.grade)
    enforce_learning_access(profile, data.mode, data.subject)
    enforce_ai_token_limit(profile.get("username") or data.username)

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

    except HTTPException:
        raise

    except Exception as e:
        return LessonFollowUpResponse(
            success=False,
            answer=None,
            source_type="LLM",
            sources=[],
            message=f"Follow-up failed: {str(e)}",
        )
