"""
Teacher Routes
==============
Endpoints specific to teacher accounts:
  POST /api/teacher/test-paper/generate  — test paper (MCQ + subjective), served from pre-authored banks
  GET  /api/teacher/student-analytics    — progress across all assigned students

Test Paper and Lesson Plan are both served entirely from pre-authored content
(question_bank / subjective_question_bank / lesson_plan_bank) — no LLM call
at request time, mirroring how Mock Test's MCQ mode works. See
docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md and
docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md for how that content gets authored.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_teacher_or_admin, get_current_user, get_user_profile
from app.services.usage_service import enforce_daily_limit, log_ai_usage
from app.services.mock_test_service import (
    get_questions_from_bank_with_fallback,
    get_bank_capacity_with_fallback,
    bank_shortfall_message,
)
from app.services.subjective_question_bank_service import (
    get_subjective_questions_from_bank_with_fallback,
    get_subjective_bank_capacity_with_fallback,
)
from app.services.lesson_plan_bank_service import get_lesson_plan as get_lesson_plan_handout
from app.services.exemplar_research_bank_service import (
    get_available_topics,
    get_exemplar_explanation,
)
from app.services.feature_authorization_service import require_feature, Feature
from app.services.teacher_lesson_plan_service import (
    get_teacher_edit,
    save_teacher_edit,
    delete_teacher_edit,
)

_logger = logging.getLogger("likhapoha.teacher")
router = APIRouter()

# Free-tier teachers get 2/day on Test Paper Generator, Lesson Plan Creator, and
# Listen to Lecture — mirrors the FREE_TEACHER_DAILY_LIMIT constant duplicated
# in TeacherTestPaperPage.jsx / TeacherLessonPlanPage.jsx / TeacherLectureAudioPage.jsx.
# Those frontend counters are UX-only (localStorage); this is the actual gate.
FREE_TEACHER_DAILY_LIMIT = 2


def _is_free_tier_teacher(profile: dict) -> bool:
    """Admins and teachers with any non-free subscription_plan are unmetered."""
    if profile.get("role") == "admin":
        return False
    return (profile.get("subscription_plan") or "free") == "free"


def _enforce_teacher_daily_limit(profile: dict, feature: str) -> None:
    """Raise 429 if this free-tier teacher has hit today's cap for `feature`."""
    if not _is_free_tier_teacher(profile):
        return
    result = enforce_daily_limit(profile.get("username") or "", feature=feature, max_requests=FREE_TEACHER_DAILY_LIMIT)
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily free-tier limit reached ({FREE_TEACHER_DAILY_LIMIT}/day). Upgrade to the Paid Teacher plan for unlimited access.",
        )


# ── Schemas ────────────────────────────────────────────────────────────────────

class TestPaperRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    difficulty: str = "Medium"
    mcq_count: int = 6
    subjective_count: int = 4


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bank_questions_to_test_paper_format(bank_questions: list) -> list:
    """Convert question_bank row format to the test-paper MCQ format."""
    result = []
    for q in bank_questions:
        opts_dict = q.get("options") or {}
        if isinstance(opts_dict, dict):
            option_list = [opts_dict.get(k, "") for k in ("A", "B", "C", "D")]
        else:
            continue
        answer_letter = q.get("answer", "A")
        answer_text = opts_dict.get(answer_letter, option_list[0] if option_list else "")
        result.append({
            "question":    q.get("question", ""),
            "options":     option_list,
            "answer":      answer_text,
            "explanation": q.get("explanation", ""),
            "type":        "mcq",
            "source":      "question_bank",
        })
    return result


def _subjective_bank_questions_to_test_paper_format(bank_questions: list) -> list:
    """Convert subjective_question_bank row format to the test-paper subjective format."""
    result = []
    for q in bank_questions:
        result.append({
            "question": q.get("question", ""),
            "answer":   q.get("model_answer", ""),
            "marks":    q.get("marks", 3),
            "lines":    max(2, (q.get("marks") or 3) + 1),
            "type":     "subjective",
            "source":   "question_bank",
        })
    return result


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/test-paper/generate")
async def generate_test_paper(data: TestPaperRequest, ctx=Depends(require_teacher_or_admin)):
    """
    Serve a CBSE test paper for the given grade/subject/chapter — entirely
    from pre-authored banks (question_bank for MCQs, subjective_question_bank
    for subjective questions), mirroring Mock Test's zero-LLM MCQ mode.
    No LLM call at request time. A bank shortfall returns success:false with
    a friendly message instead of falling back to live generation.

    Called by the Teacher Test Paper page. Returns structured question objects
    that the frontend formats as a printable HTML page.
    """
    profile = ctx["profile"]
    _enforce_teacher_daily_limit(profile, feature="teacher_test_paper_free_tier")

    mcq_count  = min(max(int(data.mcq_count or 0), 0), 30)
    subj_count = min(max(int(data.subjective_count or 0), 0), 20)

    if mcq_count + subj_count == 0:
        raise HTTPException(status_code=400, detail="At least one question is required.")

    bank_difficulty = data.difficulty if data.difficulty != "Mixed" else "Medium"
    questions: list = []

    if mcq_count > 0:
        bank_qs = get_questions_from_bank_with_fallback(
            board="CBSE",
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            difficulty=bank_difficulty,
            num_questions=mcq_count,
        )
        if not bank_qs:
            available = get_bank_capacity_with_fallback(
                "CBSE", data.grade, data.subject, data.chapter, bank_difficulty,
            )
            return {
                "success": False,
                "message": bank_shortfall_message(available, mcq_count, data.chapter or data.subject),
            }
        questions.extend(_bank_questions_to_test_paper_format(bank_qs)[:mcq_count])
        _logger.info(
            "test-paper: served %d MCQs from question_bank for %s %s %s",
            len(bank_qs), data.grade, data.subject, data.chapter[:40]
        )

    if subj_count > 0:
        bank_subjs = get_subjective_questions_from_bank_with_fallback(
            board="CBSE",
            grade=data.grade,
            subject=data.subject,
            chapter=data.chapter,
            difficulty=bank_difficulty,
            num_questions=subj_count,
        )
        if not bank_subjs:
            available = get_subjective_bank_capacity_with_fallback(
                "CBSE", data.grade, data.subject, data.chapter, bank_difficulty,
            )
            return {
                "success": False,
                "message": bank_shortfall_message(available, subj_count, data.chapter or data.subject),
            }
        questions.extend(_subjective_bank_questions_to_test_paper_format(bank_subjs)[:subj_count])
        _logger.info(
            "test-paper: served %d subjective questions from subjective_question_bank for %s %s %s",
            len(bank_subjs), data.grade, data.subject, data.chapter[:40]
        )

    if _is_free_tier_teacher(profile):
        log_ai_usage(username=profile.get("username") or "", feature="teacher_test_paper_free_tier", model="none")

    return {
        "success": True,
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "difficulty": data.difficulty,
        "questions": questions,
        "total": len(questions),
        "mcq_count": sum(1 for q in questions if q.get("type") == "mcq"),
        "subjective_count": sum(1 for q in questions if q.get("type") == "subjective"),
    }


class LessonPlanRequest(BaseModel):
    grade: str
    subject: str
    chapter: str


@router.post("/lesson-plan/generate")
async def generate_lesson_plan(data: LessonPlanRequest, ctx=Depends(require_teacher_or_admin)):
    """
    Serve a lesson-plan handout for a chapter — no LLM call at request time.

    If this teacher has previously saved their own edited copy of this
    chapter's plan (see /lesson-plan/save), that private copy is returned
    instead of the shared system-generated one, and is visible ONLY to the
    teacher who saved it — other teachers requesting the same chapter still
    get the untouched system version. The system-generated
    lesson_plan_bank/*.json file is never modified by this feature.

    If neither a teacher edit nor a system handout exists yet for this
    chapter, returns success:false with a friendly message instead of
    generating one live.
    """
    profile = ctx["profile"]
    user = ctx["auth_user"]
    _enforce_teacher_daily_limit(profile, feature="teacher_lesson_plan_free_tier")

    teacher_edit = get_teacher_edit(user.id, data.grade, data.subject, data.chapter)
    if teacher_edit:
        if _is_free_tier_teacher(profile):
            log_ai_usage(username=profile.get("username") or "", feature="teacher_lesson_plan_free_tier", model="none")
        return {
            "success": True,
            "grade": data.grade,
            "subject": data.subject,
            "chapter": data.chapter,
            "lesson_plan": teacher_edit["lesson_plan_markdown"],
            "is_teacher_edited": True,
            "edited_at": teacher_edit.get("updated_at"),
        }

    plan = get_lesson_plan_handout(data.grade, data.subject, data.chapter)
    if not plan:
        return {
            "success": False,
            "message": (
                f"No lesson plan has been created yet for '{data.chapter or data.subject}'. "
                "Please try another chapter."
            ),
        }

    if _is_free_tier_teacher(profile):
        log_ai_usage(username=profile.get("username") or "", feature="teacher_lesson_plan_free_tier", model="none")

    return {
        "success": True,
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "lesson_plan": plan,
        "is_teacher_edited": False,
    }


class ExemplarExplanationRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    topic: str


class ExemplarAvailabilityRequest(BaseModel):
    grade: str
    subject: str
    topics: list[str]


@router.post("/exemplar-research/availability")
def get_exemplar_research_availability(
    data: ExemplarAvailabilityRequest,
    user=Depends(get_current_user),
):
    """
    Report which topic cards have authored content, so the grid can mark the
    rest instead of letting a student find out one click at a time.

    168 cards ship against 132 authored explanations, and 36 of that gap is
    permanent: NCERT never published Exemplar books for three of the fourteen
    sections, so those cards will never fill.

    Exemplar Research is a student-only paid feature (see
    SubscriptionPlansPage.jsx, which no longer lists it for teachers, and the
    explain route below) — any authenticated TEACHER is blocked outright,
    matching the explain route's gate. Free-tier students/parents are then
    blocked by require_feature()'s plan check (see feature_authorization_service.py
    — Feature.EXEMPLAR_RESEARCH is gated to the same paid-plan set as
    Feature.EXEMPLAR). Both checks are backend-enforced; no client is trusted.

    Capped at 200 topics per call; the largest real section is far below that,
    and the cap keeps a malformed or hostile request from walking the bank.
    """
    profile = get_user_profile(user.id) or {}
    if profile.get("role") == "teacher":
        raise HTTPException(
            status_code=403,
            detail={
                "feature": "EXEMPLAR_RESEARCH",
                "message": "Exemplar Research is a student-only feature and is not available to teacher accounts.",
            },
        )
    require_feature(user.id, Feature.EXEMPLAR_RESEARCH)

    topics = [t for t in (data.topics or []) if isinstance(t, str) and t.strip()][:200]
    return {
        "success": True,
        "available": get_available_topics(data.grade, data.subject, topics),
    }


@router.post("/exemplar-research/explain")
async def get_exemplar_research_explanation(data: ExemplarExplanationRequest, user=Depends(get_current_user)):
    """
    Serve a pre-authored Exemplar Research explanation for a topic card — no
    LLM call at request time (replaces the old live /api/doubt/answer call
    from ExemplarResearchPage.jsx; see
    docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md for why).

    Exemplar Research is a student-only paid feature — ExemplarResearchPage.jsx
    is never shown to teachers (see App.jsx's "exemplarResearch" case and
    SubscriptionPlansPage.jsx, which no longer advertises it for teachers).
    This route (living in teacher.py since it mirrors the lesson-plan-bank
    route pattern) accepts any authenticated STUDENT/parent/admin, but blocks
    every teacher unconditionally — not just free-tier ones. Previously only
    free-tier teachers were blocked (mirroring an older paid-teacher-feature
    framing); that framing has been retired, so ANY teacher now gets the 403
    regardless of subscription plan.

    Free-tier students/parents are then blocked by require_feature()'s plan
    check — previously this feature's matrix entry was allowed_plans=None
    (every plan let through unconditionally), so the free/paid split for
    students existed only in the web client's hasPaidAccess() check. Mobile
    never replicated that check, so free-tier mobile students got full
    functional access. Both checks are backend-enforced now; see
    docs/ACCESS_CONTROL_ARCHITECTURE_BLUEPRINT.md for the audit trail.

    If no explanation has been authored yet for this topic, returns
    success:false with a friendly message instead of generating one live.
    """
    profile = get_user_profile(user.id) or {}
    if profile.get("role") == "teacher":
        raise HTTPException(
            status_code=403,
            detail={
                "feature": "EXEMPLAR_RESEARCH",
                "message": "Exemplar Research is a student-only feature and is not available to teacher accounts.",
            },
        )
    require_feature(user.id, Feature.EXEMPLAR_RESEARCH)

    explanation = get_exemplar_explanation(data.grade, data.subject, data.topic)
    if not explanation:
        return {
            "success": False,
            "message": (
                f"No Exemplar Research explanation has been authored yet for '{data.topic}'. "
                "Please try another topic."
            ),
        }

    return {
        "success": True,
        "grade": data.grade,
        "subject": data.subject,
        "chapter": data.chapter,
        "topic": data.topic,
        "explanation": explanation,
    }


class SaveLessonPlanRequest(BaseModel):
    grade: str
    subject: str
    chapter: str
    lesson_plan_markdown: str


@router.post("/lesson-plan/save")
async def save_lesson_plan_edit(data: SaveLessonPlanRequest, ctx=Depends(require_teacher_or_admin)):
    """
    Save this teacher's own edited copy of a lesson plan.

    This is ALWAYS a private write scoped to the requesting teacher
    (teacher_lesson_plan_edits.teacher_id = user.id) — it never modifies the
    shared system-generated lesson_plan_bank/*.json file, and no other
    teacher will ever see this edit. Saving again for the same chapter
    overwrites this teacher's own previous edit.
    """
    user = ctx["auth_user"]

    result = save_teacher_edit(user.id, data.grade, data.subject, data.chapter, data.lesson_plan_markdown)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to save lesson plan."))

    _logger.info(
        "lesson-plan: teacher %s saved private edit for %s %s %s",
        user.id, data.grade, data.subject, data.chapter[:40],
    )
    return {"success": True, "edit": result["edit"]}


@router.post("/lesson-plan/revert")
async def revert_lesson_plan_edit(data: LessonPlanRequest, ctx=Depends(require_teacher_or_admin)):
    """
    Delete this teacher's own saved edit for a chapter, reverting them back
    to the shared system-generated version on their next fetch. Scoped to
    the requesting teacher — cannot affect any other teacher's saved edit
    or the system-generated bank file.
    """
    user = ctx["auth_user"]

    result = delete_teacher_edit(user.id, data.grade, data.subject, data.chapter)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to revert lesson plan."))

    plan = get_lesson_plan_handout(data.grade, data.subject, data.chapter)
    return {
        "success": True,
        "lesson_plan": plan,
        "is_teacher_edited": False,
    }


@router.post("/lesson-plan/lecture-audio")
def generate_lecture_audio(data: LessonPlanRequest, ctx=Depends(require_teacher_or_admin)):
    """
    Generate (or serve cached) spoken-lecture audio for a chapter's
    pre-authored lesson plan — a teacher rehearsal aid, not a student-facing
    feature. The script is deterministically extracted from the same plan
    served by /lesson-plan/generate (see lesson_plan_lecture_script.py), so
    it stays in sync with the plan automatically.

    Reuses the existing per-step audio cache (lesson_audio_cache / Supabase
    Storage) via the step_title sentinel "__lecture__" — no schema change
    needed. If the storage upload fails for any reason, falls back to
    returning the freshly generated audio as a data: URL instead of failing
    the request — playable immediately, just not persisted/shared across
    requests.
    """
    import base64  # noqa: PLC0415
    import os as _os  # noqa: PLC0415

    from app.services.lesson_plan_lecture_script import build_lecture_script  # noqa: PLC0415
    from app.services.tts_service import clean_text_for_tts, generate_speech_file  # noqa: PLC0415
    from app.services.audio_cache_service import get_cached_audio_url, store_audio  # noqa: PLC0415

    profile = ctx["profile"]
    user = ctx["auth_user"]
    _enforce_teacher_daily_limit(profile, feature="teacher_lecture_audio_free_tier")

    # Rehearse from this teacher's own saved edit if they have one, so the
    # narration matches what they'll actually teach from — otherwise fall
    # back to the shared system-generated handout. Never touches the bank file.
    teacher_edit = get_teacher_edit(user.id, data.grade, data.subject, data.chapter)
    plan = teacher_edit["lesson_plan_markdown"] if teacher_edit else get_lesson_plan_handout(data.grade, data.subject, data.chapter)
    if not plan:
        return {
            "success": False,
            "message": (
                f"No lesson plan has been created yet for '{data.chapter or data.subject}'. "
                "Generate the lesson plan first."
            ),
        }

    voice = "hi-IN-SwaraNeural" if "hindi" in (data.subject or "").lower() else "en-IN-NeerjaNeural"
    rate = "+0%"
    step_title = "__lecture__"

    cached_url = get_cached_audio_url(data.grade, data.subject, data.chapter, step_title, voice, rate)
    if cached_url:
        if _is_free_tier_teacher(profile):
            log_ai_usage(username=profile.get("username") or "", feature="teacher_lecture_audio_free_tier", model="none")
        return {"success": True, "audio_url": cached_url, "cached": True}

    script = build_lecture_script(plan)
    if not script.strip():
        return {"success": False, "message": "This lesson plan has no lecture-worthy content to narrate."}

    cleaned = clean_text_for_tts(script)
    mp3_path = generate_speech_file(cleaned, voice=voice, rate=rate)
    try:
        with open(mp3_path, "rb") as f:
            mp3_bytes = f.read()
    finally:
        _os.remove(mp3_path)

    try:
        audio_url = store_audio(data.grade, data.subject, data.chapter, step_title, mp3_bytes, voice, rate)
    except RuntimeError as exc:
        _logger.warning("lecture_audio.store_failed_falling_back_to_data_url: %s", str(exc)[:200])
        b64 = base64.b64encode(mp3_bytes).decode("ascii")
        audio_url = f"data:audio/mpeg;base64,{b64}"

    if _is_free_tier_teacher(profile):
        log_ai_usage(username=profile.get("username") or "", feature="teacher_lecture_audio_free_tier", model="none")

    return {"success": True, "audio_url": audio_url, "cached": False}


@router.get("/student-analytics")
async def get_teacher_student_analytics(ctx=Depends(require_teacher_or_admin)):
    """
    Return mock-test history for all students assigned to this teacher.

    The frontend uses this data to show a per-student progress view.
    """
    user = ctx["auth_user"]

    try:
        # Get assignments for this teacher
        assignments_resp = (
            admin_client
            .table("teacher_student_assignments")
            .select("student_id, grade, subject, section")
            .eq("teacher_id", user.id)
            .execute()
        )
        assignments = assignments_resp.data or []
        student_ids = list({a["student_id"] for a in assignments if a.get("student_id")})

        if not student_ids:
            return {"success": True, "students": []}

        # Fetch profiles
        profiles_resp = (
            admin_client
            .table("profiles")
            .select("id, username, email, grade")
            .in_("id", student_ids)
            .execute()
        )
        profiles = {p["id"]: p for p in (profiles_resp.data or [])}

        # Fetch test history for all students
        history_resp = (
            admin_client
            .table("test_history")
            .select("profile_id, subject, chapter, percentage, created_at, difficulty")
            .in_("profile_id", student_ids)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        all_history = history_resp.data or []

        # Group history by student
        history_by_student: dict = {}
        for h in all_history:
            uid = h.get("profile_id")
            if uid:
                history_by_student.setdefault(uid, []).append(h)

        students_data = []
        for sid in student_ids:
            profile = profiles.get(sid, {})
            history = history_by_student.get(sid, [])
            scores = [float(h.get("percentage") or 0) for h in history]

            # Per-subject stats
            subject_stats: dict = {}
            for h in history:
                subj = h.get("subject") or "Unknown"
                score = float(h.get("percentage") or 0)
                if subj not in subject_stats:
                    subject_stats[subj] = {"scores": [], "latest": score}
                subject_stats[subj]["scores"].append(score)
                subject_stats[subj]["latest"] = score

            subject_performance = [
                {
                    "subject": s,
                    "best":    max(d["scores"]),
                    "average": round(sum(d["scores"]) / len(d["scores"])),
                    "latest":  d["latest"],
                    "tests":   len(d["scores"]),
                }
                for s, d in subject_stats.items()
            ]

            students_data.append({
                "id": sid,
                "username": profile.get("username", "Unknown"),
                "email": profile.get("email", ""),
                "grade": profile.get("grade") or assignments[0].get("grade", "Grade 9") if assignments else "Grade 9",
                "total_tests": len(history),
                "average_score": round(sum(scores) / len(scores)) if scores else 0,
                "best_score": max(scores) if scores else 0,
                "latest_score": scores[0] if scores else 0,
                "subject_performance": subject_performance,
                "recent_history": history[:10],
            })

        return {"success": True, "students": students_data}

    except Exception as exc:
        _logger.error("teacher student analytics error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
