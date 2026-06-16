from fastapi import APIRouter
from pydantic import BaseModel

from app.services.auth_service import admin_client as supabase  # uses service_role to bypass RLS

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
    """Record a weak-area alert when practice attempts show revision is needed."""
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
