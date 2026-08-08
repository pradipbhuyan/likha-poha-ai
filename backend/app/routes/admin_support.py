"""
admin_support.py  —  /api/admin/support/*
─────────────────────────────────────────────────────────────────────────────
Support tools and View-as-User (read-only impersonation) — admin only.

All endpoints require role=admin via require_admin.
Impersonation is frontend-only/read-only — no JWT exchange.
All sensitive actions are audited.
Passwords are NEVER retrieved or exposed.

Endpoints:
  GET  /support/user-search?q=                          — search users
  GET  /support/users/{uid}/summary                     — profile + resolved state
  GET  /support/users/{uid}/subscription-history        — subscription timeline
  GET  /support/users/{uid}/audit-history               — sanitised audit events
  POST /support/students/{uid}/reset-password           — generate + set new password
  POST /support/users/{uid}/resend-welcome              — mark welcome resent (stub)
  GET  /support/pending-teachers                        — list teacher signups awaiting review
  POST /support/users/{uid}/verify-teacher              — approve a pending teacher account
  GET  /support/view-as/{uid}                           — read-only user context
  POST /support/log-impersonation-event                 — log impersonation events
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.auth_service import admin_client, require_admin
from app.services.audit_log_service import write_audit_event
from app.services.subscription_resolver_service import resolve_user_subscription

logger = logging.getLogger("likhapoha.support")

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _safe(fn):
    try:
        r = fn()
        return r.data or [], None
    except Exception as exc:
        err = str(exc)
        if "PGRST205" in err or "schema cache" in err.lower():
            return [], None
        return [], err[:200]


def _safe_one(fn):
    rows, err = _safe(fn)
    return rows[0] if rows else None, err


# ── 1. User Search ────────────────────────────────────────────────────────────

_PROFILE_SELECT = (
    "id, username, email, role, grade, subscription_plan, account_status, created_at"
)


@router.get("/support/user-search")
def support_user_search(
    q: str = Query(..., min_length=2, max_length=100),
    role: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    admin=Depends(require_admin),
):
    """
    Search users by name or email fragment.
    Returns id, username, email, role, grade — no secrets.
    Admin-only.

    Uses two separate .ilike() queries and merges in Python to avoid
    PostgREST .or_() wildcard encoding issues (% in URL → %25 mismatch).
    """
    q_clean = q.strip()

    def _build(ilike_col: str, ilike_val: str):
        base = (
            admin_client.table("profiles")
            .select(_PROFILE_SELECT)
            .ilike(ilike_col, ilike_val)
            .limit(limit)
        )
        if role:
            base = base.eq("role", role)
        return base.execute()

    by_name, err1 = _safe(lambda: _build("username", f"%{q_clean}%"))
    by_email, err2 = _safe(lambda: _build("email", f"%{q_clean}%"))

    # Merge and deduplicate by id, preserve order (name matches first)
    seen: set = set()
    rows: list = []
    for u in by_name + by_email:
        uid = u.get("id")
        if uid and uid not in seen:
            seen.add(uid)
            rows.append(u)
    rows = rows[:limit]

    err = err1 or err2
    if err:
        logger.warning("support user-search error for q=%r: %s", q_clean, err)

    return {
        "success": True,
        "query": q,
        "users": rows,
        "count": len(rows),
        "error": err,
    }


# ── 2. User Summary ───────────────────────────────────────────────────────────

@router.get("/support/users/{user_id}/summary")
def support_user_summary(user_id: str, admin=Depends(require_admin)):
    """
    Full user summary including resolved subscription state.
    Uses canonical subscription resolver.
    Admin-only. No secrets exposed.
    """
    profile, err = _safe_one(
        lambda: admin_client.table("profiles")
        .select(
            "id, username, email, role, grade, board, "
            "subscription_plan, account_status, access_cbse, "
            "subscription_expires_at, daily_token_limit, monthly_token_limit, "
            "parent_id, created_at"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not profile:
        return {"success": False, "error": "User not found"}

    # Resolve subscription state using canonical resolver
    resolved = None
    try:
        resolved = resolve_user_subscription(user_id)
    except Exception as exc:
        resolved = {"error": str(exc)[:100]}

    # Teacher assignments for this user
    assignments, _ = _safe(
        lambda: admin_client.table("teacher_student_assignments")
        .select("teacher_id, grade, subject")
        .eq("student_id", user_id)
        .execute()
    )

    # Parent linkage
    children, _ = _safe(
        lambda: admin_client.table("profiles")
        .select("id, username, grade")
        .eq("parent_id", user_id)
        .execute()
    )

    return {
        "success": True,
        "user": profile,
        "resolved_subscription": resolved,
        "teacher_assignments": assignments,
        "linked_children": children,
    }


# ── 3. Subscription History ───────────────────────────────────────────────────

@router.get("/support/users/{user_id}/subscription-history")
def support_subscription_history(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    admin=Depends(require_admin),
):
    """
    Subscription timeline events for a specific user.
    Admin-only. No payment secrets.
    """
    timeline, err = _safe(
        lambda: admin_client.table("subscription_timeline")
        .select("event_type, from_plan, to_plan, source, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    # Payments (sanitised — no payment IDs, no Razorpay keys)
    payments, pay_err = _safe(
        lambda: admin_client.table("subscription_payments")
        .select("status, plan_key, amount, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "success": True,
        "user_id": user_id,
        "timeline_events": timeline,
        "payment_history": payments,
        "error": err or pay_err,
    }


# ── 4. Audit History ──────────────────────────────────────────────────────────

@router.get("/support/users/{user_id}/audit-history")
def support_audit_history(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    admin=Depends(require_admin),
):
    """
    Sanitised audit history for a specific user.
    Returns event_type, entity_type, timestamp only — no raw metadata/secrets.
    Admin-only.
    """
    # Events where this user is the actor or target
    actor_events, err1 = _safe(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, entity_type, entity_id, created_at")
        .eq("actor_user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    target_events, err2 = _safe(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, entity_type, entity_id, created_at")
        .eq("target_user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    # Merge and sort, cap at limit
    all_events = sorted(
        actor_events + target_events,
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:limit]

    return {
        "success": True,
        "user_id": user_id,
        "audit_events": all_events,
        "count": len(all_events),
        "note": "Metadata and secrets are not included in audit history view.",
        "error": err1 or err2,
    }


# ── 5. Reset Student Password ─────────────────────────────────────────────────

@router.post("/support/students/{student_id}/reset-password")
def support_reset_password(student_id: str, admin=Depends(require_admin)):
    """
    Generate a new secure temporary password for a student.

    Security:
    - Password never stored or logged.
    - Returned once only — caller must securely relay it.
    - Uses Supabase Auth admin API.
    Admin-only. Audited (without password).
    """
    # Validate student
    user, err = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email, role")
        .eq("id", student_id)
        .in_("role", ["student", "child"])
        .limit(1)
        .execute()
    )
    if not user:
        return {"success": False, "error": "Student not found or wrong role"}

    new_password = _generate_temp_password(12)

    try:
        admin_client.auth.admin.update_user_by_id(
            student_id, {"password": new_password}
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)[:150]}

    write_audit_event(
        event_type="support.password_reset",
        actor_user_id=admin.get("id"),
        target_user_id=student_id,
        entity_type="student",
        entity_id=student_id,
        # NO password in metadata
        metadata={"triggered_by": "admin_support_tools"},
    )

    return {
        "success": True,
        "username": user.get("username"),
        "email": user.get("email"),
        "temp_password": new_password,  # shown once only
        "warning": "Show once only. Share securely. Advise student to change immediately.",
    }


# ── 6. Resend Welcome Email ───────────────────────────────────────────────────

@router.post("/support/users/{user_id}/resend-welcome")
def support_resend_welcome(user_id: str, admin=Depends(require_admin)):
    """
    Resend welcome email for a user.
    If no email service is configured, marks as attempted and returns a stub.
    Admin-only. Audited.
    """
    user, err = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email, role")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user:
        return {"success": False, "error": "User not found"}

    write_audit_event(
        event_type="support.resend_welcome",
        actor_user_id=admin.get("id"),
        target_user_id=user_id,
        entity_type="user",
        entity_id=user_id,
        metadata={"email_address_hashed": ""},  # never log email plaintext
    )

    # Stub: attempt Supabase Auth magic link invite
    invite_sent = False
    invite_error = None
    try:
        if user.get("email"):
            admin_client.auth.admin.invite_user_by_email(user["email"])
            invite_sent = True
    except Exception as exc:
        invite_error = str(exc)[:100]

    return {
        "success": True,
        "username": user.get("username"),
        "invite_sent": invite_sent,
        "note": "If invite_sent=false, share login link manually.",
        "error": invite_error,
    }


# ── 6b. Pending Teacher Approvals ──────────────────────────────────────────────

@router.get("/support/pending-teachers")
def support_pending_teachers(admin=Depends(require_admin)):
    """
    List teacher accounts awaiting verification (self-signed-up via
    POST /api/auth/teacher-signup, account_status="pending_verification").
    Admin-only.
    """
    rows, err = _safe(
        lambda: admin_client.table("profiles")
        .select("id, username, email, school_name, created_at")
        .eq("role", "teacher")
        .eq("account_status", "pending_verification")
        .order("created_at", desc=False)
        .execute()
    )
    return {"success": err is None, "teachers": rows, "count": len(rows), "error": err}


@router.post("/support/users/{user_id}/verify-teacher")
def support_verify_teacher(user_id: str, admin=Depends(require_admin)):
    """
    Approve a pending teacher account, setting account_status="active" so
    require_teacher() lets them into the teacher dashboard. Admin-only. Audited.
    """
    user, err = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, email, role, account_status")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not user:
        return {"success": False, "error": err or "User not found"}
    if user.get("role") != "teacher":
        return {"success": False, "error": "User is not a teacher account"}
    if user.get("account_status") != "pending_verification":
        return {"success": False, "error": f"Account is not pending verification (status: {user.get('account_status')})"}

    admin_client.table("profiles").update({"account_status": "active"}).eq("id", user_id).execute()

    write_audit_event(
        event_type="support.verify_teacher",
        actor_user_id=admin.get("profile", {}).get("id"),
        target_user_id=user_id,
        entity_type="user",
        entity_id=user_id,
        metadata={},
    )

    return {"success": True, "username": user.get("username"), "account_status": "active"}


# ── 7. View-as-User context ───────────────────────────────────────────────────

@router.get("/support/view-as/{user_id}")
def support_view_as_user(user_id: str, admin=Depends(require_admin)):
    """
    Return read-only user context for frontend View-as-User mode.

    This is frontend-only simulation — NO JWT token exchange.
    Returns profile + resolved subscription + associations.
    Dangerous fields (tokens, secrets, payment IDs) are excluded.
    Admin-only. Audited.
    """
    profile, err = _safe_one(
        lambda: admin_client.table("profiles")
        .select(
            "id, username, email, role, grade, board, "
            "subscription_plan, account_status, access_cbse, "
            "subscription_expires_at, created_at"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not profile:
        return {"success": False, "error": "User not found"}

    # Block impersonating another admin
    if profile.get("role") == "admin":
        write_audit_event(
            event_type="impersonation.denied",
            actor_user_id=admin.get("id"),
            target_user_id=user_id,
            metadata={"reason": "cannot_impersonate_admin"},
        )
        return {"success": False, "error": "Cannot view-as another admin."}

    resolved = None
    try:
        resolved = resolve_user_subscription(user_id)
    except Exception:
        resolved = None

    # Activity summary (graceful — only available if ai_usage_logs exist)
    activity = None
    try:
        from app.routes.admin_control import build_student_activity
        activity = build_student_activity(profile.get("username", ""))
    except Exception:
        activity = None

    write_audit_event(
        event_type="impersonation.started",
        actor_user_id=admin.get("id"),
        target_user_id=user_id,
        entity_type=profile.get("role"),
        entity_id=user_id,
        metadata={"read_only": True},
    )

    return {
        "success": True,
        "activity": activity,
        "view_as": {
            "user_id": user_id,
            "username": profile.get("username"),
            "role": profile.get("role"),
            "grade": profile.get("grade"),
            "subscription_plan": profile.get("subscription_plan"),
            "access_cbse": profile.get("access_cbse"),
            "account_status": profile.get("account_status"),
        },
        "resolved_subscription": resolved,
        "restrictions": [
            "no_payment_actions",
            "no_password_changes",
            "no_destructive_actions",
            "no_admin_actions",
            "read_only",
        ],
        "banner": f"Viewing as {profile.get('username', user_id)} ({profile.get('role')}). Admin actions restricted. Exit to resume admin mode.",
    }


# ── 8. Log Impersonation Event ────────────────────────────────────────────────

class ImpersonationEventRequest(BaseModel):
    event_type: str   # impersonation.started | impersonation.ended
    target_user_id: str
    metadata: dict | None = None


@router.post("/support/log-impersonation-event")
def log_impersonation_event(req: ImpersonationEventRequest, admin=Depends(require_admin)):
    """
    Log an impersonation lifecycle event (started / ended).
    Called by the frontend when admin enters/exits view-as mode.
    Admin-only.
    """
    allowed_types = {"impersonation.started", "impersonation.ended", "impersonation.denied"}
    if req.event_type not in allowed_types:
        return {"success": False, "error": f"Invalid event_type. Allowed: {allowed_types}"}

    write_audit_event(
        event_type=req.event_type,
        actor_user_id=admin.get("id"),
        target_user_id=req.target_user_id,
        metadata={**(req.metadata or {}), "source": "frontend"},
    )

    return {"success": True, "event_type": req.event_type, "logged": True}
