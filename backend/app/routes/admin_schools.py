"""
admin_schools.py  —  /api/admin/schools/*
─────────────────────────────────────────────────────────────────────────────
Admin verification of principal-created schools. Mirrors the pending-teacher
review flow in admin_support.py (GET pending-teachers / POST verify-teacher)
one-for-one, applied to schools instead of individual teacher accounts.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth_service import admin_client, require_admin
from app.services.audit_log_service import write_audit_event

router = APIRouter()


@router.get("/schools/pending")
def list_pending_schools(admin=Depends(require_admin)):
    """
    List schools awaiting verification (created via POST /api/auth/principal-signup),
    with the requesting principal's username/email attached so an admin can
    tell who they're approving without a second lookup.
    """
    resp = (
        admin_client
        .table("schools")
        .select("id, name, udise_code, city, state, school_code, principal_id, created_at")
        .eq("status", "pending_verification")
        .order("created_at", desc=False)
        .execute()
    )
    schools = resp.data or []

    principal_ids = [s["principal_id"] for s in schools if s.get("principal_id")]
    principals_by_id = {}
    if principal_ids:
        principals_resp = (
            admin_client
            .table("profiles")
            .select("id, username, email")
            .in_("id", principal_ids)
            .execute()
        )
        principals_by_id = {p["id"]: p for p in (principals_resp.data or [])}

    for school in schools:
        principal = principals_by_id.get(school.get("principal_id"), {})
        school["principal_username"] = principal.get("username")
        school["principal_email"] = principal.get("email")

    return {"success": True, "schools": schools}


@router.post("/schools/{school_id}/verify")
def verify_school(school_id: str, admin=Depends(require_admin)):
    """
    Approve a pending school, activating it and the principal account that
    owns it. Sets schools.status="active" and profiles.account_status=
    "active" for the principal — mirrors support_verify_teacher() exactly.
    """
    resp = (
        admin_client
        .table("schools")
        .select("id, name, status, principal_id")
        .eq("id", school_id)
        .limit(1)
        .execute()
    )
    school = (resp.data or [None])[0]
    if not school:
        return {"success": False, "error": "School not found"}
    if school.get("status") != "pending_verification":
        return {"success": False, "error": f"School is not pending verification (status: {school.get('status')})"}

    admin_client.table("schools").update({"status": "active"}).eq("id", school_id).execute()
    admin_client.table("profiles").update({"account_status": "active"}).eq(
        "id", school["principal_id"]
    ).execute()

    write_audit_event(
        event_type="admin.verify_school",
        actor_user_id=admin.get("profile", {}).get("id"),
        target_user_id=school["principal_id"],
        entity_type="school",
        entity_id=school_id,
        metadata={"school_name": school.get("name")},
    )

    return {"success": True, "school_id": school_id, "status": "active"}


@router.post("/schools/{school_id}/reject")
def reject_school(school_id: str, admin=Depends(require_admin)):
    """Reject a pending school — its join code stops working for new links."""
    resp = (
        admin_client
        .table("schools")
        .select("id, name, status, principal_id")
        .eq("id", school_id)
        .limit(1)
        .execute()
    )
    school = (resp.data or [None])[0]
    if not school:
        return {"success": False, "error": "School not found"}
    if school.get("status") != "pending_verification":
        return {"success": False, "error": f"School is not pending verification (status: {school.get('status')})"}

    admin_client.table("schools").update({"status": "rejected"}).eq("id", school_id).execute()

    write_audit_event(
        event_type="admin.reject_school",
        actor_user_id=admin.get("profile", {}).get("id"),
        target_user_id=school["principal_id"],
        entity_type="school",
        entity_id=school_id,
        metadata={"school_name": school.get("name")},
    )

    return {"success": True, "school_id": school_id, "status": "rejected"}
