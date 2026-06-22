from fastapi import APIRouter
from pydantic import BaseModel

from app.services.profile_service import (
    get_student_profile,
    update_student_activity,
)

router = APIRouter()

from app.services.auth_service import admin_client as _sb, get_current_user  # noqa: E402
from fastapi import Depends  # noqa: E402


class ActivityRequest(BaseModel):
    username: str
    activity_type: str


class AvatarUpdateRequest(BaseModel):
    avatar: str  # emoji key (e.g. 'boy1') or base64 data: URL


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


@router.post("/update-avatar")
def update_avatar(data: AvatarUpdateRequest, user=Depends(get_current_user)):
    """
    Update the avatar for any authenticated user (student, parent, teacher).
    Accepts an emoji key ('boy1', 'girl2', ...) or a base64 data: URL.
    """
    try:
        _sb.table("profiles").update(
            {"avatar": data.avatar[:400000]}  # cap at ~300KB
        ).eq("id", user.id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
