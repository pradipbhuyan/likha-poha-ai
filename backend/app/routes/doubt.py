from fastapi import APIRouter, HTTPException, Depends, File, UploadFile

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt
from app.services.usage_service import enforce_token_limits
from app.services.ocr_service import extract_text_from_image_bytes
from app.services.model_routing_service import resolve_student_feature_model
from app.services.doubt_history_service import (
    list_doubt_history,
    save_doubt_history,
)
from app.services.platform_info_service import (
    answer_platform_info,
    is_platform_info_question,
)
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board

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


def call_with_optional_board(func, board: str, **kwargs):
    """Call upgraded tutor services with board, while tolerating old test doubles."""
    try:
        return func(board=board, **kwargs)
    except TypeError as error:
        if "unexpected keyword argument 'board'" not in str(error):
            raise
        return func(**kwargs)


def validate_required_text(value: str, field_name: str):
    """Reject empty text fields before routing the doubt to AI services."""
    if value is None or not value.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must not be empty",
        )


def get_profile_by_user_id(user_id: str):
    """Load the signed-in user's role, account status, and learning access flags."""
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
    """Prevent students from asking doubts outside their onboarded grade."""
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
    """Prevent students from asking school-board doubts outside onboarding."""
    if not profile or profile.get("role") in ["admin", "parent"]:
        return

    profile_board = normalize_board(profile.get("board"))
    request_board = normalize_board(requested_board)

    if profile_board != request_board:
        raise HTTPException(
            status_code=403,
            detail=f"This student is onboarded for {profile_board}.",
        )


def normalize_subject(subject: str):
    """Normalize SOF subject text so UI aliases map to the same access flag."""
    return (subject or "").strip().lower()


def enforce_learning_access(profile: dict, mode: str, subject: str = ""):
    """
    Enforce CBSE/SOF doubt access for the authenticated profile.

    SOF doubts require a concrete Olympiad subject so Science, Maths, and English
    plan flags stay independent and RAG retrieval can be subject-targeted.
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
    """Stop doubt generation when the user's plan token limit is exhausted."""
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
    """
    Answer an authenticated student's doubt with RAG context and mentor memory.

    The route intentionally uses the username from the authenticated profile,
    not the request body, so clients cannot spoof another student's usage or
    mentor memory.
    """
    validate_required_text(data.username, "username")
    validate_required_text(data.question, "question")

    profile = get_profile_by_user_id(user.id)
    canonical_username = profile.get("username") or data.username

    # Access checks happen before token/LLM work so unauthorized SOF subjects do
    # not consume paid AI resources.
    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    enforce_learning_access(profile, data.mode, data.subject)

    if is_platform_info_question(data.question):
        result = answer_platform_info(data.question)
        history_item = None

        if data.save_to_history:
            display_question = (
                data.display_question
                or data.question.split("Preferred answer style:", 1)[0]
                or data.question
            ).strip()

            try:
                history_item = save_doubt_history(
                    client=admin_client,
                    profile_id=profile.get("id"),
                    username=canonical_username,
                    grade=data.grade,
                    mode=data.mode,
                    board=request_board,
                    subject=data.subject,
                    chapter=data.chapter,
                    question=display_question,
                    prompt_question=data.question,
                    answer=result.get("answer") or "",
                    source_type=result.get("source_type", "PLATFORM_RAG"),
                    sources=result.get("sources", []),
                    mentor_suggestions=result.get("mentor_suggestions", []),
                )
            except Exception as history_error:
                print(f"Doubt history save failed: {history_error}")

        return {
            "success": True,
            "answer": result.get("answer"),
            "source_type": result.get("source_type", "PLATFORM_RAG"),
            "sources": result.get("sources", []),
            "textbook_visuals": [],
            "mentor_suggestions": result.get("mentor_suggestions", []),
            "history_id": history_item.get("id") if history_item else None,
            "message": "Platform information answered successfully",
        }

    enforce_ai_token_limit(canonical_username)

    try:
        model = resolve_student_feature_model(
            profile,
            feature="doubt",
            question=data.question,
            mode=data.mode,
        )
        result = call_with_optional_board(
            answer_doubt,
            grade=data.grade,
            mode=data.mode,
            board=request_board,
            subject=data.subject,
            chapter=data.chapter,
            question=data.question,
            username=canonical_username,
            model=model,
        )
        history_item = None

        if data.save_to_history:
            display_question = (
                data.display_question
                or data.question.split("Preferred answer style:", 1)[0]
                or data.question
            ).strip()

            try:
                history_item = save_doubt_history(
                    client=admin_client,
                    profile_id=profile.get("id"),
                    username=canonical_username,
                    grade=data.grade,
                    mode=data.mode,
                    board=request_board,
                    subject=data.subject,
                    chapter=data.chapter,
                    question=display_question,
                    prompt_question=data.question,
                    answer=result.get("answer") or "",
                    source_type=result.get("source_type", "LLM"),
                    sources=result.get("sources", []),
                    mentor_suggestions=result.get("mentor_suggestions", []),
                )
            except Exception as history_error:
                print(f"Doubt history save failed: {history_error}")

        return {
            "success": True,
            "answer": result.get("answer"),
            "source_type": result.get("source_type", "LLM"),
            "sources": result.get("sources", []),
            "textbook_visuals": result.get("textbook_visuals", []),
            "mentor_suggestions": result.get("mentor_suggestions", []),
            "history_id": history_item.get("id") if history_item else None,
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
            "textbook_visuals": [],
            "mentor_suggestions": [],
            "history_id": None,
            "message": f"Doubt answering failed: {str(e)}",
        }


@router.get("/history")
def get_doubt_history(
    limit: int = 20,
    user=Depends(get_current_user),
):
    """Return recent full Ask Doubt answers for the authenticated student."""
    profile = get_profile_by_user_id(user.id)

    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not found",
        )

    return {
        "success": True,
        "history": list_doubt_history(
            client=admin_client,
            profile_id=profile.get("id"),
            limit=limit,
        ),
    }


@router.post("/extract-image")
async def extract_doubt_image(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """
    OCR a student's uploaded/camera image for use as doubt context.

    This endpoint only extracts text; it does not store the image. The frontend
    lets the student review/edit extracted text before sending it to Ask Doubt.
    """
    profile = get_profile_by_user_id(user.id)

    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not found",
        )

    if profile.get("account_status") not in [None, "active", "trial"]:
        raise HTTPException(
            status_code=403,
            detail="Your account is suspended. Please contact your parent or administrator.",
        )

    content_type = file.content_type or ""

    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG, JPEG, PNG, or WEBP image.",
        )

    try:
        image_bytes = await file.read()
        extracted_text = extract_text_from_image_bytes(image_bytes).strip()

        if not extracted_text:
            return {
                "success": False,
                "text": "",
                "message": "No readable text found in the image. Try a clearer photo.",
            }

        return {
            "success": True,
            "text": extracted_text,
            "message": "Image text extracted successfully.",
        }

    except HTTPException:
        raise

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "message": f"Image extraction failed: {str(e)}",
        }
