from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    MockTestRequest,
    MockTestResponse,
)

from app.services.mock_test_service import (
    generate_olympiad_mock_test,
    generate_cbse_mock_test,
)
from app.services.model_routing_service import resolve_student_feature_model

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

from app.services.usage_service import enforce_token_limits
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board

router = APIRouter()


def call_with_optional_board(func, board: str, **kwargs):
    """Call upgraded mock-test services with board, while tolerating old doubles."""
    try:
        return func(board=board, **kwargs)
    except TypeError as error:
        if "unexpected keyword argument 'board'" not in str(error):
            raise
        return func(**kwargs)


def get_profile_by_user_id(user_id: str):
    """Load profile access fields used to gate mock-test generation."""
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
    """Prevent students from generating mock tests outside their onboarded grade."""
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
    """Prevent students from generating mock tests outside their onboarded board."""
    if not profile or profile.get("role") in ["admin", "parent"]:
        return

    profile_board = normalize_board(profile.get("board"))
    request_board = normalize_board(requested_board)

    if profile_board != request_board:
        raise HTTPException(
            status_code=403,
            detail=f"This student is onboarded for {profile_board}.",
        )


def enforce_mock_access(profile: dict, mode: str, subject: str):
    """
    Enforce mock-test access for CBSE and each SOF Olympiad subject.

    SOF mock tests are intentionally subject-specific because uploaded SOF RAG
    material, subscriptions, and parent-facing plan benefits are split by
    Science, Maths, and English.
    """
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not found",
        )

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
                detail=f"{access_label} access is not enabled.",
            )
        if not has_cbse_subject_access(profile, subject):
            subject_label = (
                f"CBSE {subject}"
                if normalize_board(mode) == "CBSE"
                else f"{normalize_board(mode)} {subject}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"{subject_label} access is not enabled.",
            )
        return

    if mode == "SOF":
        if (
            subject == "Science Olympiad"
            and not profile.get("access_sof_science")
        ):
            raise HTTPException(
                status_code=403,
                detail="SOF Science access is not enabled.",
            )

        if (
            subject == "Maths Olympiad"
            and not profile.get("access_sof_maths")
        ):
            raise HTTPException(
                status_code=403,
                detail="SOF Maths access is not enabled.",
            )

        if (
            subject == "English Olympiad"
            and not profile.get("access_sof_english")
        ):
            raise HTTPException(
                status_code=403,
                detail="SOF English access is not enabled.",
            )

        return

    raise HTTPException(
        status_code=403,
        detail="Invalid learning mode.",
    )


def enforce_ai_token_limit(username: str):
    """Block mock-test generation when the user's AI token budget is exhausted."""
    limit_check = enforce_token_limits(username)

    if not limit_check.get("allowed"):
        raise HTTPException(
            status_code=403,
            detail=limit_check.get("message", "AI token limit reached."),
        )


@router.post("/generate", response_model=MockTestResponse)
def generate_mock_test(
    data: MockTestRequest,
    user=Depends(get_current_user),
):
    """
    Generate either a CBSE mock test or an SOF RAG-based mock test.

    SOF tests route to the Olympiad generator, which requires uploaded RAG
    context; CBSE tests route to the general CBSE generator.
    """
    profile = get_profile_by_user_id(user.id)

    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    enforce_mock_access(
        profile,
        data.mode,
        data.subject,
    )

    enforce_ai_token_limit(profile.get("username"))

    try:
        if data.mock_type == "SOF Olympiad Mock Test":
            model = resolve_student_feature_model(
                profile,
                feature="sof_mock_test",
            )
            questions = generate_olympiad_mock_test(
                olympiad=data.subject,
                chapter=data.chapter,
                grade=data.grade,
                num_questions=data.question_count,
                difficulty=data.difficulty,
                username=profile.get("username") or "admin",
                model=model,
            )

        else:
            questions = call_with_optional_board(
                generate_cbse_mock_test,
                grade=data.grade,
                board=request_board,
                subject=data.subject,
                chapter=data.chapter,
                exam_type=data.exam_type or "Class Test",
                num_questions=data.question_count,
                difficulty=data.difficulty,
            )

        return MockTestResponse(
            success=True,
            questions=questions,
            message="Mock test generated successfully",
        )

    except HTTPException:
        raise

    except Exception as e:
        return MockTestResponse(
            success=False,
            questions=[],
            message=str(e),
        )
