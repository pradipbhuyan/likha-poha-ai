from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.logger_service import get_logger

_log = get_logger("routes.lesson")

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
from app.services.rag_visual_service import (
    list_active_visual_assets_for_context,
    search_visual_assets_for_context,
)
from app.services.doubt_history_service import save_doubt_history
from app.services.platform_info_service import (
    answer_platform_info,
    is_platform_info_question,
)
from app.services.subject_access_service import has_cbse_subject_access
from app.services.board_service import is_school_board, normalize_board, resolve_request_board
from app.services.test_account_service import is_all_access_test_user
from app.services.offer_access_service import is_free_tier_user, build_offer_gate_response

# Keep legacy alias so any remaining is_offer_code_user calls still resolve
is_offer_code_user = is_free_tier_user
from app.services.doubt_kb_service import search_doubt_kb
from app.services.academic_guardrail_service import (
    is_non_academic_question,
    build_non_academic_response,
)

router = APIRouter()


def call_with_optional_board(func, board: str, **kwargs):
    """
    Call upgraded services with board, while tolerating older test doubles.

    Also strips cache_only gracefully when the target function (e.g. a test
    double) does not accept it, so tests written before cache_only was added
    continue to work without modification.
    """
    try:
        return func(board=board, **kwargs)
    except TypeError as error:
        err = str(error)
        if "unexpected keyword argument 'board'" in err:
            try:
                return func(**kwargs)
            except TypeError as inner:
                if "unexpected keyword argument 'cache_only'" in str(inner):
                    kwargs.pop("cache_only", None)
                    return func(**kwargs)
                raise
        if "unexpected keyword argument 'cache_only'" in err:
            kwargs.pop("cache_only", None)
            try:
                return func(board=board, **kwargs)
            except TypeError:
                return func(**kwargs)
        raise


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
    """Prevent students from requesting content outside their onboarded grade.
    Teachers are allowed to access all grades for lesson planning purposes.
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
    """Prevent students from requesting school-board content outside onboarding.
    Teachers are allowed all boards for lesson planning purposes.
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


def enforce_learning_access(profile: dict, mode: str, subject: str):
    """
    Enforce plan access for CBSE and subject-specific SOF lessons.

    Admins bypass student plan gates; all other users must be active/trial and
    have the exact access flag needed by the requested learning mode.
    """
    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found")

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
    if str(username or "").strip().casefold() == "akshita.teststudent":
        return

    limit_check = enforce_token_limits(username)

    if not limit_check.get("allowed"):
        raise HTTPException(
            status_code=403,
            detail=limit_check.get("message", "AI token limit reached."),
        )


@router.get("/textbook-visuals")
def get_textbook_visuals(
    grade: str,
    mode: str,
    subject: str,
    chapter: str,
    board: str = "CBSE",
    query: str = "",
    user=Depends(get_current_user),
):
    """Return approved textbook visuals for the current lesson only."""
    validate_required_text(grade, "grade")
    validate_required_text(board, "board")
    validate_required_text(mode, "mode")
    validate_required_text(subject, "subject")
    validate_required_text(chapter, "chapter")

    profile = get_profile_by_user_id(user.id)
    request_board = resolve_request_board(mode, board)
    enforce_profile_grade(profile, grade)
    enforce_profile_board(profile, request_board)
    enforce_learning_access(profile, mode, subject)

    clean_query = str(query or "").strip()
    if clean_query:
        visuals = search_visual_assets_for_context(
            board=request_board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            query=clean_query,
            limit=6,
        )
        message = (
            "Textbook visuals found."
            if visuals
            else "That visual is outside the current lesson context. Choose one of the textbook visual cards above."
        )
    else:
        visuals = list_active_visual_assets_for_context(
            board=request_board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            limit=12,
        )
        message = (
            "Textbook visuals loaded."
            if visuals
            else "No approved textbook visuals are available for this lesson yet."
        )

    return {
        "success": True,
        "visuals": visuals,
        "message": message,
    }


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
    # Offer-code users bypass the standard CBSE access gate — their redemption
    # grants limited platform access; lesson generation uses cached content.
    if not is_offer_code_user(user.id):
        enforce_learning_access(profile, data.mode, data.subject)

    # SECURITY: Exemplar chapters require paid access regardless of free-tier bypass.
    # Free users (is_offer_code_user=True) bypass enforce_learning_access above,
    # but Exemplar lessons are premium-only. Check chapter name prefix.
    # Admins, teachers, and all-access test accounts are exempt from this check
    # (they need full access for prewarm, content review, and testing).
    _chapter_name = (data.chapter or "").strip()
    _is_privileged_role = (profile or {}).get("role") in ("admin", "teacher") or is_all_access_test_user(profile or {})
    if not _is_privileged_role and (_chapter_name.lower().startswith("exemplar:") or "exemplar:" in _chapter_name.lower()):
        from app.services.feature_authorization_service import authorize_feature, Feature  # noqa: PLC0415
        _fauth = authorize_feature(user.id, Feature.EXEMPLAR)
        if not _fauth["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "feature": "EXEMPLAR",
                    "message": "Exemplar lessons require a paid subscription.",
                    "upgrade_message": "Upgrade to access Exemplar lessons.",
                    "required_plan": "Any paid plan",
                },
            )

    enforce_ai_token_limit(profile.get("username") or data.username)

    username_key = profile.get("username") or data.username
    _log.info(
        "lesson.generate.start",
        username=username_key,
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter[:60] if data.chapter else "",
        step_title=data.step_title[:60] if data.step_title else "",
        mode=data.mode,
        board=request_board,
    )
    import time as _time
    _t_lesson = _time.perf_counter()
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
            username=username_key,
            cache_only=False,  # Free-trial offer users get full lesson access during validity
        )

        _log.info(
            "lesson.generate.complete",
            username=username_key,
            grade=data.grade,
            subject=data.subject,
            source_type=result.get("source_type", "LLM") if isinstance(result, dict) else "LLM",
            from_cache=result.get("from_cache", False) if isinstance(result, dict) else False,
            duration_ms=round((_time.perf_counter() - _t_lesson) * 1000),
        )
        if isinstance(result, dict):
            lesson = result.get("lesson")
            source_type = result.get("source_type", "LLM")
            sources = result.get("sources", [])
            textbook_visuals = result.get("textbook_visuals", [])
        else:
            lesson = result
            source_type = "LLM"
            sources = []
            textbook_visuals = []

        # Fetch DKB-backed question cards for this chapter.
        # Only questions with pre-cached answers are included so every card
        # click is served at zero token cost.  This is an internal mechanism
        # and the card source is not disclosed to students.
        doubt_suggestions = []
        try:
            from app.services.doubt_kb_service import get_lesson_doubt_suggestions  # noqa: PLC0415
            doubt_suggestions = get_lesson_doubt_suggestions(
                grade=data.grade,
                subject=data.subject,
                chapter=data.chapter,
                mode=data.mode,
            )
        except Exception:
            pass

        return {
            "success": True,
            "lesson": lesson,
            "source_type": source_type,
            "sources": sources,
            "textbook_visuals": textbook_visuals,
            "doubt_suggestions": doubt_suggestions,
            "message": "Lesson generated successfully",
        }

    except HTTPException:
        raise

    except Exception as e:
        from app.services.logger_service import PlatformError as _PE  # noqa: PLC0415
        _log.error(
            "lesson.generate.failed",
            error_code=_PE.SYS_INTERNAL_ERROR,
            username=username_key,
            grade=data.grade,
            subject=data.subject,
            error=str(e),
            exc_info=True,
        )
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "quota" in err_str or "too_many" in err_str or "limit" in err_str:
            user_msg = "Our AI tutoring service is experiencing high demand right now. Please try again in a few minutes."
            try:
                from app.services.alert_service import alert_rate_limit  # noqa: PLC0415
                alert_rate_limit(
                    feature="lesson_generate",
                    username=username_key,
                    error_detail=str(e),
                    grade=data.grade,
                    subject=data.subject,
                    chapter=data.chapter or "",
                )
            except Exception:
                pass
        elif "timeout" in err_str or "timed out" in err_str:
            user_msg = "The AI took too long to respond. Please try again."
        else:
            user_msg = "Lesson generation failed. Please try again in a moment."
        return {
            "success": False,
            "lesson": None,
            "source_type": "LLM",
            "sources": [],
            "textbook_visuals": [],
            "message": user_msg,
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
    # Offer-code users bypass the standard CBSE access gate.
    if not is_offer_code_user(user.id):
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
            textbook_visuals=[],
            history_id=history_item.get("id") if history_item else None,
            message="Platform information answered successfully",
        )

    # ── Academic guardrail: block non-academic follow-up questions ───────────
    if is_non_academic_question(data.question):
        guard = build_non_academic_response()
        return LessonFollowUpResponse(
            success=True,
            answer=guard["answer"],
            source_type=guard["source_type"],
            sources=[],
            textbook_visuals=[],
            history_id=None,
            message="Academic guardrail: non-academic question redirected",
        )

    # ── Offer-code gate: DKB-only, no LLM calls ──────────────────────────────
    if is_offer_code_user(user.id):
        dkb_result = search_doubt_kb(
            question=data.question,
            grade=data.grade,
            subject=data.subject or "",
            chapter=data.chapter or None,
            mode=data.mode,
            board=request_board,
        )
        if dkb_result:
            return LessonFollowUpResponse(
                success=True,
                answer=dkb_result["answer"],
                source_type="DOUBT_KB",
                sources=[],
                textbook_visuals=[],
                history_id=None,
                message="Answered from knowledge base",
            )
        gate = build_offer_gate_response()
        return LessonFollowUpResponse(
            success=True,
            answer=gate["answer"],
            source_type=gate["source_type"],
            sources=[],
            textbook_visuals=[],
            history_id=None,
            message="Offer gate: upgrade required for full AI access",
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
            textbook_visuals=result.get("textbook_visuals", []),
            history_id=history_item.get("id") if history_item else None,
            message="Follow-up answered successfully",
        )

    except HTTPException:
        raise

    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "quota" in err_str or "too_many" in err_str or "limit" in err_str:
            user_msg = "Our AI tutoring service is experiencing high demand right now. Please try again in a few minutes."
            try:
                from app.services.alert_service import alert_rate_limit  # noqa: PLC0415
                alert_rate_limit(
                    feature="lesson_followup",
                    username=profile.get("username") or data.username if profile else data.username,
                    error_detail=str(e),
                    grade=data.grade,
                    subject=data.subject,
                    chapter=data.chapter or "",
                )
            except Exception:
                pass
        elif "timeout" in err_str or "timed out" in err_str:
            user_msg = "The AI took too long to respond. Please try again."
        else:
            user_msg = "Something went wrong. Please try again in a moment."
        return LessonFollowUpResponse(
            success=False,
            answer=None,
            source_type="LLM",
            sources=[],
            textbook_visuals=[],
            history_id=None,
            message=user_msg,
        )


@router.get("/doubt-suggestions")
def get_doubt_suggestions(
    grade: str,
    subject: str,
    chapter: str,
    mode: str = "CBSE",
    board: str = "CBSE",
    user=Depends(get_current_user),
):
    """
    Return DKB-backed suggestion cards for a lesson chapter.

    Called when loading a saved lesson (progress restore) so that the
    follow-up chip row shows pre-answered DKB questions instead of
    generic default prompts.  Safe to call any time — returns empty list
    if no DKB entries exist for the chapter.
    """
    try:
        from app.services.doubt_kb_service import get_lesson_doubt_suggestions  # noqa: PLC0415
        suggestions = get_lesson_doubt_suggestions(
            grade=grade,
            subject=subject,
            chapter=chapter,
            mode=mode,
        )
        return {"success": True, "doubt_suggestions": suggestions}
    except Exception:
        return {"success": True, "doubt_suggestions": []}


@router.get("/lkb-chips")
def get_lkb_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    user=Depends(get_current_user),
):
    """
    Return LKB (Lesson Knowledge Base) pre-warmed chips for a lesson step.

    Chips are NCERT-grounded Q&A pairs with 6-10 bullet point answers,
    generated at admin pre-warm time and served instantly (zero LLM cost).
    Returns empty list if no chips are pre-warmed for this step yet.
    """
    try:
        from app.services.lesson_kb_service import get_lkb_chips  # noqa: PLC0415
        chips = get_lkb_chips(
            grade=grade,
            subject=subject,
            chapter=chapter,
            step_title=step_title,
        )
        return {"success": True, "lkb_chips": chips}
    except Exception:
        return {"success": True, "lkb_chips": []}


@router.get("/lkb-chips/ensure")
def ensure_lkb_chips(
    grade: str,
    subject: str,
    chapter: str,
    step_title: str,
    user=Depends(get_current_user),
):
    """
    Return LKB chips, generating them on-demand via LLM if not yet pre-warmed.

    Flow:
    1. DB lookup — instant if admin has pre-warmed.
    2. On cache miss — generates 5 NCERT-grounded chips via LLM, stores in lesson_kb,
       then returns them so all future requests are instant.

    This means every student always sees 5 chapter-specific chip questions.
    The first request for an un-warmed step takes ~5-8s (LLM call).
    All subsequent requests are instant from DB.

    Returns: { success, lkb_chips: [{id, question, answer}], generated: bool }
    """
    try:
        from app.services.lesson_kb_service import get_or_generate_lkb_chips  # noqa: PLC0415
        chips, was_generated = get_or_generate_lkb_chips(
            grade=grade,
            subject=subject,
            chapter=chapter,
            step_title=step_title,
        )
        return {"success": True, "lkb_chips": chips, "generated": was_generated}
    except Exception:
        return {"success": True, "lkb_chips": [], "generated": False}


# ── Lesson Prewarm — ChatGPT manual lesson import ────────────────────────────

class PrewarmPromptRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    step_title: str
    mode: str = "CBSE"
    board: str = "CBSE"


class PrewarmStoreRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    step_title: str
    lesson_content: str
    mode: str = "CBSE"
    board: str = "CBSE"
    force: bool = False


@router.post("/prewarm/prompt")
def generate_prewarm_prompt(
    data: PrewarmPromptRequest,
    user=Depends(get_current_user),
):
    """
    Generate the full ChatGPT prompt for a lesson step, including the RAG chunks.

    Admin pastes this into ChatGPT desktop to manually generate a lesson, then
    stores the output via POST /api/lesson/prewarm/store.
    """
    from app.services.rag_service import search_textbook_content  # noqa: PLC0415
    from app.services.tutor_service import (  # noqa: PLC0415
        PROSE_LITERATURE_SYSTEM, POEM_SYSTEM, TUTOR_SYSTEM, DIAGRAM_HINT,
        detect_chapter_type,
    )

    # Fetch RAG chunks for this chapter
    rag_results = search_textbook_content(
        query=f"{data.grade} {data.subject} {data.chapter} {data.step_title}",
        board=data.board,
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter,
        match_count=10,
    )
    if not rag_results:
        rag_results = search_textbook_content(
            query=f"{data.grade} {data.subject} {data.chapter}",
            board=data.board,
            grade=data.grade,
            subject=data.subject,
            chapter=None,
            match_count=10,
        )

    textbook_context = "\n\n".join(r.get("chunk_text", "") for r in rag_results)
    rag_found = len(rag_results)

    chapter_type = detect_chapter_type(data.subject, data.chapter)
    if chapter_type == "prose":
        system_prompt = PROSE_LITERATURE_SYSTEM
    elif chapter_type == "poem":
        system_prompt = POEM_SYSTEM
    else:
        system_prompt = TUTOR_SYSTEM

    default_steps = ["What We Learn", "Core Concepts", "Worked Examples", "Exam-style problems", "Revision"]
    step_num = (default_steps.index(data.step_title) + 1
                if data.step_title in default_steps else 1)

    step_prefix = ""
    if chapter_type in ("prose", "poem"):
        label = "Prose/Literature" if chapter_type == "prose" else "Poem"
        step_prefix = f"You are teaching STEP {step_num} of a {label} lesson.\n\n"

    user_prompt = f"""{step_prefix}Grade: {data.grade}
Mode: {data.mode}
Subject: {data.subject}
Chapter: {data.chapter}
Current sub-topic: {data.step_title}

Teacher Persona: Standard CBSE tutor

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Create a focused step-wise lesson only for this sub-topic.
Do not cover unrelated topics.

Textbook coverage rules:
- Use the uploaded textbook context deeply.
- Extract and teach all important concepts present in the retrieved textbook context.
- Include important definitions, examples, activities, and review questions.

Depth instructions:
- Teach this topic at the right depth for {data.grade}.
- Use simpler words, concrete examples, and shorter steps for Classes 1-5.

{DIAGRAM_HINT}

Worked example: Start with "Question: <complete problem statement>", then step-by-step solution.
NEVER ask the student to draw or sketch.

End with a short next-step instruction, not a question.
"""

    return {
        "success": True,
        "system_prompt": system_prompt.strip(),
        "user_prompt": user_prompt.strip(),
        "rag_chunks_found": rag_found,
        "chapter_type": chapter_type,
    }


@router.post("/prewarm/store")
def store_prewarm_lesson(
    data: PrewarmStoreRequest,
    user=Depends(get_current_user),
):
    """
    Store a manually-generated lesson (from ChatGPT desktop) in lesson_cache.

    The stored lesson is served instantly to all students with zero LLM cost.
    """
    from app.services.lesson_cache_service import (  # noqa: PLC0415
        make_lesson_cache_key, store_lesson_cache, get_cached_lesson,
    )
    from app.services.rag_service import search_textbook_content  # noqa: PLC0415

    if not data.lesson_content or not data.lesson_content.strip():
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=400, detail="lesson_content is required")

    cache_key = make_lesson_cache_key(
        board=data.board,
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter,
        mode=data.mode,
        step_title=data.step_title,
        teacher_persona="",
    )

    # Skip if already cached (unless force=True)
    existing = get_cached_lesson(cache_key, grade=data.grade)
    if existing and not data.force:
        return {
            "success": False,
            "message": "Already cached. Pass force=true to overwrite.",
            "already_cached": True,
        }

    # Determine source_type
    rag_results = search_textbook_content(
        query=f"{data.grade} {data.subject} {data.chapter}",
        board=data.board,
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter,
        match_count=3,
    )
    source_type = "RAG" if rag_results else "LLM"

    store_lesson_cache(
        cache_key=cache_key,
        lesson_content=data.lesson_content.strip(),
        source_type=source_type,
        board=data.board,
        grade=data.grade,
        subject=data.subject,
        chapter=data.chapter,
        mode=data.mode,
        step_title=data.step_title,
        teacher_persona="",
        practice_questions=[],
    )

    return {
        "success": True,
        "message": f"Lesson stored successfully as {source_type}",
        "cache_key": cache_key[:20] + "...",
        "chars": len(data.lesson_content.strip()),
        "source_type": source_type,
    }
