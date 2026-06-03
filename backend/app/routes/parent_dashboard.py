from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.auth_service import require_parent, create_auth_user, admin_client
from app.services.parent_dashboard_service import (
    get_children,
    get_child_by_id,
    get_family_members,
)
from app.routes.admin_control import list_subscription_plan_settings

router = APIRouter()


class CreateStudentRequest(BaseModel):
    email: str
    password: str
    username: str


class InviteParentRequest(BaseModel):
    email: str
    password: str
    username: str


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
def get_parent_subscription_plans(parent=Depends(require_parent)):
    """Return public subscription plans for the parent subscription page."""
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

    if len(children) >= 2:
        raise HTTPException(
            status_code=400,
            detail="Maximum 2 children allowed for this family.",
        )

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    child_profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "student",
        "parent_id": parent_profile["id"],
        "family_id": parent_profile["family_id"],
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


@router.post("/invite-parent")
def invite_parent(data: InviteParentRequest, parent=Depends(require_parent)):
    """Invite/create another parent profile attached to the same family."""
    parent_profile = parent["profile"]

    if not parent_profile.get("family_id"):
        raise HTTPException(
            status_code=400,
            detail="Parent does not belong to a family.",
        )

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
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
