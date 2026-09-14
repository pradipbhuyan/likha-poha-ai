#!/usr/bin/env python3
"""
Prepare GPT-5.5 Exemplar Research Practice-Question Authoring Prompts
=============================================================================
Companion to prepare_gpt55_exemplar_explanation_prompts.py, same rationale:
ExemplarResearchPage.jsx's "Generate Practice Questions" card action used to
make a live LLM call at click time (originally misrouted through the RAG
/api/doubt/answer endpoint, which silently failed for this use case; briefly
replaced with a direct ask_llm() call). The product decision is to serve
this from a pre-authored bank instead, like every other fixed-catalogue
content surface in this app (Lessons, Mock Tests, Lesson Plans, and this
page's own Explanation cards) — reusing the exact same PDF-grounding
machinery this module imports from the explanation script.

Prerequisite: the source PDFs must already be downloaded —
  scripts/download_ncert_exemplar.py            (Grade 8-10)
  scripts/download_ncert_exemplar_grade1112.py  (Grade 11-12)

Same 132-of-168 fixable-card scope as the explanation pipeline — see
docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §3 for the 36 permanently-unfixable
cards (Grade 11 Physics/Chemistry, Grade 12 Chemistry — NCERT never
published an Exemplar book for those sections).

Usage:
    cd backend
    python3 scripts/prepare_gpt55_exemplar_practice_prompts.py --grade "Grade 8" --subject Maths
    python3 scripts/prepare_gpt55_exemplar_practice_prompts.py --grade "Grade 8" --subject Maths --topics "Squares and Square Roots"
    python3 scripts/prepare_gpt55_exemplar_practice_prompts.py --all   # every fixable card, one folder per section
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_gpt55_exemplar_explanation_prompts import (  # noqa: E402
    _slugify,
    build_chapter_pdf_index,
    extract_text_from_pdf,
    parse_topic_cards,
)

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE {subject} exam-prep author writing NCERT Exemplar-level
MCQ practice questions for one specific topic card — Grade {grade_number}
{subject}, chapter "{chapter}", topic "{topic}". This is for "Exemplar
Research", a deep-study feature students use to master the harder,
HOTS-style (higher-order thinking skills) questions the Exemplar book is
known for. These 4 questions are the graded self-check a student attempts
after reading the topic's explanation — each must be genuinely tricky, not
a restated textbook definition.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every question must be grounded in EXEMPLAR_SOURCE_TEXT below
   — the actual NCERT Exemplar PDF text for this chapter. Base each question
   on a real problem, fact, or combination of facts that appears there. Do
   not invent numbers or scenarios unrelated to the source.
2. EXEMPLAR-LEVEL DIFFICULTY: each question must require multi-step
   reasoning, combine two or more sub-concepts, or use an unusual angle —
   not a one-line recall question. This is the entire point of Exemplar
   Research: standard-textbook-easy questions do not belong here.
3. FOUR DISTINCT QUESTIONS: cover different angles or sub-aspects of
   "{topic}" — do not write 4 variations of the same single idea.
4. PLAIN TEXT MATH ONLY: no LaTeX, no dollar signs, no math markup. Write
   all math in plain text (e.g. x^2, P(x), (x-2)(x-3), sqrt(x)).
5. OPTIONS: exactly 4 options per question, each prefixed "A) "/"B) "/
   "C) "/"D) ", plausible distractors (not obviously wrong), exactly one
   correct. "answer" must be the FULL correct option string, copied
   verbatim from "options" (e.g. "answer": "B) 42", matching options[1]
   exactly).
6. EXPLANATION REQUIRED: every question needs a complete explanation of at
   least 3 sentences showing the full step-by-step working to the answer —
   never blank, never a one-line "because it's correct."
7. NEVER REFERENCE VISUALS: no "as shown in the diagram/figure" — nothing
   will be shown to the student. Describe geometric/visual situations in
   words only.
8. NO MECHANICAL TEMPLATES: do not reuse the same sentence skeleton across
   the 4 questions or across other topics with only nouns swapped.
9. If EXEMPLAR_SOURCE_TEXT genuinely does not cover "{topic}" at all, say so
   in a single top-level "refusal" string field instead of fabricating
   questions — see the JSON shape below.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}
TOPIC (this card's specific focus): {topic}
STUDENT-FACING HINT (context only, do not just restate it): {hint}

EXEMPLAR_SOURCE_TEXT (the actual NCERT Exemplar PDF content for this chapter):
\"\"\"
{source_text}
\"\"\"

Return ONLY a single valid JSON object (no markdown fences, no commentary
before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}",
    "topic": "{topic}"
  }},
  "questions": [
    {{
      "q": "the question text",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "the full correct option string, copied verbatim from options",
      "explanation": "3+ sentence step-by-step working to the answer"
    }}
  ]
}}

"questions" must contain exactly 4 entries. If (and only if)
EXEMPLAR_SOURCE_TEXT does not cover "{topic}" in enough depth to write real
grounded questions, instead return
{{"manifest": {{...same as above...}}, "refusal": "brief reason the source doesn't cover this topic"}}
rather than fabricating content.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def run(grade: str, subject: str, only_topics: list[str] | None, output_dir: Path) -> None:
    all_cards = parse_topic_cards()
    pdf_index = build_chapter_pdf_index()

    cards = all_cards.get(grade, {}).get(subject, [])
    if not cards:
        print(f"ERROR: no TOPIC_CARDS found for {grade} / {subject}.")
        sys.exit(1)

    chapter_map = pdf_index.get((grade, subject), {})
    if not chapter_map:
        print(f"ERROR: no downloaded Exemplar PDFs found for {grade} / {subject}.")
        print("Either run the download script first, or this subject/grade was never published by NCERT as an Exemplar book.")
        sys.exit(1)

    if only_topics:
        wanted = {t.strip() for t in only_topics}
        cards = [c for c in cards if c["topic"] in wanted]
        if not cards:
            print("ERROR: none of the requested --topics matched a TOPIC_CARDS entry.")
            sys.exit(1)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 Exemplar practice-question prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Cards to process: {len(cards)}\n")

    index_lines = [
        f"GPT-5.5 Exemplar Research Practice-Question Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each card below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <topic_slug>_practice.json in this folder.",
        "  4. Once all cards are done, hand the folder back for ingestion via",
        "     scripts/ingest_gpt55_exemplar_practice_output.py --dir <folder>",
        "",
        "Cards:",
    ]

    written = 0
    skipped_no_pdf = []
    for i, card in enumerate(cards, start=1):
        chapter = card["chapter"]
        pdf_path = chapter_map.get(chapter)
        if not pdf_path:
            print(f"  [{i:02d}] {card['topic']} -- [skip] no PDF found for chapter {chapter!r}")
            skipped_no_pdf.append(card["topic"])
            continue

        source_text = extract_text_from_pdf(pdf_path)
        if len(source_text.strip()) < 300:
            print(f"  [{i:02d}] {card['topic']} -- [skip] extracted PDF text suspiciously short")
            continue

        grade_number = grade.split()[-1]
        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade,
            grade_number=grade_number,
            subject=subject,
            chapter=chapter,
            topic=card["topic"],
            hint=card.get("hint", ""),
            source_text=source_text,
        )

        slug = _slugify(card["topic"])
        prompt_path = output_dir / f"{i:02d}_{slug}_PROMPT.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        written += 1
        print(f"  [{i:02d}] {card['topic']}")
        print(f"       -> wrote {prompt_path.name} ({len(prompt_text):,} chars, grounded in {len(source_text):,} chars of PDF text)")
        index_lines.append(f"  [{i:02d}] {card['topic']}  (chapter: {chapter})")
        index_lines.append(f"       prompt: {prompt_path.name}")
        index_lines.append(f"       expected output: {slug}_practice.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    if skipped_no_pdf:
        print(f"\n  {len(skipped_no_pdf)} card(s) skipped — no source PDF available: {', '.join(skipped_no_pdf)}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


# ── All fixable sections, mirrors docs/EXEMPLAR_RESEARCH_CONTENT_STATUS.md §3 ──
ALL_FIXABLE_SECTIONS = [
    ("Grade 8", "Maths"), ("Grade 8", "Science"),
    ("Grade 9", "Maths"), ("Grade 9", "Science"),
    ("Grade 10", "Maths"), ("Grade 10", "Science"),
    ("Grade 11", "Maths"), ("Grade 11", "Biology"),
    ("Grade 12", "Maths"), ("Grade 12", "Physics"), ("Grade 12", "Biology"),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 Exemplar Research practice-question authoring prompts, "
                     "grounded in the full text of the actual downloaded NCERT Exemplar PDF"
    )
    parser.add_argument("--grade", help='e.g. "Grade 8"')
    parser.add_argument("--subject", help='e.g. "Maths"')
    parser.add_argument("--topics", nargs="+", metavar="TOPIC",
                         help="Restrict to specific topic card(s) by exact name")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--all", action="store_true",
                         help="Generate prompts for every fixable section (132 cards), one subfolder each")
    args = parser.parse_args()

    if args.all:
        base = Path.home() / "Downloads" / "GPT55_Exemplar_Practice_Prompts_ALL"
        for grade, subject in ALL_FIXABLE_SECTIONS:
            grade_slug = grade.replace(" ", "_")
            subject_slug = _slugify(subject)
            out = base / f"{grade_slug}_{subject_slug}"
            run(grade, subject, None, out)
        return

    if not args.grade or not args.subject:
        print("ERROR: provide --grade and --subject, or --all")
        sys.exit(1)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Exemplar_Practice_Prompts_{grade_slug}_{subject_slug}"

    run(args.grade, args.subject, args.topics, output_dir)


if __name__ == "__main__":
    main()
