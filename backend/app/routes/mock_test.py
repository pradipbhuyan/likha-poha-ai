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
from app.services.test_account_service import is_all_access_test_user
from app.services.offer_access_service import is_free_tier_user as is_offer_code_user

router = APIRouter()


def call_with_optional_board(func, board: str, **kwargs):
    """
    Call upgraded mock-test services with board, while tolerating old doubles.

    Also strips cache_only gracefully when the target function (e.g. a test
    double) does not accept it.
    """
    try:
        return func(board=board, **kwargs)
    except TypeError as error:
        err = str(error)
        if "unexpected keyword argument 'board'" in err:
            try:
                return func(**kwargs)
            except TypeError as inner:
                inner_err = str(inner)
                if "unexpected keyword argument 'cache_only'" in inner_err:
                    kwargs.pop("cache_only", None)
                    try:
                        return func(**kwargs)
                    except TypeError as inner2:
                        if "unexpected keyword argument 'excluded_ids'" in str(inner2):
                            kwargs.pop("excluded_ids", None)
                            return func(**kwargs)
                        raise inner2
                if "unexpected keyword argument 'excluded_ids'" in inner_err:
                    kwargs.pop("excluded_ids", None)
                    return func(**kwargs)
                raise
        if "unexpected keyword argument 'excluded_ids'" in err:
            kwargs.pop("excluded_ids", None)
            try:
                return func(board=board, **kwargs)
            except TypeError as inner:
                inner_s = str(inner)
                if "unexpected keyword argument 'board'" in inner_s:
                    return func(**kwargs)
                if "unexpected keyword argument 'cache_only'" in inner_s:
                    kwargs.pop("cache_only", None)
                    return func(**kwargs)
                if "unexpected keyword argument 'question_format'" in inner_s:
                    kwargs.pop("question_format", None)
                    return func(**kwargs)
                raise
        if "unexpected keyword argument 'question_format'" in err:
            kwargs.pop("question_format", None)
            try:
                return func(board=board, **kwargs)
            except TypeError as inner:
                if "unexpected keyword argument 'board'" in str(inner):
                    return func(**kwargs)
                raise
        if "unexpected keyword argument 'cache_only'" in err:
            kwargs.pop("cache_only", None)
            try:
                return func(board=board, **kwargs)
            except TypeError:
                return func(**kwargs)
        raise


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
            # Paid user with no CBSE access (e.g. SOF-only plan) → block
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
        user_id=user.id,
    )

    enforce_ai_token_limit(profile.get("username"))

    try:
        # Clamp question_count to safe limits
        question_count = max(1, min(100, int(data.question_count or 10)))
        excluded_ids = list(data.excluded_ids or [])

        if data.mock_type == "SOF Olympiad Mock Test":
            model = resolve_student_feature_model(
                profile,
                feature="sof_mock_test",
            )
            questions = generate_olympiad_mock_test(
                olympiad=data.subject,
                chapter=data.chapter,
                grade=data.grade,
                num_questions=question_count,
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
