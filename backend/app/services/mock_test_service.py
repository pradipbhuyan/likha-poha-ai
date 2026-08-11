import json
import random
import re

from app.services.logger_service import get_logger
from app.services.openai_service import ask_llm
from app.services.question_bank_service import (
    get_questions_from_bank,
    get_bank_capacity,
    get_questions_from_bank_fuzzy,
    get_bank_capacity_fuzzy,
    _distribute_across_chapters,
)

# subjective_question_bank_service imports normalize_chapter_core /
# strip_source_display_prefix from this module, so it's imported lazily
# inside _bank_written_questions() below to avoid a circular import.

_log = get_logger("services.mock_test")

# Display-source prefixes added by the syllabus review UI when multiple books
# are uploaded for one subject (e.g. "Text Book - ", "Supplementary Reader - ").
# The question bank may have been built BEFORE these prefixes were introduced,
# so we try the un-prefixed chapter name as a fallback.
_SOURCE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:Text Book|Supplementary Reader|Grammar|Workbook|Reader|"
    r"History|Geography|Political Science|Economics)\s*[-:]\s*",
    re.IGNORECASE,
)

# "Chapter N: " / "Chapter N - " style prefix, as now used by rag_documents /
# the syllabus dropdown after this year's chapter-cleanup work. Older
# question_bank rows were written without this prefix (bare titles).
_CHAPTER_LABEL_PREFIX_PATTERN = re.compile(
    r"^\s*chapter\s*\d+\s*[:\-]\s*", re.IGNORECASE,
)

# "Part N -" / "Part N:" style prefix (see rag_service.strip_chapter_display_prefix).
_PART_PREFIX_PATTERN = re.compile(r"^\s*part\s*\d+\s*[-:]\s*", re.IGNORECASE)

# Bare numeric-dot prefix, e.g. "1. Papa's Spectacles" (see
# rag_service.strip_chapter_number_prefix).
_NUMERIC_DOT_PREFIX_PATTERN = re.compile(r"^\s*\d+\.\s*")


def strip_source_display_prefix(chapter: str) -> str:
    """
    Remove a book-source display prefix from a chapter label.

    e.g. 'Text Book - Chapter 7: Madam Rides the Bus'
         → 'Chapter 7: Madam Rides the Bus'
    """
    return _SOURCE_PREFIX_PATTERN.sub("", chapter or "").strip()


def normalize_chapter_core(chapter: str) -> str:
    """
    Strip every known display-prefix style down to the bare chapter title.

    Used as a last-resort fuzzy match when question_bank's stored chapter
    format doesn't exactly match (with or without the book-source prefix)
    the current syllabus/rag_documents display format.

    Prefixes can be stacked (e.g. "Part 1 - Chapter 1: Title" has both a
    Part-prefix AND a Chapter-prefix, one wrapping the other), so every
    pattern is re-applied in a loop until a full pass makes no further
    change -- a single sequential pass would miss an inner prefix that only
    becomes exposed after an outer one is stripped (confirmed live: this
    exact case under-stripped "Part 1 - Chapter 1: ..." down to
    "Chapter 1: ..." instead of "...", because the Chapter-prefix pattern
    only ran once, before the Part-prefix in front of it had been removed).
    """
    core = chapter or ""
    while True:
        next_core = strip_source_display_prefix(core)
        next_core = _CHAPTER_LABEL_PREFIX_PATTERN.sub("", next_core).strip()
        next_core = _PART_PREFIX_PATTERN.sub("", next_core).strip()
        next_core = _NUMERIC_DOT_PREFIX_PATTERN.sub("", next_core).strip()
        if next_core == core:
            return core
        core = next_core


def get_questions_from_bank_with_fallback(
    board: str,
    grade: str,
    subject: str,
    chapter: str,
    difficulty: str,
    num_questions: int,
    exam_type: str = "General",
    excluded_ids: list[str] | None = None,
) -> list[dict]:
    """
    Look up bank questions with automatic chapter-display-format fallback.

    Tries, in order: (1) the chapter string as given, (2) with the
    book-source prefix stripped, (3) with every known prefix style stripped
    down to a bare "core" title, (4) an ILIKE substring match on that core
    title, for rows stored under a format not covered by the exact-match
    tiers above.

    excluded_ids: DB row IDs of questions already shown in recent tests.
    These are filtered out before sampling to prevent repetition across tests.
    """
    questions = get_questions_from_bank(
        board=board, grade=grade, subject=subject, chapter=chapter,
        difficulty=difficulty, num_questions=num_questions,
        exam_type=exam_type, excluded_ids=excluded_ids,
    )
    if questions:
        return questions

    stripped = strip_source_display_prefix(chapter)
    if stripped and stripped != chapter:
        questions = get_questions_from_bank(
            board=board, grade=grade, subject=subject, chapter=stripped,
            difficulty=difficulty, num_questions=num_questions,
            exam_type=exam_type, excluded_ids=excluded_ids,
        )
        if questions:
            return questions

    core = normalize_chapter_core(chapter)
    if core and core not in (chapter, stripped):
        questions = get_questions_from_bank(
            board=board, grade=grade, subject=subject, chapter=core,
            difficulty=difficulty, num_questions=num_questions,
            exam_type=exam_type, excluded_ids=excluded_ids,
        )
        if questions:
            return questions

    if core:
        questions = get_questions_from_bank_fuzzy(
            board=board, grade=grade, subject=subject, chapter_core=core,
            difficulty=difficulty, num_questions=num_questions,
            excluded_ids=excluded_ids,
        )

    return questions


def get_bank_capacity_with_fallback(
    board: str,
    grade: str,
    subject: str,
    chapter: str | None,
    difficulty: str,
) -> int:
    """Bank capacity lookup with the same chapter-format fallback tiers as sampling."""
    capacity = get_bank_capacity(board, grade, subject, chapter, difficulty)
    if capacity:
        return capacity

    stripped = strip_source_display_prefix(chapter or "")
    if stripped and stripped != chapter:
        capacity = get_bank_capacity(board, grade, subject, stripped, difficulty)
        if capacity:
            return capacity

    core = normalize_chapter_core(chapter or "")
    if core and core not in (chapter, stripped):
        capacity = get_bank_capacity(board, grade, subject, core, difficulty)
        if capacity:
            return capacity

    if core:
        return get_bank_capacity_fuzzy(board, grade, subject, core, difficulty)

    return capacity


def get_questions_from_bank_multi_chapter_with_fallback(
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
    Multi-chapter bank sampling (Mid-Term / Annual papers) with the same
    chapter-display-format fallback tiers as the single-chapter path.

    question_bank_service.get_questions_from_bank_multi_chapter only does
    exact-match lookups per chapter, so it under-reports capacity for any
    chapter whose bank rows are stored under a different display-prefix
    format than the current syllabus/rag_documents naming. This mirrors its
    distribute-then-sample logic but routes each chapter through the
    fallback-aware single-chapter functions instead.
    """
    unique_chapters = list(dict.fromkeys(c for c in chapters if c))
    if not unique_chapters:
        return []

    capacities = {
        chapter: get_bank_capacity_with_fallback(board, grade, subject, chapter, difficulty)
        for chapter in unique_chapters
    }

    counts = _distribute_across_chapters(num_questions, capacities)
    if counts is None:
        return []

    sampled: list[dict] = []
    for chapter, count in counts.items():
        if count <= 0:
            continue
        chapter_questions = get_questions_from_bank_with_fallback(
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

    for index, q in enumerate(sampled, start=1):
        q["id"] = index

    return sampled


def bank_shortfall_message(available: int, num_questions: int, selection: str) -> str:
    """
    User-facing message when the bank cannot fill the requested test.

    Mock tests are served only from pre-built bank questions, so the student
    must either lower the question count or pick different material.
    """
    if available <= 0:
        return (
            f"Practice questions for '{selection}' are still being prepared. "
            "Please try another chapter or check back soon."
        )
    return (
        f"'{selection}' is too small for a {num_questions}-question test — "
        f"it has {available} practice questions available. "
        f"Please request {available} or fewer questions, or choose a bigger "
        "chapter or another difficulty."
    )


MOCK_TEST_SYSTEM = """
You create original CBSE mock tests for the grade requested by the user.

Return ONLY valid JSON. No markdown.

JSON schema:
{
  "questions": [
    {
      "id": 1,
      "section": "...",
      "question": "...",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "answer": "A",
      "explanation": "...",
      "marks": 1
    }
  ]
}
"""


def calculate_score(questions, user_answers):
    """
    Score submitted mock-test answers and return per-question result metadata.

    The frontend uses the result list to show selected answer, correct answer,
    explanations, and marks after submission.
    """
    total_score = 0
    max_score = 0
    results = []

    for q in questions:
        qid = str(q.get("id"))
        correct = q.get("answer")
        selected = user_answers.get(qid)
        marks = int(q.get("marks", 1))
        max_score += marks

        is_correct = selected == correct
        if is_correct:
            total_score += marks

        results.append({
            "id": q.get("id"),
            "section": q.get("section"),
            "question": q.get("question"),
            "selected": selected,
            "correct": correct,
            "is_correct": is_correct,
            "marks": marks,
            "options": q.get("options", {}),
            "explanation": q.get("explanation", "")
        })

    return total_score, max_score, results


def _subjective_bank_to_mock_questions(bank_questions: list[dict]) -> list[dict]:
    """
    Convert subjective_question_bank row format to the MockTestQuestion shape.

    Marks-based split mirrors the GPT-5.5 authoring convention: 2-3 marks is
    short-answer, 4-5 marks is long-answer (see
    prepare_gpt55_subjective_question_prompts.py).
    """
    converted = []
    for q in bank_questions:
        marks = int(q.get("marks") or 3)
        is_long = marks >= 4
        converted.append({
            "id": q.get("id"),
            "db_id": q.get("db_id"),
            "section": "Section C" if is_long else "Section B",
            "question": q.get("question", ""),
            "options": {},
            "answer": "",
            "explanation": "",
            "marks": marks,
            "question_type": "written_long" if is_long else "written_short",
            "model_answer": q.get("model_answer", ""),
            "expected_keywords": q.get("expected_keywords") or [],
        })
    return converted


def _bank_written_questions(
    grade: str,
    board: str,
    subject: str,
    chapter: str,
    difficulty: str,
    num_questions: int,
    excluded_ids: list[str] | None,
) -> list[dict]:
    """
    Try to serve written questions from the pre-authored subjective bank.

    Returns [] (never raises) if the bank can't fill the request — the caller
    falls back to live LLM generation, since the bank is only populated for a
    subset of grades/subjects so far.
    """
    try:
        from app.services.subjective_question_bank_service import (  # noqa: PLC0415
            get_subjective_questions_from_bank_with_fallback,
        )
        bank_questions = get_subjective_questions_from_bank_with_fallback(
            board=board, grade=grade, subject=subject, chapter=chapter,
            difficulty=difficulty, num_questions=num_questions,
            excluded_ids=excluded_ids,
        )
        return _subjective_bank_to_mock_questions(bank_questions)
    except Exception:
        return []


def _bank_mixed_or_written(
    grade: str,
    board: str,
    subject: str,
    chapter: str,
    difficulty: str,
    num_questions: int,
    excluded_ids: list[str] | None,
    question_format: str,
) -> list[dict] | None:
    """
    Try to serve a written/mixed test entirely from the pre-authored banks
    (question_bank for MCQ, subjective_question_bank for written).

    Returns None if either portion can't be filled from the bank, so the
    caller falls back to live LLM generation rather than returning a test
    that's half bank-sourced, half missing. Only called for single-chapter
    (Class Test) requests — multi-chapter written/mixed papers still use the
    LLM path, since there's no multi-chapter subjective bank helper yet.
    """
    if question_format == "mixed":
        mcq_count = max(1, num_questions // 2)
        written_count = num_questions - mcq_count
    else:
        mcq_count = 0
        written_count = num_questions

    written_questions: list[dict] = []
    if written_count:
        written_questions = _bank_written_questions(
            grade=grade, board=board, subject=subject, chapter=chapter,
            difficulty=difficulty, num_questions=written_count,
            excluded_ids=excluded_ids,
        )
        if len(written_questions) < written_count:
            return None

    mcq_questions: list[dict] = []
    if mcq_count:
        mcq_questions = get_questions_from_bank_with_fallback(
            board=board, grade=grade, subject=subject, chapter=chapter,
            difficulty=difficulty, num_questions=mcq_count,
            excluded_ids=excluded_ids,
        )
        if len(mcq_questions) < mcq_count:
            return None
        for q in mcq_questions:
            q["question_type"] = "mcq"

    combined = mcq_questions + written_questions
    random.shuffle(combined)
    for index, q in enumerate(combined, start=1):
        q["id"] = index
    return combined


def generate_cbse_mock_test(
    grade,
    subject,
    chapter,
    exam_type="Class Test",
    num_questions=10,
    difficulty="Medium",
    board="CBSE",
    cache_only: bool = False,
    excluded_ids: list[str] | None = None,
    question_format: str = "mcq",
    chapters: list[str] | None = None,
):
    """
    Serve a CBSE mock test.

    question_format controls the type of questions generated:
      "mcq"     → standard MCQ only (default, served from the question bank)
      "written" → short/long answer questions only (AI-generated, no bank)
      "mixed"   → mix of MCQ + written questions (AI-generated, no bank)

    MCQ tests are served exclusively from the pre-built question bank — no
    LLM call at serving time. The bank is populated offline via the admin
    prewarm pipeline. When the bank cannot fill the request, a ValueError
    with a user-facing message is raised (chapter too small / not prepared).

    cache_only is kept for caller compatibility; bank-only is now the
    behavior for every user.

    chapters: multiple chapters to draw questions from in one paper (Mid
    Term / Annual Exam). When non-empty, takes priority over the single
    `chapter` argument, which is used for Class Test papers.
    """
    selected_chapters = [c for c in (chapters or []) if c]

    # ── Written / Mixed format: try the pre-authored banks first, fall back
    # to live LLM generation for grades/subjects/chapters not yet authored
    # (or for multi-chapter Mid-Term/Annual papers, not yet bank-backed) ────
    if question_format in ("written", "mixed"):
        chapter_label = ", ".join(selected_chapters) if selected_chapters else chapter

        if not selected_chapters and chapter:
            bank_result = _bank_mixed_or_written(
                grade=grade, board=board, subject=subject, chapter=chapter,
                difficulty=difficulty, num_questions=num_questions,
                excluded_ids=excluded_ids, question_format=question_format,
            )
            if bank_result:
                return bank_result

        return _generate_written_questions(
            grade=grade, board=board, subject=subject, chapter=chapter_label,
            exam_type=exam_type, num_questions=num_questions,
            difficulty=difficulty, question_format=question_format,
        )

    if selected_chapters:
        bank_questions = get_questions_from_bank_multi_chapter_with_fallback(
            board=board,
            grade=grade,
            subject=subject,
            chapters=selected_chapters,
            difficulty=difficulty,
            num_questions=num_questions,
            exam_type=exam_type,
            excluded_ids=excluded_ids,
        )
        if bank_questions:
            return bank_questions

        available = sum(
            get_bank_capacity_with_fallback(board, grade, subject, c, difficulty)
            for c in selected_chapters
        )
        raise ValueError(
            bank_shortfall_message(
                available, num_questions, ", ".join(selected_chapters)
            )
        )

    # Uses fallback that strips display prefixes (e.g. "Text Book - ")
    # so chapters stored under their plain name are still found even when
    # the frontend sends the prefixed display label.
    bank_questions = get_questions_from_bank_with_fallback(
        board=board,
        grade=grade,
        subject=subject,
        chapter=chapter,
        difficulty=difficulty,
        num_questions=num_questions,
        exam_type=exam_type,
        excluded_ids=excluded_ids,
    )
    if bank_questions:
        return bank_questions

    available = get_bank_capacity_with_fallback(
        board, grade, subject, chapter, difficulty,
    )
    raise ValueError(
        bank_shortfall_message(available, num_questions, chapter or subject)
    )


def _generate_written_questions(
    grade, board, subject, chapter, exam_type, num_questions, difficulty, question_format
):
    """
    Generate short-answer and/or long-answer written questions via LLM.

    Returns a list of dicts compatible with MockTestQuestion schema,
    with question_type set to 'written_short' or 'written_long' instead of 'mcq'.
    No options/answer fields — student types their answer and AI evaluates it.
    """
    # Split between short and long based on format and count
    if question_format == "mixed":
        mcq_count    = max(1, num_questions // 2)
        short_count  = max(1, (num_questions - mcq_count) // 2)
        long_count   = num_questions - mcq_count - short_count
    else:
        short_count  = max(1, num_questions * 2 // 3)
        long_count   = num_questions - short_count
        mcq_count    = 0

    # Build a list of question types and marks
    type_instructions = []
    if mcq_count:
        type_instructions.append(f"- {mcq_count} MCQ questions (1 mark each): provide options A/B/C/D and correct answer")
    if short_count:
        type_instructions.append(f"- {short_count} short-answer questions (2-3 marks each): question_type = written_short")
    if long_count:
        type_instructions.append(f"- {long_count} long-answer questions (5 marks each): question_type = written_long")

    type_str = "\n".join(type_instructions)

    prompt = f"""
Create a {board} {grade} {exam_type} paper.

Grade: {grade}
Board: {board}
Subject: {subject}
Chapter: {chapter}
Exam Type: {exam_type}
Difficulty: {difficulty}
Total Questions: {num_questions}

Generate the following mix:
{type_str}

For written_short questions (2-3 marks):
- Require a 3-5 sentence answer
- Cover definitions, explain concepts, give examples
- For Maths/Science: show 1-2 step calculations

For written_long questions (5 marks):
- Require a detailed paragraph or multi-step answer
- Cover reasoning, analysis, application, or value-based questions
- For English: comprehension or composition style

For MCQ questions: provide options dict with A/B/C/D and answer field.
For written questions: leave options as empty dict {{}}, answer as empty string.
Provide model_answer (reference answer for grading) and expected_keywords list.

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "id": 1,
      "section": "Section A",
      "question_type": "mcq",
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "...",
      "marks": 1,
      "model_answer": "",
      "expected_keywords": []
    }},
    {{
      "id": 2,
      "section": "Section B",
      "question_type": "written_short",
      "question": "...",
      "options": {{}},
      "answer": "",
      "explanation": "",
      "marks": 3,
      "model_answer": "Full reference answer here...",
      "expected_keywords": ["key1", "key2", "key3"]
    }},
    {{
      "id": 3,
      "section": "Section C",
      "question_type": "written_long",
      "question": "...",
      "options": {{}},
      "answer": "",
      "explanation": "",
      "marks": 5,
      "model_answer": "Detailed reference answer here...",
      "expected_keywords": ["key1", "key2", "key3", "key4", "key5"]
    }}
  ]
}}
"""

    raw = ask_llm(
        MOCK_TEST_SYSTEM,
        prompt,
        username="admin",
        feature="cbse_written_test",
    )

    # LLMs sometimes wrap JSON in a markdown code fence despite being told not
    # to — strip one defensively before parsing.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        return data.get("questions", [])
    except Exception as e:
        _log.error(
            "mock_test.written_generation.parse_failed",
            grade=grade, subject=subject, chapter=chapter[:80] if chapter else "",
            error=str(e), raw_response=raw[:2000],
        )
        raise RuntimeError(
            f"Written question generation returned an unparseable response for "
            f"'{chapter}'. Please try again."
        ) from e
