from fastapi import APIRouter
from pydantic import BaseModel

from app.services.supabase_client import supabase

router = APIRouter()


class WeakAreaAlertRequest(BaseModel):
    username: str
    grade: str
    mode: str
    subject: str
    chapter: str
    step_title: str
    step_index: int
    attempts: int = 0
    best_score: float = 0


@router.post("/save")
def save_weak_area_alert(data: WeakAreaAlertRequest):
    payload = {
        "username": data.username,
        "grade": data.grade,
        "mode": data.mode,
        "subject": data.subject,
        "chapter": data.chapter,
        "step_title": data.step_title,
        "step_index": data.step_index,
        "attempts": data.attempts,
        "best_score": data.best_score,
        "status": "needs_revision",
    }

    response = (
        supabase
        .table("weak_area_alerts")
        .insert(payload)
        .execute()
    )

    return {
        "success": True,
        "alert": response.data[0] if response.data else payload,
    }