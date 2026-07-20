"""
admin_payment_logs.py  —  /api/admin-control/*
─────────────────────────────────────────────────────────────────────────────
Payment records and revenue reporting for the admin Payment Logs page.

Extracted from app/routes/admin_control.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.auth_service import require_admin, admin_client

router = APIRouter()


@router.get("/payment-logs")
def get_payment_logs(admin=Depends(require_admin)):
    """
    Return all payment records for the admin Payment Logs page.

    Joins subscription_payments with profiles to add username, email, grade.
    Also computes summary stats: monthly revenue, active paid users, plan breakdown,
    and a 12-month revenue/user trend for charts.
    """
    from datetime import datetime, timezone  # noqa: PLC0415
    import calendar  # noqa: PLC0415

    # Load all payment records
    try:
        pay_result = (
            admin_client
            .table("subscription_payments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        payments = pay_result.data or []
    except Exception:
        return {"success": True, "payments": [], "summary": {}, "trends": []}

    # Load profiles for all parent_ids
    user_ids = list({p.get("parent_id") for p in payments if p.get("parent_id")})
    profiles_by_id: dict = {}
    if user_ids:
        try:
            batch = (
                admin_client
                .table("profiles")
                .select("id,username,email,grade,board")
                .in_("id", user_ids)
                .execute()
            )
            profiles_by_id = {p["id"]: p for p in (batch.data or [])}
        except Exception:
            pass

    # Enrich payments with profile data
    enriched = []
    for p in payments:
        profile = profiles_by_id.get(p.get("parent_id") or "") or {}
        meta = p.get("metadata") or {}
        enriched.append({
            "id": p.get("id"),
            "order_id": p.get("razorpay_order_id"),
            "payment_id": p.get("razorpay_payment_id"),
            "status": p.get("status", "unknown"),
            "plan_key": p.get("plan_key"),
            "amount": p.get("amount", 0),
            "currency": p.get("currency", "INR"),
            "username": profile.get("username") or meta.get("signup_role", "—"),
            "email": profile.get("email") or meta.get("signup_email", "—"),
            "grade": profile.get("grade") or "—",
            "created_at": (p.get("created_at") or "")[:19],
            "verified_at": (p.get("verified_at") or "")[:19],
            "failure_reason": meta.get("failure_reason") or meta.get("error") or "",
        })

    now = datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")

    # Summary stats
    paid = [p for p in enriched if p["status"] == "paid"]
    this_month_paid = [p for p in paid if (p["created_at"] or "").startswith(this_month)]
    monthly_revenue = sum(p["amount"] for p in this_month_paid)
    total_revenue = sum(p["amount"] for p in paid)
    active_paid_users = len({p["email"] for p in paid if p["email"] != "—"})

    # Plan distribution
    plan_counts: dict = {}
    for p in paid:
        k = p["plan_key"] or "unknown"
        plan_counts[k] = plan_counts.get(k, 0) + 1

    # 12-month trend
    trends = []
    for months_ago in range(11, -1, -1):
        m = (now.month - months_ago - 1) % 12 + 1
        y = now.year - (months_ago // 12) - (1 if (now.month - months_ago - 1) < 0 else 0)
        label = f"{y}-{m:02d}"
        month_paid = [p for p in paid if (p["created_at"] or "").startswith(label)]
        trends.append({
            "month": label,
            "label": f"{calendar.month_abbr[m]} {str(y)[-2:]}",
            "revenue": sum(p["amount"] for p in month_paid),
            "users": len({p["email"] for p in month_paid if p["email"] != "—"}),
        })

    return {
        "success": True,
        "payments": enriched,
        "summary": {
            "monthly_revenue": monthly_revenue,
            "total_revenue": total_revenue,
            "active_paid_users": active_paid_users,
            "total_transactions": len(paid),
            "failed_transactions": len([p for p in enriched if p["status"] == "failed"]),
            "plan_distribution": plan_counts,
        },
        "trends": trends,
    }
