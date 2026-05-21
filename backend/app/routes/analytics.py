from fastapi import APIRouter
from pydantic import BaseModel

from app.services.test_history_service import (
    save_test_result,
    get_user_history,
    get_leaderboard,
    clear_test_history,
    clear_user_test_history,
)


router = APIRouter()


class SaveTestResultRequest(BaseModel):
    username: str
    grade: str | None = None
    mode: str | None = None
    subject: str
    chapter: str | None = None
    mockType: str | None = None
    examType: str | None = None
    difficulty: str
    rawScore: float | None = None
    finalScore: float
    maxScore: float
    wrongCount: int | None = None
    penalty: float | None = None
    percentage: float
    submittedAt: str | None = None


@router.post("/test-history")
def save_history(data: SaveTestResultRequest):
    saved = save_test_result(data.model_dump())
    return {
        "success": True,
        "result": saved
    }


@router.get("/test-history/{username}")
def user_history(username: str):
    return {
        "success": True,
        "history": get_user_history(username)
    }


@router.get("/leaderboard")
def leaderboard():
    return {
        "success": True,
        "leaderboard": get_leaderboard()
    }


@router.delete("/test-history/user/{username}")
def clear_user_history(username: str):
    clear_user_test_history(username)
    return {
        "success": True,
        "message": f"History cleared for {username}"
    }


@router.delete("/test-history")
def clear_all_history():
    clear_test_history()
    return {
        "success": True,
        "message": "All history cleared"
    }