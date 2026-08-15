#!/usr/bin/env python3
"""
Prepare GPT-5.5 Exemplar Research Explanation Authoring Prompts
=============================================================================
Exemplar Research (frontend/src/pages/ExemplarResearchPage.jsx) currently
generates each card's explanation with a *live* LLM call at click time,
grounded (when grounding exists at all) in a handful of RAG-retrieved PDF
chunks and constrained to a terse 5-line template. This script replaces that
with the same pre-authored, human-in-the-loop pattern already used for
lessons and mock-test question banks: one detailed authoring prompt per
topic card, grounded in the FULL text of the actual downloaded NCERT
Exemplar PDF for that chapter (not a chunked/embedded subset), asking for a
comprehensive reference explanation rather than a quick chat answer.

Prerequisite: the source PDFs must already be downloaded —
  scripts/download_ncert_exemplar.py            (Grade 8-10)
  scripts/download_ncert_exemplar_grade1112.py  (Grade 11-12)

Only 5 of 9 NCERT Exemplar subject/grade combinations exist as published
PDFs for Grade 11-12 (Maths/Biology for Grade 11; Maths/Physics/Biology for
Grade 12) — Grade 11 Physics/Chemistry and Grade 12 Chemistry were never
published by NCERT at all (confirmed via live 404s), so no prompt can be
generated for cards in those sections regardless of method.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_exemplar_explanation_prompts.py --grade "Grade 8" --subject Maths
    python3 scripts/prepare_gpt55_exemplar_explanation_prompts.py --grade "Grade 8" --subject Maths --topics "Squares and Square Roots"
    python3 scripts/prepare_gpt55_exemplar_explanation_prompts.py --list-missing-sources   # report cards with no PDF at all
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pdfplumber  # noqa: E402

from download_ncert_exemplar import (  # noqa: E402
    EXEMPLAR_BOOKS,
    EXEMPLAR_UNIT_NAMES,
    EXEMPLAR_ROOT,
)
from download_ncert_exemplar_grade1112 import (  # noqa: E402
    EXEMPLAR_BOOKS_1112,
    OUTPUT_ROOT as EXEMPLAR_ROOT_1112,
    get_chapter_name,
)

FRONTEND_PAGE = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "pages" / "ExemplarResearchPage.jsx"
)

PROMPT_TEMPLATE = """\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are a senior CBSE {subject} exam-prep author writing a COMPREHENSIVE,
in-depth reference explanation for one specific topic from the NCERT
Exemplar Problems book — Grade {grade_number} {subject}, chapter
"{chapter}". This is for "Exemplar Research", a deep-study feature students
use to master the harder, HOTS-style questions the Exemplar book is known
for (distinct from the regular NCERT textbook). This is a reference
document a student will actually study from, NOT a quick chat answer —
write with real depth in every section.

BINDING RULES (do not violate any of these):

1. GROUNDING: Every fact, formula, and problem you reference MUST be
   grounded in EXEMPLAR_SOURCE_TEXT below — the actual NCERT Exemplar PDF
   text for this chapter. Do not invent numbers, problems, or facts that do
   not appear there.
2. WORKED EXAMPLES MUST BE REAL: Every worked example must be an ACTUAL
   problem from EXEMPLAR_SOURCE_TEXT (copy its numbers/setup faithfully),
   not one you invent. Pick 2-4 examples that best illustrate "{topic}"
   specifically, spanning different difficulty or sub-types if the source
   offers that variety. Show full step-by-step working, not just the answer.
3. REAL DEPTH: concept_overview should be 3-5 substantial sentences (or
   short paragraphs) — enough for a student encountering this for the first
   time to actually understand it, not a one-line dictionary definition.
   Do not pad with filler to reach length — every sentence should teach
   something real.
4. EXEMPLAR-SPECIFIC ANGLE: explicitly explain what makes Exemplar-level
   questions on "{topic}" harder or different from standard textbook
   questions on the same topic — that contrast is the entire point of this
   feature. Ground this in what you actually observe in EXEMPLAR_SOURCE_TEXT
   (question style, multi-step reasoning, unusual combinations of concepts,
   etc.), not a generic claim.
5. NO MECHANICAL SENTENCE TEMPLATES: Do not build content from a reusable
   sentence skeleton with just the topic name swapped in (e.g. never write
   something as generic as "X is an important concept with several key
   features" — every sentence must say something SPECIFIC to this exact
   topic's actual content). If you notice yourself reusing the same
   sentence shape you would use for any other topic, rewrite it to be
   concrete and specific to "{topic}".
6. NEVER REFERENCE VISUALS: No "as shown in the diagram/figure" — nothing
   will be shown to the student. Describe geometric/visual situations in
   words only.
7. If EXEMPLAR_SOURCE_TEXT genuinely does not cover "{topic}" in enough
   depth to fill a section honestly, say so briefly in that section rather
   than fabricating content to fill space.

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
  "concept_overview": "3-5 sentence/short-paragraph thorough explanation of the concept and why it matters",
  "key_rules_formulas": [
    {{"rule": "the formula or rule, precisely stated", "explanation": "what each term/part means and when to use it"}}
  ],
  "worked_examples": [
    {{"problem": "the actual Exemplar problem statement", "solution": "full step-by-step working", "answer": "final answer", "difficulty": "Medium or Hard"}}
  ],
  "what_makes_exemplar_questions_different": "specific, grounded explanation of how Exemplar-level questions on this topic differ from standard textbook questions",
  "common_mistakes": [
    {{"mistake": "the specific error students make", "why_it_happens": "the misconception behind it", "how_to_avoid": "the concrete fix"}}
  ],
  "problem_solving_strategy": "a clear step-by-step approach for tackling this topic's problem type",
  "quick_recall": "a concise, concrete exam-day summary or memory aid (not generic advice)",
  "practice_problem": {{"problem": "a different real Exemplar problem than the worked examples above", "answer": "the answer", "hint": "one hint, without giving the answer away"}}
}}

Include 3-6 entries in key_rules_formulas (skip if this topic has none — do
not force one), 2-4 in worked_examples, 3-5 in common_mistakes.

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text or "unnamed"


# ── Parse TOPIC_CARDS straight from the frontend source (single source of truth) ──

def parse_topic_cards() -> dict:
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    start = src.index("const TOPIC_CARDS = {")
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    body = src[i:end]

    results: dict[str, dict[str, list[dict]]] = {}
    for gm in re.finditer(r'"(Grade \d+)":\s*\{', body):
        g = gm.group(1)
        gstart = gm.end() - 1
        depth = 0
        for j in range(gstart, len(body)):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    gend = j + 1
                    break
        gbody = body[gstart:gend]
        results[g] = {}
        for sm in re.finditer(r'\n\s*(\w+):\s*\[', gbody):
            s = sm.group(1)
            sstart = sm.end() - 1
            depth2 = 0
            for j2 in range(sstart, len(gbody)):
                if gbody[j2] == "[":
                    depth2 += 1
                elif gbody[j2] == "]":
                    depth2 -= 1
                    if depth2 == 0:
                        send = j2 + 1
                        break
            sbody = gbody[sstart:send]
            cards = re.findall(
                r'\{\s*topic:\s*"((?:[^"\\]|\\.)*)",\s*chapter:\s*"((?:[^"\\]|\\.)*)",\s*'
                r'difficulty:\s*"(\w+)".*?hint:\s*"((?:[^"\\]|\\.)*)"',
                sbody,
            )
            results[g][s] = [
                {"topic": t, "chapter": c, "difficulty": d, "hint": h}
                for t, c, d, h in cards
            ]
    return results


# ── PDF path resolution: chapter name -> Path, per grade/subject ──────────────

def build_chapter_pdf_index() -> dict:
    """Return {(grade, subject): {chapter_name: pdf_path}}."""
    index: dict[tuple[str, str], dict[str, Path]] = {}

    # Grade 8-10
    for (grade_label, folder_name, subject, _subj_folder, base_code, start, end) in EXEMPLAR_BOOKS:
        book_dir = EXEMPLAR_ROOT / folder_name / subject
        chapter_map = {}
        for unit_num in range(start, end + 1):
            filename = f"{base_code}{unit_num:02d}"
            unit_name = EXEMPLAR_UNIT_NAMES.get(filename)
            if not unit_name:
                continue
            pdf_path = book_dir / f"{filename}.pdf"
            if pdf_path.exists():
                chapter_map[unit_name] = pdf_path
        index[(grade_label, subject)] = chapter_map

    # Grade 11-12
    for (grade_label, folder_name, _class_roman, _subj_url, subject_folder, code_prefix, max_chapters) in EXEMPLAR_BOOKS_1112:
        book_dir = EXEMPLAR_ROOT_1112 / folder_name / subject_folder
        chapter_map = {}
        for n in range(1, max_chapters + 1):
            chapter_name = get_chapter_name(code_prefix, n)
            pdf_path = book_dir / f"{code_prefix}{n:02d}.pdf"
            if pdf_path.exists():
                chapter_map[chapter_name] = pdf_path
        # subject_folder here is "Maths"/"Physics"/"Biology" already
        index[(grade_label, subject_folder)] = chapter_map

    return index


_REPEATED_LETTER_ARTIFACT = re.compile(r"([A-Za-z])\1{2,}")


def _fix_bold_text_artifact(text: str) -> str:
    """
    Some NCERT Exemplar PDFs render bold words as overlapping stacked glyphs
    (a "fake bold" trick), which pdfplumber extracts as each letter repeated
    ~5x in a row (e.g. "perfect" -> "pppppeeeeerrrrrfffffeeeeecccccttttt").
    Collapsing any 3+ run of the SAME letter to one instance fixes this
    cleanly — confirmed safe against numbers (digits are excluded from the
    character class, so "1000" is untouched) and no legitimate English word
    has a letter repeated 3+ times in a row.
    """
    return _REPEATED_LETTER_ARTIFACT.sub(r"\1", text)


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                text = re.sub(r"\bNCERT\b.*?\n", "", text)
                text = re.sub(r"\n{3,}", "\n\n", text)
                text = _fix_bold_text_artifact(text)
                pages.append(text.strip())
        return "\n\n".join(p for p in pages if p)
    except Exception as e:
        print(f"    [error] Could not extract {pdf_path.name}: {e}")
        return ""


def to_rag_subject_for_pdf_lookup(grade: str, subject: str) -> str:
    """TOPIC_CARDS uses 'Maths' for Grade 11/12 too; the 1112 PDF index keys by subject_folder ('Maths')."""
    return subject


def report_missing_sources(all_cards: dict, pdf_index: dict) -> None:
    print("\n  Cards with NO source PDF at all (cannot be authored by any method):\n")
    total_missing = 0
    for grade, subs in all_cards.items():
        for subject, clist in subs.items():
            chapter_map = pdf_index.get((grade, subject), {})
            missing = [c for c in clist if c["chapter"] not in chapter_map]
            if missing:
                print(f"  {grade} / {subject}: {len(missing)}/{len(clist)} cards — NO PDF EXISTS FOR THIS SECTION AT ALL")
                total_missing += len(missing)
    print(f"\n  Total: {total_missing} cards with no possible source grounding.\n")


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

    print(f"\n  Preparing GPT-5.5 Exemplar explanation prompts for {grade} / {subject}")
    print(f"  Output folder: {output_dir}")
    print(f"  Cards to process: {len(cards)}\n")

    index_lines = [
        f"GPT-5.5 Exemplar Research Explanation Authoring — {grade} / {subject}",
        "=" * 70,
        "",
        "For each card below:",
        "  1. Open the *_PROMPT.txt file and copy its full contents.",
        "  2. Paste into a fresh GPT-5.5 chat session.",
        "  3. Save the JSON response as <topic_slug>_explanation.json in this folder.",
        "  4. Once all cards are done, zip the folder and hand it back for ingestion.",
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
        index_lines.append(f"       expected output: {slug}_explanation.json")

    index_path = output_dir / "00_README_and_index.txt"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"\nDone. {written} prompt(s) prepared in:\n  {output_dir}")
    if skipped_no_pdf:
        print(f"\n  {len(skipped_no_pdf)} card(s) skipped — no source PDF available: {', '.join(skipped_no_pdf)}")
    print(f"See {index_path.name} for the full workflow and file list.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 Exemplar Research explanation authoring prompts, "
                     "grounded in the full text of the actual downloaded NCERT Exemplar PDF"
    )
    parser.add_argument("--grade", help='e.g. "Grade 8"')
    parser.add_argument("--subject", help='e.g. "Maths"')
    parser.add_argument("--topics", nargs="+", metavar="TOPIC",
                         help="Restrict to specific topic card(s) by exact name")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--list-missing-sources", action="store_true",
                         help="Report every card with no source PDF at all, across all grades/subjects, then exit")
    args = parser.parse_args()

    if args.list_missing_sources:
        all_cards = parse_topic_cards()
        pdf_index = build_chapter_pdf_index()
        report_missing_sources(all_cards, pdf_index)
        return

    if not args.grade or not args.subject:
        print("ERROR: provide --grade and --subject, or --list-missing-sources")
        sys.exit(1)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        grade_slug = args.grade.replace(" ", "_")
        subject_slug = _slugify(args.subject)
        output_dir = Path.home() / "Downloads" / f"GPT55_Exemplar_Explanation_Prompts_{grade_slug}_{subject_slug}"

    run(args.grade, args.subject, args.topics, output_dir)


if __name__ == "__main__":
    main()
