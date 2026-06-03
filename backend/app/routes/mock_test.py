from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    MockTestRequest,
    MockTestResponse,
)

from app.services.mock_test_service import (
    generate_olympiad_mock_test,
    generate_cbse_mock_test,
)

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

from app.services.usage_service import enforce_token_limits

router = APIRouter()


def get_profile_by_user_id(user_id: str):
    """Load profile access fields used to gate mock-test generation."""
    response = (
        admin_client
        .table("profiles")
        .select(
            "id, username, role, access_cbse, access_sof_science, access_sof_maths, access_sof_english, account_status"
        )
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data


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

    if mode == "CBSE":
        if not profile.get("access_cbse"):
            raise HTTPException(
                status_code=403,
                detail="CBSE access is not enabled.",
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

    enforce_mock_access(
        profile,
        data.mode,
        data.subject,
    )

    enforce_ai_token_limit(profile.get("username"))

    try:
        if data.mock_type == "SOF Olympiad Mock Test":
            questions = generate_olympiad_mock_test(
                olympiad=data.subject,
                chapter=data.chapter,
                grade=data.grade,
                num_questions=data.question_count,
                difficulty=data.difficulty,
                username=profile.get("username") or "admin",
            )

        else:
            questions = generate_cbse_mock_test(
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
