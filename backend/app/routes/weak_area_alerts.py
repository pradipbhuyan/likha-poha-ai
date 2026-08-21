from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import (
    admin_client as supabase,  # uses service_role to bypass RLS
    get_current_user,
    get_user_profile,
)

router = APIRouter()


class WeakAreaAlertRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str
    step_title: str
    step_index: int
    attempts: int = 0
    best_score: float = 0


@router.post("/save")
def save_weak_area_alert(data: WeakAreaAlertRequest, user=Depends(get_current_user)):
    """
    Record a weak-area alert when practice attempts show revision is needed.

    username is derived from the authenticated session, never taken from the
    request body — this endpoint previously trusted a client-supplied
    username with no auth check at all, letting any caller spoof weak-area
    records for any student account.
    """
    profile = get_user_profile(user.id)
    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found")

    payload = {
        "profile_id": profile.get("id"),
        "username": profile.get("username"),
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
