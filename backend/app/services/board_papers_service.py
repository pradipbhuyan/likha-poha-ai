"""
Board Sample Papers service — CBSE official sample question papers.

Bank-only serving, same philosophy as Mock Test: everything queried here was
written by the extract_cbse_sample_paper.py / import_cbse_sample_paper_answers.py
scripts ahead of time (with a human-reviewed GPT-5 round trip for answers).
No LLM call ever happens on the read path.

Access tier: free-tier accounts see the single most recent academic year and
one subject only (a taste of the feature); paid accounts and
akshita.teststudent see everything. Enforced here (not just hidden in the
UI) so a free-tier user can't bypass the gate by calling the API directly
with a different year/subject.
"""
import threading
import time as _time_module

from app.services.auth_service import admin_client
from app.services.grade_db_router import get_content_db
from app.services.offer_access_service import is_free_tier_user
from app.services.test_account_service import is_all_access_test_user

BOARD = "CBSE"


def is_full_access(profile: dict, user_id: str) -> bool:
    """True if this account should see every year/subject, not just the
    free-tier preview (admin, paid CBSE access, or the all-access test
    account)."""
    if not profile:
        return False
    if profile.get("role") == "admin" or is_all_access_test_user(profile):
        return True
    if is_free_tier_user(user_id, profile=profile):
        return False
    return bool(profile.get("access_cbse"))


def free_tier_year(grade: str, years: list[str] | None = None) -> str | None:
    """The single academic year a free-tier account may see: the most recent
    one. Pass `years` when the caller already has the list (e.g. `/years`
    just fetched it) to skip a redundant identical query."""
    if years is None:
        years = list_years(grade)
    return years[0] if years else None


# Grade 11/12 stream -> the one subject a free-tier student from that stream
# actually cares about (mirrors STREAM_SUBJECTS in routes/auth.py). Picking
# the alphabetically-first subject regardless of stream meant a PCB student
# was shown Accountancy — not relevant to their exams at all.
_STREAM_PREFERRED_SUBJECT = {
    "PCM": "Physics",
    "PCB": "Physics",
    "PCMB": "Physics",
    "Commerce": "Accountancy",
    "Humanities": "English",
}


def free_tier_subject(
    grade: str, academic_year: str, subjects: list[str] | None = None, stream: str | None = None,
) -> str | None:
    """The single subject a free-tier account may see for that year.

    Prefers the subject relevant to the student's Grade 11/12 stream (see
    _STREAM_PREFERRED_SUBJECT); falls back to alphabetically-first when no
    stream is set (Grade 10 has none) or the preferred subject isn't offered
    for that year. Pass `subjects` when the caller already has the list to
    skip a redundant identical query.
    """
    if subjects is None:
        subjects = list_subjects(grade, academic_year)
    if not subjects:
        return None
    preferred = _STREAM_PREFERRED_SUBJECT.get((stream or "").strip())
    if preferred and preferred in subjects:
        return preferred
    return subjects[0]


# ── Bank-content cache (years/subjects only) ────────────────────────────────
# board_sample_papers is written ahead of time by the offline extract/import
# scripts (see module docstring) — nothing here changes mid-request the way
# a profile's entitlements can, so a short TTL is safe and cuts the fan-out
# of duplicate `board_sample_papers` queries the Board Papers page produces:
# it fires one /years + one /subjects call per visible year, all landing
# within the same second or two, each of which re-runs the same query for
# the same grade. Deliberately NOT caching anything from `profiles` (see
# auth_service.py) — this cache only ever holds bank content.
_CONTENT_CACHE_TTL_SECONDS = 30
_content_cache: dict[tuple, tuple[float, object]] = {}
_content_cache_lock = threading.Lock()


def _cache_get(key: tuple):
    now = _time_module.monotonic()
    with _content_cache_lock:
        entry = _content_cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            _content_cache.pop(key, None)
            return None
        return value


def _cache_put(key: tuple, value) -> None:
    with _content_cache_lock:
        _content_cache[key] = (_time_module.monotonic() + _CONTENT_CACHE_TTL_SECONDS, value)


def list_papers(grade: str, subject: str | None = None, academic_year: str | None = None) -> list[dict]:
    db = get_content_db(grade)
    query = (
        db.table("board_sample_papers")
        .select("id, board, academic_year, grade, subject, subject_variant, "
                "question_paper_url, marking_scheme_url, source_page_url, status")
        .eq("board", BOARD)
        .eq("grade", grade)
        .eq("status", "active")
    )
    if subject:
        query = query.eq("subject", subject)
    if academic_year:
        query = query.eq("academic_year", academic_year)
    result = query.order("academic_year", desc=True).order("subject").execute()
    return result.data or []


def list_overview(grade: str) -> list[dict]:
    """Every active paper for this grade, grouped by year, in a single query.

    The Board Papers timeline used to call /years then /subjects + /list once
    per visible year (20+ requests on one page load) — any one of those
    requests silently failing (network blip, auth race, etc.) left that
    year's row stuck on "Loading…" forever, since nothing retried and the
    frontend swallowed the error. One query for the whole grade removes that
    failure surface entirely: either the whole page loads or the whole page
    errors, nothing to get stuck mid-way.
    """
    cache_key = ("overview", grade)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("id, board, academic_year, grade, subject, subject_variant, "
                "question_paper_url, marking_scheme_url, source_page_url, status")
        .eq("board", BOARD).eq("grade", grade).eq("status", "active")
        .execute()
    )
    by_year: dict[str, list[dict]] = {}
    for row in (result.data or []):
        by_year.setdefault(row["academic_year"], []).append(row)
    for papers in by_year.values():
        papers.sort(key=lambda p: p["subject"])
    overview = [{"year": y, "papers": by_year[y]} for y in sorted(by_year, reverse=True)]
    _cache_put(cache_key, overview)
    return overview


def list_years(grade: str) -> list[str]:
    cache_key = ("years", grade)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("academic_year")
        .eq("board", BOARD).eq("grade", grade).eq("status", "active")
        .execute()
    )
    years = sorted({row["academic_year"] for row in (result.data or [])}, reverse=True)
    _cache_put(cache_key, years)
    return years


def list_subjects(grade: str, academic_year: str) -> list[str]:
    cache_key = ("subjects", grade, academic_year)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("subject")
        .eq("board", BOARD).eq("grade", grade).eq("academic_year", academic_year).eq("status", "active")
        .execute()
    )
    subjects = sorted({row["subject"] for row in (result.data or [])})
    _cache_put(cache_key, subjects)
    return subjects


def get_paper(grade: str, paper_id: str) -> dict | None:
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("id, board, academic_year, grade, subject, subject_variant, "
                "question_paper_url, marking_scheme_url, source_page_url, status")
        .eq("id", paper_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_paper_questions(grade: str, paper_id: str) -> list[dict]:
    db = get_content_db(grade)
    result = (
        db.table("board_sample_paper_questions")
        .select("id, question_number, section, question_type, marks, question_text, "
                "options, diagram_dependent, answer_text, answer_explanation, status")
        .eq("paper_id", paper_id)
        .execute()
    )
    rows = result.data or []
    # question_number is stored as text so it sorts correctly numerically, not
    # lexically. English papers use a compound "N.ROMAN" form (e.g. "3.VII")
    # for nested passage sub-parts — sort by the top-level number first, then
    # by the roman-numeral sub-part's value.
    rows.sort(key=lambda r: _question_number_sort_key(r["question_number"]))
    return rows


_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}

# Devanagari consonants in traditional varnamala order — Hindi papers label
# nested passage sub-parts "(क)", "(ख)", "(ग)"... the same way English labels
# them with roman numerals.
_DEVANAGARI_ORDER = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
_DEVANAGARI_VALUES = {ch: i + 1 for i, ch in enumerate(_DEVANAGARI_ORDER)}


def _roman_to_int(roman: str) -> int:
    total = 0
    for i, ch in enumerate(roman):
        value = _ROMAN_VALUES.get(ch, 0)
        if i + 1 < len(roman) and value < _ROMAN_VALUES.get(roman[i + 1], 0):
            total -= value
        else:
            total += value
    return total


def _subpart_to_int(part: str) -> int:
    """A nested sub-part label is either a roman numeral (English papers) or
    a Devanagari letter (Hindi papers) — try roman first (only I/V/X
    characters), fall back to the Devanagari lookup."""
    if part and all(ch in _ROMAN_VALUES for ch in part):
        return _roman_to_int(part)
    if part in _DEVANAGARI_VALUES:
        return _DEVANAGARI_VALUES[part]
    return 0


def _question_number_sort_key(question_number) -> tuple:
    """Handles plain integers ("12"), nested sub-parts — roman for English
    ("3.VII"), Devanagari letters for Hindi ("1.क") — and literature extract
    OR-choices with their own sub-parts ("6.A.III"), sorted as (top-level,
    extract letter or '', sub-part value)."""
    text = str(question_number)
    if text.isdigit():
        return (int(text), "", 0)
    parts = text.split(".")
    if len(parts) == 2 and parts[0].isdigit():
        return (int(parts[0]), "", _subpart_to_int(parts[1]))
    if len(parts) == 3 and parts[0].isdigit():
        return (int(parts[0]), parts[1], _subpart_to_int(parts[2]))
    return (0, "", 0)


# ── Timed Test attempts ─────────────────────────────────────────────────────
# Unlike papers/questions above (grade-routed via get_content_db), attempt
# history is user-owned data and is centralized on the PRIMARY Supabase
# project only, same convention as test_history_service.py — a student's
# attempt history must not be split across two Supabase projects even though
# the paper itself may live on the Grade 11/12 project. Always use
# admin_client (primary project, service role) here, never get_content_db.

def save_attempt(username: str, paper: dict, payload: dict) -> dict:
    """Persist one Timed Test attempt. Scoring in `payload` was computed
    client-side (MCQ auto-graded, subjective self-marked) — this just
    denormalizes paper metadata and stores the result, no validation."""
    row = {
        "username": username,
        "paper_id": paper.get("id"),
        "grade": payload.get("grade") or paper.get("grade"),
        "board": paper.get("board") or BOARD,
        "academic_year": paper.get("academic_year"),
        "subject": paper.get("subject"),
        "subject_variant": paper.get("subject_variant") or "",
        "started_at": payload.get("started_at"),
        "time_taken_seconds": payload.get("time_taken_seconds"),
        "mcq_score": payload.get("mcq_score") or 0,
        "mcq_max_score": payload.get("mcq_max_score") or 0,
        "subjective_self_marked_correct": payload.get("subjective_self_marked_correct") or 0,
        "subjective_max_score": payload.get("subjective_max_score") or 0,
        "answers": payload.get("answers") or {},
    }
    response = admin_client.table("board_paper_attempts").insert(row).execute()
    return response.data[0] if response.data else row


def list_attempts(username: str, paper_id: str) -> list[dict]:
    """Return this user's past Timed Test attempts for one paper, most
    recent first."""
    response = (
        admin_client.table("board_paper_attempts")
        .select("*")
        .eq("username", username)
        .eq("paper_id", paper_id)
        .order("submitted_at", desc=True)
        .execute()
    )
    return response.data or []
