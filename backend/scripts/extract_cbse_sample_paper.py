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
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypdf

from app.services.grade_db_router import get_content_db

BOARD = "CBSE"

# A-F, not just A-E: SocialScience 2023-24/2024-25 add a 6th section (F —
# the map-based question) beyond the usual A-E tier structure.
# \b on both ends: without a word boundary right after "Section" and right
# after the captured letter, this matched inside ordinary prose words like
# "cross-sectional area" (Science 2024-25, Q33's own stem) — "section" +
# "al" reads as "Section" + captured letter "A", wrongly resetting
# current_section to A mid-paper and corrupting every question's marks/type
# after it until the next real section header.
SECTION_RE = re.compile(r"\(?\bSection\b\s*[–-]?\s*([A-F])\b\)?", re.IGNORECASE)
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
# The optional " ?[AB]?" handles OR-choice questions numbered as a fused
# "5A."/"5B." (no separator between digit and the internal-choice letter,
# unlike Maths' "21.(A)" which keeps the letter parenthesized and separate) —
# and inconsistently, sometimes with a stray space ("6 A.") even within the
# same PDF. Only the first ("5A." / "6 A.") is ever accepted as the real
# question start; the "B" alternative still matches (same group(1)) but
# fails the sequential check and falls back to being ordinary block content
# — the OR-alternative text, same as before.
QUESTION_START_RE_STRICT = re.compile(r"(?m)^\s*(\d{1,2})\s?[AB]?\.\s*")
# Lowercase allowed in the lookahead too: some papers (Science 2023-24) open
# a higher-mark question directly with its own lowercase internal-choice
# label ("34 a) Rehmat classified...") rather than a capitalized sentence —
# requiring an uppercase-only lookahead silently dropped those question
# numbers from the sequential run entirely.
# Period made optional (not "required absent"): SocialScience 2024-25
# inconsistently drops the period on SOME question numbers within an
# otherwise dot-numbered paper ("14. In Indian..." then "15 Consider...",
# back to "16. The frequent...") — a single paper can't be forced into
# either the always-dot STRICT or the never-dot original BARE. The mandatory
# whitespace + letter/paren lookahead (not \s*, and not "any digit") is what
# keeps this safe against Maths' bare stacked-fraction denominator lines
# (never followed immediately by a letter), so making the period optional
# here doesn't reopen that false-positive risk.
# Quote characters included in the lookahead too: a question that opens
# with a quoted statement ("21 “Agriculture and industry are not
# exclusive..." — SocialScience 2024-25) starts with a curly opening quote,
# not a letter or "(" — the real Q21 silently never matched at all without
# this, desyncing the sequential counter for every question after it.
_QUOTE_OR_LETTER = "A-Za-z(\"'“”‘’"
QUESTION_START_RE_BARE = re.compile(r"(?m)^\s*(\d{1,2})\.?\s+(?=[" + _QUOTE_OR_LETTER + r"])")
# Some papers mix BOTH conventions across their own sections (SocialScience
# 2023-24/2024-25: Sections A-C use dot style "1." "21." but Section D's
# OR-choice questions drop the period entirely — "30 (A) : Analyze...").
# Neither STRICT nor BARE alone covers a paper like that (whichever wins the
# per-paper score misses the other section's questions outright), so
# UNIFIED accepts either branch per match: a period (with optional trailing
# whitespace, same as STRICT) OR no period but mandatory whitespace + an
# immediate letter/paren/quote (the same guard BARE uses against Maths' bare
# fraction-denominator lines).
QUESTION_START_RE_UNIFIED = re.compile(
    r"(?m)^\s*(\d{1,2})\s?[AB]?(?:\.\s*|\s+(?=[" + _QUOTE_OR_LETTER + r"]))"
)
# Matching-columns questions (e.g. Social Science History) print their own
# answer key as numbered lines like "1.A-4, B-1, C-2, D-3" — each line is
# textually indistinguishable from a real "question 1" start under
# QUESTION_START_RE_STRICT. Detect this specific shape (4 comma-separated
# "letter-digit" pairs right after the number) and treat it as embedded
# content to skip, not a real question boundary.
_MATCHING_KEY_RE = re.compile(r"^\s*[A-D]-\d+\s*,\s*[A-D]-\d+\s*,\s*[A-D]-\d+\s*,\s*[A-D]-\d+")
# Three option styles seen across subjects/years: parenthesized "(A) ... (B)
# ..." (Maths 2025-26, SocialScience), letter-dot "A. ... B. ..." (Science),
# and close-paren-only "A) ... B) ..." with no opening paren (Maths
# 2024-25, Science 2023-24). All three also show up in lowercase in older
# papers ("(a) ... (b) ...", "a) ... b) ...") — CBSE isn't consistent about
# case across years, so every style regex is case-insensitive; parse_options
# normalizes on the matched marker itself rather than assuming a case.
# A paper uses one style consistently throughout — detect_option_style()
# below picks it once per paper rather than trying to match all three
# simultaneously.
# "\s?" before the closing paren/dot-marker: CBSE's own typesetting is
# inconsistent even within one question list — "C ) rational and distinct"
# (stray space) right next to "A) 1" (no space) in the same MCQ.
OPTION_LINE_RE_PAREN = re.compile(r"\(\s?[A-D]\s?\)(?!:)", re.IGNORECASE)
OPTION_LINE_RE_DOT = re.compile(r"(?m)^\s*[A-D]\.\s+", re.IGNORECASE)
# NOT line-anchored (unlike DOT): MathsStandard 2024-25 packs all 4 options
# on a single line ("A) - 6,0   B) 4, 6   C) - 30,-20   D) - 6,6"), so a
# ^-anchored pattern only ever catches the first ("A)") of the four and
# undercounts this style so badly that detect_option_style picks "paren"
# instead (matching only the paper's much rarer genuine parenthesized text,
# e.g. Assertion-Reason options) — same shape as PAREN, just without the
# opening paren. Excludes a preceding "(" (negative lookbehind) so a genuine
# "(A)" (PAREN style) doesn't also count as a CLOSE-style match on its own
# "A)" tail — without that guard, CLOSE's count could rival or beat PAREN's
# on a paren-style paper and get wrongly chosen, splitting on just the "A)"
# half and leaving the stray "(" stuck onto the wrong option.
OPTION_LINE_RE_CLOSE = re.compile(r"(?<!\()(?<!\(\s)[A-D]\s?\)(?!:)", re.IGNORECASE)
TRAILING_MARKS_RE = re.compile(r"(?m)^\s*(\d{1,2})\s*$")
# \b for the same "cross-sectional area" reason as SECTION_RE above.
PAPER_START_RE = re.compile(r"\(?\bSection\b\s*[–-]?\s*A\b\)?", re.IGNORECASE)


def extract_pages(pdf_path: Path) -> list[str]:
    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def strip_page_furniture(text: str) -> str:
    """Remove page-number footers/headers and the repeated assessment-scheme note."""
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text)
    text = re.sub(
        r"\*Please note that the assessment scheme.*?2025-26", "", text, flags=re.DOTALL
    )
    # Option markers that sit right next to a math expression (e.g. the "A)"
    # opening an option list whose text starts with a stacked fraction) are
    # sometimes typeset in a math italic font — the PDF text layer then
    # extracts as MATHEMATICAL ITALIC CAPITAL A (U+1D434) rather than plain
    # ASCII "A", which every option-marker regex in this file only matches
    # in its ASCII form. NFKD decomposes the whole Mathematical Alphanumeric
    # Symbols block (italic/bold/script letters, digits, etc.) back to their
    # plain ASCII base letters, so option markers match regardless of which
    # font CBSE happened to use around them.
    text = unicodedata.normalize("NFKD", text)
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
    r"(?:select|choose|selecting)(?:ing)?\s+the\s+(?:correct|appropriate)\s+option"
    r"|codes?\s+(?:given|provided)\s+below",
    re.IGNORECASE,
)
ASSERTION_REASON_OPTIONS = [
    "Both assertion (A) and reason (R) are true and reason (R) is the correct explanation of assertion (A)",
    "Both assertion (A) and reason (R) are true but reason (R) is not the correct explanation of assertion (A)",
    "Assertion (A) is true but reason (R) is false",
    "Assertion (A) is false but reason (R) is true",
]
# "Section B consists of 5 questions of 2 marks each" (Maths/Science) is one
# phrasing; SocialScience uses several others across years ("Section B –
# Question no. 21 to 24 ... carrying 2 marks each", "Section-E - Questions no
# from 34 to 36 ... are of 4 marks each", "Section F – ... carrying 5 marks
# with two parts"). All of them eventually say "carrying|of <N> marks" not
# too far after the section letter — matching that generic tail (instead of
# requiring the specific "consists of ... each" wording) covers every
# phrasing seen so far. Non-greedy: for "consists of 5 questions of 2 marks
# each" this still lands on the *second* "of" (whose immediate next tokens
# are digit+marks) because the first "of 5 questions" doesn't satisfy
# \s+(\d+)\s*marks?\b (next word is "questions", not "marks") and the regex
# engine keeps trying later positions until one does.
# Also accepts a parenthetical "(04 marks each)" trigger (Maths 2023-24's
# Section E: "...case based integrated units of assessment (04 marks each)
# with sub-parts..." — the number isn't preceded by "carrying"/"of" at all,
# it's set off in parens right after "assessment"). Matters for *which*
# occurrence wins, not just whether one is found: without this alternative,
# the non-greedy scan skips past the real "(04 marks each)" (neither
# trigger word sits directly before it) and matches a LATER, unrelated "of
# 5 marks" inside the next instruction's "...internal choice in 2 Qs of 5
# marks..." sentence instead, silently mis-tagging every Section E question
# as 5-mark long_answer instead of 4-mark case_study.
# "each" is mandatory, not just "marks": SocialScience 2025-26 uses Section
# A-D for SUBJECT AREAS (History/Geography/PoliticalScience/Economics), not
# mark tiers, and never states a blanket per-question mark value for a whole
# section — but it does mention a specific map-based sub-question's split
# ("...Q9. In Section A-History (2 marks) and Q19. In Section B -Geography
# (3 marks)"), which the parenthetical trigger above would otherwise latch
# onto as if it meant "every Section A question is 2 marks." Every genuine
# blanket-marks declaration seen across every paper's phrasing so far
# ("carrying 2 marks each", "of 4 marks each", "(04 marks each)") includes
# "each"; this one-off aside about a single question's sub-parts doesn't.
SECTION_MARKS_RE = re.compile(
    r"\bSection\b[\s-]*([A-F])\b[\s\S]{0,250}?(?:carrying|of|\()\s*(\d+)\s*marks?\s*each\b",
    re.IGNORECASE,
)


def parse_section_marks(full_text: str) -> dict[str, int]:
    """Read authoritative per-section marks from the paper's own section-intro
    lines — far more reliable than inferring marks from scattered trailing
    numbers per question, which get scrambled by PDF layout quirks on
    multi-part (case-study) questions.

    Caps at 5: some papers never state per-question marks next to the
    section letter at all — SocialScience 2025-26 only labels marks by
    question TYPE ("VSA carry 2 marks each"), and separately states each
    section's *aggregate* total ("Each Section is of 20 Marks") which the
    generic "of/carrying <N> marks" trigger below also matches structurally.
    No single CBSE Class X question is ever worth more than 5 marks, so a
    captured value above that is always this aggregate-total false match,
    not a real per-question figure — skip it and let that section fall back
    to the (correct, for a paper shaped like this) per-block trailing-marks
    detection instead."""
    return {
        m.group(1).upper(): int(m.group(2))
        for m in SECTION_MARKS_RE.finditer(full_text)
        if int(m.group(2)) <= 5
    }


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
    """A paper uses one option style consistently: parenthesized "(A)/(a) ...
    (B)/(b) ...", letter-dot "A./a. ... B./b. ...", or close-paren-only
    "A)/a) ... B)/b) ...". Pick whichever has the most matches paper-wide
    rather than trying to match all three per-question."""
    counts = {
        "paren": len(OPTION_LINE_RE_PAREN.findall(full_text)),
        "dot": len(OPTION_LINE_RE_DOT.findall(full_text)),
        "close": len(OPTION_LINE_RE_CLOSE.findall(full_text)),
    }
    return max(counts, key=counts.get)


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
    if style == "dot":
        marker_re = r"(?m)(^\s*[A-D]\.\s+)"
        label_re = r"\s*[A-D]\.\s+"
    elif style == "close":
        # Not line-anchored (see OPTION_LINE_RE_CLOSE) — options can share a
        # single line, so split on the marker wherever it occurs, same as
        # the "paren" branch below.
        marker_re = r"((?<!\()(?<!\(\s)[A-D]\s?\)(?!:))"
        label_re = r"[A-D]\s?\)"
    else:
        marker_re = r"(\(\s?[A-D]\s?\)(?!:))"
        label_re = r"\(\s?[A-D]\s?\)"
    parts = re.split(marker_re, block, flags=re.IGNORECASE)
    options: list[str] = []
    current_label = None
    for part in parts:
        if re.fullmatch(label_re, part, flags=re.IGNORECASE):
            current_label = part
        elif current_label:
            options.append(_join_wrapped_option(part))
            current_label = None
    return [o for o in options if o]


def _score_regex_from(full_text: str, question_re: "re.Pattern", start_offset: int) -> int:
    """Length of the longest strictly-sequential 1,2,3,... run of question
    numbers this regex finds from a given offset — the shared scoring
    function both paper-start selection and question-regex selection use."""
    window = full_text[start_offset:]
    starts = list(question_re.finditer(window))
    expected = 1
    score = 0
    for m in starts:
        if _MATCHING_KEY_RE.match(window[m.end():m.end() + 40]):
            continue
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
    for question_re in (QUESTION_START_RE_STRICT, QUESTION_START_RE_BARE, QUESTION_START_RE_UNIFIED):
        for cand in candidates:
            score = _score_regex_from(full_text, question_re, cand)
            if score > best_score:
                best_regex, best_start, best_score = question_re, cand, score
    return best_regex, best_start


# Matches "(A)"/"(a)", "A."/"a.", and "A)"/"a)" marker styles — same
# case/punctuation variance as the main option styles above.
_AR_OPTION_LINE_RE = re.compile(r"^\s*(?:\([A-D]\)|[A-D][.)])\s*", re.IGNORECASE)


def _scan_ar_option_lines(text: str, question_start_re: "re.Pattern", limit: int = 800) -> list[str]:
    """Shared line-anchored scan for 4 marker-led A-R option lines, used both
    paper-wide (from a shared preamble match) and per-question (within a
    single already-isolated A-R block). Line-anchored on purpose, unlike
    parse_options(): each option's own prose re-mentions "assertion (A)" /
    "reason (R)" inline (e.g. "Both assertion (A) and reason (R) are
    true..."), which parse_options()'s anywhere-in-text marker matching
    mistakes for additional option boundaries. The real markers only ever
    start a line here, so split on line-start markers and fold wrapped
    continuation lines into the option that precedes them."""
    options: list[str] = []
    current = None
    for line in text[:limit].split("\n"):
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
    return [o for o in options if o]


def extract_assertion_reason_options(full_text: str, question_start_re: "re.Pattern") -> list[str]:
    """The 4 interpretive Assertion-Reason choices are printed once per paper
    (not per question) in most papers, with wording that varies by subject
    ("select the correct option" for Maths, "selecting the appropriate
    option given below" for Science, etc). Extract the actual 4 option
    strings from wherever that preamble appears in this paper rather than
    assuming one fixed wording — falls back to the Maths wording only if
    nothing is found (should not happen for a paper that actually has A-R
    questions and doesn't print its options per-question — see
    extract_ar_options_from_block for that case)."""
    m = ASSERTION_REASON_PREAMBLE_RE.search(full_text)
    if not m:
        return list(ASSERTION_REASON_OPTIONS)
    options = _scan_ar_option_lines(full_text[m.end():], question_start_re)
    return options[:4] if len(options) >= 4 else list(ASSERTION_REASON_OPTIONS)


def extract_ar_options_from_block(block: str, question_start_re: "re.Pattern") -> list[str] | None:
    """Some papers (e.g. SocialScience 2023-24) print the 4 interpretive A-R
    choices inline under each individual Assertion-Reason question instead
    of once for the whole paper — and the wording can even vary slightly
    between two such questions in the same paper (a real difference seen in
    that 2023-24 paper, not a parsing bug). This question's own block is the
    most locally-accurate source when present, so try it first; callers fall
    back to the paper-wide extract_assertion_reason_options() result when
    this returns None (the common case — options usually aren't repeated
    per-question)."""
    options = _scan_ar_option_lines(block, question_start_re)
    return options[:4] if len(options) >= 4 else None


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

    starts = [
        m for m in question_start_re.finditer(full_text)
        if not _MATCHING_KEY_RE.match(full_text[m.end():m.end() + 40])
    ]
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
            # Don't cut if doing so would remove this question's OWN labeled
            # Assertion statement, not just a trailing shared preamble.
            # Usually the shared preamble sits in the *gap* before an AR
            # question even starts (so it trails the *previous*, non-AR
            # question's block and is safe to strip there) — but some papers
            # (Maths 2023-24) print a "DIRECTION: ... Choose the correct
            # option" note as literally the first line of the AR question
            # itself, followed by its own "Statement A (Assertion): ..." /
            # "Assertion (A): ..." a few lines later, still inside the part
            # we'd be cutting off.
            # The check must be tight: "(?:Assertion|A)\)\s*:" — a colon
            # immediately after a closing "(A)"/"(Assertion)" label, nothing
            # looser. An earlier, looser version ("colon within 15 chars of
            # the word Assertion") false-positived on ordinary preamble
            # bleed-over text like "...Choose the correct option:\n(A) Both
            # assertion (A) and reason (R)..." — the colon after "option"
            # sits well within 15 chars of "assertion" a few words later,
            # wrongly keeping preamble+options attached to the *previous*,
            # genuinely non-AR question and misclassifying it as AR.
            removed = block[cut_at:]
            if not re.search(r"\((?:A|Assertion)\)\s*:", removed, re.IGNORECASE):
                block = block[:cut_at]

        # Section markers can appear inside the gap before this question.
        # Normally that gap is just starts[i-1].end() (the immediately
        # preceding regex match) to here, same as always. Q1 specifically
        # gets the widest possible window instead (from the very start of
        # the paper) — a paper whose General Instructions number each
        # section's own description ("3. Section B would have...", ...,
        # "6. Section E would have...") produces REJECTED matches there too
        # (they fail the sequential check), and if one of those sits right
        # before Q1, starts[i-1].end() would narrow the window down to
        # exclude the real "SECTION A" header, wrongly tagging Q1 (and
        # everything after, since current_section only changes on a new
        # match) as whatever *later* section the rejected match happened to
        # mention. Only Q1 needs this: it's the sole question whose
        # "preceding" text is General Instructions prose rather than another
        # question's own (much shorter, safe) trailing content.
        if q_num == 1:
            # Widest possible window, and take the LAST ("closest to Q1")
            # match rather than the first: General Instructions can walk
            # through every section in order ("...Section B... Section
            # C..."), so the first mention overall is rarely the real header
            # immediately above Q1.
            sec_matches = list(SECTION_RE.finditer(full_text[0:m.start()]))
            if sec_matches:
                current_section = sec_matches[-1].group(1).upper()
        else:
            preceding = full_text[starts[i - 1].end():m.start()]
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
        option_marker_re = {
            "dot": OPTION_LINE_RE_DOT, "close": OPTION_LINE_RE_CLOSE, "paren": OPTION_LINE_RE_PAREN,
        }[option_style]
        has_options = marks == 1 and bool(option_marker_re.search(block))
        options = parse_options(block, option_style) if has_options else []

        # Question text = block with option lines and trailing bare numbers removed.
        text = block
        if has_options:
            split_re = {
                "dot": r"(?m)^\s*[A-D]\.\s+",
                "close": r"(?<!\()(?<!\(\s)[A-D]\s?\)(?!:)",
                "paren": r"\(\s?[A-D]\s?\)(?!:)",
            }[option_style]
            text = re.split(split_re, text, maxsplit=1, flags=re.IGNORECASE)[0]
        text = TRAILING_MARKS_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()

        q_type = infer_type_and_marks(marks, has_options, block)
        if q_type == "assertion_reason":
            options = extract_ar_options_from_block(block, question_start_re) or list(ar_options)
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
        # If this paper already exists and is "active" (fully answered),
        # a re-run (e.g. to patch one question) must not downgrade its
        # status back to pending_answers and hide it from students again.
        already_active = (
            db.table("board_sample_papers")
            .select("status")
            .eq("board", BOARD).eq("academic_year", args.academic_year)
            .eq("grade", args.grade).eq("source_subject_code", args.source_subject_code)
            .execute()
        )
        preserve_status = (
            already_active.data[0]["status"]
            if already_active.data and already_active.data[0]["status"] == "active"
            else "pending_answers"
        )
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
                "status": preserve_status,
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
