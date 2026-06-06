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
from app.services.doubt_history_service import save_doubt_history
from app.services.platform_info_service import (
    answer_platform_info,
    is_platform_info_question,
)
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board

router = APIRouter()


def call_with_optional_board(func, board: str, **kwargs):
    """Call upgraded services with board, while tolerating older test doubles."""
    try:
        return func(board=board, **kwargs)
    except TypeError as error:
        if "unexpected keyword argument 'board'" not in str(error):
            raise
        return func(**kwargs)


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


def enforce_profile_board(profile: dict, requested_board: str):
    """Prevent students from requesting school-board content outside onboarding."""
    if not profile or profile.get("role") in ["admin", "parent"]:
        return

    profile_board = normalize_board(profile.get("board"))
    request_board = normalize_board(requested_board)

    if profile_board != request_board:
        raise HTTPException(
            status_code=403,
            detail=f"This student is onboarded for {profile_board}.",
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

    if is_school_board(mode):
        if not profile.get("access_cbse"):
            access_label = "CBSE" if normalize_board(mode) == "CBSE" else "School-board"
            raise HTTPException(
                status_code=403,
                detail=f"{access_label} access is not enabled for this student.",
            )
        if not has_cbse_subject_access(profile, subject):
            subject_label = (
                f"CBSE {subject}"
                if normalize_board(mode) == "CBSE"
                else f"{normalize_board(mode)} {subject}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"{subject_label} access is not enabled for this student.",
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
    validate_required_text(data.board, "board")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")

    profile = get_profile_by_user_id(user.id)
    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    enforce_learning_access(profile, data.mode, data.subject)

    enforce_ai_token_limit(profile.get("username") or data.username)

    try:
        result = call_with_optional_board(
            generate_step_lesson,
            grade=data.grade,
            board=request_board,
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
    validate_required_text(data.board, "board")
    validate_required_text(data.mode, "mode")
    validate_required_text(data.subject, "subject")
    validate_required_text(data.chapter, "chapter")
    validate_required_text(data.step_title, "step_title")
    validate_required_text(data.lesson, "lesson")
    validate_required_text(data.question, "question")

    profile = get_profile_by_user_id(user.id)

    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    enforce_learning_access(profile, data.mode, data.subject)

    if is_platform_info_question(data.question):
        result = answer_platform_info(data.question)
        history_item = None

        try:
            history_item = save_doubt_history(
                client=admin_client,
                profile_id=profile.get("id"),
                username=profile.get("username") or data.username,
                grade=data.grade,
                mode=data.mode,
                board=request_board,
                subject=data.subject,
                chapter=data.chapter,
                question=data.question,
                prompt_question=data.question,
                answer=result.get("answer") or "",
                source_type="LESSON_PLATFORM_RAG",
                sources=result.get("sources", []),
                mentor_suggestions=[],
            )
        except Exception as history_error:
            print(f"Lesson follow-up history save failed: {history_error}")

        return LessonFollowUpResponse(
            success=True,
            answer=result["answer"],
            source_type=result.get("source_type", "PLATFORM_RAG"),
            sources=result.get("sources", []),
            history_id=history_item.get("id") if history_item else None,
            message="Platform information answered successfully",
        )

    enforce_ai_token_limit(profile.get("username") or data.username)

    try:
        result = call_with_optional_board(
            answer_lesson_follow_up,
            grade=data.grade,
            mode=data.mode,
            board=request_board,
            subject=data.subject,
            chapter=data.chapter,
            step_title=data.step_title,
            lesson=data.lesson,
            question=data.question,
            username=data.username,
        )

        history_item = None

        try:
            history_item = save_doubt_history(
                client=admin_client,
                profile_id=profile.get("id"),
                username=profile.get("username") or data.username,
                grade=data.grade,
                mode=data.mode,
                board=request_board,
                subject=data.subject,
                chapter=data.chapter,
                question=data.question,
                prompt_question=data.question,
                answer=result.get("answer") or "",
                source_type="LESSON_FOLLOW_UP",
                sources=result.get("sources", []),
                mentor_suggestions=[],
            )
        except Exception as history_error:
            print(f"Lesson follow-up history save failed: {history_error}")

        return LessonFollowUpResponse(
            success=True,
            answer=result["answer"],
            source_type=result.get("source_type", "LLM"),
            sources=result.get("sources", []),
            history_id=history_item.get("id") if history_item else None,
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
            history_id=None,
            message=f"Follow-up failed: {str(e)}",
        )
