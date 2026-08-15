#!/usr/bin/env python3
"""
Prepare GPT-5.5 Subjective Question-Bank Authoring Prompts
=============================================================================
See docs/GPT55_SUBJECTIVE_QUESTION_BANK_AUTHORING_PROMPT.md for the full
workflow. Sibling of prepare_gpt55_question_prompts.py (MCQ bank), adapted
for short/long-answer subjective questions.

Generates one prompt .txt file per chapter, grounded in the chapter's ALREADY
AUTHORED lesson_cache content. A chapter with no authored lesson_cache
content yet is skipped with a clear warning.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_subjective_question_prompts.py --grade "Grade 9" --subject "Social Science"
    python3 scripts/prepare_gpt55_subjective_question_prompts.py --grade "Grade 11" --subject Biology \\
        --chapters "Chapter 1: X,Chapter 3: Y" --questions-per-chapter 20
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

You are a senior CBSE {subject} question-setter creating an ORIGINAL
subjective (short/long-answer) test-paper question bank for Grade
{grade_number} students, for one specific chapter, for a CBSE AI tutoring
platform. You must act like a strict, curriculum-accurate question-setter
who never invents a fact not present in the lesson content below.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, and example referenced in a question
   or model answer MUST be grounded in CHAPTER_LESSON_TEXT provided below.
   Do not invent numbers, dates, names, or facts that do not appear there.
2. MARKS BANDS: Short-answer questions are worth 2-3 marks and expect a
   3-5 sentence answer. Long-answer questions are worth 4-5 marks and
   expect a detailed, multi-point answer (definitions, reasoning, examples,
   or comparison as appropriate to the topic).
3. COMPLETE MODEL ANSWERS: Each model_answer must be a complete, ready-to-use
   reference answer a teacher can hand out directly as an answer key — not
   bullet hints or a restatement of the question.
4. DIFFICULTY BANDS (same definitions as the MCQ question bank):
   - Easy: direct recall of a definition/fact stated plainly in the text.
   - Medium: requires connecting two ideas from the text, or applying a
     concept to a straightforward new situation.
   - Hard: requires multi-step reasoning, comparing/contrasting concepts, or
     a value-based/application question — still fully answerable using only
     CHAPTER_LESSON_TEXT.
5. NO REPETITION: Do not write two questions that test the exact same fact
   in different words. Spread coverage across the chapter's different
   sections/sub-topics as evenly as possible.
6. LANGUAGE LEVEL: Write for Grade {grade_number} level -- clear, exam-style
   CBSE phrasing.
7. NEVER TREAT MARKDOWN STRUCTURE AS CONTENT: CHAPTER_LESSON_TEXT below is
   internal lesson-authoring material and may contain markdown artifacts
   such as "## Step-by-step breakdown", "**Bold sub-labels**:", section
   titles like "Worked example" / "Quick check question" / "Exam-style
   problems" / "Revision and recap", or generic labels like "Section B" /
   "Opening overview" / "core explanation" / "revision activities". These
   are internal authoring scaffolding, NOT chapter content, and must NEVER
   appear as the subject of a question. Do NOT write template questions
   like "Explain the chapter point about <bold label> and connect it with
   another idea from <some other section name>" or "How is <bold label>
   explained in <section name>?" — these are meaningless to a student
   because <bold label> and <section name> are not real facts, characters,
   events, or concepts from the actual chapter/story/poem. Every question
   must be about a REAL, NAMEABLE fact: a character's action, a specific
   event, a definition, a rule, a number, an example — something a student
   could point to in the actual textbook chapter, not in this lesson-notes
   scaffolding. If you cannot find enough real content to write the
   requested number of distinct, well-grounded questions, write FEWER
   questions rather than templating around section/label names.
8. NO MECHANICAL SENTENCE TEMPLATES: Do not build every question from one
   or two reusable sentence skeletons with just the topic noun swapped in
   (e.g. "Explain <topic> and state its key features, mechanism or
   significance.", "Explain <topic A> and <topic B> in detail, showing the
   relationship between them.", "Explain <topic> and distinguish the linked
   ideas where relevant.", "Give a detailed account of <topic>, including
   the mechanism, evidence, examples or consequences stated in the
   chapter.", "Explain the major points relating to <topic>.", "What role
   does the treatment of <topic> play in the development of the scene?",
   "Why are the details associated with <topic> significant in this
   episode?", "Compare the treatment of <X> and <Y> in <chapter>. What
   larger idea emerges when they are read together?", "Examine the
   relationship between <X> and <Y>. Why is that relationship important to
   the meaning of <chapter>?", "What does the chapter reveal through the
   treatment of <topic>?", "How does the treatment of <topic> contribute to
   the text's meaning?", "What becomes clearer to the reader through the
   treatment of <topic>?" — the prose/poetry-flavored examples in this list
   apply to literature chapters specifically; the same rule holds regardless
   of subject.), or, matched on their TAIL rather than the opener since the
   openers alone are legitimate CBSE phrasing, "Give a brief account of
   <topic> using two specific details from the text." / "...including the
   relevant definition, pattern or example.", "What is the significance of
   <topic> in <chapter>? Support your answer with two facts.", "State two
   features, examples or implications associated with <topic>.", "What
   does the text state about <topic>? Give two relevant details." These
   exact phrases are banned outright — do not use them even once. A
   student answering 20 questions built from 2-3 repeated skeletons is doing rote
   glossary recall, not a genuine CBSE exam. Each
   question's STEM must vary and match how CBSE actually phrases questions
   for this content type: "Why does...", "How does X differ from Y?",
   "Give two reasons why...", "A student observed that <scenario> — explain
   this using the chapter's explanation of <concept>.", "Justify the
   statement that...", "Differentiate between X and Y with one example
   each.", "What would happen if...", "State any three...", "With the help
   of a suitable example, explain...". Reuse of "Explain" as a verb across
   several questions is fine (CBSE does this too) — what's forbidden is
   reusing the SAME surrounding sentence structure/scaffold repeatedly.
   IMPORTANT — inventing your OWN fixed list of stems and then applying that
   same list once per chapter is THE SAME VIOLATION, even if each individual
   stem looks fine and no single phrase repeats within one chapter: e.g.
   deciding on a personal formula of "one 'state two important points about
   X' question, one 'give the main defining features of X' question, one 'a
   student gives an incomplete account of X' question..." and then filling
   that same fixed set of slots for every chapter is still a rigid template,
   just disguised as variety. The right way to get variety is to let the
   chapter's actual content decide which question types make sense — a
   chapter full of processes calls for more "explain the steps of..."
   questions, a chapter full of comparisons calls for more "distinguish
   X from Y" questions — not to pre-decide a fixed roster of question types
   and mechanically fill it in for every chapter regardless of content.
   ALSO FORBIDDEN — reusing a fixed PHRASE as a generic keyword-insertion
   point across many differently-worded questions, e.g. writing "the
   treatment of <topic>" or "the writer's use of <topic>" over and over with
   only <topic> swapped, each time wrapped in a different surrounding
   sentence to look varied ("What effect is created through the treatment
   of <topic>?", "What does the treatment of <topic> reveal about...",
   "How does the writer's use of <topic> shape...", "What does the writer's
   use of <topic> contribute to..."). Varying the WRAPPER sentence while
   reusing the same insertion phrase as the actual analytical content is
   still templating — it just hides the repetition one level down. For
   literature/poetry chapters specifically: name the actual literary
   device, technique, character, event, or theme directly in each
   question's own words ("How does the imagery of the pigeons underline the
   loss of freedom?", not "What effect is created through the treatment of
   pigeons?") rather than filling a generic "the treatment of X" slot.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}

CHAPTER_LESSON_TEXT:
\"\"\"
{chapter_lesson_text}
\"\"\"

Generate exactly {n_short} short-answer (2-3 marks) and {n_long} long-answer
(4-5 marks) questions ({total} total), with a mix of Easy/Medium/Hard
difficulty across them.

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
      "marks": 3,
      "model_answer": "...",
      "expected_keywords": ["...", "...", "..."],
      "difficulty": "Medium"
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

    n_short = (questions_per_chapter * 3) // 5
    n_long = questions_per_chapter - n_short

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 subjective question-bank prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {len(chapters)}")
    print(f"  Questions per chapter: {questions_per_chapter} "
          f"({n_short} short-answer / {n_long} long-answer)\n")

    index_lines = [
        f"GPT-5.5 Subjective Question-Bank Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each chapter below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <chapter_slug>_subjective.json in this folder.",
        "  4. Once all chapters are done, ingest them all in one command:",
        "",
        f"     cd backend",
        f"     python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir {output_dir} --dry-run",
        f"     python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir {output_dir}",
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
            n_short=n_short,
            n_long=n_long,
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
        index_lines.append(f"       expected output: {slug}_subjective.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 subjective test-paper question-bank authoring prompts, "
                     "grounded in authored lesson_cache content"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Social Science"')
    parser.add_argument(
        "--chapters", default=None,
        help="Comma-separated list of exact chapter strings to scope to "
             "(default: all authored chapters for this grade/subject)",
    )
    parser.add_argument(
        "--questions-per-chapter", type=int, default=20,
        help="Total questions per chapter, split ~60/40 short/long-answer (default: 20)",
    )
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Subjective_Prompts_{grade_slug}_{subject_slug}"

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
