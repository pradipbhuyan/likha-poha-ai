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

from app.services.grade_db_router import get_content_db
from app.services.auth_service import admin_client as _primary_client


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
    supabase = get_content_db(grade)
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

        # Filter out malformed questions (< 4 options, short explanation, bad answer)
        questions = [
            q for q in questions
            if q.get("options") and isinstance(q["options"], dict) and len(q["options"]) >= 4
            and all(str(v).strip() for v in q["options"].values())
            and q.get("answer") in ("A", "B", "C", "D")
            and q.get("question") and len(str(q.get("question", ""))) >= 10
            and q.get("explanation") and len(str(q.get("explanation", ""))) >= 15
        ]

        # Deduplicate by question text (keep first occurrence) to prevent
        # the same question appearing twice in one test when the bank has duplicates.
        seen_texts: set = set()
        deduped: list = []
        for q in questions:
            text_key = str(q.get("question", "")).strip().lower()[:120]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduped.append(q)
        questions = deduped

        if len(questions) < num_questions:
            return []  # Not enough after filtering — caller falls back to LLM

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

    Before inserting, validates each question has 4 options and deduplicates
    against existing bank entries to prevent the bank growing with near-identical
    questions.

    Failures are silently ignored.
    """
    if not questions:
        return

    supabase = get_content_db(grade)
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()

        # Only insert well-formed questions with 4 complete options
        valid_questions = [
            q for q in questions
            if q.get("options") and isinstance(q.get("options"), dict) and len(q["options"]) >= 4
            and all(str(v).strip() for v in q["options"].values())
            and q.get("answer") in ("A", "B", "C", "D")
            and q.get("question") and len(str(q.get("question", ""))) >= 10
        ]

        if not valid_questions:
            return

        # Fetch existing question texts for this chapter to skip duplicates
        try:
            existing = supabase.table("question_bank").select("question").eq(
                "board", board
            ).eq("grade", grade).eq("subject", subject).eq(
                "chapter", clean_chapter
            ).eq("status", "active").limit(500).execute()
            existing_texts = {
                row["question"].strip().lower()[:120]
                for row in (existing.data or [])
                if row.get("question")
            }
        except Exception:
            existing_texts = set()

        rows = []
        seen_in_batch: set = set()

        for q in valid_questions:
            text_key = str(q.get("question", "")).strip().lower()[:120]
            # Skip if already in bank OR duplicated within this batch
            if text_key in existing_texts or text_key in seen_in_batch:
                continue
            seen_in_batch.add(text_key)
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
    supabase = get_content_db(grade)
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
    """Return summary statistics for the admin question bank panel (both DBs)."""
    from app.services.supabase_grade_1112_client import grade_1112_client  # noqa: PLC0415

    def _fetch(db):
        try:
            r = db.table("question_bank").select("status, grade, subject, difficulty").execute()
            return r.data or []
        except Exception:
            return []

    rows = _fetch(_primary_client) + _fetch(grade_1112_client)
    active = [r for r in rows if r.get("status") == "active"]
    needs_review = [r for r in rows if r.get("status") == "needs_review"]
    return {
        "total": len(rows),
        "active": len(active),
        "needs_review": len(needs_review),
    }
