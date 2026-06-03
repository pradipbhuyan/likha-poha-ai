from copy import deepcopy

from fastapi import APIRouter

from app.data.syllabus import SYLLABUS, LESSON_STEPS
from app.services.supabase_client import supabase

router = APIRouter()


def merge_uploaded_rag_chapters(syllabus):
    """
    Add uploaded RAG document chapters to the static syllabus tree.

    This lets Class 1-10 books become selectable after bulk upload without a code
    change for every new book or chapter. Failures are ignored so syllabus loading
    still works if Supabase is temporarily unavailable.
    """
    merged = deepcopy(syllabus)

    try:
        response = (
            supabase
            .table("rag_documents")
            .select("grade,subject,chapter")
            .execute()
        )
    except Exception:
        return merged

    for document in response.data or []:
        grade = document.get("grade")
        subject = document.get("subject")
        chapter = document.get("chapter")

        if not grade or not subject or not chapter:
            continue

        grade_data = merged.setdefault(grade, {"CBSE": {}})
        mode = "SOF" if "Olympiad" in subject else "CBSE"
        mode_data = grade_data.setdefault(mode, {})
        chapters = mode_data.setdefault(subject, [])

        if chapter not in chapters:
            chapters.append(chapter)

    return merged


@router.get("")
def get_syllabus():
    """Return the Class 1-10 syllabus tree plus uploaded RAG chapter metadata."""
    return {
        "success": True,
        "syllabus": merge_uploaded_rag_chapters(SYLLABUS),
        "lesson_steps": LESSON_STEPS
    }
