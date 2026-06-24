from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from app.services.test_history_service import (
    save_test_result,
    get_user_history,
    get_leaderboard,
    clear_test_history,
    clear_user_test_history,
)
from app.services.auth_service import admin_client as supabase


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


class WrongAnswerItem(BaseModel):
    question_id: int | str
    question: str
    selected: str | None = None
    correct: str
    options: dict | None = None
    explanation: str | None = None
    section: str | None = None
    marks: float | None = 1


class SaveWrongAnswersRequest(BaseModel):
    username: str
    grade: str
    mode: str
    subject: str
    chapter: str
    wrong_answers: List[WrongAnswerItem]


@router.post("/test-history")
def save_history(data: SaveTestResultRequest):
    """Save one submitted mock-test result for analytics and leaderboard views."""
    saved = save_test_result(data.model_dump())
    return {
        "success": True,
        "result": saved
    }


@router.get("/test-history/{username}")
def user_history(username: str):
    """Return saved test-history records for one student."""
    return {
        "success": True,
        "history": get_user_history(username)
    }


@router.get("/leaderboard")
def leaderboard():
    """Return ranked students based on stored test-history performance."""
    return {
        "success": True,
        "leaderboard": get_leaderboard()
    }


@router.delete("/test-history/user/{username}")
def clear_user_history(username: str):
    """Delete test-history records for one student username."""
    clear_user_test_history(username)
    return {
        "success": True,
        "message": f"History cleared for {username}"
    }


@router.delete("/test-history")
def clear_all_history():
    """Delete all locally stored test-history records."""
    clear_test_history()
    return {
        "success": True,
        "message": "All history cleared"
    }


@router.post("/wrong-answers")
def save_wrong_answers(data: SaveWrongAnswersRequest):
    """
    Persist per-question wrong answers from a submitted mock test.
    Each wrong answer row records subject, chapter, the question, and the
    correct answer + explanation so students can study them before a retest.
    """
    if not data.wrong_answers:
        return {"success": True, "saved": 0}

    rows = [
        {
            "username": data.username,
            "grade": data.grade,
            "mode": data.mode,
            "subject": data.subject,
            "chapter": data.chapter,
            "question_id": str(item.question_id),
            "question": item.question[:1000],
            "selected_answer": item.selected,
            "correct_answer": item.correct,
            "options": item.options,
            "explanation": (item.explanation or "")[:2000],
            "section": item.section,
            "marks": item.marks,
        }
        for item in data.wrong_answers
    ]

    try:
        supabase.table("mock_test_wrong_answers").insert(rows).execute()
        return {"success": True, "saved": len(rows)}
    except Exception as exc:
        # Non-fatal — test was already saved; wrong-answer tracking is best-effort
        return {"success": False, "error": str(exc), "saved": 0}


@router.get("/wrong-answers/{username}")
def get_wrong_answers_for_chapter(
    username: str,
    subject: str | None = None,
    chapter: str | None = None,
    limit: int = 50,
):
    """
    Return the stored wrong-answer rows for one student, optionally filtered by
    subject and chapter. Used by the Dashboard expandable review card to show
    per-question mistakes with explanations.
    """
    try:
        query = (
            supabase
            .table("mock_test_wrong_answers")
            .select("id, subject, chapter, grade, mode, question, correct_answer, selected_answer, options, explanation, created_at")
            .eq("username", username)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if subject:
            query = query.eq("subject", subject)
        if chapter:
            query = query.eq("chapter", chapter)
        resp = query.execute()
        return {"success": True, "wrong_answers": resp.data or []}
    except Exception as exc:
        return {"success": False, "error": str(exc), "wrong_answers": []}


@router.get("/weak-chapters/{username}")
def get_weak_chapters(username: str, limit: int = 10):
    """
    Return the chapters where the student has the most cumulative wrong answers,
    ordered by error count descending. Used by the Dashboard retest reminder widget.
    """
    try:
        resp = (
            supabase
            .table("mock_test_wrong_answers")
            .select("grade, mode, subject, chapter")
            .eq("username", username)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        return {"success": False, "error": str(exc), "weak_chapters": []}

    # Aggregate error counts by (grade, mode, subject, chapter)
    counts: dict = {}
    for row in rows:
        key = (row["grade"], row["mode"], row["subject"], row["chapter"])
        counts[key] = counts.get(key, 0) + 1

    # Sort by error count descending and return top N
    sorted_chapters = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    weak_chapters = [
        {
            "grade": k[0],
            "mode": k[1],
            "subject": k[2],
            "chapter": k[3],
            "wrong_count": v,
        }
        for k, v in sorted_chapters[:limit]
    ]

    return {"success": True, "weak_chapters": weak_chapters}
