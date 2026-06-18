"""
academic_guardrail_service.py
─────────────────────────────
Detects non-academic questions and returns a polished redirect message
instead of calling the LLM.

Covers:
  • Current political office-holders (president, PM, CM, governor, minister)
  • Election results and political parties
  • Current affairs / breaking news / "today's" queries
  • Live sports scores, match results, tournament winners
  • Stock market / share prices / crypto
  • Celebrity / entertainment gossip
  • Any question explicitly asking for "current", "latest", or "today"
    in a non-academic context

Academic exceptions are deliberately kept generous — topics that overlap
with the CBSE curriculum (e.g. "who was the first president of India",
"what does a governor do", "explain democracy") pass through freely.
"""

from __future__ import annotations

import re

# ── Redirect message (Option 1) ───────────────────────────────────────────────
NON_ACADEMIC_MESSAGE = (
    "📚 **I'm focused on your studies**\n\n"
    "This question is about current events or politics, which can change "
    "frequently and is outside my area as an academic tutor. I'm here to "
    "help with Science, Maths, English, Social Science, and Hindi for "
    "CBSE Grade 5–10.\n\n"
    "Try asking something from your textbook or homework!"
)

NON_ACADEMIC_SOURCE_TYPE = "ACADEMIC_GUARDRAIL"

# ── Patterns that indicate non-academic / current-affairs questions ───────────

# Phrases that signal a "who currently holds office" question
_CURRENT_OFFICE_PHRASES: list[tuple[re.Pattern, str]] = [
    # "who is the president/pm/cm/chief minister/governor/minister of X"
    (re.compile(
        r"\b(who\s+is\s+(the\s+)?(current\s+)?"
        r"(president|prime\s*minister|pm|chief\s*minister|cm|governor|"
        r"minister|speaker|mayor|ceo|chairman|secretary|chancellor)\b)",
        re.I,
    ), "current office holder"),

    # "who won the (election|vote|poll|match|game|tournament|ipl|world cup)"
    (re.compile(
        r"\b(who\s+(won|won\s+the|is\s+winning|will\s+win)\s+"
        r"(the\s+)?(election|elections|vote|poll|match|game|tournament|"
        r"ipl|world\s*cup|series|championship|trophy|medal|gold))\b",
        re.I,
    ), "election or sports result"),

    # "what is the current government / ruling party / score"
    (re.compile(
        r"\b(current\s+(government|ruling\s+party|score|result|"
        r"pm|president|cm|chief\s*minister|governor|minister|"
        r"stock\s*price|share\s*price|exchange\s*rate))\b",
        re.I,
    ), "current government or score"),

    # "latest news / today's news / breaking news"
    (re.compile(
        r"\b(latest\s+news|today['']?s?\s+news|breaking\s+news|"
        r"recent\s+news|current\s+news|news\s+today)\b",
        re.I,
    ), "news query"),

    # "score of the match / IPL score / match result"
    (re.compile(
        r"\b(score\s+of\s+(the\s+)?match|ipl\s+score|match\s+score|"
        r"cricket\s+score|football\s+score|match\s+result|"
        r"live\s+score|live\s+match)\b",
        re.I,
    ), "live sports score"),

    # "stock price / share price / crypto price"
    (re.compile(
        r"\b(stock\s+(price|market)|share\s+price|nifty|sensex|"
        r"bitcoin\s+price|crypto\s+price|exchange\s+rate|"
        r"dollar\s+rate|usd\s+to\s+inr)\b",
        re.I,
    ), "financial market query"),

    # "who is the richest / most popular person right now"
    (re.compile(
        r"\b(who\s+is\s+(the\s+)?(richest|most\s+popular|most\s+famous|"
        r"most\s+powerful|number\s+one|top\s+ranked)\s+"
        r"(person|celebrity|actor|actress|cricketer|player|politician)"
        r"(\s+in\s+\w+)?\s*(right\s+now|today|currently|now)?)\b",
        re.I,
    ), "celebrity ranking"),
]

# Standalone high-confidence non-academic terms (exact phrase match)
_NON_ACADEMIC_EXACT: frozenset[str] = frozenset([
    "ipl winner",
    "ipl champion",
    "world cup winner",
    "world cup champion",
    "who won ipl",
    "who won world cup",
    "who is winning ipl",
    "election result",
    "election results",
    "who won election",
    "lok sabha result",
    "assembly election",
    "current pm of india",
    "current president of india",
    "current president of usa",
    "current president of america",
    "president of usa",
    "president of america",
    "president of us",
    "pm of india",
    "cm of assam",
    "cm of gujarat",
    "cm of maharashtra",
    "cm of delhi",
    "cm of up",
    "cm of kerala",
    "cm of karnataka",
    "cm of rajasthan",
    "cm of west bengal",
    "who is bjp president",
    "who is congress president",
    "who is the bjp",
    "who is the congress",
    "ruling party",
    "stock market today",
    "nifty today",
    "sensex today",
    "bitcoin price",
    "latest ipl",
    "today's match",
    "today match",
])

# ── Academic ALLOW patterns — override the block list ────────────────────────
# Questions that look political but are firmly CBSE curriculum content.
_ACADEMIC_ALLOW: list[re.Pattern] = [
    # "who was the first president of India" — history, not current affairs
    re.compile(r"\b(first|second|third|last|former|ex[-\s]|previous|"
               r"historic|original|founding)\s+"
               r"(president|prime\s*minister|pm|chief\s*minister|cm|governor|"
               r"minister|speaker|mayor)\b", re.I),

    # "explain the role of the president / prime minister" — civics
    re.compile(r"\b(explain|describe|what\s+does|role\s+of|powers\s+of|"
               r"function\s+of|duties\s+of|responsibilities\s+of)\s+"
               r"(the\s+)?(president|prime\s*minister|governor|"
               r"chief\s*minister|parliament|lok\s*sabha|rajya\s*sabha|"
               r"supreme\s*court|high\s*court)\b", re.I),

    # "what is democracy / federalism / constitution"
    re.compile(r"\b(what\s+is|define|meaning\s+of|explain)\s+"
               r"(democracy|federalism|constitution|parliament|"
               r"fundamental\s+rights|directive\s+principles|"
               r"preamble|citizenship|judicial\s+review|"
               r"separation\s+of\s+powers)\b", re.I),

    # Historical Indian leaders as textbook content
    re.compile(r"\b(gandhi|nehru|ambedkar|sardar\s+patel|subhas\s+chandra\s+bose|"
               r"bhagat\s+singh|chandrashekhar\s+azad|lal\s+bahadur\s+shastri|"
               r"indira\s+gandhi|rajiv\s+gandhi)\b", re.I),

    # Science / sports history (olympics, world records as academic facts)
    re.compile(r"\b(first\s+person\s+to|who\s+invented|who\s+discovered|"
               r"who\s+wrote|who\s+founded|who\s+established|"
               r"who\s+built|who\s+created)\b", re.I),
]


def is_non_academic_question(question: str) -> bool:
    """
    Return True if the question is about current affairs, politics, live
    sports, or other non-academic topics that the CBSE AI tutor should not
    attempt to answer.

    The function first checks academic allow-list patterns (CBSE civics, history,
    science) — these always pass through.  Then it checks the non-academic
    block patterns.
    """
    text = str(question or "").strip()
    if not text:
        return False

    text_lower = text.lower()

    # ── Step 1: Academic allow-list — never block these ──────────────────────
    for allow_pattern in _ACADEMIC_ALLOW:
        if allow_pattern.search(text):
            return False

    # ── Step 2: Exact phrase match ────────────────────────────────────────────
    for phrase in _NON_ACADEMIC_EXACT:
        if phrase in text_lower:
            return True

    # ── Step 3: Regex pattern match ───────────────────────────────────────────
    for pattern, _ in _CURRENT_OFFICE_PHRASES:
        if pattern.search(text):
            return True

    return False


def build_non_academic_response() -> dict:
    """Return the standard academic-guardrail response payload."""
    return {
        "answer": NON_ACADEMIC_MESSAGE,
        "source_type": NON_ACADEMIC_SOURCE_TYPE,
        "sources": [],
        "textbook_visuals": [],
        "mentor_suggestions": [],
    }
