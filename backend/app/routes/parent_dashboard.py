from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_parent, get_current_user, create_auth_user, invite_parent_by_email, admin_client
from app.services.parent_dashboard_service import (
    get_children,
    get_child_by_id,
    get_family_members,
)
from app.services.subscription_resolver_service import resolve_user_subscription
from app.routes.admin_control import (
    list_subscription_contact_settings,
    list_subscription_plan_settings,
)
from app.services.board_service import normalize_board

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CHILD_EMAIL_DOMAIN = "child.likhapoha.in"


def _resolve_child_auth_email(requested_email: str | None, username: str) -> str:
    """
    Return the email used for Supabase auth + profile lookup.

    - If the parent provided a real email, use it.
    - Otherwise generate a synthetic email so Supabase auth (which always
      requires an email) succeeds and the lookup-email login flow works.
    """
    raw = (requested_email or "").strip()
    if raw and _EMAIL_RE.match(raw):
        return raw
    # Sanitise username to a safe local-part
    safe = re.sub(r"[^a-zA-Z0-9._-]", "", username) or "child"
    return f"{safe}@{_CHILD_EMAIL_DOMAIN}"


class CreateStudentRequest(BaseModel):
    email: Optional[str] = None   # optional for children — real or synthetic
    password: str
    username: str
    board: str = "CBSE"
    grade: str = "Grade 9"   # required from the parent form — defaults kept for API compat
    avatar: Optional[str] = None  # emoji key (e.g. 'boy1') or data: URL
    cbse_subjects: Optional[list] = None


class InviteParentRequest(BaseModel):
    email: str
    username: str
    # password is NOT accepted here — Supabase sends an invite email and the
    # parent sets their own password when they click the confirmation link.
    # This enforces real email ownership verification before first login.


@router.get("/family")
def get_family(parent=Depends(require_parent)):
    """Return all parents and children in the signed-in parent's family."""
    parent_profile = parent["profile"]
    family = get_family_members(parent_profile["id"])

    return {
        "success": True,
        "family_id": family["family_id"],
        "parents": family["parents"],
        "children": family["children"],
    }


@router.get("/children")
def get_parent_children(parent=Depends(require_parent)):
    """Return only the children that belong to the signed-in parent's family."""
    parent_profile = parent["profile"]

    return {
        "success": True,
        "children": get_children(parent_profile["id"]),
    }


@router.get("/subscription-plans")
def get_parent_subscription_plans(user=Depends(get_current_user)):
    """Return public subscription plans for the subscription page.

    Accessible by any authenticated user (parent, student, child, teacher)
    — this endpoint only returns public pricing data, not personal information.
    """
    settings = list_subscription_plan_settings()
    plans = {
        key: plan
        for key, plan in settings["plans"].items()
        if plan.get("is_public") is not False
    }
    plan_order = [
        key for key in settings["plan_order"]
        if key in plans
    ]

    return {
        "success": True,
        "persisted": settings.get("persisted", False),
        "source": settings.get("source", "defaults"),
        "load_error": settings.get("load_error"),
        "plans": plans,
        "plan_order": plan_order,
        "contact": list_subscription_contact_settings().get("contact", {}),
    }


@router.get("/children/{child_id}")
def get_single_child(child_id: str, parent=Depends(require_parent)):
    """Return one child profile after parent-scoped ownership validation."""
    parent_profile = parent["profile"]

    child = get_child_by_id(parent_profile["id"], child_id)

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    return {
        "success": True,
        "child": child,
    }
    
@router.get("/children/{child_id}/weak-area-alerts")
def get_child_weak_area_alerts(child_id: str, parent=Depends(require_parent)):
    """Return weak-area alerts for one child owned by the signed-in parent."""
    parent_profile = parent["profile"]

    child = get_child_by_id(parent_profile["id"], child_id)

    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    response = (
        admin_client
        .table("weak_area_alerts")
        .select("*")
        .eq("username", child.get("username"))
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "success": True,
        "alerts": response.data or [],
    }


@router.post("/create-student")
def create_student(data: CreateStudentRequest, parent=Depends(require_parent)):
    """
    Create a student auth account and profile inside the parent's family.

    Families are capped at two children here to keep the paid-plan/family-plan
    assumptions consistent.
    """
    parent_profile = parent["profile"]

    children = get_children(parent_profile["id"])

    # Child limit from canonical subscription resolver (not hardcoded).
    # FREE/NANO/PREMIUM = 1 child. FAMILY_PREMIUM = 2. ADMIN_GRANT = None (no limit).
    parent_sub = resolve_user_subscription(parent_profile["id"])
    child_limit = parent_sub.get("child_limit")  # None means no limit (admin)
    if child_limit is None:
        cpk = parent_sub.get("canonical_plan_key", "FREE_TIER")
        child_limit = 2 if cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL") else 1
    if len(children) >= child_limit:
        plan_name = parent_sub.get("plan_name", "your plan")
        raise HTTPException(
            status_code=400,
            detail=f"Child limit reached for {plan_name}. Maximum {child_limit} child{'ren' if child_limit > 1 else ''} allowed.",
        )

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    auth_email = _resolve_child_auth_email(data.email, data.username)

    auth_user = create_auth_user(
        email=auth_email,
        password=data.password,
    )

    from app.data.product_catalogue import ALL_GRADES_INCLUDING_HIDDEN  # noqa: PLC0415
    grade = data.grade if data.grade in ALL_GRADES_INCLUDING_HIDDEN else "Grade 9"

    child_profile = {
        "id": auth_user.id,
        # Store the resolved email (real or synthetic) so the username→email
        # lookup-email login flow returns a usable address for signInWithPassword.
        "email": auth_email,
        "username": data.username,
        "role": "student",
        "parent_id": parent_profile["id"],
        "family_id": parent_profile["family_id"],
        "board": normalize_board(data.board),
        "grade": grade,
        "subscription_plan": parent_profile.get("subscription_plan", "free"),
        "account_status": "active",
        "access_cbse": parent_profile.get("access_cbse", False),
        "access_sof_science": parent_profile.get("access_sof_science", False),
        "access_sof_maths": parent_profile.get("access_sof_maths", False),
        "access_sof_english": parent_profile.get("access_sof_english", False),
        "cbse_subjects": data.cbse_subjects or [],
        "daily_token_limit": parent_profile.get("daily_token_limit", 50000),
        "monthly_token_limit": parent_profile.get("monthly_token_limit", 1000000),
        "ai_model_preference": "default",
    }

    # Save avatar if provided (emoji key or data: URL)
    if data.avatar:
        child_profile["avatar"] = data.avatar[:400000]  # cap at ~300KB

    response = (
        admin_client
        .table("profiles")
        .insert(child_profile)
        .execute()
    )

    # Detect silent insert failure (RLS or constraint violation with empty data)
    if not response.data:
        # Profile insert silently returned nothing — attempt to rollback auth user
        try:
            admin_client.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Child account created but profile could not be saved. Please try again.",
        )

    created_profile = response.data[0]

    # login_id: what the child types to log in (their username in the lookup-email flow)
    # The lookup-email endpoint resolves username → email → Supabase signIn
    login_id = data.username  # display name is the login identifier

    return {
        "success": True,
        "child": created_profile,
        "login_id": login_id,
        "login_email": auth_email,  # actual Supabase auth email (synthetic or real)
        "login_note": (
            "Child logs in with their display name as username. "
            f"Login ID: {login_id}"
        ),
    }


class UpdateAvatarRequest(BaseModel):
    avatar: str  # emoji key or data: URL


@router.post("/update-avatar")
def update_avatar(data: UpdateAvatarRequest, parent=Depends(require_parent)):
    """Parent updates their own avatar."""
    parent_profile = parent["profile"]
    admin_client.table("profiles").update(
        {"avatar": data.avatar[:400000]}
    ).eq("id", parent_profile["id"]).execute()
    return {"success": True}


@router.post("/invite-parent")
def invite_parent(data: InviteParentRequest, parent=Depends(require_parent)):
    """
    Invite another parent to join the same family.

    Email confirmation is always enforced for parent-initiated invites so the
    invited parent must verify their email address before they can log in.
    Only admin-created accounts bypass this check.
    """
    parent_profile = parent["profile"]

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    # Use invite_user_by_email so Supabase sends a real invitation email.
    # The invited parent must click the link to confirm their email and set
    # their password before they can log in. This is the only Supabase admin
    # API method that actually sends an email upon account creation.
    auth_user = invite_parent_by_email(
        email=data.email,
        username=data.username,
    )

    invited_parent = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "parent",
        "family_id": parent_profile["family_id"],
        "parent_id": None,
    }

    response = (
        admin_client
        .table("profiles")
        .insert(invited_parent)
        .execute()
    )

    return {
        "success": True,
        "parent": response.data[0] if response.data else invited_parent,
    }
