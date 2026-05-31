from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt
from app.services.usage_service import enforce_token_limits

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

router = APIRouter()


def validate_required_text(value: str, field_name: str):
    if value is None or not value.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not be empty",
        )


def get_profile_by_user_id(user_id: str):
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


def enforce_learning_access(profile: dict, mode: str):
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
            detail="Account is not active.",
        )

    if mode == "CBSE":
        if not profile.get("access_cbse"):
            raise HTTPException(
                status_code=403,
                detail="CBSE access is not enabled.",
            )
        return

    if mode == "SOF":
        sof_enabled = (
            profile.get("access_sof_science")
            or profile.get("access_sof_maths")
            or profile.get("access_sof_english")
        )

        if not sof_enabled:
            raise HTTPException(
                status_code=403,
                detail="SOF access is not enabled.",
            )

        return

    raise HTTPException(
        status_code=403,
        detail="Invalid learning mode.",
    )


def enforce_ai_token_limit(username: str):
    limit_check = enforce_token_limits(username)

    if not limit_check.get("allowed"):
        raise HTTPException(
            status_code=403,
            detail=limit_check.get("message", "AI token limit reached."),
        )


@router.post("/answer")
def answer_student_doubt(
    data: DoubtRequest,
    user=Depends(get_current_user),
):
    validate_required_text(data.username, "username")
    validate_required_text(data.question, "question")

    profile = get_profile_by_user_id(user.id)
    enforce_learning_access(profile, data.mode)
    enforce_ai_token_limit(profile.get("username") or data.username)

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

    except HTTPException:
        raise

    except Exception as e:
        return {
            "success": False,
            "answer": None,
            "source_type": "ERROR",
            "sources": [],
            "mentor_suggestions": [],
            "message": f"Doubt answering failed: {str(e)}",
        }