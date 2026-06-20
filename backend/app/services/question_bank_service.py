"""
Question Bank Service
=====================
Pre-generated mock test questions stored in Supabase for random sampling.

Design principles:
- Every operation is wrapped in try/except and fails silently.
- get_questions_from_bank returns [] when the bank is too small or unavailable,
  so the caller falls back to live LLM generation — existing flow unchanged.
- Run backend/sql/add_question_bank.sql in Supabase before enabling.
- Populate via: python3 backend/scripts/build_question_bank.py
"""

import random

from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS


def get_questions_from_bank(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
    num_questions: int,
    exam_type: str = "General",
    excluded_ids: list[str] | None = None,
) -> list[dict]:
    """
    Sample random questions from the bank for a mock test.

    Returns a randomly sampled list of num_questions questions if the bank
    has enough active questions, otherwise returns [] to trigger LLM fallback.

    excluded_ids: database row IDs (as strings) of questions shown in recent
    tests for this user.  These are filtered out before sampling so the same
    question cannot appear in the same test or the next 30 tests.

    The caller should always handle the empty-list case.
    """
    try:
        clean_chapter = "".join(
            c for c in (chapter or "") if c.isprintable()
        ).strip()

        query = (
            supabase
            .table("question_bank")
            .select("id, section, question, options, answer, explanation, marks")
            .eq("board", board)
            .eq("grade", grade)
            .eq("subject", subject)
            .eq("difficulty", difficulty)
            .eq("status", "active")
        )

        if clean_chapter:
            query = query.eq("chapter", clean_chapter)

        # Fetch a large pool so exclusion still leaves enough candidates
        result = query.limit(1000).execute()
        questions = result.data or []

        # Filter out recently-shown questions to prevent repetition
        if excluded_ids:
            excluded_set = {str(eid) for eid in excluded_ids}
            questions = [q for q in questions if str(q.get("id", "")) not in excluded_set]

        if len(questions) < num_questions:
            return []  # Not enough after exclusion — caller falls back to LLM

        sampled = random.sample(questions, num_questions)

        # Store original DB ids BEFORE renumbering so the frontend can send them
        # back as excluded_ids in the next test request.
        for q in sampled:
            q["db_id"] = str(q.get("id", ""))

        # Renumber questions for the test (1-based id expected by frontend UI)
        for index, q in enumerate(sampled, start=1):
            q["id"] = index

        # Increment times_shown fire-and-forget (fixed: use rpc or raw update)
        try:
            db_ids = [q.get("db_id") for q in sampled if q.get("db_id")]
            if db_ids:
                # Use SQL expression via RPC to safely increment the counter
                supabase.rpc("increment_times_shown", {"question_ids": db_ids}).execute()
        except Exception:
            pass  # times_shown is advisory — never fail the test for this

        return sampled

    except Exception:
        return []  # Table may not exist yet — fall back to LLM


def add_questions_to_bank(
    questions: list[dict],
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    difficulty: str,
    exam_type: str = "General",
) -> None:
    """
    Add LLM-generated questions to the bank for future use.

    Questions added here become available for random sampling in the next
    test request for the same chapter/difficulty, gradually reducing LLM
    dependency as the bank grows.

    Failures are silently ignored.
    """
    if not questions:
        return

    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
        rows = []

        for q in questions:
            rows.append({
                "board": board,
                "grade": grade,
                "subject": subject,
                "chapter": clean_chapter,
                "exam_type": exam_type,
                "difficulty": difficulty,
                "section": q.get("section") or "",
                "question": q.get("question") or "",
                "options": q.get("options") or {},
                "answer": q.get("answer") or "",
                "explanation": q.get("explanation") or "",
                "marks": int(q.get("marks") or 1),
                "status": "active",
            })

        if rows:
            supabase.table("question_bank").insert(rows).execute()

    except Exception:
        pass  # Bank inserts must never break test delivery


def invalidate_bank_for_chapter(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
) -> None:
    """
    Mark all bank questions for a chapter as needs_review.

    Call this when RAG content is updated for a chapter so questions
    grounded in the old content are flagged for admin review before
    serving them again.
    """
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()
        supabase.table("question_bank").update(
            {"status": "needs_review"}
        ).match({
            "board": board,
            "grade": grade,
            "subject": subject,
            "chapter": clean_chapter,
        }).execute()
    except Exception:
        pass


def get_bank_stats() -> dict:
    """Return summary statistics for the admin question bank panel."""
    try:
        result = (
            supabase
            .table("question_bank")
            .select("status, grade, subject, difficulty")
            .execute()
        )
        rows = result.data or []
        active = [r for r in rows if r.get("status") == "active"]
        needs_review = [r for r in rows if r.get("status") == "needs_review"]
        return {
            "total": len(rows),
            "active": len(active),
            "needs_review": len(needs_review),
        }
    except Exception:
        return {"total": 0, "active": 0, "needs_review": 0}
