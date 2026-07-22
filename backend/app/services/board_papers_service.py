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
    if is_free_tier_user(user_id):
        return False
    return bool(profile.get("access_cbse"))


def free_tier_year(grade: str) -> str | None:
    """The single academic year a free-tier account may see: the most recent one."""
    years = list_years(grade)
    return years[0] if years else None


def free_tier_subject(grade: str, academic_year: str) -> str | None:
    """The single subject a free-tier account may see for that year (deterministic —
    alphabetically first of whatever's available)."""
    subjects = list_subjects(grade, academic_year)
    return subjects[0] if subjects else None


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


def list_years(grade: str) -> list[str]:
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("academic_year")
        .eq("board", BOARD).eq("grade", grade).eq("status", "active")
        .execute()
    )
    years = sorted({row["academic_year"] for row in (result.data or [])}, reverse=True)
    return years


def list_subjects(grade: str, academic_year: str) -> list[str]:
    db = get_content_db(grade)
    result = (
        db.table("board_sample_papers")
        .select("subject")
        .eq("board", BOARD).eq("grade", grade).eq("academic_year", academic_year).eq("status", "active")
        .execute()
    )
    subjects = sorted({row["subject"] for row in (result.data or [])})
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
    # question_number is stored as text so it sorts correctly numerically, not lexically.
    rows.sort(key=lambda r: int(r["question_number"]) if str(r["question_number"]).isdigit() else 0)
    return rows
