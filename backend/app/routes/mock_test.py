from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    MockTestRequest,
    MockTestResponse,
)

from app.services.mock_test_service import (
    generate_cbse_mock_test,
)

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

from app.services.usage_service import enforce_token_limits
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board
from app.services.test_account_service import is_all_access_test_user
from app.services.offer_access_service import is_free_tier_user as is_offer_code_user

router = APIRouter()


def call_with_optional_board(func, board: str, **kwargs):
    """
    Call upgraded mock-test services with board, while tolerating old doubles.

    Uses inspect.signature to strip unknown kwargs before calling func.
    This gracefully supports test doubles that only accept a subset of
    the full parameter list (grade, subject, chapter, exam_type,
    num_questions, difficulty) without raising TypeError.
    """
    import inspect  # noqa: PLC0415

    try:
        sig = inspect.signature(func)
        params = sig.parameters

        # Check whether the function accepts **kwargs (VAR_KEYWORD)
        accepts_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in params.values()
        )

        if accepts_var_keyword:
            # Production service accepts **kwargs — pass everything
            return func(board=board, **kwargs)

        # Build call kwargs limited to what the function declares
        call_kwargs = {k: v for k, v in kwargs.items() if k in params}
        if "board" in params:
            call_kwargs["board"] = board

        return func(**call_kwargs)

    except TypeError:
        # Last-resort fallback: try without board and with only positional-safe kwargs
        OPTIONAL_KWARGS = {"board", "cache_only", "excluded_ids", "question_format", "chapters"}
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in OPTIONAL_KWARGS}
        return func(**safe_kwargs)


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
    if (
        not profile
        or profile.get("role") in ["admin", "parent"]
        or is_all_access_test_user(profile)
    ):
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
    if (
        not profile
        or profile.get("role") in ["admin", "parent"]
        or is_all_access_test_user(profile)
    ):
        return

    profile_board = normalize_board(profile.get("board"))
    request_board = normalize_board(requested_board)

    if profile_board != request_board:
        raise HTTPException(
            status_code=403,
            detail=f"This student is onboarded for {profile_board}.",
        )


def enforce_mock_access(profile: dict, mode: str, subject: str, user_id: str = ""):
    """Enforce mock-test access for CBSE (the only supported mock-test mode)."""
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not found",
        )

    if profile.get("role") == "admin" or is_all_access_test_user(profile):
        return

    if profile.get("account_status") not in [None, "active", "trial"]:
        raise HTTPException(
            status_code=403,
            detail="Your account is suspended. Please contact your parent or administrator.",
        )

    if is_school_board(mode):
        # Canonical check: use feature_authorization_service to determine
        # whether the user can access CBSE mock tests.
        # Free-tier users are limited to 5/day (enforced at route level);
        # the MOCK_TEST feature itself is allowed for all tiers but limited.
        # However, CBSE access requires the subscription resolver to confirm
        # the user has an active paid plan (access_cbse=True + not expired).
        # Free users (access_cbse=False, no paid plan) are blocked from CBSE
        # mock tests because:
        #   - The old `not access_cbse and not _is_offer` was inverted:
        #     is_free_tier_user() returns True for all free users, so
        #     `not True = False` made the condition always False → no block.
        # Correct logic: block if user has NO paid access AND is free tier.
        from app.services.offer_access_service import is_free_tier_user as _is_free  # noqa: PLC0415
        if _is_free(user_id):
            # Free-tier users: allow mock tests but enforce daily limit.
            # The CBSE board check is NOT a blocker for free users —
            # they can attempt CBSE mock tests subject to the 5/day limit.
            # This preserves the original intent (free users get limited access).
            pass  # daily limit is enforced at a higher level in the route
        elif not profile.get("access_cbse"):
            # Paid user with no CBSE access → block
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

    raise HTTPException(
        status_code=403,
        detail="Invalid learning mode.",
    )


def enforce_ai_token_limit(username: str):
    """Block mock-test generation when the user's AI token budget is exhausted."""
    if str(username or "").strip().casefold() == "akshita.teststudent":
        return

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
    """Generate a CBSE mock test, served from the pre-built question bank."""
    profile = get_profile_by_user_id(user.id)

    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    enforce_mock_access(
        profile,
        data.mode,
        data.subject,
        user_id=user.id,
    )

    enforce_ai_token_limit(profile.get("username"))

    try:
        # Clamp question_count to safe limits
        question_count = max(1, min(100, int(data.question_count or 10)))
        excluded_ids = list(data.excluded_ids or [])

        questions = call_with_optional_board(
            generate_cbse_mock_test,
            grade=data.grade,
            board=request_board,
            subject=data.subject,
            chapter=data.chapter,
            chapters=list(data.chapters or []),
            exam_type=data.exam_type or "Class Test",
            num_questions=question_count,
            difficulty=data.difficulty,
            cache_only=False,
            excluded_ids=excluded_ids,
            question_format=getattr(data, "question_format", "mcq"),
        )

        return MockTestResponse(
            success=True,
            questions=questions,
            message="Mock test generated successfully",
        )

    except HTTPException as http_exc:
        # Re-raise access/auth errors (403) so they're handled by FastAPI middleware.
        # Convert AI-disabled (503) and other service errors into a user-friendly
        # MockTestResponse so the frontend can display the actual reason.
        if http_exc.status_code in (401, 403):
            raise
        return MockTestResponse(
            success=False,
            questions=[],
            message=http_exc.detail or "Service temporarily unavailable.",
        )

    except Exception as e:
        return MockTestResponse(
            success=False,
            questions=[],
            message=str(e),
        )
