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


class JoinSchoolRequest(BaseModel):
    school_code: str


@router.post("/join-school")
def join_school(data: JoinSchoolRequest, user=Depends(get_current_user)):
    """
    Self-serve, opt-in link to a school by its join code — for a student,
    parent, or teacher who wants their principal to see them on the school
    roster (e.g. for school-level incentive tracking).

    Deliberately NOT part of signup, login, or OAuth completion — this is a
    new optional action a signed-in user takes from their own account
    settings, on their own schedule. It only ever sets profiles.school_id;
    it never touches role, subscription plan, password, or any other part
    of the account, so it cannot change what the caller can already do.
    """
    code_clean = (data.school_code or "").strip().upper()
    if not code_clean:
        return {"success": False, "error": "School code is required."}

    school_resp = (
        _sb.table("schools")
        .select("id, name, status")
        .eq("school_code", code_clean)
        .limit(1)
        .execute()
    )
    school = (school_resp.data or [None])[0]
    if not school:
        return {"success": False, "error": "No school found for that code."}
    if school.get("status") == "rejected":
        return {"success": False, "error": "This school code is no longer valid."}

    _sb.table("profiles").update({"school_id": school["id"]}).eq("id", user.id).execute()

    return {
        "success": True,
        "school": {"id": school["id"], "name": school["name"]},
    }


@router.post("/leave-school")
def leave_school(user=Depends(get_current_user)):
    """
    Self-serve: unlink the signed-in user's account from their school.

    Only clears profiles.school_id — the rest of the account (role, plan,
    login, progress) is untouched.
    """
    _sb.table("profiles").update({"school_id": None}).eq("id", user.id).execute()
    return {"success": True}
