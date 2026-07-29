#!/usr/bin/env python3
"""
Prepare GPT-5.5 Prompts for Grade 10 English / Hindi / Social Science
=========================================================================
Reuses the exact prompt template, subject-specific guidance, and heading
sets from prepare_gpt55_prompts.py, but accepts an explicit PDF source
directory + book code + chapter-name list per invocation instead of a
fixed BOOK_SOURCES lookup. This is needed because Grade 10 Social Science
alone is made of FOUR separate NCERT books (Geography, History, Political
Science, Economics), each with its own PDF folder and book code — the
original script's one-book-per-subject BOOK_SOURCES dict can't express
that, so this script is driven by an explicit --book config instead.

Source PDFs for this run are NOT in "RAG DB/" (they were provided
directly in ~/Downloads/<FolderName>/ by the user), but are otherwise
identical NCERT chapter PDFs with the standard "<book_code><NN>.pdf"
naming convention.

Usage:
    cd backend
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book first_flight
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book footprints
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book kshitiz
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book geography
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book history
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book political_science
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book economics
    python3 scripts/prepare_gpt55_prompts_grade10_electives.py --book all   # does all 7 in one run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_gpt55_prompts import (  # noqa: E402
    PROMPT_TEMPLATE,
    HEADING_SETS,
    _get_subject_guidance,
    _slugify,
    extract_pdf_text,
)
import shutil  # noqa: E402

DOWNLOADS = Path.home() / "Downloads"

# Exact chapter names confirmed directly from live rag_documents rows
# (Grade 10 / English / Hindi / Social Science) so the GPT-5.5 manifest's
# "chapter" field will exactly match what students' dropdown expects —
# same "always check rag_documents.chapter, not assumptions" rule
# documented from earlier ingestion sessions.
BOOKS: dict[str, dict] = {
    "first_flight": {
        "grade": "Grade 10",
        "subject": "English",
        "pdf_dir": DOWNLOADS / "English-Class10",
        "book_code": "jeff1",
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: A Letter to God",
            "Chapter 2: Nelson Mandela: Long Walk to Freedom",
            "Chapter 3: Two Stories about Flying",
            "Chapter 4: From the Diary of Anne Frank",
            "Chapter 5: Glimpses of India",
            "Chapter 6: Mijbil the Otter",
            "Chapter 7: Madam Rides the Bus",
            "Chapter 8: The Sermon at Benares",
            "Chapter 9: The Proposal",
        ],
    },
    "footprints": {
        "grade": "Grade 10",
        "subject": "English",
        "pdf_dir": DOWNLOADS / "EnglishSuppl-Class10",
        "book_code": "jefp1",
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: A Triumph of Surgery",
            "Chapter 2: The Thief's Story",
            "Chapter 3: The Midnight Visitor",
            "Chapter 4: A Question of Trust",
            "Chapter 5: Footprints without Feet",
            "Chapter 6: The Making of a Scientist",
            "Chapter 7: The Necklace",
            "Chapter 8: Bholi",
            "Chapter 9: The Book That Saved the Earth",
        ],
    },
    "kshitiz": {
        "grade": "Grade 10",
        "subject": "Hindi",
        "pdf_dir": DOWNLOADS / "Hindi-Class10",
        "book_code": "jhks1",
        "subject_class": "humanities_or_language",
        "content_language": "hi",
        "chapters": [
            "अध्याय 1: सूरदास",
            "अध्याय 2: तुलसीदास",
            "अध्याय 3: जयशंकर प्रसाद",
            "अध्याय 4: सूर्यकांत त्रिपाठी 'निराला'",
            "अध्याय 5: नागार्जुन",
            "अध्याय 6: मंगलेश डबराल",
            "अध्याय 7: स्वयं प्रकाश",
            "अध्याय 8: रामवृक्ष बेनीपुरी",
            "अध्याय 9: यशपाल",
            "अध्याय 10: मन्नू भंडारी",
            "अध्याय 11: यतींद्र मिश्र",
            "अध्याय 12: भदंत आनंद कौसल्यायन",
        ],
    },
    "geography": {
        "grade": "Grade 10",
        "subject": "Social Science",
        "pdf_dir": DOWNLOADS / "Social-ContemproryIndia-Class10",
        "book_code": "jess1",
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: Resources and Development",
            "Chapter 2: Forest and Wildlife Resources",
            "Chapter 3: Water Resources",
            "Chapter 4: Agriculture",
            "Chapter 5: Minerals and Energy Resources",
            "Chapter 6: Manufacturing Industries",
            "Chapter 7: Lifelines of National Economy",
        ],
    },
    "history": {
        "grade": "Grade 10",
        "subject": "Social Science",
        "pdf_dir": DOWNLOADS / "History-Class10",
        "book_code": "jess3",
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: The Rise of Nationalism in Europe",
            "Chapter 2: Nationalism in India",
            "Chapter 3: The Making of a Global World",
            "Chapter 4: The Age of Industrialisation",
            "Chapter 5: Print Culture and the Modern World",
        ],
    },
    "political_science": {
        "grade": "Grade 10",
        "subject": "Social Science",
        "pdf_dir": DOWNLOADS / "PoliticalSc-Class10",
        "book_code": "jess4",
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: Power-sharing",
            "Chapter 2: Federalism",
            "Chapter 3: Gender, Religion and Caste",
            "Chapter 4: Political Parties",
            "Chapter 5: Outcomes of Democracy",
        ],
    },
    "economics": {
        "grade": "Grade 10",
        "subject": "Social Science",
        "pdf_dir": DOWNLOADS / "Social-Class10",
        "book_code": "jess2",
        # Economics may use real data/tables/numbers directly from the
        # source text (see SUBJECT_GUIDANCE["Social Science"] in
        # prepare_gpt55_prompts.py), but is still grounded strictly in
        # CHAPTER_PDF_TEXT — humanities_or_language is still the correct
        # class here, NOT science_or_maths, because external economic
        # facts/data must NOT be imported from outside the NCERT text.
        "subject_class": "humanities_or_language",
        "chapters": [
            "Chapter 1: Development",
            "Chapter 2: Sectors of the Indian Economy",
            "Chapter 3: Money and Credit",
            "Chapter 4: Globalisation and the Indian Economy",
            "Chapter 5: Consumer Rights",
        ],
    },
}


def run_book(book_key: str, output_root: Path, limit: int | None) -> None:
    if book_key not in BOOKS:
        print(f"ERROR: unknown --book '{book_key}'. Valid options: {list(BOOKS.keys())} or 'all'")
        sys.exit(1)

    cfg = BOOKS[book_key]
    grade = cfg["grade"]
    subject = cfg["subject"]
    pdf_dir = cfg["pdf_dir"]
    book_code = cfg["book_code"]
    subject_class = cfg["subject_class"]
    chapters = cfg["chapters"]
    content_language = cfg.get("content_language", "en")
    headings = HEADING_SETS.get(content_language, HEADING_SETS["en"])

    if content_language == "hi":
        content_language_name = "Hindi (हिंदी)"
        content_language_note = (
            "Every heading, sentence, question, answer, and explanation in "
            "the lesson body must be written in Hindi (Devanagari script), "
            "matching the language of CHAPTER_PDF_TEXT — do not write any "
            "part of the lesson body in English."
        )
    else:
        content_language_name = "English"
        content_language_note = ""

    # Same humanities/language worked-example format as the main script:
    # no invented arithmetic, evidence-based reasoning only.
    worked_example_format_note = (
        "Question: <a genuine interpretive/analytical question — ideally "
        "citing a real NCERT exercise number — about the text's meaning, "
        "a character's motivation, a literary device, a grammar rule, or "
        "a historical/social concept from CHAPTER_PDF_TEXT>\n\n"
        "IF this question cites a specific numbered/labelled extract, "
        "exercise, or activity from CHAPTER_PDF_TEXT (e.g. 'NCERT "
        "Critical Reflection I.2(iv)', 'NCERT Q7', 'Exercise 3.2'), you "
        "MUST immediately follow the Question line with a fenced "
        "```extract-ref``` JSON block containing the ACTUAL verbatim "
        "text of that extract/exercise/activity copied from "
        "CHAPTER_PDF_TEXT, in exactly this shape:\n"
        "```extract-ref\n"
        '{"citation": "<the exact citation, e.g. NCERT Critical '
        'Reflection I.2(iv)>", "extract_text": "<the full verbatim '
        "text of that numbered extract/exercise/activity, copied "
        'exactly from CHAPTER_PDF_TEXT — never summarized or '
        'invented>", "note": "<optional: one short line of context, '
        'e.g. the chapter/section this extract is from>"}\n'
        "```\n"
        "This is MANDATORY whenever you cite a specific numbered "
        "source reference — a bare citation with nothing for the "
        "student to refer back to is not acceptable. If the citation "
        "is a general reference to the whole chapter/story (not a "
        "specific numbered extract), the extract-ref block is not "
        "needed.\n\n"
        "Solution:\n"
        "- Step 1: <identify the relevant textual evidence — a direct "
        "quote or specific reference from CHAPTER_PDF_TEXT>\n"
        "- Step 2: <interpret what that evidence means/shows>\n"
        "- Final answer: <the reasoned conclusion, in prose — NEVER a "
        "number derived from invented arithmetic>\n\n"
        "Do NOT invent any quantity (a count, date, duration, age, "
        "distance, etc.) to calculate — every worked example for this "
        "subject must be answered through reasoning and textual evidence, "
        "not arithmetic."
    )

    if not pdf_dir.exists():
        print(f"ERROR: PDF source directory not found: {pdf_dir}")
        sys.exit(1)

    n = len(chapters)
    if limit:
        n = min(n, limit)

    output_dir = output_root / f"GPT55_Prompts_grade_10_{book_key}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Preparing GPT-5.5 prompts for {grade} / {subject} — book: {book_key}")
    print(f"  Source PDFs: {pdf_dir}")
    print(f"  Output folder: {output_dir}")
    print(f"  Chapters to process: {n}\n")

    manifest_lines = [f"GPT-5.5 Prompt Bundle — {grade} / {subject} ({book_key})", ""]

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
            content_language_name=content_language_name,
            content_language_note=content_language_note,
            worked_example_format_note=worked_example_format_note,
            subject_guidance=_get_subject_guidance(subject),
            h_what_you_will_learn=headings["what_you_will_learn"],
            h_simple_explanation=headings["simple_explanation"],
            h_step_by_step_breakdown=headings["step_by_step_breakdown"],
            h_worked_example=headings["worked_example"],
            h_common_mistake=headings["common_mistake"],
            h_quick_check_question=headings["quick_check_question"],
            h_summary=headings["summary"],
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
    manifest_lines.append(
        "IMPORTANT: the 'chapter' field in each prompt already matches the "
        "EXACT rag_documents.chapter string students' dropdown expects — "
        "do NOT rename it before ingesting."
    )
    manifest_lines.append("")

    manifest_path = output_dir / "00_README_and_index.txt"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"\n  Wrote index/instructions: {manifest_path}")
    print(f"\nDone. {n} chapter prompt(s) + source PDF(s) prepared in:\n  {output_dir}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare GPT-5.5 prompts for Grade 10 English/Hindi/Social Science books"
    )
    parser.add_argument(
        "--book", required=True,
        help=f"One of {list(BOOKS.keys())} or 'all'",
    )
    parser.add_argument(
        "--output-dir", default=str(DOWNLOADS),
        help="Root output folder (default: ~/Downloads) — a per-book subfolder is created inside it",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N chapters")
    args = parser.parse_args()

    output_root = Path(args.output_dir).expanduser()

    if args.book == "all":
        for book_key in BOOKS:
            run_book(book_key, output_root, args.limit)
    else:
        run_book(args.book, output_root, args.limit)


if __name__ == "__main__":
    main()
