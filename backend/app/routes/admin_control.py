"""
admin_control.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Core admin overview: family/student listing and student account
administration (access flags, token limits, deletion).

This file used to hold every admin-control feature area (offer codes,
onboarding, AI settings, payment logs, blog collaborators, platform
settings, associations, subscription settings) in one 2,600+ line file.
Those were split out into their own admin_*.py modules — see main.py's
/api/admin-control router registrations for the full list. This file keeps
only the routes/helpers with no other natural home: the family overview
(the original, oldest endpoint here) and student account admin.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.model_routing_service import normalize_model_preference
from app.services.auth_service import require_admin, admin_client
from app.services.board_service import normalize_board
from app.services.subject_access_service import clean_subject_access_list
from app.services.usage_service import normalize_token_limit

router = APIRouter()


class UpdateAccessRequest(BaseModel):
    access_cbse: bool
    cbse_subjects: list[str] = Field(default_factory=list)
    subscription_plan: str = "free"
    account_status: str = "active"
    grade: str = "Grade 9"
    board: str = "CBSE"
    ai_model_preference: str = "default"


class UpdateLimitsRequest(BaseModel):
    daily_token_limit: int = Field(default=0, ge=0)
    monthly_token_limit: int = Field(default=0, ge=0)


def summarize_student_activity(username: str, logs: list[dict]):
    """Summarize raw AI usage logs into the admin child activity card."""
    now = datetime.now(timezone.utc)
    today_start = now.date().isoformat()
    month_start = now.replace(day=1).date().isoformat()

    today_prefix = f"{today_start}T"
    month_prefix = f"{month_start[:7]}-"

    today_logs = [
        item for item in logs
        if str(item.get("created_at", "")).startswith(today_prefix)
    ]

    month_logs = [
        item for item in logs
        if str(item.get("created_at", "")).startswith(month_prefix)
    ]

    def feature_count(feature_name: str):
        """Count how many logged AI requests used one feature name."""
        return len([
            item for item in logs
            if item.get("feature") == feature_name
        ])

    return {
        "username": username,
        "lessons_generated": feature_count("lesson"),
        "doubts_asked": feature_count("doubt"),
        "mock_tests_generated": feature_count("mock_test"),
        "requests_total": len(logs),
        "tokens_today": sum(int(item.get("total_tokens") or 0) for item in today_logs),
        "tokens_this_month": sum(int(item.get("total_tokens") or 0) for item in month_logs),
        "tokens_total": sum(int(item.get("total_tokens") or 0) for item in logs),
        "cost_total": sum(float(item.get("estimated_cost") or 0) for item in logs),
        "last_activity": logs[0].get("created_at") if logs else None,
    }


def build_student_activity(username: str):
    """Load and summarize AI usage for one student username."""
    usage_response = (
        admin_client
        .table("ai_usage_logs")
        .select("*")
        .eq("username", username)
        .execute()
    )

    return summarize_student_activity(username, usage_response.data or [])


def build_activity_by_username(usernames: list[str]):
    """
    Batch-load usage logs and summarize activity for many students at once.

    This avoids one Supabase query per child on the admin family list.
    """
    if not usernames:
        return {}

    usage_response = (
        admin_client
        .table("ai_usage_logs")
        .select("*")
        .in_("username", usernames)
        .execute()
    )

    logs_by_username = {username: [] for username in usernames}

    for log in usage_response.data or []:
        username = log.get("username")

        if username in logs_by_username:
            logs_by_username[username].append(log)

    return {
        username: summarize_student_activity(username, logs)
        for username, logs in logs_by_username.items()
    }


def build_activity_by_profile_id(profiles_by_id: dict[str, dict]):
    """Batch-load usage scoped to immutable student profile IDs."""
    profile_ids = list(profiles_by_id)
    if not profile_ids:
        return {}

    usage_response = (
        admin_client.table("ai_usage_logs")
        .select("*")
        .in_("profile_id", profile_ids)
        .execute()
    )
    logs_by_profile_id = {profile_id: [] for profile_id in profile_ids}
    for log in usage_response.data or []:
        profile_id = log.get("profile_id")
        if profile_id in logs_by_profile_id:
            logs_by_profile_id[profile_id].append(log)

    return {
        profile_id: summarize_student_activity(
            profiles_by_id[profile_id].get("username", ""), logs,
        )
        for profile_id, logs in logs_by_profile_id.items()
    }


def list_teacher_profiles_by_id():
    """Return teacher metadata rows keyed by profile_id for admin display."""
    try:
        response = (
            admin_client
            .table("teacher_profiles")
            .select("*")
            .execute()
        )
    except Exception:
        return {}

    return {
        item.get("profile_id"): item
        for item in response.data or []
        if item.get("profile_id")
    }


def list_teacher_assignments():
    """Return all teacher-student links for the admin assignment panel."""
    try:
        response = (
            admin_client
            .table("teacher_student_assignments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        return []

    return response.data or []


@router.get("/families")
def get_all_families(admin=Depends(require_admin)):
    """
    Return all profiles grouped by family for the admin control page.

    Student rows are enriched with activity summaries so admins can review usage
    and plan limits without opening separate reports.
    """
    profiles_response = (
        admin_client
        .table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    profiles = profiles_response.data or []
    student_usernames = [
        profile.get("username") or ""
        for profile in profiles
        if profile.get("role") == "student"
    ]
    activity_by_username = build_activity_by_username(student_usernames)

    teacher_profiles_by_id = list_teacher_profiles_by_id()
    teacher_assignments = list_teacher_assignments()
    assignments_by_teacher = {}

    for assignment in teacher_assignments:
        teacher_id = assignment.get("teacher_id")
        if teacher_id:
            assignments_by_teacher.setdefault(teacher_id, []).append(assignment)

    families = {}

    for profile in profiles:
        family_id = profile.get("family_id") or "no-family"

        if family_id not in families:
            families[family_id] = {
                "family_id": family_id,
                "parents": [],
                "children": [],
                "admins": [],
                "teachers": [],
            }

        if profile.get("role") == "parent":
            families[family_id]["parents"].append(profile)
        elif profile.get("role") == "student":
            username = profile.get("username") or ""
            profile["activity"] = activity_by_username.get(
                username,
                summarize_student_activity(username, []),
            )
            families[family_id]["children"].append(profile)
        elif profile.get("role") == "admin":
            families[family_id]["admins"].append(profile)
        elif profile.get("role") == "teacher":
            profile["teacher_profile"] = teacher_profiles_by_id.get(
                profile.get("id"),
                {},
            )
            profile["assignments"] = assignments_by_teacher.get(
                profile.get("id"),
                [],
            )
            families[family_id]["teachers"].append(profile)

    return {
        "success": True,
        "families": list(families.values()),
    }


@router.patch("/access/{child_id}")
def update_child_access(
    child_id: str,
    data: UpdateAccessRequest,
    admin=Depends(require_admin),
):
    """Update a student's subscription plan, status, and subject access flags."""
    response = (
        admin_client
        .table("profiles")
        .update({
            "access_cbse": data.access_cbse,
            "cbse_subjects": clean_subject_access_list(data.cbse_subjects),
            "subscription_plan": data.subscription_plan,
            "account_status": data.account_status,
            "grade": data.grade or "Grade 9",
            "board": normalize_board(data.board),
            "ai_model_preference": normalize_model_preference(
                data.ai_model_preference,
            ),
            # Clear subscription_expires_at when admin explicitly sets access flags.
            # Without this, a stale expires_at from a previous paid plan would cause
            # the expiry job to revoke this admin-granted access.
            "subscription_expires_at": None,
        })
        .eq("id", child_id)
        .eq("role", "student")
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return {
        "success": True,
        "profile": response.data[0],
    }


@router.patch("/limits/{child_id}")
def update_child_limits(
    child_id: str,
    data: UpdateLimitsRequest,
    admin=Depends(require_admin),
):
    """Update a student's daily and monthly AI token limits."""
    response = (
        admin_client
        .table("profiles")
        .update({
            "daily_token_limit": normalize_token_limit(data.daily_token_limit),
            "monthly_token_limit": normalize_token_limit(data.monthly_token_limit),
        })
        .eq("id", child_id)
        .eq("role", "student")
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return {
        "success": True,
        "profile": response.data[0],
    }


@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin=Depends(require_admin)):
    """
    Delete a user from Supabase auth and then remove their profile row.

    Auth deletion happens first so a profile is not removed while the login
    account remains active.
    """
    profile_response = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if not profile_response.data:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        admin_client.auth.admin.delete_user(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to delete auth user: {str(exc)}",
        )

    admin_client.table("profiles").delete().eq("id", user_id).execute()

    return {
        "success": True,
        "message": "User deleted successfully.",
    }
