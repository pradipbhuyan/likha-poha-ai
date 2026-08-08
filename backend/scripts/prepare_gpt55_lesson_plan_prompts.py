#!/usr/bin/env python3
"""
Prepare GPT-5.5 Lesson-Plan Handout Authoring Prompts
=============================================================================
See docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md for the full workflow.

Generates one prompt .txt file per chapter, grounded in the chapter's ALREADY
AUTHORED lesson_cache content — the same grounding source
prepare_gpt55_question_prompts.py uses. A chapter with no authored lesson_cache
content yet is skipped with a clear warning.

Each authored handout is duration-agnostic (sized for a standard ~40-45
minute CBSE period) since a single static file can't vary by the duration a
teacher picks at request time — see the doc for why.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_lesson_plan_prompts.py --grade "Grade 9" --subject "Social Science"
    python3 scripts/prepare_gpt55_lesson_plan_prompts.py --grade "Grade 11" --subject Biology \\
        --chapters "Chapter 1: X,Chapter 3: Y"
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

You are an experienced CBSE {subject} school teacher creating a classroom-
ready lesson plan handout for Grade {grade_number}, for one specific chapter,
for a CBSE AI tutoring platform used by teachers. You must ground every
activity, example, and reference strictly in the CHAPTER_LESSON_TEXT
provided below — never invent NCERT exercise/example numbers, facts, or
figures that do not appear there.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every concept, example, and NCERT reference in the plan MUST
   be grounded in CHAPTER_LESSON_TEXT. Do not invent exercise numbers,
   figure numbers, or facts that do not appear there.
2. DURATION: Size the plan for a single standard ~40-45 minute CBSE class
   period. Do not ask for a duration — always produce one plan sized this
   way.
3. FULL COVERAGE: The plan must cover the chapter's main concepts as a
   whole, not just one narrow sub-topic.
4. PRACTICAL, NOT ACADEMIC: Write in the voice of an experienced classroom
   teacher's planning notes — short, actionable bullet points, not
   textbook prose.
5. LANGUAGE LEVEL: Write for a teacher instructing Grade {grade_number}
   students — clear, classroom-appropriate CBSE phrasing.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}

CHAPTER_LESSON_TEXT:
\"\"\"
{chapter_lesson_text}
\"\"\"

Produce ONE lesson plan in Markdown, using EXACTLY this section structure:

## 📋 Lesson Overview
- **Topic:** {chapter}
- **Grade:** {grade}
- **Subject:** {subject}
- **Duration:** 40-45 minutes
- **CBSE Unit:** (identify the unit/chapter from NCERT)

## 🎯 Learning Objectives
By the end of this lesson, students will be able to:
1. (recall/understand level objective)
2. (application level objective)
3. (analysis/evaluation level objective — HOTS)

## 📚 Prerequisites
Students should already know:
- (prerequisite 1)
- (prerequisite 2)

## 🛠️ Materials & Resources
- NCERT Textbook {grade} {subject}
- Blackboard / Whiteboard
- (additional materials specific to this topic)

## 📝 Lesson Plan (Step-by-Step)

### 🔔 Introduction & Hook (5 minutes)
- (attention-grabbing opening activity or question)
- Connect to prior knowledge

### 📖 Direct Instruction (15 minutes)
- (key concept explanation step by step)
- Include the main formula/rule/concept

### 🔬 Guided Practice (10 minutes)
- (worked example with student participation)
- Solve one problem together on the board

### 🏃 Student Activity (10 minutes)
- (individual or pair activity)
- Practice problems from NCERT

### ✅ Assessment & Closure (5 minutes)
- Quick oral questions to check understanding
- Summary of key points
- Exit ticket: (one question to assess learning)

## 📘 Homework Assignment
- NCERT Exercise: (specific exercise numbers)
- (any additional practice)

## 🎯 Differentiation Strategies
- **For slow learners:** (simplified approach or extra support)
- **For advanced learners:** (extension or HOTS challenge)

## 📌 Common Misconceptions to Address
1. (common student mistake 1)
2. (common student mistake 2)

## 🔗 NCERT Alignment
- Chapter reference, Exercise numbers, Example numbers

Return ONLY a single valid JSON object (no markdown fences, no commentary
before or after) with exactly this shape:

{{
  "grade": "{grade}",
  "subject": "{subject}",
  "chapter": "{chapter}",
  "lesson_plan_markdown": "## 📋 Lesson Overview\\n- **Topic:** ...\\n(the full markdown plan, using \\n for line breaks)"
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
    """Distinct chapters with active authored lesson_cache content."""
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
    """Join all active lesson_cache step content for one chapter into one grounding string."""
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
) -> None:
    grade_number = grade.split()[-1]

    chapters = get_lesson_authored_chapters(grade, subject)
    if not chapters:
        print(f"ERROR: no authored lesson_cache content found for {grade} / {subject}. "
              f"Nothing to ground a lesson plan in yet — run the lesson pipeline for this "
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

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 lesson-plan prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {len(chapters)}\n")

    index_lines = [
        f"GPT-5.5 Lesson-Plan Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each chapter below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <chapter_slug>_lesson_plan.json in this folder.",
        "  4. Once all chapters are done, ingest them all in one command:",
        "",
        f"     cd backend",
        f"     python3 scripts/ingest_gpt55_lesson_plan_output.py --dir {output_dir} --dry-run",
        f"     python3 scripts/ingest_gpt55_lesson_plan_output.py --dir {output_dir}",
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
        index_lines.append(f"       expected output: {slug}_lesson_plan.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 lesson-plan handout authoring prompts, "
                     "grounded in authored lesson_cache content"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Social Science"')
    parser.add_argument(
        "--chapters", default=None,
        help="Comma-separated list of exact chapter strings to scope to "
             "(default: all authored chapters for this grade/subject)",
    )
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Lesson_Plan_Prompts_{grade_slug}_{subject_slug}"

    only_chapters = [c for c in (args.chapters.split(",") if args.chapters else []) if c.strip()]

    run(
        grade=args.grade,
        subject=args.subject,
        output_dir=output_dir,
        only_chapters=only_chapters or None,
    )


if __name__ == "__main__":
    main()
