from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.auth_service import (
    get_current_user,
    require_self_by_username,
    resolve_session_username,
)
from app.services.progress_service import (
    get_chapter_progress,
    save_chapter_progress,
    get_user_progress,
)

router = APIRouter()


class ChapterProgressRequest(BaseModel):
    # username is accepted for backward compatibility with older clients but is
    # ignored — the signed-in session is the only source of identity here.
    username: str | None = None
    grade: str
    mode: str
    subject: str
    chapter: str


class SaveProgressRequest(BaseModel):
    username: str | None = None
    grade: str
    mode: str
    subject: str
    chapter: str
    current_step_index: int
    highest_unlocked_step: int = 0
    completed: bool = False
    last_lesson: str = ""
    step_lessons: dict = Field(default_factory=dict)


@router.post("/chapter")
def read_chapter_progress(data: ChapterProgressRequest, user=Depends(get_current_user)):
    """
    Return saved progress for one grade/mode/subject/chapter of the signed-in user.

    The username comes from the session, never the request body — this endpoint
    previously had no auth at all, so any caller could read another student's
    chapter progress by naming them.
    """
    username = resolve_session_username(user)

    return {
        "success": True,
        "progress": get_chapter_progress(
            username,
            data.grade,
            data.mode,
            data.subject,
            data.chapter,
        ),
    }


@router.post("/save")
def save_progress(data: SaveProgressRequest, user=Depends(get_current_user)):
    """
    Persist chapter progress, unlocked lesson step, and generated lesson cache.

    The username comes from the session, never the request body. Untrusted
    writes here were reachable without any credential and surfaced in the
    parent progress report, which reads student_progress by username.
    """
    payload = data.model_dump()
    payload["username"] = resolve_session_username(user)

    saved = save_chapter_progress(payload)

    return {
        "success": True,
        "progress": saved,
    }


@router.get("/user/{username}")
def user_progress(username: str, _auth=Depends(require_self_by_username)):
    """Return all saved chapter progress records for one user (self, or any as admin/teacher)."""
    return {
        "success": True,
        "progress": get_user_progress(username),
    }
