"""
admin_views.py  —  /api/admin/views/*
─────────────────────────────────────────────────────────────────────────────
Prebuilt admin saved views — admin only.
Views query live data on each request; no DB table needed.

Endpoints:
  GET /views           — list available view definitions
  GET /views/{view_id} — run a view and return results + count
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query

from app.services.auth_service import admin_client, require_admin

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _safe(fn):
    try:
        r = fn()
        return r.data or [], None
    except Exception as exc:
        err = str(exc)
        if "PGRST205" in err or "schema cache" in err.lower():
            return [], None
        return [], err[:200]


# ── View registry ─────────────────────────────────────────────────────────────

VIEW_DEFINITIONS = [
    {
        "id": "expired_subscriptions",
        "label": "Expired Subscriptions",
        "description": "Students/parents whose subscription_expires_at is in the past and still have access_cbse set.",
        "category": "subscriptions",
    },
    {
        "id": "teachers_with_many_students",
        "label": "Teachers with 10+ Students",
        "description": "Teachers who have 10 or more assigned students.",
        "category": "teachers",
    },
    {
        "id": "parents_without_children",
        "label": "Parents Without Linked Children",
        "description": "Parent accounts that have no linked child profiles.",
        "category": "families",
    },
    {
        "id": "students_without_parent",
        "label": "Students Without Parent",
        "description": "Student accounts that have no parent_id set.",
        "category": "families",
    },
    {
        "id": "students_without_teacher",
        "label": "Students Without Teacher",
        "description": "Students who have no teacher assignment.",
        "category": "teachers",
    },
    {
        "id": "recent_failed_payments",
        "label": "Recent Failed Payments",
        "description": "Payment orders with signature_failed or failed status in last 30 days.",
        "category": "payments",
    },
    {
        "id": "recent_signups",
        "label": "Recent Signups",
        "description": "Users who signed up in the last 7 days.",
        "category": "users",
    },
    {
        "id": "offer_code_users",
        "label": "Offer Code Users",
        "description": "Users who signed up using an offer code.",
        "category": "offers",
    },
    {
        "id": "free_users",
        "label": "Free Users (No Access)",
        "description": "Students/parents on free tier without access_cbse.",
        "category": "subscriptions",
    },
    {
        "id": "active_paid_users",
        "label": "Active Paid Users",
        "description": "Users with an active non-free subscription.",
        "category": "subscriptions",
    },
]


@router.get("/views")
def list_views(admin=Depends(require_admin)):
    """Return all prebuilt view definitions."""
    return {
        "success": True,
        "views": VIEW_DEFINITIONS,
        "total": len(VIEW_DEFINITIONS),
    }


@router.get("/views/{view_id}")
def run_view(
    view_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_admin),
):
    """
    Run a named prebuilt view and return live results with pagination.
    Admin-only.
    """
    offset = (page - 1) * page_size
    now = _now()
    since = _days_ago(days)

    if view_id == "expired_subscriptions":
        rows, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, role, subscription_plan, subscription_expires_at, access_cbse")
            .in_("role", ["student", "parent"])
            .eq("access_cbse", True)
            .lt("subscription_expires_at", now)
            .order("subscription_expires_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    elif view_id == "teachers_with_many_students":
        # Get teacher assignment counts
        all_assignments, err = _safe(
            lambda: admin_client.table("teacher_student_assignments")
            .select("teacher_id")
            .execute()
        )
        from collections import Counter
        counts = Counter(a["teacher_id"] for a in all_assignments)
        heavy_ids = [tid for tid, cnt in counts.items() if cnt >= 10]
        if heavy_ids:
            rows, err2 = _safe(
                lambda: admin_client.table("profiles")
                .select("id, username, email")
                .in_("id", heavy_ids)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            for r in rows:
                r["student_count"] = counts.get(r["id"], 0)
            err = err or err2
        else:
            rows = []

    elif view_id == "parents_without_children":
        all_parents, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, created_at")
            .eq("role", "parent")
            .execute()
        )
        # Find parents with no children (parent_id column in profiles)
        all_children, err2 = _safe(
            lambda: admin_client.table("profiles")
            .select("parent_id")
            .eq("role", "student")
            .not_.is_("parent_id", "null")
            .execute()
        )
        err = err or err2
        linked_parent_ids = {c["parent_id"] for c in all_children if c.get("parent_id")}
        rows = [p for p in all_parents if p["id"] not in linked_parent_ids]
        rows = rows[offset: offset + page_size]

    elif view_id == "students_without_parent":
        rows, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, grade, created_at")
            .eq("role", "student")
            .is_("parent_id", "null")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    elif view_id == "students_without_teacher":
        all_students, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, grade")
            .eq("role", "student")
            .execute()
        )
        assigned_ids_data, err2 = _safe(
            lambda: admin_client.table("teacher_student_assignments")
            .select("student_id")
            .execute()
        )
        err = err or err2
        assigned_ids = {a["student_id"] for a in assigned_ids_data}
        rows = [s for s in all_students if s["id"] not in assigned_ids]
        rows = rows[offset: offset + page_size]

    elif view_id == "recent_failed_payments":
        rows, err = _safe(
            lambda: admin_client.table("subscription_payments")
            .select("id, status, plan_key, amount, created_at, razorpay_order_id")
            .in_("status", ["signature_failed", "failed"])
            .gte("created_at", since)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    elif view_id == "recent_signups":
        rows, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, role, grade, created_at")
            .gte("created_at", _days_ago(7))
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    elif view_id == "offer_code_users":
        redemptions, err = _safe(
            lambda: admin_client.table("offer_redemptions")
            .select("user_id, enrolled_at, access_until")
            .order("enrolled_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        # Enrich with profile data
        rows = []
        if redemptions:
            user_ids = [r["user_id"] for r in redemptions if r.get("user_id")]
            profiles, err2 = _safe(
                lambda: admin_client.table("profiles")
                .select("id, username, email, grade")
                .in_("id", user_ids)
                .execute()
            )
            err = err or err2
            profile_map = {p["id"]: p for p in profiles}
            for rr in redemptions:
                uid = rr.get("user_id")
                p = profile_map.get(uid, {})
                rows.append({
                    "user_id": uid,
                    "username": p.get("username", ""),
                    "email": p.get("email", ""),
                    "grade": p.get("grade", ""),
                    "enrolled_at": rr.get("enrolled_at"),
                    "access_until": rr.get("access_until"),
                })

    elif view_id == "free_users":
        rows, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, role, grade, created_at")
            .in_("role", ["student", "parent"])
            .eq("access_cbse", False)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    elif view_id == "active_paid_users":
        rows, err = _safe(
            lambda: admin_client.table("profiles")
            .select("id, username, email, role, subscription_plan, subscription_expires_at")
            .in_("role", ["student", "parent"])
            .eq("access_cbse", True)
            .neq("subscription_plan", "free")
            .gt("subscription_expires_at", now)
            .order("subscription_expires_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

    else:
        return {"success": False, "error": f"Unknown view: {view_id}"}

    # Find view definition
    view_def = next((v for v in VIEW_DEFINITIONS if v["id"] == view_id), {})

    return {
        "success": True,
        "view_id": view_id,
        "label": view_def.get("label", view_id),
        "description": view_def.get("description", ""),
        "rows": rows,
        "count": len(rows),
        "page": page,
        "page_size": page_size,
        "error": err if err else None,
    }
