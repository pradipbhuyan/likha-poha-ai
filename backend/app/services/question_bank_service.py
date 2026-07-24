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


def _fetch_question_pool(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> list[dict]:
    """
    Fetch the full pool of servable bank questions for a chapter/difficulty.

    Filters out malformed rows and deduplicates by question text so the pool
    size equals the number of distinct questions a test could contain.
    """
    supabase = get_content_db(grade)
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

    return deduped


def get_bank_capacity(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> int:
    """
    Number of distinct, servable questions the bank holds for this selection.

    Used to tell the student how many questions a (small) chapter can support
    instead of failing silently. Returns 0 when the bank is unavailable.
    """
    try:
        return len(_fetch_question_pool(board, grade, subject, chapter, difficulty))
    except Exception:
        return 0


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
    has enough distinct active questions, otherwise returns [] so the caller
    can report the bank shortfall to the user (no LLM fallback).

    excluded_ids: database row IDs (as strings) of questions shown in recent
    tests for this user. Unseen questions are preferred; if exclusions leave
    fewer than num_questions, previously seen questions top up the test —
    repetition across tests is allowed as a last resort, repetition within
    one test never is.
    """
    try:
        pool = _fetch_question_pool(board, grade, subject, chapter, difficulty)

        if len(pool) < num_questions:
            return []  # Bank too small — caller reports capacity to the user

        excluded_set = {str(eid) for eid in (excluded_ids or [])}
        fresh = [q for q in pool if str(q.get("id", "")) not in excluded_set]

        if len(fresh) >= num_questions:
            sampled = random.sample(fresh, num_questions)
        else:
            # Not enough unseen questions — keep all fresh ones and top up
            # with previously seen ones so the test still has no internal dupes.
            seen = [q for q in pool if str(q.get("id", "")) in excluded_set]
            sampled = fresh + random.sample(seen, num_questions - len(fresh))
            random.shuffle(sampled)

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
                supabase = get_content_db(grade)
                supabase.rpc("increment_times_shown", {"question_ids": db_ids}).execute()
        except Exception:
            pass  # times_shown is advisory — never fail the test for this

        return sampled

    except Exception:
        return []  # Table may not exist yet — fall back to LLM


def _distribute_across_chapters(
    num_questions: int,
    capacities: dict[str, int],
) -> dict[str, int] | None:
    """
    Spread num_questions across chapters as evenly as possible, capped by
    each chapter's own bank capacity.

    Returns None if the combined capacity across all chapters can't fill
    num_questions, so the caller can report a capacity shortfall instead of
    silently serving a shorter test.
    """
    if sum(capacities.values()) < num_questions:
        return None

    counts = {chapter: 0 for chapter in capacities}
    remaining = num_questions
    active = [chapter for chapter, cap in capacities.items() if cap > 0]

    while remaining > 0 and active:
        share = max(1, remaining // len(active))
        for chapter in list(active):
            if remaining <= 0:
                break
            take = min(share, capacities[chapter] - counts[chapter], remaining)
            if take <= 0:
                active.remove(chapter)
                continue
            counts[chapter] += take
            remaining -= take
            if counts[chapter] >= capacities[chapter]:
                active.remove(chapter)

    return counts if remaining == 0 else None


def get_questions_from_bank_multi_chapter(
    board: str,
    grade: str,
    subject: str,
    chapters: list[str],
    difficulty: str,
    num_questions: int,
    exam_type: str = "General",
    excluded_ids: list[str] | None = None,
) -> list[dict]:
    """
    Sample bank questions spread across multiple chapters in one paper.

    Used for Mid Term / Annual Exam papers, which cover several chapters at
    once instead of a single chapter's Class Test. Each chapter is sampled
    independently and without replacement (via get_questions_from_bank), and
    every chapter is queried exactly once per call — so no question can ever
    repeat within the generated test, whichever chapter it came from.

    Returns [] when the combined capacity across the given chapters can't
    fill num_questions, so the caller can report the shortfall to the user.
    """
    unique_chapters = list(dict.fromkeys(c for c in chapters if c))
    if not unique_chapters:
        return []

    capacities = {
        chapter: get_bank_capacity(board, grade, subject, chapter, difficulty)
        for chapter in unique_chapters
    }

    counts = _distribute_across_chapters(num_questions, capacities)
    if counts is None:
        return []

    sampled: list[dict] = []
    for chapter, count in counts.items():
        if count <= 0:
            continue
        chapter_questions = get_questions_from_bank(
            board=board,
            grade=grade,
            subject=subject,
            chapter=chapter,
            difficulty=difficulty,
            num_questions=count,
            exam_type=exam_type,
            excluded_ids=excluded_ids,
        )
        if len(chapter_questions) < count:
            return []  # bank shrank between the capacity check and sampling
        sampled.extend(chapter_questions)

    random.shuffle(sampled)

    # Renumber 1..n across the merged set (each chapter's own sampling call
    # already renumbered 1..count on its own, so ids collide after merging).
    for index, q in enumerate(sampled, start=1):
        q["id"] = index

    return sampled


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
    """Return summary statistics for the admin question bank panel."""
    def _fetch(db):
        try:
            r = db.table("question_bank").select("status, grade, subject, difficulty").execute()
            return r.data or []
        except Exception:
            return []

    rows = _fetch(_primary_client)
    active = [r for r in rows if r.get("status") == "active"]
    needs_review = [r for r in rows if r.get("status") == "needs_review"]
    return {
        "total": len(rows),
        "active": len(active),
        "needs_review": len(needs_review),
    }
