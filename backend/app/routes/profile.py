from fastapi import APIRouter
from pydantic import BaseModel

from app.services.profile_service import (
    get_student_profile,
    update_student_activity,
)

router = APIRouter()

from app.services.auth_service import (  # noqa: E402
    admin_client as _sb,
    get_current_user,
    require_self_by_username,
    resolve_session_username,
)
from fastapi import Depends  # noqa: E402


class ActivityRequest(BaseModel):
    # Accepted for backward compatibility but ignored — identity comes from the
    # session, so activity cannot be logged against another student's profile.
    username: str | None = None
    activity_type: str


class AvatarUpdateRequest(BaseModel):
    avatar: str  # emoji key (e.g. 'boy1') or base64 data: URL


@router.get("/{username}")
def get_profile(username: str, _auth=Depends(require_self_by_username)):
    """
    Return the gamified profile/progress summary for one student username.

    Self, or any student when called by an admin/teacher. This was previously
    unauthenticated, leaking a child's streak/points/activity to anyone who
    guessed their username.
    """
    return {
        "success": True,
        "profile": get_student_profile(
            username,
            profile_id=(
                (_auth.get("target_profile") or _auth.get("profile") or {}).get("id")
            ),
        ),
    }


@router.post("/activity")
def log_activity(data: ActivityRequest, user=Depends(get_current_user)):
    """Record one activity for the signed-in user and return the updated profile."""
    return {
        "success": True,
        "profile": update_student_activity(
            username=resolve_session_username(user),
            activity_type=data.activity_type,
            profile_id=user.id,
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
