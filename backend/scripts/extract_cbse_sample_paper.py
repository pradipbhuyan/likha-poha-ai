#!/usr/bin/env python3
"""
Extract a CBSE Sample Question Paper PDF into structured questions (no answers).

Parses on directly-observable structural markers rather than free-form
instruction prose, since instruction wording varies across papers:
  - "(Section X)" markers set the `section` field.
  - A standalone integer line right after a question (and its options, if MCQ)
    is that question's marks.
  - "(A) ... (B) ... (C) ... (D) ..." lines mark it as MCQ and populate `options`.
  - Section E (case-study) questions have internal sub-parts (i., ii., iii.(A)/(B)
    with "OR" alternatives) that are NOT split into separate rows in this pass —
    each top-level question number becomes one row with the full passage +
    sub-parts as `question_text`, type "case_study". Splitting sub-parts is
    future work, not attempted here.

Output: writes {output}.json (array of questions, no answer fields) and upserts
into board_sample_paper_questions with status="extracted". Requires the paper's
board_sample_papers row to already exist (create via --create-paper or pass
--paper-id directly).

Usage:
    cd backend
    .venv/bin/python3 scripts/extract_cbse_sample_paper.py \\
        --pdf /path/to/MathsStandard-SQP.pdf \\
        --grade "Grade 10" --subject "Mathematics" --subject-variant "Maths Standard" \\
        --academic-year "2025-26" --source-subject-code MathsStandard \\
        --create-paper
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypdf

from app.services.grade_db_router import get_content_db

BOARD = "CBSE"

SECTION_RE = re.compile(r"\(?Section\s*[–-]?\s*([A-E])\)?", re.IGNORECASE)
QUESTION_START_RE = re.compile(r"(?m)^\s*(\d{1,2})\.\s*")
OPTION_LINE_RE = re.compile(r"\((?:A|B|C|D)\)(?!:)")
TRAILING_MARKS_RE = re.compile(r"(?m)^\s*(\d{1,2})\s*$")
PAPER_START_RE = re.compile(r"\(?Section\s*[–-]?\s*A\)?", re.IGNORECASE)


def extract_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def strip_page_furniture(text: str) -> str:
    """Remove page-number footers/headers and the repeated assessment-scheme note."""
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text)
    text = re.sub(
        r"\*Please note that the assessment scheme.*?2025-26", "", text, flags=re.DOTALL
    )
    return text


ASSERTION_REASON_RE = re.compile(r"\bAssertion\b.{0,20}\bReason\b", re.IGNORECASE | re.DOTALL)
# CBSE prints this interpretive key once (between the last plain MCQ and the
# first Assertion-Reason question) rather than repeating it under each A-R
# question. It's fixed, standard wording across every CBSE paper — hardcode
# it and assign it directly to every assertion_reason question, rather than
# trying to parse it out of whichever question's text it happens to trail.
ASSERTION_REASON_PREAMBLE_RE = re.compile(r"(?:select|choose)\s+the\s+correct\s+option", re.IGNORECASE)
ASSERTION_REASON_OPTIONS = [
    "Both assertion (A) and reason (R) are true and reason (R) is the correct explanation of assertion (A)",
    "Both assertion (A) and reason (R) are true but reason (R) is not the correct explanation of assertion (A)",
    "Assertion (A) is true but reason (R) is false",
    "Assertion (A) is false but reason (R) is true",
]
SECTION_MARKS_RE = re.compile(
    r"Section\s+([A-E])\s+consists\s+of\s+\d+.*?of\s+(\d+)\s+marks?\s+each",
    re.IGNORECASE,
)


def parse_section_marks(full_text: str) -> dict[str, int]:
    """Read authoritative per-section marks from the paper's own section-intro
    lines ('Section B consists of 5 questions of 2 marks each') — far more
    reliable than inferring marks from scattered trailing numbers per
    question, which get scrambled by PDF layout quirks on multi-part
    (case-study) questions."""
    return {m.group(1).upper(): int(m.group(2)) for m in SECTION_MARKS_RE.finditer(full_text)}


def infer_type_and_marks(section: str, marks: int, has_options: bool, block_text: str = "") -> str:
    if section == "A":
        if ASSERTION_REASON_RE.search(block_text):
            return "assertion_reason"
        return "mcq" if has_options else "assertion_reason"
    if section in ("B", "C"):
        return "short_answer"
    if section == "D":
        return "long_answer"
    if section == "E":
        return "case_study"
    return "short_answer"


def parse_options(block: str) -> list[str]:
    """Pull the four (A)/(B)/(C)/(D) option strings out of a question block.

    NOTE: options built from stacked-fraction layouts (numerator/denominator
    on separate lines with no "/" character, no consistent whitespace
    pattern to key off) are NOT reliably reconstructable from the text layer
    alone — tried a line-joining heuristic here and it made option counts
    *worse* on several questions (verified against the pilot paper). Any
    question flagged with corrupted/wrong-count options should be fixed via
    vision extraction (render the page, read the options visually) rather
    than more text-layer regex tuning — see extract_cbse_options_vision.py.
    """
    # Split on the option markers, keep the marker with its following text.
    parts = re.split(r"(\([A-D]\)(?!:))", block)
    options: list[str] = []
    current_label = None
    for part in parts:
        if re.fullmatch(r"\([A-D]\)", part):
            current_label = part
        elif current_label:
            options.append(part.strip().split("\n")[0].strip())
            current_label = None
    return [o for o in options if o]


def parse_questions(full_text: str) -> list[dict]:
    # Skip the General Instructions block — its numbered list items ("1. This
    # question paper contains...") match the same "N. " pattern as real
    # questions. Start parsing from the first Section-A marker instead.
    start_match = PAPER_START_RE.search(full_text)
    if start_match:
        full_text = full_text[start_match.start():]

    section_marks = parse_section_marks(full_text)
    current_section = "A"
    questions: list[dict] = []
    expected_next = 1

    starts = list(QUESTION_START_RE.finditer(full_text))
    for i, m in enumerate(starts):
        q_num = int(m.group(1))
        # Real questions are strictly sequential (1, 2, 3, ... in order).
        # Numbered sub-lists embedded inside a question's own text (e.g. a
        # probability question listing "1. ... 2. ..." as conditions) match
        # the same regex but break the sequence — skip those.
        if q_num != expected_next:
            continue
        expected_next += 1

        block_start = m.end()
        block_end = starts[i + 1].start() if i + 1 < len(starts) else len(full_text)
        # Re-scan forward from here for the *next accepted* start, in case the
        # very next regex match is itself a skipped embedded number — using
        # starts[i+1] blindly would truncate this question's text early.
        for j in range(i + 1, len(starts)):
            if int(starts[j].group(1)) == expected_next:
                block_end = starts[j].start()
                break
        block = full_text[block_start:block_end]
        # Strip the shared Assertion-Reason interpretive key if it trails
        # this question's own content (see ASSERTION_REASON_PREAMBLE_RE) —
        # it belongs to the *next* question(s), not this one.
        preamble_match = ASSERTION_REASON_PREAMBLE_RE.search(block)
        if preamble_match:
            block = block[: preamble_match.start()]

        # Section markers can appear inside the gap before this question.
        preceding = full_text[starts[i - 1].end() if i > 0 else 0 : m.start()]
        sec_match = SECTION_RE.search(preceding)
        if sec_match:
            current_section = sec_match.group(1).upper()

        # Only Section A actually has 4-way MCQ/assertion-reason options.
        # In every other section, a bare "(A)"/"(B)" marker means either an
        # internal OR-choice between two alternative versions of the SAME
        # question (e.g. "32.(A) ... OR (B) ...") or a stray figure/diagram
        # label pypdf pulled out of visual order — neither is a real option
        # list, and splitting on it there emptied question_text entirely
        # while stuffing the real question into `options`.
        has_options = current_section == "A" and bool(OPTION_LINE_RE.search(block))
        options = parse_options(block) if has_options else []

        if current_section in section_marks:
            marks = section_marks[current_section]
        else:
            marks_matches = TRAILING_MARKS_RE.findall(block)
            marks = int(marks_matches[0]) if marks_matches else 1

        # Question text = block with option lines and trailing bare numbers removed.
        text = block
        if has_options:
            text = re.split(r"\([A-D]\)(?!:)", text, maxsplit=1)[0]
        text = TRAILING_MARKS_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()

        q_type = infer_type_and_marks(current_section, marks, has_options, block)
        if q_type == "assertion_reason":
            # The 4 interpretive choices are fixed, standard CBSE wording
            # printed once per paper (not per question) — see
            # ASSERTION_REASON_OPTIONS docstring above.
            options = list(ASSERTION_REASON_OPTIONS)
        diagram_dependent = bool(
            re.search(r"figure|diagram|picture|graph shown|shown below|shown above", block, re.I)
        )

        questions.append({
            "question_number": q_num,
            "section": current_section,
            "question_type": q_type,
            "marks": marks,
            "question_text": text,
            "options": options,
            "diagram_dependent": diagram_dependent,
        })

    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a CBSE SQP PDF into structured questions")
    parser.add_argument("--pdf", help="Source PDF to parse (mutually exclusive with --from-json)")
    parser.add_argument("--from-json", help="Load already-extracted/corrected questions JSON instead of re-parsing a PDF")
    parser.add_argument("--grade", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--subject-variant", default="")
    parser.add_argument("--academic-year", required=True)
    parser.add_argument("--source-subject-code", required=True)
    parser.add_argument("--question-paper-url", default="")
    parser.add_argument("--marking-scheme-url", default="")
    parser.add_argument("--source-page-url", default="")
    parser.add_argument("--create-paper", action="store_true", help="Create/update the board_sample_papers row")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print summary only, no DB writes")
    parser.add_argument("--output", default="questions_extracted.json")
    args = parser.parse_args()

    if args.from_json:
        questions = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        pdf_name = Path(args.from_json).name
    elif args.pdf:
        pdf_path = Path(args.pdf)
        pages = extract_pages(pdf_path)
        full_text = strip_page_furniture("\n".join(pages))
        questions = parse_questions(full_text)
        pdf_name = pdf_path.name
    else:
        print("Pass either --pdf or --from-json")
        sys.exit(1)

    by_type: dict[str, int] = {}
    diagram_count = 0
    for q in questions:
        by_type[q["question_type"]] = by_type.get(q["question_type"], 0) + 1
        if q["diagram_dependent"]:
            diagram_count += 1

    print(f"Parsed {len(questions)} questions from {pdf_name}")
    print(f"  By type: {by_type}")
    print(f"  Flagged diagram-dependent: {diagram_count}")
    print(f"  Sections seen: {sorted(set(q['section'] for q in questions))}")

    Path(args.output).write_text(json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote {args.output}")

    if args.dry_run:
        print("[dry-run] skipping DB writes")
        return

    db = get_content_db(args.grade)

    paper_id = None
    if args.create_paper:
        result = (
            db.table("board_sample_papers")
            .upsert({
                "board": BOARD,
                "academic_year": args.academic_year,
                "grade": args.grade,
                "subject": args.subject,
                "subject_variant": args.subject_variant,
                "source_subject_code": args.source_subject_code,
                "question_paper_url": args.question_paper_url,
                "marking_scheme_url": args.marking_scheme_url,
                "source_page_url": args.source_page_url,
            }, on_conflict="board,academic_year,grade,source_subject_code")
            .execute()
        )
        paper_id = result.data[0]["id"]
        print(f"  Paper row: {paper_id}")
    else:
        existing = (
            db.table("board_sample_papers")
            .select("id")
            .eq("board", BOARD).eq("academic_year", args.academic_year)
            .eq("grade", args.grade).eq("source_subject_code", args.source_subject_code)
            .execute()
        )
        if not existing.data:
            print("  [error] no existing paper row found — pass --create-paper")
            sys.exit(1)
        paper_id = existing.data[0]["id"]

    stored = 0
    for q in questions:
        db.table("board_sample_paper_questions").upsert({
            "paper_id": paper_id,
            "question_number": q["question_number"],
            "section": q["section"],
            "question_type": q["question_type"],
            "marks": q["marks"],
            "question_text": q["question_text"],
            "options": q["options"],
            "diagram_dependent": q["diagram_dependent"],
            "status": "extracted",
        }, on_conflict="paper_id,question_number").execute()
        stored += 1
    print(f"  Upserted {stored} question rows (status=extracted, no answers yet)")


if __name__ == "__main__":
    main()
