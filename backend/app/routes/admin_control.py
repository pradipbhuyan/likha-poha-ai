from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_admin, create_auth_user, admin_client

router = APIRouter()


class CreateParentRequest(BaseModel):
    email: str
    password: str
    username: str
    family_id: str | None = None


class CreateChildRequest(BaseModel):
    email: str
    password: str
    username: str
    parent_id: str
    family_id: str


class UpdateAccessRequest(BaseModel):
    access_cbse: bool
    access_sof_science: bool
    access_sof_maths: bool
    access_sof_english: bool
    subscription_plan: str = "free"
    account_status: str = "active"


class UpdateLimitsRequest(BaseModel):
    daily_token_limit: int
    monthly_token_limit: int


def build_student_activity(username: str):
    now = datetime.now(timezone.utc)
    today_start = now.date().isoformat()
    month_start = now.replace(day=1).date().isoformat()

    usage_response = (
        admin_client
        .table("ai_usage_logs")
        .select("*")
        .eq("username", username)
        .execute()
    )

    logs = usage_response.data or []

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


@router.get("/families")
def get_all_families(admin=Depends(require_admin)):
    profiles_response = (
        admin_client
        .table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    profiles = profiles_response.data or []

    families = {}

    for profile in profiles:
        family_id = profile.get("family_id") or "no-family"

        if family_id not in families:
            families[family_id] = {
                "family_id": family_id,
                "parents": [],
                "children": [],
                "admins": [],
            }

        if profile.get("role") == "parent":
            families[family_id]["parents"].append(profile)
        elif profile.get("role") == "student":
            profile["activity"] = build_student_activity(
                profile.get("username") or ""
            )
            families[family_id]["children"].append(profile)
        elif profile.get("role") == "admin":
            families[family_id]["admins"].append(profile)

    return {
        "success": True,
        "families": list(families.values()),
    }


@router.post("/parents")
def create_parent(data: CreateParentRequest, admin=Depends(require_admin)):
    family_id = data.family_id

    if not family_id:
        family_response = (
            admin_client
            .table("families")
            .insert({
                "family_name": f"{data.username}'s Family",
            })
            .execute()
        )

        if not family_response.data:
            raise HTTPException(
                status_code=400,
                detail="Unable to create family.",
            )

        family_id = family_response.data[0]["id"]

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    parent_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "parent",
        "parent_id": None,
        "family_id": family_id,
        "account_status": "active",
        "subscription_plan": "free",
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
    }

    response = (
        admin_client
        .table("profiles")
        .insert(parent_profile)
        .execute()
    )

    return {
        "success": True,
        "parent": response.data[0] if response.data else parent_profile,
    }


@router.post("/children")
def create_child(data: CreateChildRequest, admin=Depends(require_admin)):
    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    child_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "student",
        "parent_id": data.parent_id,
        "family_id": data.family_id,
        "account_status": "active",
        "subscription_plan": "free",
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 50000,
        "monthly_token_limit": 1000000,
    }

    response = (
        admin_client
        .table("profiles")
        .insert(child_profile)
        .execute()
    )

    return {
        "success": True,
        "child": response.data[0] if response.data else child_profile,
    }


@router.patch("/access/{child_id}")
def update_child_access(
    child_id: str,
    data: UpdateAccessRequest,
    admin=Depends(require_admin),
):
    response = (
        admin_client
        .table("profiles")
        .update({
            "access_cbse": data.access_cbse,
            "access_sof_science": data.access_sof_science,
            "access_sof_maths": data.access_sof_maths,
            "access_sof_english": data.access_sof_english,
            "subscription_plan": data.subscription_plan,
            "account_status": data.account_status,
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
    response = (
        admin_client
        .table("profiles")
        .update({
            "daily_token_limit": data.daily_token_limit,
            "monthly_token_limit": data.monthly_token_limit,
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

    admin_client.table("profiles").delete().eq("id", user_id).execute()

    try:
        admin_client.auth.admin.delete_user(user_id)
    except Exception:
        pass

    return {
        "success": True,
        "message": "User deleted successfully.",
    }
