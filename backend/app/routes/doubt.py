from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt
from app.services.usage_service import enforce_token_limits

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

router = APIRouter()


SOF_SUBJECT_ACCESS = {
    "science olympiad": "access_sof_science",
    "maths olympiad": "access_sof_maths",
    "mathematics olympiad": "access_sof_maths",
    "english olympiad": "access_sof_english",
}


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


def normalize_subject(subject: str):
    return (subject or "").strip().lower()


def enforce_learning_access(profile: dict, mode: str, subject: str = ""):
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
        subject_key = SOF_SUBJECT_ACCESS.get(normalize_subject(subject))

        if not subject_key:
            raise HTTPException(
                status_code=400,
                detail="Please select Science, Maths, or English Olympiad for SOF doubts.",
            )

        if not profile.get(subject_key):
            readable_subject = subject.replace(" Olympiad", "")
            raise HTTPException(
                status_code=403,
                detail=f"SOF {readable_subject} access is not enabled.",
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
    canonical_username = profile.get("username") or data.username

    enforce_learning_access(profile, data.mode, data.subject)
    enforce_ai_token_limit(canonical_username)

    try:
        result = answer_doubt(
            grade=data.grade,
            mode=data.mode,
            subject=data.subject,
            chapter=data.chapter,
            question=data.question,
            username=canonical_username,
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
