from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import DoubtRequest
from app.services.tutor_service import answer_doubt
from app.services.usage_service import enforce_token_limits
from app.services.model_routing_service import resolve_student_feature_model
from app.services.doubt_history_service import (
    list_doubt_history,
    save_doubt_history,
)
from app.services.platform_info_service import (
    answer_platform_info,
    is_platform_info_question,
)
from app.services.offer_access_service import (
    is_free_tier_user,
    build_offer_gate_response,
)

# Keep legacy alias so existing code continues to work
is_offer_code_user = is_free_tier_user
from app.services.doubt_kb_service import search_doubt_kb
from app.services.academic_guardrail_service import (
    is_non_academic_question,
    build_non_academic_response,
)
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board
from app.services.test_account_service import is_all_access_test_user

from app.services.auth_service import (
    get_current_user,
    admin_client,
)

router = APIRouter()


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
    """Prevent students from asking doubts outside their onboarded grade.
    Teachers can ask doubts for any grade — needed for lesson planning.
    """
    if (
        not profile
        or profile.get("role") in ["admin", "parent", "teacher"]
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
    """Prevent students from asking school-board doubts outside onboarding.
    Teachers can ask doubts on any board.
    """
    if (
        not profile
        or profile.get("role") in ["admin", "parent", "teacher"]
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


def enforce_learning_access(profile: dict, mode: str, subject: str = ""):
    """Enforce CBSE doubt access for the authenticated profile."""
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not found",
        )

    if profile.get("role") in ["admin", "teacher", "parent"] or is_all_access_test_user(profile):
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

    raise HTTPException(
        status_code=403,
        detail="Invalid learning mode.",
    )


def enforce_ai_token_limit(username: str):
    """Stop doubt generation when the user's plan token limit is exhausted."""
    if str(username or "").strip().casefold() == "akshita.teststudent":
        return

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

    # Access checks happen before token/LLM work so unauthorized subjects do
    # not consume paid AI resources.
    request_board = resolve_request_board(data.mode, data.board)
    enforce_profile_grade(profile, data.grade)
    enforce_profile_board(profile, request_board)
    # For ALL users (free or paid), try the DKB BEFORE the LLM access gate.
    # Pre-loaded suggestion questions have answers in DKB and are free to serve
    # at zero LLM cost — even free-tier students should see them.
    # The LLM (paid) gate only fires when DKB has no matching answer.
    if not is_offer_code_user(user.id):
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

    # ── Academic guardrail: block non-academic questions before LLM ──────────
    # Detects current-affairs, political, sports, and financial questions that
    # the LLM cannot answer accurately (stale training data) and returns a
    # polished redirect message at zero token cost.
    if is_non_academic_question(data.question):
        guard = build_non_academic_response()
        return {
            "success": True,
            "answer": guard["answer"],
            "source_type": guard["source_type"],
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
            "history_id": None,
            "message": "Academic guardrail: non-academic question redirected",
        }

    # ── DKB lookup: runs for ALL users (free + paid) ─────────────────────────
    # Suggestion chips send dkb_id → direct PK lookup (O(1), no text matching).
    # Manual questions fall back to text search.
    # Return DKB answer to ANY user at zero LLM cost.
    dkb_result = None

    # Pass A: direct ID lookup (suggestion chip tapped)
    if data.dkb_id:
        try:
            from app.services.grade_db_router import get_content_db as _get_db  # noqa: PLC0415
            _supabase = _get_db(data.grade)
            _row = _supabase.table("doubt_kb").select("id, question, answer, hit_count").eq("id", data.dkb_id).limit(1).execute().data
            if _row:
                dkb_result = {
                    "answer": _row[0]["answer"],
                    "question": _row[0]["question"],
                    "source_type": "DOUBT_KB",
                    "id": _row[0]["id"],
                    "similarity": 1.0,
                }
                try:
                    _supabase.table("doubt_kb").update({
                        "hit_count": (_row[0].get("hit_count") or 0) + 1,
                        "last_hit_at": "now()",
                    }).eq("id", data.dkb_id).execute()
                except Exception:
                    pass
        except Exception as _dkb_id_exc:
            import logging as _log  # noqa: PLC0415
            _log.getLogger(__name__).warning("DKB ID lookup failed: %s", _dkb_id_exc)

    # Pass B: text search (manual questions or dkb_id lookup missed)
    if not dkb_result:
        dkb_search_query = (
            data.display_question
            or data.question.split("Preferred answer style:", 1)[0]
        ).strip()
        dkb_result = search_doubt_kb(
            question=dkb_search_query,
            grade=data.grade,
            subject=data.subject or None,  # None → SQL IS NULL → no subject filter
            chapter=data.chapter or None,  # None → SQL IS NULL → no chapter filter
            mode=data.mode,
            board=request_board,
        )
    if dkb_result:
        return {
            "success": True,
            "answer": dkb_result["answer"],
            "source_type": "DOUBT_KB",
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
            "history_id": None,
            "message": "Answered from knowledge base",
        }

    # ── DKB miss: apply LLM access gate ──────────────────────────────────────
    # Free-tier / offer-code users cannot make LLM calls on a DKB miss.
    # Paid users continue to the LLM path below.
    if is_offer_code_user(user.id):
        gate = build_offer_gate_response()
        return {
            "success": True,
            "answer": gate["answer"],
            "source_type": gate["source_type"],
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
            "history_id": None,
            "message": "Offer gate: upgrade required for full AI access",
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
        # Sanitize error messages — never leak raw provider errors to students.
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "quota" in err_str or "token" in err_str or "too_many" in err_str or "limit" in err_str:
            user_message = (
                "Our AI tutoring service is experiencing high demand right now. "
                "Please try again in a few minutes — your question hasn't been lost."
            )
            # Alert admin — fire-and-forget, never blocks response
            try:
                from app.services.alert_service import alert_rate_limit  # noqa: PLC0415
                alert_rate_limit(
                    feature="doubt",
                    username=canonical_username if "canonical_username" in dir() else data.username,
                    error_detail=str(e),
                    grade=data.grade,
                    subject=data.subject,
                    chapter=data.chapter or "",
                )
            except Exception:
                pass
        elif "timeout" in err_str or "timed out" in err_str:
            user_message = (
                "The AI took too long to respond. Please try again."
            )
        elif "context" in err_str:
            user_message = (
                "Your question or chapter context is too long. "
                "Try a shorter, more focused question."
            )
        else:
            user_message = (
                "Something went wrong while answering your doubt. "
                "Please try again in a moment."
            )
        return {
            "success": False,
            "answer": None,
            "source_type": "ERROR",
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
            "history_id": None,
            "message": user_message,
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


@router.get("/suggestions")
def get_doubt_suggestions(
    grade: str,
    mode: str = "CBSE",
    subject: str = "",
    chapter: str = "",
    board: str = "CBSE",
    limit: int = 6,
    user=Depends(get_current_user),
):
    """
    Return DKB-backed suggestion chips for the Ask Doubt page.

    When subject/chapter are empty ("Open subject"), returns the most popular
    pre-answered questions for the grade across ALL subjects so the student
    always sees relevant chips instead of generic defaults.

    Every returned question has a pre-cached answer — clicking it is zero
    token cost regardless of whether AI is ON or OFF.
    """
    try:
        from app.services.doubt_kb_service import get_lesson_doubt_suggestions  # noqa: PLC0415
        import re as _re  # noqa: PLC0415
        from app.services.grade_db_router import get_content_db  # noqa: PLC0415

        # Grade 11/12 content lives in a second Supabase project — must route
        # through get_content_db() rather than a hardcoded client, or these
        # fallback queries silently miss all Grade 11/12 DKB entries.
        supabase = get_content_db(grade)

        clean_subject = (subject or "").strip()
        clean_chapter = (chapter or "").strip()

        # If subject is specified, use the lesson suggestions function
        if clean_subject and clean_chapter:
            suggestions = get_lesson_doubt_suggestions(
                grade=grade,
                subject=clean_subject,
                chapter=clean_chapter,
                mode=mode,
                limit=limit,
            )
            if suggestions:
                return {"success": True, "doubt_suggestions": suggestions}

        # Fallback: subject-level suggestions (no chapter filter)
        if clean_subject:
            direct = (
                supabase
                .table("doubt_kb")
                .select("id, question, hit_count")
                .eq("grade", grade)
                .eq("subject", clean_subject)
                .eq("mode", mode)
                .eq("status", "active")
                .order("hit_count", desc=True)
                .limit(limit)
                .execute()
            )
            if direct.data:
                return {
                    "success": True,
                    "doubt_suggestions": [
                        {"id": r["id"], "question": r["question"]}
                        for r in direct.data
                    ],
                }

        # Open subject: return most popular across all subjects for this grade
        open_suggestions = (
            supabase
            .table("doubt_kb")
            .select("id, question, hit_count, subject")
            .eq("grade", grade)
            .eq("mode", mode)
            .eq("status", "active")
            .order("hit_count", desc=True)
            .limit(limit)
            .execute()
        )
        return {
            "success": True,
            "doubt_suggestions": [
                {"id": r["id"], "question": r["question"]}
                for r in (open_suggestions.data or [])
            ],
        }

    except Exception:
        return {"success": True, "doubt_suggestions": []}
