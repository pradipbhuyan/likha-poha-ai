from fastapi import APIRouter
from pydantic import BaseModel

from app.services.profile_service import (
    get_student_profile,
    update_student_activity,
)

router = APIRouter()


class ActivityRequest(BaseModel):
    username: str
    activity_type: str


@router.get("/{username}")
def get_profile(username: str):
    """Return gamified profile/progress summary for one student username."""
    return {
        "success": True,
        "profile": get_student_profile(username),
    }


@router.post("/activity")
def log_activity(data: ActivityRequest):
    """Record one student activity and return the updated profile summary."""
    return {
        "success": True,
        "profile": update_student_activity(
            username=data.username,
            activity_type=data.activity_type,
        ),
    }
