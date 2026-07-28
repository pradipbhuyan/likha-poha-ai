#!/usr/bin/env python3
"""
Prepare GPT-5.5 Chapter-Authoring Prompts for Grade 9 Advanced Maths & Science
================================================================================
See docs/GPT55_CHAPTER_AUTHORING_PROMPT.md for the base workflow. This
variant targets the two "Advanced / Optional" CBSE Grade 9 books, which
live as single combined PDFs (not one-PDF-per-chapter).

Unlike the standard prompt, this ALSO asks GPT-5.5 for a clearly
separated "supplementary_enrichment" section per chapter containing:
  1. Extra research material beyond the textbook PDF (real-world
     context, current applications, well-known extensions) -- clearly
     labelled and never mixed into the strictly-grounded 5 lesson steps.
  2. Suggested freely-licensed web images (Wikimedia Commons, NASA/ISRO
     public galleries, PhET simulation screenshots, etc.) as a
     search-description + suggested-source + alt-text list for a human
     to verify and source manually (GPT-5.5 cannot fetch live URLs).

Usage:
    cd backend
    python3 scripts/prepare_gpt55_prompts_advanced.py --subject Maths
    python3 scripts/prepare_gpt55_prompts_advanced.py --subject Science
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── PDF page-range extraction as a standalone PDF file ──────────────────
# In addition to raw text, we now also export a per-chapter PDF slice
# (using pypdf) so the user can attach BOTH the filled-in text prompt AND
# the actual chapter pages as a PDF when pasting into GPT-5.5 -- matching
# the original workflow (see docs/GPT55_CHAPTER_AUTHORING_PROMPT.md §1
# step 2-4) of pairing a prompt with the raw source PDF rather than
# relying on extracted text alone.
from pypdf import PdfReader, PdfWriter  # noqa: E402

GRADE = "Grade 9"

MATHS_PDF = Path.home() / "Downloads" / "grade9advancedMaths.pdf"
MATHS_SUBJECT = "Advanced Mathematics"
MATHS_CHAPTERS = [
    ("Advanced - Sets", 2, 20),
    ("Advanced - Logarithms", 21, 36),
    ("Advanced - Relations and Functions", 37, 53),
    ("Advanced - Coordinate Geometry", 54, 69),
    ("Advanced - Combinatorics", 70, 82),
    ("Advanced - Exploring some more Progressions", 83, 93),
]

SCIENCE_PDF = Path.home() / "Downloads" / "grade9advscience.pdf"
SCIENCE_SUBJECT = "Advanced Science"
SCIENCE_CHAPTERS = [
    ("Advanced - Measurement: Foundation of Science", 3, 8),
    ("Advanced - Understanding Motion through Experience", 9, 14),
    ("Advanced - Newton's Laws of Motion", 15, 24),
    ("Advanced - The Geometry of Power: Advanced Simple Machines", 25, 29),
    ("Advanced - Work and Energy", 30, 33),
    ("Advanced - Structure of Atom", 34, 41),
    ("Advanced - Chemical Bonding", 42, 48),
    ("Advanced - Mixtures and their Separation", 49, 53),
    ("Advanced - Microscope and Microscopy", 54, 68),
    ("Advanced - Engineering Life: Miracles in Biotechnology", 69, 85),
]

MATHS_GUIDANCE = (
    "SUBJECT-SPECIFIC GUIDANCE FOR ADVANCED MATHS: Worked examples MUST show "
    "COMPLETE, correct step-by-step algebraic/arithmetic/geometric working -- "
    "every intermediate step, not just the final answer -- exactly as a "
    "student would need to show it in a written answer. Prefer problems "
    "adapted from (or directly citing) the chapter's own worked Examples or "
    "Exercise numbers over invented numbers, but inventing a NEW numeric "
    "problem that tests the same concept using the same method as a textbook "
    "example IS acceptable for Maths, as long as the method/formula itself "
    "is correct and standard for this chapter (never invent a new theorem or "
    "formula that does not exist). In the Common Mistake section, flag a "
    "genuine, well-known student error for this specific topic."
)

SCIENCE_GUIDANCE = (
    "SUBJECT-SPECIFIC GUIDANCE FOR ADVANCED SCIENCE: Ground every explanation "
    "in a real activity, derivation, or observation from the chapter wherever "
    "one exists -- cite it explicitly (e.g. 'as shown in Activity 3.2'). "
    "Worked examples should walk through the SCIENTIFIC REASONING "
    "(observation -> principle -> prediction/explanation), not just formula "
    "substitution, even when a numeric formula is used. Flag and correct "
    "common conceptual misconceptions specific to this topic (e.g. confusing "
    "mass with weight, pseudo force with a real force, magnification with "
    "resolution) in the Common Mistake section wherever the chapter content "
    "invites that confusion."
)

SUBJECT_CONFIG = {
    "Maths": {
        "pdf_path": MATHS_PDF,
        "subject_name": MATHS_SUBJECT,
        "chapters": MATHS_CHAPTERS,
        "subject_class": "science_or_maths",
        "subject_guidance": MATHS_GUIDANCE,
    },
    "Science": {
        "pdf_path": SCIENCE_PDF,
        "subject_name": SCIENCE_SUBJECT,
        "chapters": SCIENCE_CHAPTERS,
        "subject_class": "science_or_maths",
        "subject_guidance": SCIENCE_GUIDANCE,
    },
}

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE curriculum expert and textbook author. You are
reviewing and rewriting ONE chapter of the CBSE "Advanced / Optional"
enrichment book for Grade 9 for an AI tutoring platform. You must act like
a strict, subject-matter-accurate teacher who never invents facts,
numbers, or examples that are not present in -- or a direct, standard
consequence of -- the provided source text.

{subject_guidance}

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, definition, formula, and worked-example number
   in the 5 main lesson steps MUST come from the CHAPTER_PDF_TEXT provided
   below, or from a well-known, standard external fact that any qualified
   subject teacher would consider textbook-level common knowledge (e.g.
   the speed of light, standard atomic masses, Avogadro's number).
2. NO FABRICATED NUMBERS: Every worked example and quick-check question in
   the 5 main lesson steps MUST cite/reuse actual Activities, Examples, or
   Exercise numbers from CHAPTER_PDF_TEXT wherever the chapter has any
   (e.g. "Activity 3.2" or "Example 7"). Never invent a numeric scenario
   that does not appear in or is not a direct standard extension of the
   source text.
3. CHAPTER BOUNDARY: Only include content that belongs to THIS chapter in
   the 5 main lesson steps. Do NOT include content that would more
   naturally belong to an adjacent or different chapter of this same book.
4. FULL COVERAGE, NO TUNNEL VISION: Your `must_include_keywords` list and
   your 5 lesson steps together MUST proportionally cover EVERY major
   section/sub-heading that appears in CHAPTER_PDF_TEXT.
5. NO PLACEHOLDER OR VAGUE TEXT: Every "Quick check question" must have a
   complete, correct, specific Answer and Explanation.
6. LANGUAGE LEVEL: Write for Grade 9 level -- simple, clear, age-appropriate
   English, but scientifically/factually precise. This is an ADVANCED /
   OPTIONAL enrichment chapter, so you may pitch slightly above the core
   NCERT Grade 9 syllabus, matching the depth of CHAPTER_PDF_TEXT itself.
7. SUPPLEMENTARY ENRICHMENT SECTION (separate from the 5 grounded lesson
   steps -- see the "supplementary_enrichment" object in the output shape
   below): because this is explicitly an "Advanced / Optional" enrichment
   chapter, ALSO produce a clearly separated research/enrichment section
   that MAY go beyond CHAPTER_PDF_TEXT itself, containing:
   (a) 3-6 short "beyond_the_textbook" notes: real-world context, current
       real applications, well-known extensions, or interesting historical/
       modern context related to this chapter's core concepts. Each note
       must be factually accurate and clearly written for a curious Grade 9
       student -- do not fabricate statistics or invent specific companies/
       products/events; keep claims general and verifiable
       (e.g. "Logarithmic scales similar to the Richter scale are also used
       to measure sound intensity in decibels" is fine; a specific invented
       statistic is not).
   (b) 4-8 "suggested_web_images": each one a {{"topic": "<short label>",
       "search_description": "<a specific, descriptive search phrase a
       teacher could type into Wikimedia Commons, NASA/ISRO image galleries,
       PhET Interactive Simulations, or a similar free/open-licence image
       source to find a genuinely relevant, freely-licensed image>",
       "suggested_source": "<e.g. 'Wikimedia Commons', 'PhET Interactive
       Simulations (University of Colorado Boulder)', 'NASA/ISRO public
       image gallery'>", "alt_text": "<a short, accurate alt-text
       description of what the image should show>"}}. You must NOT invent a
       specific URL or claim a specific image exists -- this is a sourcing
       suggestion list for a human to verify and fetch manually, always
       preferring well-known free/open-licence sources (Wikimedia Commons,
       NASA, ISRO, PhET, or similar public-domain/CC-licensed repositories).

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}
SUBJECT_CLASS: {subject_class}

CHAPTER_PDF_TEXT:
\"\"\"
{chapter_pdf_text}
\"\"\"

Your task has three parts. Return ONLY a single valid JSON object (no
markdown fences, no commentary before or after) with exactly this shape:

{{
  "manifest": {{
    "grade": "{grade}",
    "subject": "{subject}",
    "chapter": "{chapter}",
    "central_question": "<one sentence: what is the single unifying question this chapter answers?>",
    "in_scope_units": [
      "<one string per major section/sub-heading actually present in CHAPTER_PDF_TEXT, in the order they appear>"
    ],
    "banned_topics": [
      "<any topic that might mistakenly be included but belongs to a DIFFERENT chapter of this book -- empty array if none>"
    ],
    "must_include_keywords": [
      "<15-40 specific terms/names/concepts that MUST appear somewhere across the 5 lesson steps combined>"
    ],
    "known_pitfalls": [
      {{
        "claim": "<a specific, plausible mistake a non-expert AI or student might make about this chapter's content>",
        "correction": "<the precise correct statement, grounded in CHAPTER_PDF_TEXT>"
      }}
    ],
    "recommended_example_progression": [
      "<a short ordered list of worked-example ideas, each one explicitly citing which Activity/Example/Exercise number it is based on>"
    ],
    "ncert_end_of_chapter_exercises_reference": "<one sentence pointing to the actual end-of-chapter exercise/question section name found in CHAPTER_PDF_TEXT, if present>"
  }},
  "lessons": {{
    "Concept introduction": "<full markdown lesson content, see FORMAT below>",
    "Core explanation": "<full markdown lesson content, see FORMAT below>",
    "Worked examples": "<full markdown lesson content, see FORMAT below>",
    "Exam-style problems": "<full markdown lesson content, see FORMAT below>",
    "Revision and recap": "<full markdown lesson content, see FORMAT below>"
  }},
  "supplementary_enrichment": {{
    "beyond_the_textbook": [
      "<3-6 short, factually careful real-world context / application / extension notes -- see BINDING RULE 7(a)>"
    ],
    "suggested_web_images": [
      {{
        "topic": "<short label>",
        "search_description": "<specific search phrase for a free/open image source>",
        "suggested_source": "<e.g. Wikimedia Commons, PhET Interactive Simulations, NASA/ISRO public image gallery>",
        "alt_text": "<short accurate description of what the image should show>"
      }}
    ]
  }}
}}

FORMAT for each value inside "lessons" (a single markdown string, using
exactly these 7 headings in this order):

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
Question: <a question that cites a real Activity/Example/Exercise number>

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
much space each major section takes in the original text -- do NOT let any
single topic dominate more than 1-2 of the 5 steps. The
"supplementary_enrichment" object must remain clearly separate from the 5
lesson steps and must never be merged into them.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


# The source PDFs encode common mathematical symbols using a "Symbol" font
# whose custom glyph codes pdfplumber extracts as literal Private-Use-Area
# Unicode codepoints (U+F0xx) instead of the real Unicode symbol -- e.g.
# U+F0CE became a garbled glyph instead of "∈". This map translates the
# specific PUA codepoints observed in the two Advanced-book PDFs back to
# their correct Unicode symbols, so extracted text (and anything built
# from it, like citation popups) is human-readable instead of showing
# boxes/garbage characters.
_SYMBOL_FONT_MAP = {
    "\uf0ce": "\u2208",  # ∈  (element of)
    "\uf0cf": "\u2209",  # ∉  (not an element of)
    "\uf0a3": "\u2264",  # ≤  (less than or equal to)
    "\uf0b3": "\u2265",  # ≥  (greater than or equal to)
    "\uf0ab": "\u21d2",  # ⇒  (implies)
    "\uf0ac": "\u21d4",  # ⇔  (if and only if)
    "\uf0d8": "\u00d8",  # placeholder mapped to a visible glyph (rare)
    "\uf0ec": "\u2229",  # ∩  (intersection) — Symbol font "Ç" position
    "\uf0e9": "\u222a",  # ∪  (union) — Symbol font position
    "\uf066": "\u2205",  # ∅  (empty set) — Symbol font "f" position
    "\uf020": "",         # blank glyph — drop entirely (was rendering as a box)
    "\uf0b1": "\u00b1",  # ±
    "\uf0d7": "\u00d7",  # ×
    "\uf0b8": "\u00f7",  # ÷
    "\uf0a2": "\u2202",  # ∂
    "\uf0a5": "\u221e",  # ∞ (rare alt position)
    "\uf0ca": "\u2229",  # ∩ (alt position seen in some fonts)
    "\uf0c9": "\u222a",  # ∪ (alt position)
    "\uf0cb": "\u2282",  # ⊂ (subset)
    "\uf0cc": "\u2283",  # ⊃ (superset)
    "\uf0cd": "\u2286",  # ⊆ (subset or equal)
    "\uf0ce\uf020": "\u2208",  # defensive: element-of glyph directly followed by blank
}


def _fix_symbol_font_glyphs(text: str) -> str:
    """Replace known Symbol-font Private-Use-Area codepoints with their
    correct Unicode mathematical symbols; drop the ones that have no
    reliable mapping (better to omit than to show a garbled box glyph)."""
    for bad, good in _SYMBOL_FONT_MAP.items():
        text = text.replace(bad, good)
    # Catch-all: any remaining Private-Use-Area codepoint (U+F000-U+F8FF)
    # that we have not explicitly mapped is dropped rather than shown as
    # a garbled box character.
    text = re.sub(r"[\uf000-\uf8ff]", "", text)
    return text


def extract_text_pages(pdf_path: Path, start: int, end: int) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = []
        for i in range(start, min(end + 1, len(pdf.pages))):
            text = pdf.pages[i].extract_text() or ""
            text = re.sub(r"\bPage\s*\|\s*\d+\b", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = _fix_symbol_font_glyphs(text)
            pages.append(text.strip())
    return "\n\n".join(p for p in pages if p)


def extract_pdf_slice(pdf_path: Path, start: int, end: int, out_path: Path) -> None:
    """Write a standalone PDF containing only pages [start, end] (0-indexed,
    inclusive) of pdf_path to out_path, so the user can attach the ACTUAL
    chapter pages (not just extracted text) alongside the text prompt when
    pasting into GPT-5.5 -- matching the original two-artifact workflow
    (prompt text + source PDF) described in
    docs/GPT55_CHAPTER_AUTHORING_PROMPT.md."""
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    last_page = min(end, len(reader.pages) - 1)
    for i in range(start, last_page + 1):
        writer.add_page(reader.pages[i])
    with open(out_path, "wb") as f:
        writer.write(f)


def run(subject_key: str, output_dir: Path, limit: int | None) -> None:
    if subject_key not in SUBJECT_CONFIG:
        print(f"ERROR: unknown subject {subject_key!r}. Use 'Maths' or 'Science'.")
        sys.exit(1)

    cfg = SUBJECT_CONFIG[subject_key]
    pdf_path: Path = cfg["pdf_path"]
    subject_name: str = cfg["subject_name"]
    chapters = cfg["chapters"]
    subject_class = cfg["subject_class"]
    subject_guidance = cfg["subject_guidance"]

    if not pdf_path.exists():
        print(f"ERROR: source PDF not found: {pdf_path}")
        sys.exit(1)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    n = len(chapters)
    if limit:
        n = min(n, limit)

    print(f"\n  Preparing GPT-5.5 Advanced prompts for {GRADE} / {subject_name}")
    print(f"  Source PDF: {pdf_path}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {n}\n")

    for i in range(1, n + 1):
        chapter_name, start, end = chapters[i - 1]
        chapter_slug = _slugify(chapter_name)
        safe_prefix = f"{i:02d}_{chapter_slug}"

        print(f"  [{i:02d}] {chapter_name} (pages {start+1}-{end+1})")
        try:
            pdf_text = extract_text_pages(pdf_path, start, end)
        except Exception as e:
            print(f"       [error] could not extract text: {e}")
            continue

        if len(pdf_text.strip()) < 200:
            print(f"       [warn] extracted text is suspiciously short ({len(pdf_text)} chars)")

        prompt_text = PROMPT_TEMPLATE.format(
            grade=GRADE,
            subject=subject_name,
            chapter=chapter_name,
            subject_class=subject_class,
            chapter_pdf_text=pdf_text,
            subject_guidance=subject_guidance,
        )

        out_path = output_dir / f"{safe_prefix}_PROMPT.txt"
        out_path.write_text(prompt_text, encoding="utf-8")
        print(f"       -> wrote {out_path.name} ({len(prompt_text):,} chars)")

        pdf_out_path = output_dir / f"{safe_prefix}_source.pdf"
        try:
            extract_pdf_slice(pdf_path, start, end, pdf_out_path)
            print(f"       -> wrote {pdf_out_path.name} (chapter pages as standalone PDF)")
        except Exception as e:
            print(f"       [warn] could not extract PDF slice: {e}")

    print(f"\nDone. {n} chapter prompt(s) + source PDF slice(s) prepared in:\n  {output_dir}")
    print("For each chapter, paste the *_PROMPT.txt text into GPT-5.5 AND attach the")
    print("matching *_source.pdf file (the actual chapter pages) in the same message,")
    print("exactly as with the standard workflow -- text + PDF together.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GPT-5.5 prompts for Grade 9 Advanced Maths/Science")
    parser.add_argument("--subject", required=True, choices=["Maths", "Science"])
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path.home() / "Downloads" / f"GPT55_Adv_Prompts_{args.subject}"

    run(subject_key=args.subject, output_dir=output_dir, limit=args.limit)


if __name__ == "__main__":
    main()
