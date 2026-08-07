#!/usr/bin/env python3
"""
Seed Doubt Knowledge Base (DKB) directly from existing lesson_cache content
=============================================================================
Per user request: "I want to completely eliminate LLM calls for Ask Doubt
and wherever a chat interface exists." Chosen approach (Option A): massively
expand DKB coverage using Q&A pairs ALREADY WRITTEN inside the GPT-5.5/
prewarm-generated lesson_cache content — the "Worked example" and "Quick
check question" sections every lesson step already contains — instead of
calling an LLM to generate new questions (the existing admin "DKB prewarm"
button in app/services/prewarm_service.py does call an LLM; this script
does not).

For every active lesson_cache row across every grade, this script:
  1. Parses out the "Worked example" Question/Answer pair (if present).
  2. Parses out the "Quick check question" Question/Answer/Explanation
     (if present).
  3. Skips a pair if an existing DKB row already has the exact same
     question text for that grade/subject/chapter (idempotent, safe to
     re-run after new chapters are ingested).
  4. Stores each new pair via doubt_kb_service.store_in_doubt_kb(), which
     generates a real OpenAI embedding for semantic-search matching later
     (a small one-time embedding cost — NOT a per-student LLM answer cost;
     text-embedding-3-small is billed at a small fraction of a cent per
     1,000 tokens and this runs once, not once per doubt asked).

This is a pure content-extraction step — it does NOT call ask_llm() at any
point, so no chat-completion tokens are spent by this script itself.

Usage:
    cd backend
    venv/bin/python3 scripts/seed_doubt_kb_from_lessons.py --grade "Grade 11"
    venv/bin/python3 scripts/seed_doubt_kb_from_lessons.py --all-grades
    venv/bin/python3 scripts/seed_doubt_kb_from_lessons.py --all-grades --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402
from app.services.doubt_kb_service import store_in_doubt_kb  # noqa: E402

ALL_GRADES = [
    "Grade 5", "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11", "Grade 12",
]

# Matches an ```extract-ref ... ``` fenced JSON block so it can be stripped
# out of an Answer body before storing (the raw JSON citation payload isn't
# useful as a spoken answer to a student).
_EXTRACT_REF_RE = re.compile(r"```extract-ref.*?```", re.DOTALL)


def _strip_extract_ref(text: str) -> str:
    return _EXTRACT_REF_RE.sub("", text).strip()


def _extract_worked_example(lesson_markdown: str) -> tuple[str, str] | None:
    """Pull the Question/Answer pair out of the '## Worked example' section.

    Handles both the humanities format:
        Question: ...
        ```extract-ref ... ```   (optional, stripped)
        Answer:
        - ...
        - Final answer: ...
    and the science/maths format:
        Question: ...
        Solution:
        - ...
        - Final answer: ...
    Returns (question, answer) or None if the section/pattern isn't found.
    """
    # Hindi lessons translate the section header ("हल किया गया उदाहरण")
    # but keep the internal Question:/Answer:/Solution: labels in English --
    # confirmed by direct inspection across Grades 6, 7, 8, 9, 12 Hindi content.
    match = re.search(
        r"##\s*(?:Worked example|हल किया गया उदाहरण)\s*\n(.*?)(?=\n##\s|\Z)",
        lesson_markdown,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    section = match.group(1).strip()

    q_match = re.search(
        r"Question:\s*(.+?)(?=\n(?:```extract-ref|Answer:|Solution:))",
        section,
        re.DOTALL | re.IGNORECASE,
    )
    a_match = re.search(
        r"(?:Answer|Solution):\s*\n?(.+)\Z",
        section,
        re.DOTALL | re.IGNORECASE,
    )
    if not q_match or not a_match:
        return None

    question = q_match.group(1).strip()
    answer = _strip_extract_ref(a_match.group(1)).strip()
    if not question or not answer:
        return None
    return question, answer


def _extract_quick_check(lesson_markdown: str) -> tuple[str, str] | None:
    """Pull Question/Answer/Explanation out of '## Quick check question'.

    Combines Answer + Explanation into one answer string so the student
    gets both the direct answer and the reasoning behind it.
    """
    match = re.search(
        r"##\s*(?:Quick check question|शीघ्र जाँच प्रश्न)\s*\n(.*?)(?=\n##\s|\Z)",
        lesson_markdown,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    section = match.group(1).strip()

    q_match = re.search(r"Question:\s*(.+?)(?=\nAnswer:)", section, re.DOTALL | re.IGNORECASE)
    a_match = re.search(r"Answer:\s*(.+?)(?=\nExplanation:|\Z)", section, re.DOTALL | re.IGNORECASE)
    e_match = re.search(r"Explanation:\s*(.+)\Z", section, re.DOTALL | re.IGNORECASE)

    if not q_match or not a_match:
        return None

    question = q_match.group(1).strip()
    answer_text = a_match.group(1).strip()
    if e_match:
        explanation_text = e_match.group(1).strip()
        answer_text = f"{answer_text}\n\n{explanation_text}"
    if not question or not answer_text:
        return None
    return question, answer_text


def seed_grade(grade: str, dry_run: bool = False) -> dict:
    """Extract and store DKB entries for every lesson_cache row in one grade.

    Returns a summary dict: {"scanned": N, "extracted": N, "stored": N,
    "skipped_duplicate": N, "skipped_no_match": N}.
    """
    db = get_content_db(grade)

    print(f"\n{'=' * 70}")
    print(f"  Grade: {grade}{'  [DRY RUN — no writes]' if dry_run else ''}")
    print(f"{'=' * 70}")

    # Supabase's default REST page size is 1000 rows — both lesson_cache
    # (Grade 11 alone has 1200+ active rows) and doubt_kb (some grades
    # already have 2000+ Q&A pairs, see prewarm_service.py's own comment
    # about this exact same limit) can exceed that in a single .execute()
    # call, which would silently truncate results instead of erroring.
    # Paginate explicitly with .range() to fetch every row.
    def _fetch_all(table_name: str, select_cols: str) -> list[dict]:
        all_rows: list[dict] = []
        page_size = 1000
        offset = 0
        while True:
            page = (
                db.table(table_name)
                .select(select_cols)
                .eq("grade", grade)
                .eq("status", "active")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            page_rows = page.data or []
            all_rows.extend(page_rows)
            if len(page_rows) < page_size:
                break
            offset += page_size
        return all_rows

    lessons = _fetch_all("lesson_cache", "grade,subject,chapter,step_title,lesson_content")
    print(f"  Found {len(lessons)} active lesson_cache row(s) for {grade}.")

    # Pre-load existing DKB questions per (subject, chapter) to avoid an
    # extra DB round-trip per candidate pair, and to make this idempotent
    # on re-runs (skip a question if it's already stored verbatim).
    existing_rows = _fetch_all("doubt_kb", "subject,chapter,question")
    existing_questions: set[tuple[str, str, str]] = {
        (
            (row.get("subject") or "").strip(),
            (row.get("chapter") or "").strip(),
            (row.get("question") or "").strip().lower(),
        )
        for row in existing_rows
    }
    print(f"  {len(existing_questions)} existing DKB question(s) already stored for {grade}.")

    scanned = 0
    extracted = 0
    stored = 0
    skipped_duplicate = 0
    skipped_no_match = 0

    for row in lessons:
        scanned += 1
        subject = row["subject"]
        chapter = row["chapter"]
        content = row.get("lesson_content") or ""

        candidates: list[tuple[str, str]] = []
        we = _extract_worked_example(content)
        if we:
            candidates.append(we)
        qc = _extract_quick_check(content)
        if qc:
            candidates.append(qc)

        if not candidates:
            skipped_no_match += 1
            continue

        for question, answer in candidates:
            extracted += 1
            dedupe_key = (subject.strip(), chapter.strip(), question.strip().lower())
            if dedupe_key in existing_questions:
                skipped_duplicate += 1
                continue

            if dry_run:
                stored += 1
                existing_questions.add(dedupe_key)
                continue

            new_id = store_in_doubt_kb(
                question=question,
                answer=answer,
                grade=grade,
                subject=subject,
                chapter=chapter,
                mode="CBSE",
                board="CBSE",
                source="lesson_content",
            )
            if new_id:
                stored += 1
                existing_questions.add(dedupe_key)
            else:
                print(f"    [warn] failed to store: {subject} / {chapter} — {question[:60]!r}")

            # Gentle pacing: still one OpenAI embedding call per new Q&A,
            # avoid bursting the embeddings endpoint on large grades.
            time.sleep(0.05)

    print(f"  Scanned: {scanned} lesson rows")
    print(f"  Extracted candidate Q&A pairs: {extracted}")
    print(f"  Stored (new): {stored}")
    print(f"  Skipped (already existed): {skipped_duplicate}")
    print(f"  Lesson rows with no extractable Q&A: {skipped_no_match}")

    return {
        "scanned": scanned,
        "extracted": extracted,
        "stored": stored,
        "skipped_duplicate": skipped_duplicate,
        "skipped_no_match": skipped_no_match,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Doubt Knowledge Base from existing lesson_cache Q&A content (no LLM calls)."
    )
    parser.add_argument("--grade", help='e.g. "Grade 11" — process a single grade')
    parser.add_argument("--all-grades", action="store_true", help="Process every grade")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without writing to the DB")
    args = parser.parse_args()

    if not args.grade and not args.all_grades:
        print("ERROR: pass --grade \"Grade N\" or --all-grades")
        sys.exit(1)

    grades = ALL_GRADES if args.all_grades else [args.grade]

    totals = {"scanned": 0, "extracted": 0, "stored": 0, "skipped_duplicate": 0, "skipped_no_match": 0}
    for grade in grades:
        result = seed_grade(grade, dry_run=args.dry_run)
        for key in totals:
            totals[key] += result[key]

    print(f"\n{'=' * 70}")
    print("  GRAND TOTAL")
    print(f"{'=' * 70}")
    for key, value in totals.items():
        print(f"  {key}: {value}")
    print()


if __name__ == "__main__":
    main()
