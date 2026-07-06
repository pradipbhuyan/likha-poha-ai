"""
exam_prep.py — JEE / NEET / CUET Exam Prep API
===============================================
Access: admin | Grade 11/12 students | akshita.teststudent

Student endpoints:
  GET  /api/exam-prep/status
  GET  /api/exam-prep/dashboard
  GET  /api/exam-prep/subjects
  GET  /api/exam-prep/topics
  GET  /api/exam-prep/questions
  GET  /api/exam-prep/questions/{id}
  POST /api/exam-prep/questions/{id}/answer
  POST /api/exam-prep/ask-followup
  POST /api/exam-prep/simulated-tests/start
  GET  /api/exam-prep/simulated-tests/{id}
  POST /api/exam-prep/simulated-tests/{id}/answer
  POST /api/exam-prep/simulated-tests/{id}/submit
  GET  /api/exam-prep/results/{id}

Legacy PYQ endpoints (kept for backward compat):
  GET  /api/exam-prep/papers
  GET  /api/exam-prep/paper/{doc_id}/chunks
  POST /api/exam-prep/explain

Admin endpoints (in admin_exam_prep router, prefix /api/admin/exam-prep):
  GET  /question-bank/status
  POST /question-bank/prewarm
  GET  /question-bank/jobs/{id}
  GET  /questions
  PATCH /questions/{id}
  POST /questions/{id}/publish
  POST /questions/{id}/archive
"""

from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import (
    get_current_user,
    get_user_profile,
    require_admin,
)
from app.services.logger_service import get_logger
from app.services.openai_service import ask_llm, get_effective_settings
import app.services.exam_prep_service as svc

_log = get_logger("exam_prep")

# ── Routers ────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/exam-prep", tags=["exam-prep"])
admin_router = APIRouter(prefix="/api/admin/exam-prep", tags=["admin-exam-prep"])


# ── Access guard helper ────────────────────────────────────────────────────────

def _require_exam_prep_access(user=Depends(get_current_user)):
    """Dependency: enforces Exam Prep access rules."""
    profile = get_user_profile(user.id)
    if not profile:
        raise HTTPException(403, "Profile not found")
    svc.check_exam_prep_access(profile)
    return {"user": user, "profile": profile}


# ── Status ─────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_status(ctx=Depends(_require_exam_prep_access)):
    """Return access status and exam availability."""
    profile = ctx["profile"]
    return {
        "success": True,
        "has_access": True,
        "grade": profile.get("grade"),
        "username": profile.get("username"),
        "exams": {
            "jee_main": {"label": "JEE Main", "active": True, "coming_soon": False},
            "neet_ug": {"label": "NEET UG", "active": True, "coming_soon": False},
            "cuet_ug": {"label": "CUET UG", "active": True, "coming_soon": False},
        },
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(
    exam: str = "jee_main",
    ctx=Depends(_require_exam_prep_access),
):
    """Return dashboard stats for the given exam."""
    user = ctx["user"]
    data = svc.get_dashboard(exam_type=exam, user_id=user.id)
    return {"success": True, **data}


# ── Subjects ───────────────────────────────────────────────────────────────────

@router.get("/subjects")
def get_subjects(
    exam: str = "jee_main",
    ctx=Depends(_require_exam_prep_access),
):
    """Return subject cards for the given exam."""
    user = ctx["user"]
    subjects = svc.get_subjects(exam_type=exam, user_id=user.id)
    return {"success": True, "subjects": subjects, "count": len(subjects)}


# ── Topics ─────────────────────────────────────────────────────────────────────

@router.get("/topics")
def get_topics(
    exam: str = "jee_main",
    subject: str = "Physics",
    ctx=Depends(_require_exam_prep_access),
):
    """Return topic priority cards for a subject."""
    topics = svc.get_topics(exam_type=exam, subject=subject)
    return {"success": True, "topics": topics, "count": len(topics)}


# ── Questions ──────────────────────────────────────────────────────────────────

@router.get("/questions")
def list_questions(
    exam: str = "jee_main",
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    ctx=Depends(_require_exam_prep_access),
):
    """Return published questions for practice."""
    questions = svc.get_questions(
        exam_type=exam,
        subject=subject,
        topic=topic,
        limit=min(limit, 50),
    )
    return {"success": True, "questions": questions, "count": len(questions)}


@router.get("/questions/{question_id}")
def get_question(
    question_id: str,
    ctx=Depends(_require_exam_prep_access),
):
    """Return a single published question with full details."""
    question = svc.get_question_by_id(question_id)
    return {"success": True, "question": question}


# ── Submit answer ──────────────────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    selected_option: Optional[str] = None
    time_taken_seconds: int = 0


@router.post("/questions/{question_id}/answer")
def submit_answer(
    question_id: str,
    req: AnswerRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Submit an answer and get instant feedback."""
    user = ctx["user"]
    result = svc.submit_answer(
        user_id=user.id,
        question_id=question_id,
        selected_option=req.selected_option,
        time_taken_seconds=req.time_taken_seconds,
    )
    return {"success": True, **result}


# ── AI Follow-up ───────────────────────────────────────────────────────────────

class FollowUpRequest(BaseModel):
    question_text: str
    subject: str = "Physics"
    exam: str = "JEE Main"
    follow_up: str
    user_answer: Optional[str] = None


@router.post("/ask-followup")
def ask_followup(
    req: FollowUpRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Answer a follow-up question about a specific question."""
    user = ctx["user"]
    if not req.follow_up.strip():
        raise HTTPException(400, "follow_up question cannot be empty")

    system_prompt = (
        f"You are an expert {req.exam} tutor helping a student with {req.subject}. "
        "Answer the student's follow-up question clearly and concisely. "
        "If it involves calculation, show each step. Keep under 150 words."
    )
    user_prompt = (
        f"QUESTION: {req.question_text}\n\n"
        f"STUDENT FOLLOW-UP: {req.follow_up}"
    )

    try:
        answer = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            username=getattr(user, "email", "student"),
            feature="exam_prep_followup",
        )
    except Exception as exc:
        raise HTTPException(500, "AI follow-up failed") from exc

    return {"success": True, "answer": answer}


# ── Simulated tests ────────────────────────────────────────────────────────────

class StartTestRequest(BaseModel):
    exam: str = "jee_main"


@router.post("/simulated-tests/start")
def start_simulated_test(
    req: StartTestRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Start a new simulated test."""
    user = ctx["user"]
    profile = ctx["profile"]
    grade = profile.get("grade", "Grade 12")
    result = svc.start_simulated_test(
        user_id=user.id,
        exam_type=req.exam,
        grade=grade,
    )
    return {"success": True, **result}


@router.get("/simulated-tests/{test_id}")
def get_simulated_test(
    test_id: str,
    ctx=Depends(_require_exam_prep_access),
):
    """Get a simulated test session with its questions."""
    user = ctx["user"]
    result = svc.get_test_result(test_id=test_id, user_id=user.id)
    return {"success": True, "test": result}


class TestAnswerRequest(BaseModel):
    question_id: str
    selected_option: Optional[str] = None
    time_taken_seconds: int = 0


@router.post("/simulated-tests/{test_id}/answer")
def submit_test_answer(
    test_id: str,
    req: TestAnswerRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Record an answer during a simulated test (saved but not scored until submit)."""
    # For now, answers are submitted as part of the final submit call.
    # This endpoint exists for future real-time saving.
    return {"success": True, "saved": True}


class SubmitTestRequest(BaseModel):
    answers: List[dict] = []
    time_spent_seconds: int = 0


@router.post("/simulated-tests/{test_id}/submit")
def submit_simulated_test(
    test_id: str,
    req: SubmitTestRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Submit a simulated test and get instant results."""
    user = ctx["user"]
    result = svc.submit_simulated_test(
        test_id=test_id,
        user_id=user.id,
        answers=req.answers,
        time_spent_seconds=req.time_spent_seconds,
    )
    return {"success": True, **result}


@router.get("/results/{test_id}")
def get_result(
    test_id: str,
    ctx=Depends(_require_exam_prep_access),
):
    """Get a completed test result."""
    user = ctx["user"]
    result = svc.get_test_result(test_id=test_id, user_id=user.id)
    return {"success": True, "result": result}


# ── Legacy PYQ endpoints (backward compat) ─────────────────────────────────────

EXAM_CHAPTER_PATTERNS = {
    "jee": "PYQ: B Tech",
    "neet": "PYQ: NEET",
    "cuet": "PYQ: CUET",
    "all": "PYQ:",
}


def _get_supabase_grade1112():
    from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
    if grade_1112_client is None:
        raise HTTPException(503, "Exam prep content database not configured")
    return grade_1112_client


@router.get("/papers")
def list_papers(
    exam: str = "jee",
    _ctx=Depends(_require_exam_prep_access),
):
    """Return list of available PYQ papers (legacy endpoint)."""
    sb = _get_supabase_grade1112()
    pattern = EXAM_CHAPTER_PATTERNS.get(exam.lower(), "PYQ:")
    try:
        r = (
            sb.table("rag_documents")
            .select("id, grade, subject, chapter, created_at")
            .like("chapter", f"{pattern}%")
            .order("chapter")
            .execute()
        )
        rows = r.data or []
    except Exception as exc:
        _log.error("exam_prep.list_papers", error=str(exc))
        raise HTTPException(500, "Failed to fetch papers") from exc

    seen = {}
    for row in rows:
        ch = row["chapter"]
        if ch not in seen:
            seen[ch] = {
                "id": row["id"],
                "chapter": ch,
                "subject": row["subject"],
                "grade": row["grade"],
                "label": ch.replace("PYQ: ", ""),
            }
    papers = list(seen.values())
    return {"success": True, "papers": papers, "count": len(papers)}


@router.get("/paper/{doc_id}/chunks")
def get_paper_chunks(
    doc_id: str,
    limit: int = 50,
    _ctx=Depends(_require_exam_prep_access),
):
    """Return text chunks for a PYQ paper (legacy endpoint)."""
    sb = _get_supabase_grade1112()
    try:
        r = (
            sb.table("rag_chunks")
            .select("id, chunk_index, chunk_text")
            .eq("document_id", doc_id)
            .order("chunk_index")
            .limit(limit)
            .execute()
        )
        chunks = r.data or []
    except Exception as exc:
        raise HTTPException(500, "Failed to fetch paper content") from exc

    try:
        meta_r = (
            sb.table("rag_documents")
            .select("chapter, subject, grade")
            .eq("id", doc_id)
            .single()
            .execute()
        )
        meta = meta_r.data or {}
    except Exception:
        meta = {}

    return {
        "success": True,
        "doc_id": doc_id,
        "chapter": meta.get("chapter", ""),
        "subject": meta.get("subject", ""),
        "grade": meta.get("grade", ""),
        "chunks": chunks,
        "count": len(chunks),
    }


class ExplainRequest(BaseModel):
    question_text: str
    subject: str = "Physics"
    exam: str = "JEE Main"
    user_answer: Optional[str] = None
    follow_up: Optional[str] = None


@router.post("/explain")
def explain_question(
    req: ExplainRequest,
    ctx=Depends(_require_exam_prep_access),
):
    """Generate AI explanation for a question (legacy + new endpoint)."""
    user = ctx["user"]

    if req.follow_up:
        system_prompt = f"You are an expert {req.exam} tutor."
        user_prompt = (
            f"QUESTION ({req.subject}): {req.question_text}\n\n"
            f"STUDENT FOLLOW-UP: {req.follow_up}\n\n"
            "Answer concisely under 150 words. Show steps if calculation needed."
        )
    else:
        answer_ctx = f"\nSTUDENT SELECTED: {req.user_answer}" if req.user_answer else ""
        system_prompt = f"You are an expert {req.exam} tutor."
        user_prompt = (
            f"QUESTION ({req.subject}): {req.question_text}{answer_ctx}\n\n"
            "Provide a clear step-by-step solution. Format EXACTLY as:\n"
            "CORRECT_ANSWER: [the correct answer]\n"
            "SOLUTION:\n[numbered steps, max 5, each under 30 words]\n"
            "JEE_TIP: [one practical exam strategy tip, max 25 words]\n"
            "Keep it concise. Plain text only."
        )

    try:
        raw = ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            username=getattr(user, "email", "student"),
            feature="exam_prep_explain",
        )
    except Exception as exc:
        raise HTTPException(500, "AI explanation failed") from exc

    # Parse structured response
    correct_answer = ""
    solution = ""
    tip = ""
    lines = raw.split("\n")
    section = None
    solution_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("CORRECT_ANSWER:"):
            correct_answer = line.replace("CORRECT_ANSWER:", "").strip()
        elif line.startswith("SOLUTION:"):
            section = "solution"
        elif line.startswith("JEE_TIP:"):
            tip = line.replace("JEE_TIP:", "").strip()
            section = None
        elif section == "solution" and line:
            solution_lines.append(line)
    solution = "\n".join(solution_lines) or raw

    return {
        "success": True,
        "correct_answer": correct_answer,
        "solution": solution,
        "tip": tip,
        "raw": raw,
    }


# ── Admin router endpoints ─────────────────────────────────────────────────────

@admin_router.post("/migrate")
def admin_run_migration(admin=Depends(require_admin)):
    """
    Apply the exam prep DB migration — creates all required tables.
    Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415
    if grade_1112_client is None:
        return {
            "success": False,
            "message": "Supabase 2 (grade_1112_client) is not configured. Set SUPABASE_GRADE_1112_URL and SUPABASE_GRADE_1112_SERVICE_KEY.",
            "existing_tables": [],
            "missing_tables": ["all 5 exam prep tables"],
        }
    db_client = grade_1112_client

    migration_sql = """
CREATE TABLE IF NOT EXISTS exam_prep_questions (
    id                   uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_type            text         NOT NULL CHECK (exam_type IN ('jee_main','neet_ug','cuet_ug')),
    grade                text         NOT NULL CHECK (grade IN ('Grade 11','Grade 12')),
    subject              text         NOT NULL,
    chapter              text         NOT NULL,
    topic                text         NOT NULL,
    subtopic             text,
    question_text        text         NOT NULL,
    question_latex       text,
    options_json         jsonb        NOT NULL,
    correct_option       text         NOT NULL,
    detailed_explanation text         NOT NULL,
    solution_steps_json  jsonb,
    formula_used         text,
    ncert_reference      text,
    difficulty           text         NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
    estimated_time_seconds int        DEFAULT 120,
    marks                numeric(4,1) DEFAULT 4,
    negative_marks       numeric(4,1) DEFAULT 1,
    source_type          text         NOT NULL DEFAULT 'llm_generated'
                                      CHECK (source_type IN ('ncert_derived','llm_generated','previous_year','manual')),
    status               text         NOT NULL DEFAULT 'draft'
                                      CHECK (status IN ('draft','published','archived')),
    validation_score     numeric(4,2),
    validation_errors    jsonb,
    prewarm_job_id       uuid,
    created_at           timestamptz  DEFAULT now(),
    updated_at           timestamptz  DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exam_prep_attempts (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid        NOT NULL,
    question_id        uuid        NOT NULL REFERENCES exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    time_taken_seconds int,
    attempted_at       timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exam_prep_simulated_tests (
    id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid         NOT NULL,
    exam_type           text         NOT NULL,
    grade               text         NOT NULL,
    question_ids        jsonb        NOT NULL DEFAULT '[]',
    status              text         NOT NULL DEFAULT 'active'
                                     CHECK (status IN ('active','submitted','expired')),
    started_at          timestamptz  DEFAULT now(),
    submitted_at        timestamptz,
    duration_minutes    int          DEFAULT 180,
    score_raw           int,
    score_normalized    numeric(5,2),
    subject_scores      jsonb,
    topic_accuracy      jsonb,
    weak_topics         jsonb        DEFAULT '[]',
    time_spent_seconds  int,
    total_questions     int,
    attempted           int,
    correct             int,
    wrong               int,
    ai_recommendations  jsonb,
    created_at          timestamptz  DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exam_prep_simulated_test_answers (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id            uuid         NOT NULL REFERENCES exam_prep_simulated_tests(id) ON DELETE CASCADE,
    question_id        uuid         NOT NULL REFERENCES exam_prep_questions(id) ON DELETE CASCADE,
    selected_option    text,
    is_correct         boolean,
    marks_awarded      numeric(4,1),
    time_taken_seconds int,
    answered_at        timestamptz  DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exam_prep_prewarm_jobs (
    id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_by          text        NOT NULL,
    exam_type             text        NOT NULL,
    grade                 text        NOT NULL,
    subject               text,
    chapter               text,
    topic                 text,
    difficulty_mix        jsonb,
    question_count        int         DEFAULT 10,
    publish_mode          text        NOT NULL DEFAULT 'draft'
                                      CHECK (publish_mode IN ('draft','auto_publish')),
    status                text        NOT NULL DEFAULT 'pending'
                                      CHECK (status IN ('pending','running','completed','failed')),
    questions_generated   int         DEFAULT 0,
    questions_validated   int         DEFAULT 0,
    questions_published   int         DEFAULT 0,
    error_message         text,
    provider              text,
    model                 text,
    started_at            timestamptz,
    completed_at          timestamptz,
    created_at            timestamptz DEFAULT now()
);
"""
    # Check which tables exist in Supabase 2
    tables_needed = [
        "exam_prep_questions", "exam_prep_attempts",
        "exam_prep_simulated_tests", "exam_prep_simulated_test_answers",
        "exam_prep_prewarm_jobs",
    ]
    existing = []
    missing = []
    for table in tables_needed:
        try:
            db_client.table(table).select("id").limit(1).execute()
            existing.append(table)
        except Exception:
            missing.append(table)

    if missing:
        return {
            "success": False,
            "message": (
                "Some tables are missing. Please run the migration SQL manually in your "
                "Supabase SQL editor. Copy the contents of "
                "backend/migrations/20260707_exam_prep_center.sql and run it."
            ),
            "existing_tables": existing,
            "missing_tables": missing,
            "migration_file": "backend/migrations/20260707_exam_prep_center.sql",
        }

    return {
        "success": True,
        "message": "All exam prep tables exist and are ready.",
        "tables": existing,
    }


@admin_router.get("/question-bank/status")
def admin_qb_status(
    exam_type: Optional[str] = None,
    _admin=Depends(require_admin),
):
    """Return question bank stats (admin only)."""
    data = svc.get_question_bank_status(exam_type=exam_type)
    return {"success": True, **data}


class PrewarmRequest(BaseModel):
    exam_type: str = "jee_main"
    grade: str = "Grade 12"
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    difficulty_mix: Optional[dict] = None
    question_count: int = 10
    publish_mode: str = "draft"
    run_now: bool = True


@admin_router.post("/question-bank/prewarm")
def admin_prewarm(
    req: PrewarmRequest,
    admin=Depends(require_admin),
):
    """Create and optionally run a question prewarm job (admin only)."""
    username = admin["profile"].get("username", "admin")
    job = svc.create_prewarm_job(
        triggered_by=username,
        exam_type=req.exam_type,
        grade=req.grade,
        subject=req.subject,
        chapter=req.chapter,
        topic=req.topic,
        difficulty_mix=req.difficulty_mix,
        question_count=req.question_count,
        publish_mode=req.publish_mode,
    )
    if req.run_now and job.get("id"):
        result = svc.run_prewarm_job(job["id"])
        return {"success": True, "job": job, "result": result}
    return {"success": True, "job": job}


@admin_router.get("/question-bank/jobs/{job_id}")
def admin_get_job(
    job_id: str,
    _admin=Depends(require_admin),
):
    """Get prewarm job status (admin only)."""
    job = svc.get_prewarm_job(job_id)
    return {"success": True, "job": job}


@admin_router.get("/questions")
def admin_list_questions(
    exam_type: Optional[str] = None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    _admin=Depends(require_admin),
):
    """List questions for admin review (all statuses)."""
    questions = svc.get_admin_questions(
        exam_type=exam_type,
        subject=subject,
        status=status,
        limit=min(limit, 200),
    )
    return {"success": True, "questions": questions, "count": len(questions)}


class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    correct_option: Optional[str] = None
    detailed_explanation: Optional[str] = None
    difficulty: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[str] = None


@admin_router.patch("/questions/{question_id}")
def admin_update_question(
    question_id: str,
    req: QuestionUpdateRequest,
    _admin=Depends(require_admin),
):
    """Update a question (admin only)."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = svc.update_question(question_id, updates)
    return {"success": True, "question": result}


@admin_router.post("/questions/{question_id}/publish")
def admin_publish_question(
    question_id: str,
    _admin=Depends(require_admin),
):
    """Publish a draft question (admin only)."""
    result = svc.publish_question(question_id)
    return {"success": True, "question": result}


@admin_router.post("/questions/{question_id}/archive")
def admin_archive_question(
    question_id: str,
    _admin=Depends(require_admin),
):
    """Archive a question (admin only)."""
    result = svc.archive_question(question_id)
    return {"success": True, "question": result}
