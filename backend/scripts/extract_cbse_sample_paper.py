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
QUESTION_START_RE_STRICT = re.compile(r"(?m)^\s*(\d{1,2})\.\s*")
QUESTION_START_RE_BARE = re.compile(r"(?m)^\s*(\d{1,2})\s+(?=[A-Z(])")
# Two option styles seen across subjects: parenthesized "(A) ... (B) ..."
# (Maths) and letter-dot "A. ... B. ..." (Science). A paper uses one style
# consistently throughout — detect_option_style() below picks it once per
# paper rather than trying to match both simultaneously.
OPTION_LINE_RE_PAREN = re.compile(r"\((?:A|B|C|D)\)(?!:)")
OPTION_LINE_RE_DOT = re.compile(r"(?m)^\s*[A-D]\.\s+")
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


# A proximity window is fragile — "Assertion (A): <statement, sometimes long>
# Reason (R): ..." varies too much in length across subjects/questions.
# "Assertion" and "Reason" both appearing anywhere in a 1-mark question block
# is already a highly specific signal on its own (no real Maths/Science/etc
# question about anything else would contain both words) — check presence,
# not distance.
ASSERTION_REASON_RE = re.compile(r"\bAssertion\b", re.IGNORECASE)
_REASON_WORD_RE = re.compile(r"\bReason\b", re.IGNORECASE)
# CBSE prints this interpretive key once (between the last plain MCQ and the
# first Assertion-Reason question) rather than repeating it under each A-R
# question. It's fixed, standard wording across every CBSE paper — hardcode
# it and assign it directly to every assertion_reason question, rather than
# trying to parse it out of whichever question's text it happens to trail.
ASSERTION_REASON_PREAMBLE_RE = re.compile(
    r"(?:select|choose|selecting)(?:ing)?\s+the\s+(?:correct|appropriate)\s+option", re.IGNORECASE
)
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


def infer_type_and_marks(marks: int, has_options: bool, block_text: str = "") -> str:
    """Question type follows the mark value, not the section letter — CBSE's
    mark distribution (1=MCQ/AR, 2/3=short answer, 4=case study, 5=long
    answer) is consistent across subjects, but what a "section" *means*
    isn't: Maths uses Section A-E as literal type tiers, while Science labels
    sections by subject area (Biology/Chemistry/Physics) with the same
    mark-tier structure repeating inside each one."""
    if marks == 1:
        if ASSERTION_REASON_RE.search(block_text) and _REASON_WORD_RE.search(block_text):
            return "assertion_reason"
        # Not AR-shaped text, so it's an mcq even when has_options is False
        # (e.g. table-formatted options like a matching-columns question
        # that the regex-based option detector couldn't parse cleanly) —
        # defaulting those to "assertion_reason" would confidently attach
        # the *wrong* (unrelated) AR options rather than surfacing an empty
        # options list for the answer-validation step to catch.
        return "mcq"
    if marks in (2, 3):
        return "short_answer"
    if marks == 5:
        return "long_answer"
    if marks == 4:
        return "case_study"
    return "short_answer"


def detect_option_style(full_text: str) -> str:
    """A paper uses one option style consistently: parenthesized "(A) ... (B)
    ..." (Maths) or letter-dot "A. ... B. ..." (Science). Pick whichever has
    more matches paper-wide rather than trying to match both per-question."""
    paren_count = len(OPTION_LINE_RE_PAREN.findall(full_text))
    dot_count = len(OPTION_LINE_RE_DOT.findall(full_text))
    return "paren" if paren_count >= dot_count else "dot"


def _join_wrapped_option(part: str) -> str:
    """An option's text between two markers can legitimately wrap across 2+
    lines ("As sunlight passes through the atmosphere, shorter wavelengths,
    such \\nas blue are scattered more..."). Join those lines with a space,
    but stop at a blank line or a bare marks-value line (e.g. "1" on its own
    line after the last option) — those aren't part of the option text.

    A bare 1-2 digit line is ambiguous on its own: some Maths options *are*
    literally a single digit ("1", "2", "3", "0" as numeric-answer MCQ
    choices), which is indistinguishable in isolation from a trailing marks
    value. Only treat it as the marks-value terminator once at least one
    real content line has already been collected — a genuine option is
    never empty before its own first line."""
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
    """Pull the four option strings out of a question block, in whichever
    style this paper uses.

    NOTE: options built from stacked-fraction layouts (numerator/denominator
    on separate lines with no "/" character, no consistent whitespace
    pattern to key off) are NOT reliably reconstructable from the text layer
    alone — tried a line-joining heuristic for *that specific case* and it
    made option counts *worse* on several questions (verified against the
    pilot paper). That's different from an option's prose simply wrapping
    across lines (handled by _join_wrapped_option above, which joins on
    whitespace rather than trying to reconstruct a fraction with no
    delimiter). Any question flagged with corrupted/wrong-count options
    should be fixed via vision extraction (render the page, read the
    options visually) rather than more text-layer regex tuning — see
    extract_cbse_options_vision.py.
    """
    marker_re = r"(?m)(^\s*[A-D]\.\s+)" if style == "dot" else r"(\([A-D]\)(?!:))"
    label_re = r"\s*[A-D]\.\s+" if style == "dot" else r"\([A-D]\)"
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
    """Length of the longest strictly-sequential 1,2,3,... run of question
    numbers this regex finds from a given offset — the shared scoring
    function both paper-start selection and question-regex selection use."""
    starts = list(question_re.finditer(full_text[start_offset:]))
    expected = 1
    score = 0
    for m in starts:
        if int(m.group(1)) == expected:
            score += 1
            expected += 1
    return score


def choose_question_regex(full_text: str) -> tuple["re.Pattern", int]:
    """Pick both the question-numbering regex (STRICT vs BARE) and the
    offset where real numbered questions begin, for this specific paper.

    General Instructions sections often mention "Section A" incidentally
    (e.g. "... contains sections: Section A-History (20 marks) and Section
    B-...") — naively trimming at the first match anchors on the wrong spot.
    For each candidate "Section A" position and each regex style, score by
    how long a sequential run of question numbers follows; keep whichever
    (regex, offset) pair scores highest overall. An incidental mid-sentence
    mention, or the wrong numbering style, won't sustain a real long
    sequential run the way the actual paper start does."""
    candidates = [m.start() for m in PAPER_START_RE.finditer(full_text)] or [0]
    best_regex, best_start, best_score = QUESTION_START_RE_STRICT, candidates[0], -1
    for question_re in (QUESTION_START_RE_STRICT, QUESTION_START_RE_BARE):
        for cand in candidates:
            score = _score_regex_from(full_text, question_re, cand)
            if score > best_score:
                best_regex, best_start, best_score = question_re, cand, score
    return best_regex, best_start


_AR_OPTION_LINE_RE = re.compile(r"^\s*(?:\([A-D]\)|[A-D]\.)\s*")


def extract_assertion_reason_options(full_text: str, question_start_re: "re.Pattern") -> list[str]:
    """The 4 interpretive Assertion-Reason choices are printed once per paper
    (not per question), with wording that varies by subject ("select the
    correct option" for Maths, "selecting the appropriate option given
    below" for Science, etc). Extract the actual 4 option strings from
    wherever that preamble appears in this paper rather than assuming one
    fixed wording — falls back to the Maths wording only if nothing is found
    (should not happen for a paper that actually has A-R questions).

    Line-anchored on purpose, unlike parse_options(): each option's own
    prose re-mentions "assertion (A)" / "reason (R)" inline (e.g. "Both
    assertion (A) and reason (R) are true..."), which parse_options()'s
    anywhere-in-text marker matching mistakes for additional option
    boundaries. The real markers only ever start a line here, so split on
    line-start markers and fold wrapped continuation lines into the option
    that precedes them."""
    m = ASSERTION_REASON_PREAMBLE_RE.search(full_text)
    if not m:
        return list(ASSERTION_REASON_OPTIONS)

    options: list[str] = []
    current = None
    for line in full_text[m.end():m.end() + 800].split("\n"):
        marker = _AR_OPTION_LINE_RE.match(line)
        # Some papers (Maths) put a blank line after the 4th option before
        # the next question; others (Science) run straight into "8 Assertion
        # (A): ..." with no separator at all — either ends the wrap.
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


def parse_questions(full_text: str) -> list[dict]:
    # Skip the General Instructions block — its numbered list items ("1. This
    # question paper contains...") match the same "N. " pattern as real
    # questions, and may even mention "Section A" incidentally. Start parsing
    # from whichever (regex style, offset) combination actually leads into a
    # real sequential run of questions in this specific paper.
    question_start_re, start_offset = choose_question_regex(full_text)
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
        # "Select/choose the correct option" is generic MCQ instruction
        # phrasing that also shows up in ordinary (non-AR) questions — e.g.
        # a question's own stem can start "Choose the correct option ...
        # which explains the reason for us to perceive the day sky as
        # blue." That's the *first* match in the block, so checking only
        # the first candidate (rather than iterating) would wrongly give up
        # instead of finding the real preamble later in the same block —
        # only treat a candidate as the shared AR preamble if "Assertion"
        # actually appears nearby (the genuine preamble always names it:
        # "...statements – Assertion (A) and Reason (R)...").
        preamble_match = None
        for candidate in ASSERTION_REASON_PREAMBLE_RE.finditer(block):
            if re.search(r"\bAssertion\b", block[max(0, candidate.start() - 200):candidate.end()], re.IGNORECASE):
                preamble_match = candidate
                break
        if preamble_match:
            cut_at = preamble_match.start()
            # The shared AR preamble often opens with its own lead-in
            # sentence ("...consist of two statements – Assertion (A) and
            # Reason (R)...") before the "select the correct option" phrase
            # this regex matches on. Left untruncated, that lead-in's own
            # "Assertion"/"Reason" words leak into the *preceding* (non-AR)
            # question's block and falsely trigger AR-type detection there.
            # Search only a nearby window, not the whole block — a question
            # further back may use "reason" as an ordinary English word
            # (e.g. "...explains the reason for us to perceive..."), which
            # isn't the preamble and shouldn't seed an earlier cut point.
            window_start = max(0, cut_at - 200)
            lead_in = re.search(r"\bAssertion\b|\bReason\b", block[window_start:cut_at], re.IGNORECASE)
            if lead_in:
                cut_at = window_start + lead_in.start()
            block = block[:cut_at]

        # Section markers can appear inside the gap before this question.
        preceding = full_text[starts[i - 1].end() if i > 0 else 0 : m.start()]
        sec_match = SECTION_RE.search(preceding)
        if sec_match:
            current_section = sec_match.group(1).upper()

        if current_section in section_marks:
            marks = section_marks[current_section]
        else:
            marks_matches = TRAILING_MARKS_RE.findall(block)
            marks = int(marks_matches[0]) if marks_matches else 1

        # Only 1-mark questions actually carry 4-way MCQ/assertion-reason
        # options. At higher mark values, a bare "(A)"/"(B)" or "A."/"B."
        # marker means either an internal OR-choice between two alternative
        # versions of the SAME question (e.g. "32.(A) ... OR (B) ...") or a
        # multi-part case-study subquestion — neither is a real option list,
        # and splitting on it there emptied question_text entirely while
        # stuffing the real question into `options`.
        option_marker_re = OPTION_LINE_RE_DOT if option_style == "dot" else OPTION_LINE_RE_PAREN
        has_options = marks == 1 and bool(option_marker_re.search(block))
        options = parse_options(block, option_style) if has_options else []

        # Question text = block with option lines and trailing bare numbers removed.
        text = block
        if has_options:
            split_re = r"(?m)^\s*[A-D]\.\s+" if option_style == "dot" else r"\([A-D]\)(?!:)"
            text = re.split(split_re, text, maxsplit=1)[0]
        text = TRAILING_MARKS_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()

        q_type = infer_type_and_marks(marks, has_options, block)
        if q_type == "assertion_reason":
            options = list(ar_options)
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
