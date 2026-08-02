#!/usr/bin/env python3
"""
Prepare GPT-5.5 Mock-Test Question-Bank Authoring Prompts
=============================================================================
See docs/GPT55_QUESTION_BANK_AUTHORING_PROMPT.md for the full workflow.

Generates one prompt .txt file per chapter, grounded in the chapter's ALREADY
AUTHORED lesson_cache content (the corrected, de-mojibaked, richly-explained
prose produced by the GPT-5.5 chapter-authoring pipeline) rather than raw PDF
text or RAG chunks — the same grounding source used by the in-app question
bank builder's lesson-cache-preferring path (see
app/services/prewarm_service.py:_get_grounding_context).

A chapter with no authored lesson_cache content yet is skipped with a clear
warning — there is nothing high-quality to ground questions in until the
lesson pipeline has run for that chapter.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_question_prompts.py --grade "Grade 11" --subject Biology
    python3 scripts/prepare_gpt55_question_prompts.py --grade "Grade 12" --subject Geography \\
        --chapters "Chapter 1: Human Geography: Nature and Scope,Chapter 3: Population"
    python3 scripts/prepare_gpt55_question_prompts.py --grade "Grade 11" --subject Chemistry \\
        --questions-per-chapter 45 --output-dir ~/Desktop/GPT55_Question_Prompts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grade_db_router import get_content_db  # noqa: E402

MODE = "CBSE"

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE {subject} question-setter creating an ORIGINAL mock-test
question bank for Grade {grade_number} students, for one specific chapter, for
a CBSE AI tutoring platform. You must act like a strict, curriculum-accurate
question-setter who never invents a fact not present in the lesson content
below, never writes an ambiguous or multi-correct-answer question, and never
contradicts the CBSE syllabus.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and example referenced in a
   question, option, or explanation MUST be grounded in CHAPTER_LESSON_TEXT
   provided below. Do not invent numbers, dates, names, or facts that do not
   appear there.
2. EXACTLY FOUR OPTIONS: Every question must have exactly four options,
   keyed "A", "B", "C", "D". Exactly one must be correct. The three
   distractors must be plausible (not obviously wrong, not silly) and must
   not themselves be true statements about the topic.
3. NO AMBIGUITY: Never write a question where more than one option could
   reasonably be argued correct, or where the correct option depends on an
   interpretation not settled by CHAPTER_LESSON_TEXT.
4. DIFFICULTY BANDS:
   - Easy: direct recall of a definition/fact/formula stated plainly in the text.
   - Medium: requires connecting two ideas from the text, or applying a
     formula/rule to a straightforward new situation.
   - Hard: requires multi-step reasoning, comparing/contrasting concepts, or
     applying the concept to a less obvious situation -- still fully
     answerable using only CHAPTER_LESSON_TEXT.
5. EXPLANATIONS MUST JUSTIFY: Each explanation must say WHY the correct
   answer is right (not just restate it), in one to two sentences.
6. NO REPETITION: Do not write two questions that test the exact same fact
   in different words. Spread coverage across the chapter's different
   sections/sub-topics as evenly as possible.
7. LANGUAGE LEVEL: Write for Grade {grade_number} level -- clear, exam-style
   CBSE phrasing.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}

CHAPTER_LESSON_TEXT:
\"\"\"
{chapter_lesson_text}
\"\"\"

Generate exactly {n_easy} Easy, {n_medium} Medium, and {n_hard} Hard
questions ({total} total).

Return ONLY a single valid JSON object (no markdown fences, no commentary
before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}"
  }},
  "questions": [
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "...",
      "difficulty": "Easy",
      "marks": 1
    }}
  ]
}}

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def get_lesson_authored_chapters(grade: str, subject: str, mode: str = MODE) -> list[str]:
    """Distinct chapters with active authored lesson_cache content, in the
    order Supabase returns them (not necessarily syllabus order)."""
    db = get_content_db(grade)
    rows = (
        db.table("lesson_cache")
        .select("chapter")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("mode", mode)
        .eq("status", "active")
        .execute()
    )
    seen: list[str] = []
    for r in (rows.data or []):
        ch = r.get("chapter")
        if ch and ch not in seen:
            seen.append(ch)
    return seen


def get_chapter_lesson_text(grade: str, subject: str, chapter: str, mode: str = MODE) -> str:
    """Join all active lesson_cache step content for one chapter into one
    grounding string."""
    db = get_content_db(grade)
    rows = (
        db.table("lesson_cache")
        .select("lesson_content")
        .eq("grade", grade)
        .eq("subject", subject)
        .eq("chapter", chapter)
        .eq("mode", mode)
        .eq("status", "active")
        .execute()
    )
    texts = [r.get("lesson_content", "") for r in (rows.data or []) if r.get("lesson_content")]
    return "\n\n".join(texts)


def run(
    grade: str,
    subject: str,
    output_dir: Path,
    only_chapters: list[str] | None,
    questions_per_chapter: int,
) -> None:
    grade_number = grade.split()[-1]

    chapters = get_lesson_authored_chapters(grade, subject)
    if not chapters:
        print(f"ERROR: no authored lesson_cache content found for {grade} / {subject}. "
              f"Nothing to ground questions in yet — run the lesson pipeline for this "
              f"subject first.")
        sys.exit(1)

    if only_chapters:
        wanted = {c.strip() for c in only_chapters}
        chapters = [c for c in chapters if c in wanted]
        missing = wanted - set(chapters)
        if missing:
            print(f"[warn] These requested chapters have no authored lesson content "
                  f"(or the string didn't match exactly) and will be skipped: {sorted(missing)}")
        if not chapters:
            print("ERROR: none of the requested --chapters matched an authored chapter.")
            sys.exit(1)

    n_easy = questions_per_chapter // 3
    n_medium = questions_per_chapter // 3
    n_hard = questions_per_chapter - n_easy - n_medium

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 question-bank prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {len(chapters)}")
    print(f"  Questions per chapter: {questions_per_chapter} "
          f"({n_easy} Easy / {n_medium} Medium / {n_hard} Hard)\n")

    index_lines = [
        f"GPT-5.5 Question-Bank Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each chapter below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <chapter_slug>_questions.json in this folder.",
        "  4. Once all chapters are done, ingest them all in one command:",
        "",
        f"     cd backend",
        f"     python3 scripts/ingest_gpt55_question_bank_output.py --dir {output_dir} --dry-run",
        f"     python3 scripts/ingest_gpt55_question_bank_output.py --dir {output_dir}",
        "",
        "Chapters:",
    ]

    written = 0
    for i, chapter in enumerate(chapters, start=1):
        lesson_text = get_chapter_lesson_text(grade, subject, chapter)
        if len(lesson_text.strip()) < 200:
            print(f"  [{i:02d}] {chapter} -- [skip] authored lesson content is suspiciously short")
            continue

        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade,
            grade_number=grade_number,
            subject=subject,
            chapter=chapter,
            chapter_lesson_text=lesson_text,
            n_easy=n_easy,
            n_medium=n_medium,
            n_hard=n_hard,
            total=questions_per_chapter,
        )

        slug = _slugify(chapter)
        prompt_path = output_dir / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        written += 1
        print(f"  [{i:02d}] {chapter}")
        print(f"       -> wrote {prompt_path.name} ({len(prompt_text):,} chars, "
              f"grounded in {len(lesson_text):,} chars of lesson content)")
        index_lines.append(f"  [{i:02d}] {chapter}")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {slug}_questions.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 mock-test question-bank authoring prompts, "
                     "grounded in authored lesson_cache content"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 11"')
    parser.add_argument("--subject", required=True, help='e.g. "Biology"')
    parser.add_argument(
        "--chapters", default=None,
        help="Comma-separated list of exact chapter strings to scope to "
             "(default: all authored chapters for this grade/subject)",
    )
    parser.add_argument(
        "--questions-per-chapter", type=int, default=30,
        help="Total questions per chapter, split evenly across Easy/Medium/Hard (default: 30)",
    )
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Question_Prompts_{grade_slug}_{subject_slug}"

    only_chapters = [c for c in (args.chapters.split(",") if args.chapters else []) if c.strip()]

    run(
        grade=args.grade,
        subject=args.subject,
        output_dir=output_dir,
        only_chapters=only_chapters or None,
        questions_per_chapter=args.questions_per_chapter,
    )


if __name__ == "__main__":
    main()
