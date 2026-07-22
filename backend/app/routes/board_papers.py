from fastapi import APIRouter, Depends, HTTPException

from app.services.auth_service import get_current_user, admin_client
from app.services.subject_access_service import has_cbse_subject_access
from app.services.test_account_service import is_all_access_test_user
from app.services import board_papers_service

router = APIRouter()

FREE_TIER_MESSAGE = (
    "Free tier includes the most recent year's sample paper for one subject. "
    "Upgrade to unlock every year and subject."
)


def _get_profile(user_id: str) -> dict:
    response = (
        admin_client.table("profiles").select("*").eq("id", user_id).single().execute()
    )
    return response.data or {}


def _exam_grade_for(profile_grade: str) -> str:
    """Board Sample Papers only has content for Grade 10 and Grade 12 (CBSE
    only publishes Class X and XII sample papers) — map every onboarded
    grade to whichever of those two is its upcoming board exam, so a Grade 9
    student previews Grade 10 papers and a Grade 11 student previews Grade
    12, rather than requiring an exact (and impossible) grade match."""
    import re  # noqa: PLC0415
    m = re.search(r"\d+", profile_grade or "")
    num = int(m.group()) if m else 10
    return "Grade 12" if num >= 11 else "Grade 10"


def _enforce_grade(profile: dict, grade: str):
    if not profile or profile.get("role") in ("admin", "parent") or is_all_access_test_user(profile):
        return
    profile_grade = (profile.get("grade") or "").strip()
    allowed_grade = _exam_grade_for(profile_grade) if profile_grade else grade
    if grade != allowed_grade:
        raise HTTPException(
            status_code=403,
            detail=f"Board Sample Papers for {profile_grade} students covers {allowed_grade}.",
        )


def _enforce_custom_subject_list(profile: dict, subject: str | None):
    """Separate from the free-tier year/subject cap below — this is the
    existing custom-low-cost-plan subject list (populated cbse_subjects on
    the profile), same as Mock Test."""
    if not profile or profile.get("role") in ("admin", "parent") or is_all_access_test_user(profile):
        return
    if subject and not has_cbse_subject_access(profile, subject):
        raise HTTPException(status_code=403, detail=f"No access to {subject} on this plan.")


@router.get("/years")
def get_years(grade: str, user=Depends(get_current_user)):
    profile = _get_profile(user.id)
    _enforce_grade(profile, grade)
    years = board_papers_service.list_years(grade)
    full_access = board_papers_service.is_full_access(profile, user.id)
    free_year = None if full_access else board_papers_service.free_tier_year(grade)
    return {
        "success": True,
        "full_access": full_access,
        "years": [{"year": y, "locked": (not full_access) and y != free_year} for y in years],
    }


@router.get("/subjects")
def get_subjects(grade: str, academic_year: str, user=Depends(get_current_user)):
    profile = _get_profile(user.id)
    _enforce_grade(profile, grade)
    subjects = board_papers_service.list_subjects(grade, academic_year)
    full_access = board_papers_service.is_full_access(profile, user.id)

    if full_access:
        return {"success": True, "full_access": True, "subjects": [{"subject": s, "locked": False} for s in subjects]}

    free_year = board_papers_service.free_tier_year(grade)
    if academic_year != free_year:
        # A locked year — every subject in it is locked too.
        return {"success": True, "full_access": False, "subjects": [{"subject": s, "locked": True} for s in subjects]}

    free_subject = board_papers_service.free_tier_subject(grade, academic_year)
    return {
        "success": True,
        "full_access": False,
        "subjects": [{"subject": s, "locked": s != free_subject} for s in subjects],
    }


@router.get("/list")
def get_papers(
    grade: str,
    subject: str | None = None,
    academic_year: str | None = None,
    user=Depends(get_current_user),
):
    profile = _get_profile(user.id)
    _enforce_grade(profile, grade)
    _enforce_custom_subject_list(profile, subject)

    if not board_papers_service.is_full_access(profile, user.id):
        free_year = board_papers_service.free_tier_year(grade)
        if academic_year and academic_year != free_year:
            raise HTTPException(status_code=403, detail=FREE_TIER_MESSAGE)
        academic_year = free_year
        free_subject = board_papers_service.free_tier_subject(grade, free_year) if free_year else None
        if subject and subject != free_subject:
            raise HTTPException(status_code=403, detail=FREE_TIER_MESSAGE)
        subject = free_subject

    papers = board_papers_service.list_papers(grade, subject, academic_year)
    return {"success": True, "papers": papers}


@router.get("/{paper_id}/questions")
def get_paper_questions(paper_id: str, grade: str, user=Depends(get_current_user)):
    profile = _get_profile(user.id)
    paper = board_papers_service.get_paper(grade, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    _enforce_grade(profile, grade)
    _enforce_custom_subject_list(profile, paper.get("subject"))

    if not board_papers_service.is_full_access(profile, user.id):
        free_year = board_papers_service.free_tier_year(grade)
        free_subject = board_papers_service.free_tier_subject(grade, free_year) if free_year else None
        if paper.get("academic_year") != free_year or paper.get("subject") != free_subject:
            raise HTTPException(status_code=403, detail=FREE_TIER_MESSAGE)

    questions = board_papers_service.get_paper_questions(grade, paper_id)
    return {"success": True, "paper": paper, "questions": questions}
