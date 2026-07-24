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

Extended to handle older paper formats (2020-21, 2021-22):
  - 2021-22 Term 1: section-local numbering (each section starts at 1),
    lowercase (a)(b)(c)(d) options, "Any N questions are to be attempted".
    Triggered by TERM1_ANY_N_RE -> _parse_questions_term1_sections().
  - Mixed BARE/STRICT format (2021-22 T2 SocSci, 2020-21 SocSci):
    QUESTION_START_RE_COMBINED tries both "N. text" and "N text".
  - 2021-22 T2 Science lowercase sub-question starts ("3 a. Trace..."):
    BARE lookahead widened to [A-Za-z(delta].
  - 2020-21 table-format: q=1 embedded in "No. Questions Marks 1 List...":
    strip_page_furniture injects newline before the first question number.
  - SECTION_MARKS_RE handles "comprises of" / "has N questions of M marks each"
    in addition to "consists of".
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
# Two question-numbering styles seen across subjects. STRICT requires a
# period ("21." — Maths, sometimes with no space after it before an option
# marker like "21.(A)"). BARE has no period at all ("1 Select..." —
# Science), so it requires whitespace + an immediate capital letter to stay
# safe. These must stay separate regexes, not merged into one permissive
# pattern: Maths' stacked-fraction options print a bare denominator digit on
# its own line (e.g. "15" then a line with just "4"), which a permissive
# "bare number" pattern false-matches as a question number. Per-paper
# selection (choose_question_regex, scored by resulting sequential-run
# length) picks whichever actually fits this paper.
# STRICT also handles "Q1." format used in some Grade 12 Physics/Maths papers:
# "Q1. A uniform electric field..." — the Q prefix is optional.
QUESTION_START_RE_STRICT = re.compile(r"(?m)^\s*Q?(\d{1,2})\.\s*")
# Widened from (?=[A-Z(]) to allow:
#   - Lowercase: "3 a. Trace the path..." (2021-22 T2 Science sub-question labels)
#   - Greek Δ: "6 ΔABC~ΔPQR..." (Maths geometry questions)
#   - Quoted text: '7.\n\n"Tribal peasants...' (2021-22 T2 SocSci question 7 starts with ")
# NOTE: uses non-raw f-string to embed actual Δ (U+0394) so the character class
# correctly matches the Devanagari-adjacent glyph that pypdf emits for ∆ in PDFs.
# A standalone denominator digit is always followed immediately by a newline only,
# never by a letter or quote — so the widened lookahead does not affect it.
# \u201c = LEFT DOUBLE QUOTATION MARK " (U+201C) — pypdf curly quote in question text
# \u2018 = LEFT SINGLE QUOTATION MARK ' (U+2018) — curly single quote
# \u2206 = INCREMENT SIGN ∆ (U+2206) — geometric delta in Maths PDFs
# \u0394 = Greek capital Δ (U+0394)
QUESTION_START_RE_BARE = re.compile(
    "(?m)^\\s*(\\d{1,2})\\s+(?=[A-Za-z(\u0394\u2206\u201c\u2018\"'])"
)
# Combined: handles papers mixing STRICT ("6.  Why do most...") and BARE
# ("1 How did...") within the same paper (2021-22 T2 SocSci, 2020-21 SocSci).
QUESTION_START_RE_COMBINED = re.compile(
    "(?m)^\\s*Q?(\\d{1,2})(?:\\.\\s*|\\s+)(?=[A-Za-z(\u0394\u2206\u201c\u2018\"'])"
)
OPTION_LINE_RE_PAREN = re.compile(r"\((?:A|B|C|D)\)(?!:)")
# Term 1 (2021-22) papers use lowercase (a)(b)(c)(d) option markers.
OPTION_LINE_RE_PAREN_LOWER = re.compile(r"\((?:a|b|c|d)\)(?!:)")
OPTION_LINE_RE_DOT = re.compile(r"(?m)^\s*[A-D]\.\s+")
TRAILING_MARKS_RE = re.compile(r"(?m)^\s*(\d{1,2})\s*$")
PAPER_START_RE = re.compile(r"\(?Section\s*[–-]?\s*A\)?", re.IGNORECASE)
# Term 1 (2021-22) papers have this unique marker per section.
# Matches both "Any 16 questions are to be attempted" (Maths) and
# "Attempt any 20 questions" (Science) phrasings.
TERM1_ANY_N_RE = re.compile(
    r"Any\s+\d+\s+questions?\s+are\s+to\s+be\s+attempted"
    r"|[Aa]ttempt\s+any\s+\d+\s+questions?",
    re.IGNORECASE,
)
TERM1_SECTION_SPLIT_RE = re.compile(
    r"(?m)^[ \t]*SECTION\s*[–-]?\s*([A-E])\b", re.IGNORECASE
)


def extract_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def strip_page_furniture(text: str) -> str:
    """Remove page-number footers/headers and the repeated assessment-scheme note.

    Also normalises two older-paper table-format quirks so that question 1
    is detectable at line-start by the BARE/COMBINED regex:

    1. "No. Questions Marks 1 List any two..." (2020-21 Science) becomes
       "No. Questions Marks\n1 List any two..."
    2. "Q No  Marks\n1 Find the value..." is already fine but "Q No  Marks 1 Find..."
       (same-line variant) gets a newline injected the same way.
    """
    # Remove null bytes that pypdf occasionally emits from malformed PDFs —
    # Supabase/Postgres rejects \u0000 in text columns.
    text = text.replace("\x00", "")
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text)
    text = re.sub(
        r"\*Please note that the assessment scheme.*?2025-26", "", text, flags=re.DOTALL
    )
    # Table-format header: inject newline before the first question number.
    text = re.sub(
        r"(No\.?\s+Questions?\s+Marks?)\s+(\d{1,2}\s)",
        r"\1\n\2",
        text,
    )
    text = re.sub(
        r"(Q\s+No\s+Marks?)\s+(\d{1,2}\s)",
        r"\1\n\2",
        text,
    )
    return text


ASSERTION_REASON_RE = re.compile(r"\bAssertion\b", re.IGNORECASE)
_REASON_WORD_RE = re.compile(r"\bReason\b", re.IGNORECASE)
ASSERTION_REASON_PREAMBLE_RE = re.compile(
    r"(?:select|choose|selecting)(?:ing)?\s+the\s+(?:correct|appropriate)\s+option",
    re.IGNORECASE,
)
ASSERTION_REASON_OPTIONS = [
    "Both assertion (A) and reason (R) are true and reason (R) is the correct explanation of assertion (A)",
    "Both assertion (A) and reason (R) are true but reason (R) is not the correct explanation of assertion (A)",
    "Assertion (A) is true but reason (R) is false",
    "Assertion (A) is false but reason (R) is true",
]
# Extended to handle wording variants found in older papers:
#   "Section A comprises of 6 questions of 2 marks each" (2021-22 T2 Maths)
#   "Section -A has 7 questions of 2 marks each" (2021-22 T2 Science)
SECTION_MARKS_RE = re.compile(
    r"Section\s*[–-]?\s*([A-E])\s+"
    r"(?:consists\s+of|comprises\s+of?|has)\s+\d+\s+questions?\s+(?:of|carrying)\s+"
    r"(\d+)\s+marks?\s+each",
    re.IGNORECASE,
)


def parse_section_marks(full_text: str) -> dict[str, int]:
    """Read authoritative per-section marks from the paper's own section-intro lines."""
    return {m.group(1).upper(): int(m.group(2)) for m in SECTION_MARKS_RE.finditer(full_text)}


def infer_type_and_marks(marks: int, has_options: bool, block_text: str = "") -> str:
    if marks == 1:
        if ASSERTION_REASON_RE.search(block_text) and _REASON_WORD_RE.search(block_text):
            return "assertion_reason"
        return "mcq"
    if marks in (2, 3):
        return "short_answer"
    if marks == 5:
        return "long_answer"
    if marks == 4:
        return "case_study"
    return "short_answer"


def detect_option_style(full_text: str) -> str:
    """Pick option style: paren uppercase (A)(B)(C)(D), paren lowercase (a)(b)(c)(d), or dot A./B."""
    paren_upper = len(OPTION_LINE_RE_PAREN.findall(full_text))
    paren_lower = len(OPTION_LINE_RE_PAREN_LOWER.findall(full_text))
    dot_count = len(OPTION_LINE_RE_DOT.findall(full_text))
    if paren_lower > paren_upper and paren_lower > dot_count:
        return "paren_lower"
    if paren_upper >= dot_count:
        return "paren"
    return "dot"


def _join_wrapped_option(part: str) -> str:
    joined: list[str] = []
    for line in part.split("\n"):
        stripped = line.strip()
        if not stripped:
            break
        if joined and re.fullmatch(r"\d{1,2}", stripped):
            break
        joined.append(stripped)
    return " ".join(joined).strip()


def parse_options(block: str, style: str) -> list[str]:
    if style == "dot":
        marker_re = r"(?m)(^\s*[A-D]\.\s+)"
        label_re = r"\s*[A-D]\.\s+"
    elif style == "paren_lower":
        marker_re = r"(\((?:a|b|c|d)\)(?!:))"
        label_re = r"\([a-d]\)"
    else:
        marker_re = r"(\([A-D]\)(?!:))"
        label_re = r"\([A-D]\)"
    parts = re.split(marker_re, block)
    options: list[str] = []
    current_label = None
    for part in parts:
        if re.fullmatch(label_re, part):
            current_label = part
        elif current_label:
            options.append(_join_wrapped_option(part))
            current_label = None
    return [o for o in options if o]


def _score_regex_from(full_text: str, question_re: "re.Pattern", start_offset: int) -> int:
    """Length of the longest strictly-sequential 1,2,3,... run starting from 1."""
    starts = list(question_re.finditer(full_text[start_offset:]))
    expected = 1
    score = 0
    for m in starts:
        if int(m.group(1)) == expected:
            score += 1
            expected += 1
    return score


def choose_question_regex(full_text: str) -> tuple["re.Pattern", int]:
    """Pick the question-numbering regex (STRICT / BARE / COMBINED) and the
    offset where real numbered questions begin.

    Tries STRICT and BARE first (as before). If neither scores more than 5,
    also tries COMBINED — which handles papers that mix period and bare
    numbering styles across sections (2021-22 T2 SocSci, 2020-21 SocSci).
    """
    candidates = [m.start() for m in PAPER_START_RE.finditer(full_text)] or [0]
    best_regex, best_start, best_score = QUESTION_START_RE_STRICT, candidates[0], -1
    # Try all three regex styles. COMBINED is tried last and only wins if it
    # strictly beats both STRICT and BARE — preserving backward-compatibility
    # with papers that work well with a single style while letting mixed-format
    # papers (2021-22 T1 Science, T2 SocSci, 2020-21 SocSci) use COMBINED.
    for question_re in (QUESTION_START_RE_STRICT, QUESTION_START_RE_BARE, QUESTION_START_RE_COMBINED):
        for cand in candidates:
            score = _score_regex_from(full_text, question_re, cand)
            if score > best_score:
                best_regex, best_start, best_score = question_re, cand, score
    return best_regex, best_start


_AR_OPTION_LINE_RE = re.compile(r"^\s*(?:\([A-Da-d]\)|[A-D]\.)\s*")


def extract_assertion_reason_options(full_text: str, question_start_re: "re.Pattern") -> list[str]:
    m = ASSERTION_REASON_PREAMBLE_RE.search(full_text)
    if not m:
        return list(ASSERTION_REASON_OPTIONS)
    options: list[str] = []
    current = None
    for line in full_text[m.end():m.end() + 800].split("\n"):
        marker = _AR_OPTION_LINE_RE.match(line)
        next_question = question_start_re.match(line)
        if marker:
            if current is not None:
                options.append(current.strip())
            if len(options) == 4:
                break
            current = line[marker.end():].strip()
        elif not line.strip() or next_question:
            if current is not None:
                options.append(current.strip())
                current = None
            if len(options) == 4:
                break
        elif current is not None:
            current = f"{current} {line.strip()}".strip()
    if current is not None and len(options) < 4:
        options.append(current.strip())
    options = [o for o in options if o]
    return options[:4] if len(options) >= 4 else list(ASSERTION_REASON_OPTIONS)


def _build_question_row(
    q_num: int,
    block: str,
    current_section: str,
    section_marks: dict,
    option_style: str,
    ar_options: list,
    section_offset: int = 0,
) -> dict:
    """Assemble one question dict from its parsed block."""
    if current_section in section_marks:
        marks = section_marks[current_section]
    else:
        marks_matches = TRAILING_MARKS_RE.findall(block)
        marks = int(marks_matches[0]) if marks_matches else 1

    if option_style == "paren_lower":
        option_marker_re = OPTION_LINE_RE_PAREN_LOWER
    elif option_style == "dot":
        option_marker_re = OPTION_LINE_RE_DOT
    else:
        option_marker_re = OPTION_LINE_RE_PAREN

    has_options = marks == 1 and bool(option_marker_re.search(block))
    options = parse_options(block, option_style) if has_options else []

    text = block
    if has_options:
        if option_style == "dot":
            split_re = r"(?m)^\s*[A-D]\.\s+"
        elif option_style == "paren_lower":
            split_re = r"\([a-d]\)(?!:)"
        else:
            split_re = r"\([A-D]\)(?!:)"
        text = re.split(split_re, text, maxsplit=1)[0]
    text = TRAILING_MARKS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()

    q_type = infer_type_and_marks(marks, has_options, block)
    if q_type == "assertion_reason":
        options = list(ar_options)
    diagram_dependent = bool(
        re.search(r"figure|diagram|picture|graph shown|shown below|shown above", block, re.I)
    )
    return {
        "question_number": q_num + section_offset,
        "section": current_section,
        "question_type": q_type,
        "marks": marks,
        "question_text": text,
        "options": options,
        "diagram_dependent": diagram_dependent,
    }


def _parse_section_text(
    section_text: str, section_letter: str, section_offset: int
) -> list[dict]:
    """Extract questions from a single section's text for Term 1 papers.

    Term 1 papers number questions locally within each section (Section A:
    1-20, Section B: 1-20, Section C: 1-10).  section_offset is added to
    each local question_number so the combined output is globally unique:
    Section A offset=0, Section B offset=20, Section C offset=40.
    """
    question_start_re, start_offset = choose_question_regex(section_text)
    section_text = section_text[start_offset:]
    option_style = detect_option_style(section_text)
    ar_options = extract_assertion_reason_options(section_text, question_start_re)
    section_marks = parse_section_marks(section_text)
    if section_letter not in section_marks:
        section_marks[section_letter] = 1
    questions: list[dict] = []
    expected_next = 1
    starts = list(question_start_re.finditer(section_text))
    for i, m in enumerate(starts):
        q_num = int(m.group(1))
        if q_num != expected_next:
            continue
        expected_next += 1
        block_start = m.end()
        block_end = starts[i + 1].start() if i + 1 < len(starts) else len(section_text)
        for j in range(i + 1, len(starts)):
            if int(starts[j].group(1)) == expected_next:
                block_end = starts[j].start()
                break
        block = section_text[block_start:block_end]
        questions.append(
            _build_question_row(q_num, block, section_letter, section_marks, option_style, ar_options, section_offset)
        )
    return questions


# Term 1 Science papers number questions globally (Section B: Sl. No.25-48).
# Term 1 Maths papers number locally (each section starts at 1).
_TERM1_GLOBAL_NUM_RE = re.compile(
    r"Sl\.?\s*No\.?\s*\d+\s+to\s+\d+|Serial\s+No\.?\s*\d+", re.IGNORECASE
)


def _parse_questions_term1_sections(full_text: str) -> list[dict]:
    """Handle Term 1 (2021-22) papers with section-local question numbering.

    Splits the paper text at SECTION A / B / C boundaries, extracts each
    section independently with _parse_section_text(), and renumbers
    questions globally: Section A keeps local numbers, Section B += count_A,
    Section C += count_A + count_B.

    Falls back to regular parse_questions() if the paper uses global
    question numbering across sections (e.g. T1 Science: Sl. No.25 to 48
    in Section B).  In that case section-split extraction is the wrong
    approach — the whole-paper sequential scan handles it correctly.

    Deduplication: CBSE Term 1 papers often repeat the section heading once
    in the intro and once as the actual header — keep only the first
    occurrence of each section letter.
    """
    # If sections carry globally-sequential numbers, skip section-split logic.
    if _TERM1_GLOBAL_NUM_RE.search(full_text):
        # Fall through to the regular whole-paper scanner below. Strip the
        # TERM1_ANY_N_RE guard to prevent infinite recursion.
        return _parse_questions_global(full_text)

    boundaries = list(TERM1_SECTION_SPLIT_RE.finditer(full_text))
    if not boundaries:
        return _parse_questions_global(full_text)  # fallback

    # Deduplicate: for each letter, use only its first boundary position;
    # slice ends at the first boundary of the next different letter.
    seen_letters: list[str] = []
    first_pos: dict[str, int] = {}
    for bnd in boundaries:
        letter = bnd.group(1).upper()
        if letter not in first_pos:
            first_pos[letter] = bnd.start()
            seen_letters.append(letter)

    sections: list[tuple[str, str]] = []
    for i, letter in enumerate(seen_letters):
        start = first_pos[letter]
        # End at first boundary of the next different letter
        end = len(full_text)
        for future_letter in seen_letters[i + 1:]:
            if future_letter != letter:
                end = first_pos[future_letter]
                break
        sections.append((letter, full_text[start:end]))

    all_questions: list[dict] = []
    running_offset = 0
    for letter, sec_text in sections:
        qs = _parse_section_text(sec_text, letter, running_offset)
        if qs:
            running_offset += max(q["question_number"] - running_offset for q in qs)
        all_questions.extend(qs)
    return all_questions


def _parse_questions_global(full_text: str) -> list[dict]:
    """Core whole-paper sequential question scanner (no Term1 routing)."""
    question_start_re, start_offset = choose_question_regex(full_text)
    return _parse_questions_from(full_text, question_start_re, start_offset)


def _parse_questions_from(full_text: str, question_start_re, start_offset: int) -> list[dict]:
    """Sequential question scanner from a fixed offset with a given regex."""
    full_text = full_text[start_offset:]
    option_style = detect_option_style(full_text)
    ar_options = extract_assertion_reason_options(full_text, question_start_re)
    section_marks = parse_section_marks(full_text)
    current_section = "A"
    questions: list[dict] = []
    expected_next = 1
    starts = list(question_start_re.finditer(full_text))
    for i, m in enumerate(starts):
        q_num = int(m.group(1))
        if q_num != expected_next:
            # Tolerate a single missing question number (e.g. Q20 absent from
            # extracted text because pypdf couldn't read a custom-font or
            # image-embedded number). Only advance by 1 at a time so that
            # larger gaps and genuine false positives are still rejected.
            if q_num == expected_next + 1:
                expected_next += 1  # silently skip the one missing question
            else:
                continue
            if q_num != expected_next:
                continue
        expected_next += 1
        block_start = m.end()
        block_end = starts[i + 1].start() if i + 1 < len(starts) else len(full_text)
        for j in range(i + 1, len(starts)):
            if int(starts[j].group(1)) == expected_next:
                block_end = starts[j].start()
                break
        block = full_text[block_start:block_end]
        preamble_match = None
        for candidate in ASSERTION_REASON_PREAMBLE_RE.finditer(block):
            if re.search(r"\bAssertion\b", block[max(0, candidate.start() - 200):candidate.end()], re.IGNORECASE):
                preamble_match = candidate
                break
        if preamble_match:
            cut_at = preamble_match.start()
            window_start = max(0, cut_at - 200)
            lead_in = re.search(r"\bAssertion\b|\bReason\b", block[window_start:cut_at], re.IGNORECASE)
            if lead_in:
                cut_at = window_start + lead_in.start()
            block = block[:cut_at]
        preceding = full_text[starts[i - 1].end() if i > 0 else 0 : m.start()]
        sec_match = SECTION_RE.search(preceding)
        if sec_match:
            current_section = sec_match.group(1).upper()
        questions.append(
            _build_question_row(q_num, block, current_section, section_marks, option_style, ar_options)
        )
    return questions


def parse_questions(full_text: str) -> list[dict]:
    # Term 1 (2021-22) papers have section-local numbering — detect and handle separately.
    if TERM1_ANY_N_RE.search(full_text):
        return _parse_questions_term1_sections(full_text)
    return _parse_questions_global(full_text)


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
                "status": "pending_answers",
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
