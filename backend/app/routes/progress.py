from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.progress_service import (
    get_chapter_progress,
    save_chapter_progress,
    get_user_progress,
)

router = APIRouter()


class ChapterProgressRequest(BaseModel):
    username: str
    grade: str
    mode: str
    subject: str
    chapter: str


class SaveProgressRequest(BaseModel):
    username: str
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
def read_chapter_progress(data: ChapterProgressRequest):
    return {
        "success": True,
        "progress": get_chapter_progress(
            data.username,
            data.grade,
            data.mode,
            data.subject,
            data.chapter,
        ),
    }


@router.post("/save")
def save_progress(data: SaveProgressRequest):
    saved = save_chapter_progress(data.model_dump())

    return {
        "success": True,
        "progress": saved,
    }


@router.get("/user/{username}")
def user_progress(username: str):
    return {
        "success": True,
        "progress": get_user_progress(username),
    }