#!/usr/bin/env python3
"""
Prepare GPT-5.5 Doubt Knowledge Base (DKB) Authoring Prompts
=============================================================================
See docs/GPT55_DOUBT_KB_AUTHORING_PROMPT.md for the full workflow.

Generates one prompt .txt file per chapter, grounded in the chapter's ALREADY
AUTHORED lesson_cache content (the corrected, de-mojibaked, richly-explained
prose produced by the GPT-5.5 chapter-authoring pipeline) rather than raw PDF
text or RAG chunks -- the same grounding source used by
prepare_gpt55_question_prompts.py.

A chapter with no authored lesson_cache content yet is skipped with a clear
warning -- there is nothing high-quality to ground Q&A pairs in until the
lesson pipeline has run for that chapter.

This is the high-quality, deliberate-coverage counterpart to the existing
live auto-prewarm (doubt_kb_service.prewarm_doubt_kb_for_grade, gpt-4.1-nano,
admin "Build" button) -- that one stays as the fast/cheap option; this
pipeline is for building the DKB out to near-full syllabus coverage.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_doubt_kb_prompts.py --grade "Grade 9" --subject Science
    python3 scripts/prepare_gpt55_doubt_kb_prompts.py --grade "Grade 11" --subject Biology \\
        --chapters "Chapter 1: The Living World,Chapter 2: Biological Classification"
    python3 scripts/prepare_gpt55_doubt_kb_prompts.py --grade "Grade 10" --subject Maths \\
        --questions-per-chapter 40 --output-dir ~/Desktop/GPT55_DKB_Prompts
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

You are a senior CBSE {subject} tutor building an ORIGINAL "doubt bank" of
questions students commonly ask about one specific Grade {grade_number}
chapter, for a CBSE AI tutoring platform. Each entry pairs a realistic
student question with a direct, correct answer. You must act like a strict,
curriculum-accurate tutor who never invents a fact not present in the
chapter text below, and never contradicts the CBSE syllabus.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and example in an answer MUST
   be grounded in CHAPTER_LESSON_TEXT provided below. Do not invent numbers,
   dates, names, or facts that do not appear there.
2. QUESTION DIVERSITY: Spread questions across these categories, roughly
   evenly, and cover the chapter's different sections/sub-topics as evenly
   as possible:
   - Definition ("What is...?", "Define...?")
   - Conceptual / "why" ("Why does...?", "What is the difference between...?")
   - Application / "how" ("How does...?", "Give an example of...?")
   - Common misconception ("Is it true that...?", "Why isn't it...?")
   Do NOT name the chapter, unit, or lesson inside the question (no "in this
   chapter", "in Chapter 9", "in this topic", quoting the chapter title,
   etc.). Write each question exactly as a real student would type it,
   referring only to the concept itself -- a student asking a doubt never
   says "in this chapter."
3. NO REPETITION: Do not write two questions that test the exact same fact
   in different words.
4. ANSWER STYLE: Write each answer as flowing, natural prose in a real
   tutor's voice -- 3 to 6 sentences, varying naturally in length across the
   30 answers based on what the question actually needs. Do not make every
   answer the same length or shape.
   - Do NOT reuse a fixed template/skeleton across answers. In particular,
     NEVER use stock openers like "The main idea behind X is...", "A related
     point is...", "This is confirmed by the related fact that...", "The
     chapter also connects this with the fact that...", "The chapter defines
     X as follows...", or "That interpretation is not correct. The correct
     chapter point is..." (or equivalents in another language, e.g. "...का
     मुख्य विचार है", "इससे जुड़ा दूसरा तथ्य है", "पाठ में सही बात यह दी गई
     है"). Every answer should read as if a different person wrote its
     opening sentence.
   - Synthesize each answer in your own words. Do not stitch together
     verbatim quoted fragments from CHAPTER_LESSON_TEXT into a patchwork --
     use direct quotes only for a genuine technical term, formula, or named
     definition, and even then sparingly.
   - Never say "the textbook says", "the chapter says/defines/connects", or
     reference chapter/page numbers -- answer exactly as a tutor would if
     the student asked the question out loud, from knowledge.
5. LANGUAGE LEVEL: Write for Grade {grade_number} level -- clear, exam-style
   CBSE phrasing for the question, plain explanatory language for the answer.

-----------------------------------------------------------------------------
EXAMPLE OF THE REQUIRED STYLE (illustrative only -- do not reuse this content)

BAD -- do not write like this (templated, names the chapter, stitches quotes):
  Q: "Why is 'photosynthesis' important in Chapter 6: Life Processes?"
  A: "The main idea behind 'photosynthesis' is: it is the process by which
  plants make food. A related point is: it requires sunlight, water, and
  carbon dioxide. The chapter also connects this with the fact that oxygen
  is released as a by-product."

GOOD -- write like this instead (natural, no chapter reference, own words):
  Q: "Why do plants need sunlight to make their own food?"
  A: "Plants use sunlight as the energy source that powers photosynthesis --
  without it they can't convert water and carbon dioxide into glucose. The
  chlorophyll in their leaves absorbs that light energy and uses it to drive
  the reaction. It's also why a plant kept in the dark for too long turns
  pale and stops growing well."

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}

CHAPTER_LESSON_TEXT:
\"\"\"
{chapter_lesson_text}
\"\"\"

Generate exactly {n_questions} distinct question/answer pairs following all
binding rules above.

Return ONLY a single valid JSON object (no markdown fences, no commentary
before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}"
  }},
  "qa_pairs": [
    {{
      "question": "...",
      "answer": "..."
    }}
  ]
}}

Before you output the JSON, re-read all {n_questions} answers you drafted and
check: no two answers open with the same sentence structure, no question
names the chapter/unit/lesson, no answer uses any of the banned stock
phrases from rule 4, and answers are not all the same length. Rewrite any
that fail this check.

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
              f"Nothing to ground Q&A pairs in yet — run the lesson pipeline for this "
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

    print(f"\n  Preparing GPT-5.5 DKB authoring prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {len(chapters)}")
    print(f"  Q&A pairs per chapter: {questions_per_chapter}\n")

    index_lines = [
        f"GPT-5.5 Doubt Knowledge Base Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each chapter below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <chapter_slug>_dkb.json in this folder.",
        "  4. Once all chapters are done, ingest them all in one command:",
        "",
        f"     cd backend",
        f"     python3 scripts/ingest_gpt55_doubt_kb_output.py --dir {output_dir} --dry-run",
        f"     python3 scripts/ingest_gpt55_doubt_kb_output.py --dir {output_dir}",
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
            n_questions=questions_per_chapter,
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
        index_lines.append(f"       expected output: {slug}_dkb.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 Doubt Knowledge Base authoring prompts, "
                     "grounded in authored lesson_cache content"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Science"')
    parser.add_argument(
        "--chapters", default=None,
        help="Comma-separated list of exact chapter strings to scope to "
             "(default: all authored chapters for this grade/subject)",
    )
    parser.add_argument(
        "--questions-per-chapter", type=int, default=30,
        help="Q&A pairs to generate per chapter (default: 30)",
    )
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_DKB_Prompts_{grade_slug}_{subject_slug}"

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
