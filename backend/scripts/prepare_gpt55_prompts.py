#!/usr/bin/env python3
"""
Prepare GPT-5.5 Chapter-Authoring Prompts + Source PDFs (local bundle)
=========================================================================
See docs/GPT55_CHAPTER_AUTHORING_PROMPT.md for the full prompt design and
workflow this script prepares the inputs for.

For a given grade/subject, this script:
  1. Extracts the full text of each chapter's source NCERT PDF.
  2. Fills in the GPT-5.5 chapter-authoring prompt template with that text.
  3. Writes one ready-to-paste .txt prompt file per chapter, AND copies the
     original source PDF alongside it, into a single local output folder
     (default: ~/Downloads/GPT55_Prompts_<Grade>_<Subject>/).

Nothing here calls any LLM — this only prepares the exact inputs the user
will manually paste into a GPT-5.5 chat session (per Condition 3/4: no
free-tier LLM, and the actual generation step stays a manual, human-
initiated action).

Usage:
    cd backend
    python3 scripts/prepare_gpt55_prompts.py --grade "Grade 9" --subject Science
    python3 scripts/prepare_gpt55_prompts.py --grade "Grade 9" --subject Science --output-dir ~/Desktop/GPT55_Prompts
"""

from __future__ import annotations

import argparse
import re
import sys
import shutil
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── Book code -> (subject, PDF folder) map for locally available RAG DB PDFs ──
# Grade 9 Science lives in "RAG DB/Science/" with book code "iesc1",
# chapters iesc101.pdf .. iesc113.pdf (13 chapters), matching CBSE_9["Science"]
# order in backend/app/data/syllabus.py exactly.
BOOK_SOURCES = {
    ("Grade 9", "Science"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Science",
        "book_code": "iesc1",
        "num_chapters": 13,
        "subject_class": "science_or_maths",
    },
    # Grade 9 Maths lives in "RAG DB/Maths/" with book code "iemh1",
    # chapters iemh101.pdf .. iemh108.pdf (8 chapters), matching CBSE_9["Maths"]
    # order in backend/app/data/syllabus.py exactly.
    ("Grade 9", "Maths"): {
        "pdf_dir": REPO_ROOT / "RAG DB" / "Maths",
        "book_code": "iemh1",
        "num_chapters": 8,
        "subject_class": "science_or_maths",
    },
}

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE curriculum expert and textbook author. You are
reviewing and rewriting ONE chapter of an NCERT textbook for an AI
tutoring platform. You must act like a strict, subject-matter-accurate
teacher who never invents facts, numbers, or examples that are not
present in — or a direct, standard consequence of — the provided source
text.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and worked-example number
   you use MUST come from the CHAPTER_PDF_TEXT provided below, or (only if
   SUBJECT_CLASS = "science_or_maths") from a well-known, standard external
   fact that any qualified subject teacher would consider textbook-level
   common knowledge (e.g. the speed of light, standard atomic masses). If
   SUBJECT_CLASS = "humanities_or_language", you may use ONLY facts present
   in CHAPTER_PDF_TEXT — no external knowledge, no paraphrasing that
   changes meaning, no invented examples.
2. NO FABRICATED NUMBERS: Every worked example and quick-check question
   MUST cite/reuse actual activities, experiments, or end-of-chapter
   exercise numbers from CHAPTER_PDF_TEXT wherever the chapter has any
   (e.g. "NCERT Activity 2.2" or "NCERT Q7"). Never invent a numeric
   scenario (e.g. a fictional cell's exact diameter/timing) that does not
   appear in the source text.
3. CHAPTER BOUNDARY: Only include content that belongs to THIS chapter.
   Do NOT include content that would more naturally belong to an adjacent
   or different chapter (e.g. don't teach periodic table classification
   inside a "Structure of Atom" chapter). If you are not fully certain a
   topic is genuinely part of this chapter, leave it out.
4. FULL COVERAGE, NO TUNNEL VISION: Your `must_include_keywords` list and
   your 5 lesson steps together MUST proportionally cover EVERY major
   section/sub-heading that appears in CHAPTER_PDF_TEXT — do not let one
   topic (e.g. one type of numerical calculation) dominate 3+ of the 5
   steps while other major sections of the source text get little or no
   coverage.
5. NO PLACEHOLDER OR VAGUE TEXT: Every "quick_check" question must have a
   complete, correct, specific Answer and Explanation — never leave a
   question unanswered.
6. LANGUAGE LEVEL: Write for the given GRADE level — simple, clear,
   age-appropriate English, but scientifically/factually precise.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}
SUBJECT_CLASS: {subject_class}   (one of: "science_or_maths" | "humanities_or_language")

CHAPTER_PDF_TEXT:
\"\"\"
{chapter_pdf_text}
\"\"\"

Your task has two parts. Return ONLY a single valid JSON object (no
markdown fences, no commentary before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}",
    "central_question": "<one sentence: what is the single unifying question this chapter answers?>",
    "in_scope_units": [
      "<one string per major section/sub-heading actually present in CHAPTER_PDF_TEXT, in the order they appear, each describing what that section covers>"
    ],
    "banned_topics": [
      "<any topic that a lesson on this chapter might mistakenly include but that actually belongs to a DIFFERENT chapter — infer this from context; if you cannot identify any with confidence, return an empty array>"
    ],
    "must_include_keywords": [
      "<15-40 specific terms/names/concepts that MUST appear somewhere across the 5 lesson steps combined, drawn from ALL major sections of CHAPTER_PDF_TEXT, not just one>"
    ],
    "known_pitfalls": [
      {{
        "claim": "<a specific, plausible mistake a non-expert AI or student might make about this chapter's content>",
        "correction": "<the precise correct statement, grounded in CHAPTER_PDF_TEXT>"
      }}
    ],
    "recommended_example_progression": [
      "<a short ordered list of worked-example ideas, each one explicitly citing which NCERT activity/exercise/example it is based on>"
    ],
    "ncert_end_of_chapter_exercises_reference": "<one sentence pointing to the actual end-of-chapter exercise section name/number range found in CHAPTER_PDF_TEXT, if present>"
  }},
  "lessons": {{
    "Concept introduction": "<full markdown lesson content, see FORMAT below>",
    "Core explanation": "<full markdown lesson content, see FORMAT below>",
    "Worked examples": "<full markdown lesson content, see FORMAT below>",
    "Exam-style problems": "<full markdown lesson content, see FORMAT below>",
    "Revision and recap": "<full markdown lesson content, see FORMAT below>"
  }}
}}

FORMAT for each value inside "lessons" (this must be a single markdown
string, using exactly these 7 headings in this order):

# <Step Title>: <Chapter Name>

## What you will learn
<2-4 sentences>

## Simple explanation
<a short, plain-language paragraph introducing the core idea(s) for this step>

## Step-by-step breakdown
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
- **<sub-topic>**: <explanation, grounded in CHAPTER_PDF_TEXT>
  (as many bullet points as needed to cover this step's share of the chapter)

## Worked example
Question: <a question that cites a real NCERT activity/example/exercise number>

Solution:
- Step 1: ...
- Step 2: ...
- Final answer: ...

## Common mistake
<one specific, plausible misconception and its correction>

## Quick check question
Question: <a specific question>
Answer: <the correct, complete answer>
Explanation: <why this is correct>

## Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>
(3-6 bullets recapping this step's key points)

IMPORTANT: split the chapter content across the 5 steps so that, combined,
they cover the WHOLE of CHAPTER_PDF_TEXT roughly proportionally to how
much space each major section takes in the original text — do NOT let any
single topic dominate more than 1-2 of the 5 steps.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract full text from a PDF using pdfplumber."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)


def get_chapter_list(grade: str, subject: str) -> list[str]:
    """Load the ordered chapter list for a grade/subject from syllabus.py."""
    from app.data.syllabus import SYLLABUS  # noqa: PLC0415
    try:
        subjects = SYLLABUS[grade]["CBSE"]
        return list(subjects[subject])
    except KeyError as e:
        raise ValueError(f"Could not find chapter list for {grade}/{subject} in syllabus.py: {e}")


def run(grade: str, subject: str, output_dir: Path, limit: int | None) -> None:
    key = (grade, subject)
    if key not in BOOK_SOURCES:
        print(f"ERROR: no BOOK_SOURCES entry configured for {grade}/{subject}.")
        print(f"       Configured combinations: {list(BOOK_SOURCES.keys())}")
        sys.exit(1)

    source_cfg = BOOK_SOURCES[key]
    pdf_dir = source_cfg["pdf_dir"]
    book_code = source_cfg["book_code"]
    num_chapters = source_cfg["num_chapters"]
    subject_class = source_cfg["subject_class"]

    if not pdf_dir.exists():
        print(f"ERROR: PDF source directory not found: {pdf_dir}")
        sys.exit(1)

    chapters = get_chapter_list(grade, subject)
    if len(chapters) != num_chapters:
        print(f"  [warn] syllabus.py lists {len(chapters)} chapters for {grade}/{subject}, "
              f"but {num_chapters} PDF files are configured. Proceeding with min() of the two.")
    n = min(len(chapters), num_chapters)
    if limit:
        n = min(n, limit)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 prompts for {grade} / {subject}")
    print(f"  Source PDFs: {pdf_dir}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {n}\n")

    manifest_lines = [f"GPT-5.5 Prompt Bundle — {grade} / {subject}", ""]

    for i in range(1, n + 1):
        chapter_name = chapters[i - 1]
        pdf_filename = f"{book_code}{i:02d}.pdf"
        pdf_path = pdf_dir / pdf_filename

        chapter_slug = _slugify(chapter_name)
        safe_prefix = f"{i:02d}_{chapter_slug}"

        print(f"  [{i:02d}] {chapter_name}")
        if not pdf_path.exists():
            print(f"       [skip] source PDF not found: {pdf_path}")
            continue

        try:
            pdf_text = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"       [error] could not extract text from {pdf_path.name}: {e}")
            continue

        if len(pdf_text.strip()) < 200:
            print(f"       [warn] extracted text is suspiciously short ({len(pdf_text)} chars) — check the PDF")

        prompt_text = PROMPT_TEMPLATE.format(
            grade=grade,
            subject=subject,
            chapter=chapter_name,
            subject_class=subject_class,
            chapter_pdf_text=pdf_text,
        )

        prompt_out_path = output_dir / f"{safe_prefix}_PROMPT.txt"
        pdf_out_path = output_dir / f"{safe_prefix}_source.pdf"

        prompt_out_path.write_text(prompt_text, encoding="utf-8")
        shutil.copy2(pdf_path, pdf_out_path)

        print(f"       -> wrote {prompt_out_path.name} ({len(prompt_text):,} chars)")
        print(f"       -> copied {pdf_out_path.name}")

        manifest_lines.append(f"{i:02d}. {chapter_name}")
        manifest_lines.append(f"    prompt: {prompt_out_path.name}")
        manifest_lines.append(f"    source pdf: {pdf_out_path.name}")
        manifest_lines.append(f"    gpt output should be saved as: {chapter_slug}_gpt_output.json")
        manifest_lines.append("")

    manifest_lines.append("-" * 70)
    manifest_lines.append("Next steps for each chapter:")
    manifest_lines.append("  1. Open the *_PROMPT.txt file, copy its full contents.")
    manifest_lines.append("  2. Paste into a GPT-5.5 chat session.")
    manifest_lines.append("  3. Save GPT-5.5's JSON response as <chapter_slug>_gpt_output.json")
    manifest_lines.append("     inside backend/gpt_output/.")
    manifest_lines.append("  4. Run:")
    manifest_lines.append("       cd backend")
    manifest_lines.append("       python3 scripts/ingest_gpt55_chapter_output.py \\")
    manifest_lines.append("           --input gpt_output/<chapter_slug>_gpt_output.json --force")
    manifest_lines.append("     This writes the manifest, seeds all 5 lesson steps into lesson_cache,")
    manifest_lines.append("     and automatically re-runs the Tier A audit for that chapter.")
    manifest_lines.append("")

    manifest_path = output_dir / "00_README_and_index.txt"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"\n  Wrote index/instructions: {manifest_path}")
    print(f"\nDone. {n} chapter prompt(s) + source PDF(s) prepared in:\n  {output_dir}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 chapter-authoring prompts + source PDFs into a local folder"
    )
    parser.add_argument("--grade", required=True, help='e.g. "Grade 9"')
    parser.add_argument("--subject", required=True, help='e.g. "Science"')
    parser.add_argument(
        "--output-dir", default=None,
        help="Output folder (default: ~/Downloads/GPT55_Prompts_<Grade>_<Subject>)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N chapters")
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = _slugify(args.grade)
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Prompts_{grade_slug}_{subject_slug}"

    run(grade=args.grade, subject=args.subject, output_dir=output_dir, limit=args.limit)


if __name__ == "__main__":
    main()
