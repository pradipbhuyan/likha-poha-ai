"""
Subjective Question Bank Service
=================================
Pre-authored short/long-answer test-paper questions stored in Supabase for
random sampling. Sibling of question_bank_service.py (which holds MCQs) —
same design principles, applied to subjective questions instead.

Design principles:
- Every operation is wrapped in try/except and fails silently.
- get_subjective_questions_from_bank returns [] when the bank is too small
  or unavailable, so the caller reports a shortfall — no LLM fallback.
- Run backend/sql/add_subjective_question_bank.sql in Supabase before enabling.
- Populate via: docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md
"""

import random

from app.services.grade_db_router import get_content_db
from app.services.mock_test_service import normalize_chapter_core, strip_source_display_prefix


def _fetch_subjective_pool(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> list[dict]:
    """
    Fetch the full pool of servable subjective bank questions for a
    chapter/difficulty. Filters malformed rows and dedupes by question text.
    """
    supabase = get_content_db(grade)
    clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()

    query = (
        supabase
        .table("subjective_question_bank")
        .select("id, question, marks, model_answer, expected_keywords")
        .eq("board", board)
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("difficulty", difficulty)
        .eq("status", "active")
    )

    if clean_chapter:
        query = query.eq("chapter", clean_chapter)

    result = query.limit(1000).execute()
    questions = result.data or []

    questions = [
        q for q in questions
        if q.get("question") and len(str(q.get("question", ""))) >= 10
        and q.get("model_answer") and len(str(q.get("model_answer", ""))) >= 15
    ]

    seen_texts: set = set()
    deduped: list = []
    for q in questions:
        text_key = str(q.get("question", "")).strip().lower()[:120]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            deduped.append(q)

    return deduped


def _fetch_subjective_pool_fuzzy(
    board: str,
    grade: str,
    subject: str,
    chapter_core: str,
    difficulty: str,
) -> list[dict]:
    """
    Same as _fetch_subjective_pool, but matches chapter via an ILIKE substring
    on an already-normalized "core" chapter title — see normalize_chapter_core()
    in mock_test_service.py, which callers use to compute chapter_core.
    """
    supabase = get_content_db(grade)
    if not chapter_core:
        return []

    query = (
        supabase
        .table("subjective_question_bank")
        .select("id, question, marks, model_answer, expected_keywords")
        .eq("board", board)
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("difficulty", difficulty)
        .eq("status", "active")
        .ilike("chapter", f"%{chapter_core}%")
    )

    result = query.limit(1000).execute()
    questions = result.data or []

    questions = [
        q for q in questions
        if q.get("question") and len(str(q.get("question", ""))) >= 10
        and q.get("model_answer") and len(str(q.get("model_answer", ""))) >= 15
    ]

    seen_texts: set = set()
    deduped: list = []
    for q in questions:
        text_key = str(q.get("question", "")).strip().lower()[:120]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            deduped.append(q)

    return deduped


def _sample_pool(pool: list[dict], num_questions: int) -> list[dict]:
    """Sample num_questions from an already-fetched pool. [] if too small."""
    if len(pool) < num_questions:
        return []
    sampled = random.sample(pool, num_questions)
    for index, q in enumerate(sampled, start=1):
        q["id"] = index
    return sampled


def get_subjective_bank_capacity(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> int:
    """Number of distinct, servable subjective questions for this selection."""
    try:
        return len(_fetch_subjective_pool(board, grade, subject, chapter, difficulty))
    except Exception:
        return 0


def get_subjective_bank_capacity_fuzzy(
    board: str,
    grade: str,
    subject: str,
    chapter_core: str,
    difficulty: str,
) -> int:
    """Capacity lookup via ILIKE substring match on a normalized chapter core."""
    try:
        return len(_fetch_subjective_pool_fuzzy(board, grade, subject, chapter_core, difficulty))
    except Exception:
        return 0


def get_subjective_questions_from_bank(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
    num_questions: int,
) -> list[dict]:
    """
    Sample random subjective questions from the bank for a test paper.

    Returns [] if the bank doesn't have enough distinct active questions, so
    the caller can report the shortfall to the user (no LLM fallback).
    """
    try:
        pool = _fetch_subjective_pool(board, grade, subject, chapter, difficulty)
        return _sample_pool(pool, num_questions)
    except Exception:
        return []


def get_subjective_questions_from_bank_fuzzy(
    board: str,
    grade: str,
    subject: str,
    chapter_core: str,
    difficulty: str,
    num_questions: int,
) -> list[dict]:
    """Sample subjective questions via ILIKE substring match on a normalized chapter core."""
    try:
        pool = _fetch_subjective_pool_fuzzy(board, grade, subject, chapter_core, difficulty)
        return _sample_pool(pool, num_questions)
    except Exception:
        return []


def get_subjective_questions_from_bank_with_fallback(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    difficulty: str,
    num_questions: int,
) -> list[dict]:
    """
    Look up subjective bank questions with the same chapter-display-format
    fallback tiers as get_questions_from_bank_with_fallback() in
    mock_test_service.py: exact match -> source-prefix stripped -> fully
    normalized "core" title -> ILIKE substring match on that core title.
    """
    questions = get_subjective_questions_from_bank(
        board=board, grade=grade, subject=subject, chapter=chapter,
        difficulty=difficulty, num_questions=num_questions,
    )
    if questions:
        return questions

    stripped = strip_source_display_prefix(chapter)
    if stripped and stripped != chapter:
        questions = get_subjective_questions_from_bank(
            board=board, grade=grade, subject=subject, chapter=stripped,
            difficulty=difficulty, num_questions=num_questions,
        )
        if questions:
            return questions

    core = normalize_chapter_core(chapter)
    if core and core not in (chapter, stripped):
        questions = get_subjective_questions_from_bank(
            board=board, grade=grade, subject=subject, chapter=core,
            difficulty=difficulty, num_questions=num_questions,
        )
        if questions:
            return questions

    if core:
        questions = get_subjective_questions_from_bank_fuzzy(
            board=board, grade=grade, subject=subject, chapter_core=core,
            difficulty=difficulty, num_questions=num_questions,
        )

    return questions


def get_subjective_bank_capacity_with_fallback(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> int:
    """Subjective bank capacity lookup with the same fallback tiers as sampling."""
    capacity = get_subjective_bank_capacity(board, grade, subject, chapter, difficulty)
    if capacity:
        return capacity

    stripped = strip_source_display_prefix(chapter or "")
    if stripped and stripped != chapter:
        capacity = get_subjective_bank_capacity(board, grade, subject, stripped, difficulty)
        if capacity:
            return capacity

    core = normalize_chapter_core(chapter or "")
    if core and core not in (chapter, stripped):
        capacity = get_subjective_bank_capacity(board, grade, subject, core, difficulty)
        if capacity:
            return capacity

    if core:
        return get_subjective_bank_capacity_fuzzy(board, grade, subject, core, difficulty)

    return capacity


def add_questions_to_subjective_bank(
    questions: list[dict],
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    difficulty: str,
) -> None:
    """
    Add GPT-5.5-authored subjective questions to the bank.

    Validates each question has a real question and model answer, and
    deduplicates against existing bank entries. Failures are silently ignored.
    """
    if not questions:
        return

    supabase = get_content_db(grade)
    try:
        clean_chapter = "".join(c for c in (chapter or "") if c.isprintable()).strip()

        valid_questions = [
            q for q in questions
            if q.get("question") and len(str(q.get("question", ""))) >= 10
            and q.get("model_answer") and len(str(q.get("model_answer", ""))) >= 15
        ]

        if not valid_questions:
            return

        try:
            existing = supabase.table("subjective_question_bank").select("question").eq(
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
            if text_key in existing_texts or text_key in seen_in_batch:
                continue
            seen_in_batch.add(text_key)
            rows.append({
                "board": board,
                "grade": grade,
                "subject": subject,
                "chapter": clean_chapter,
                "difficulty": difficulty,
                "question": q.get("question") or "",
                "marks": int(q.get("marks") or 3),
                "model_answer": q.get("model_answer") or "",
                "expected_keywords": q.get("expected_keywords") or [],
                "status": "active",
            })

        if rows:
            supabase.table("subjective_question_bank").insert(rows).execute()

    except Exception:
        pass  # Bank inserts must never break test-paper delivery


def clear_subjective_bank_for_chapter(grade: str, subject: str, chapter: str) -> int:
    """
    Delete all subjective bank rows for one chapter, regardless of which
    display-prefix format they were stored under — mirrors
    clear_question_bank_for_chapter() in prewarm_service.py. Used by the
    GPT-5.5 ingest script so a re-authored chapter fully replaces its old
    question set instead of accumulating duplicates. Returns rows deleted.
    """
    core = normalize_chapter_core(chapter)
    if not core:
        return 0
    try:
        result = (
            get_content_db(grade)
            .table("subjective_question_bank")
            .delete()
            .eq("grade", grade)
            .eq("subject", subject)
            .ilike("chapter", f"%{core}%")
            .execute()
        )
        return len(result.data or [])
    except Exception:
        return 0
