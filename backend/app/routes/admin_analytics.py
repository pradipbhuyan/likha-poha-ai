"""
admin_analytics.py  —  /api/admin/analytics/*
─────────────────────────────────────────────────────────────────────────────
Admin analytics endpoints — admin only.
All data is aggregated; no individual user secrets are exposed.
Missing data sources return "not_available" gracefully.

Endpoints:
  GET /analytics/summary  — aggregate counts across all data sources
  GET /analytics/trends   — time-bucketed trends by days
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query

from app.services.auth_service import admin_client, require_admin

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(fn):
    """Return (data, error). Gracefully handles missing tables (PGRST205)."""
    try:
        r = fn()
        return r.data or [], None
    except Exception as exc:
        err = str(exc)
        if "PGRST205" in err or "schema cache" in err.lower():
            return [], None
        return [], err[:200]


def _date_bucket(iso_ts: str, bucket: str = "day") -> str:
    """Truncate ISO timestamp to day or week string for grouping."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if bucket == "week":
            # ISO week: YYYY-Www
            return dt.strftime("%Y-W%V")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/analytics/summary")
def analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_admin),
):
    """
    Aggregate summary counts for admin analytics overview.
    Admin-only. Sanitised — no individual user data.
    """
    since = _days_ago(days)
    now = _now()

    # ── Users ──
    all_profiles, _ = _safe(
        lambda: admin_client.table("profiles")
        .select("role, access_cbse, subscription_plan, subscription_expires_at, created_at")
        .execute()
    )
    total_users = len(all_profiles)
    roles = Counter(p.get("role", "unknown") for p in all_profiles)
    new_signups = sum(1 for p in all_profiles if (p.get("created_at") or "") >= since)
    free_users = sum(1 for p in all_profiles if not p.get("access_cbse"))
    paid_active = sum(
        1 for p in all_profiles
        if p.get("access_cbse")
        and p.get("subscription_plan", "free") != "free"
        and (p.get("subscription_expires_at") or "") > now
    )
    admin_granted = sum(
        1 for p in all_profiles
        if p.get("access_cbse")
        and p.get("subscription_plan", "free") == "free"
        and not p.get("subscription_expires_at")
    )

    # ── Payments ──
    payments, _ = _safe(
        lambda: admin_client.table("subscription_payments")
        .select("status, amount, created_at")
        .gte("created_at", since)
        .execute()
    )
    pay_counts = Counter(p.get("status", "unknown") for p in payments)
    total_paid = pay_counts.get("paid", 0)
    total_failed = pay_counts.get("signature_failed", 0) + pay_counts.get("failed", 0)
    conversion_rate = round(total_paid / len(payments) * 100, 1) if payments else None

    # ── Offer redemptions ──
    redemptions, _ = _safe(
        lambda: admin_client.table("offer_redemptions")
        .select("enrolled_at")
        .gte("enrolled_at", since)
        .execute()
    )
    offer_redemptions = len(redemptions)

    # ── Teacher assignments ──
    assignments, _ = _safe(
        lambda: admin_client.table("teacher_student_assignments")
        .select("created_at")
        .execute()
    )
    total_assignments = len(assignments)

    # ── AI usage (graceful if table absent) ──
    ai_rows, ai_err = _safe(
        lambda: admin_client.table("ai_usage_logs")
        .select("tokens_used, created_at")
        .gte("created_at", since)
        .execute()
    )
    ai_tokens = sum(r.get("tokens_used", 0) for r in ai_rows) if ai_rows else None
    ai_requests = len(ai_rows) if ai_rows else None

    # ── Mock test history (graceful) ──
    test_rows, test_err = _safe(
        lambda: admin_client.table("test_history")
        .select("created_at")
        .gte("created_at", since)
        .execute()
    )
    mock_tests_completed = len(test_rows) if not test_err else None

    return {
        "success": True,
        "period_days": days,
        "users": {
            "total": total_users,
            "by_role": dict(roles),
            "new_signups_in_period": new_signups,
            "free_no_access": free_users,
            "paid_active": paid_active,
            "admin_granted_access": admin_granted,
        },
        "payments": {
            "total_in_period": len(payments),
            "paid": total_paid,
            "failed": total_failed,
            "conversion_rate_percent": conversion_rate,
        },
        "offer_redemptions_in_period": offer_redemptions,
        "teacher_student_assignments_total": total_assignments,
        "ai_usage": {
            "requests_in_period": ai_requests,
            "tokens_in_period": ai_tokens,
            "available": ai_err is None,
        },
        "mock_tests_completed_in_period": mock_tests_completed,
    }


# ── Trends ────────────────────────────────────────────────────────────────────

@router.get("/analytics/trends")
def analytics_trends(
    days: int = Query(default=30, ge=7, le=365),
    bucket: str = Query(default="day", pattern="^(day|week)$"),
    admin=Depends(require_admin),
):
    """
    Time-bucketed trend data for charts.
    Buckets: 'day' or 'week'.
    Returns one entry per bucket for each metric.
    Admin-only. No individual user data.
    """
    since = _days_ago(days)

    # ── Signup trend ──
    profiles, _ = _safe(
        lambda: admin_client.table("profiles")
        .select("created_at, role")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    signup_by_day: dict[str, int] = defaultdict(int)
    for p in profiles:
        day = _date_bucket(p.get("created_at") or "", bucket)
        signup_by_day[day] += 1
    signup_trend = [{"date": k, "count": v} for k, v in sorted(signup_by_day.items())]

    # ── Payment trend ──
    payments, _ = _safe(
        lambda: admin_client.table("subscription_payments")
        .select("status, created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    pay_trend_paid: dict[str, int] = defaultdict(int)
    pay_trend_failed: dict[str, int] = defaultdict(int)
    for p in payments:
        day = _date_bucket(p.get("created_at") or "", bucket)
        if p.get("status") == "paid":
            pay_trend_paid[day] += 1
        elif p.get("status") in ("signature_failed", "failed"):
            pay_trend_failed[day] += 1
    all_pay_days = sorted(set(list(pay_trend_paid) + list(pay_trend_failed)))
    payment_trend = [
        {"date": d, "paid": pay_trend_paid.get(d, 0), "failed": pay_trend_failed.get(d, 0)}
        for d in all_pay_days
    ]

    # ── Subscription activation trend (from timeline if available) ──
    timeline_rows, tl_err = _safe(
        lambda: admin_client.table("subscription_timeline")
        .select("event_type, created_at")
        .eq("event_type", "activated")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    activation_trend_data: dict[str, int] = defaultdict(int)
    for t in (timeline_rows or []):
        day = _date_bucket(t.get("created_at") or "", bucket)
        activation_trend_data[day] += 1
    activation_trend = [{"date": k, "count": v} for k, v in sorted(activation_trend_data.items())]

    # ── Offer redemption trend ──
    redemptions, _ = _safe(
        lambda: admin_client.table("offer_redemptions")
        .select("enrolled_at")
        .gte("enrolled_at", since)
        .order("enrolled_at")
        .execute()
    )
    offer_trend_data: dict[str, int] = defaultdict(int)
    for r in (redemptions or []):
        day = _date_bucket(r.get("enrolled_at") or "", bucket)
        offer_trend_data[day] += 1
    offer_trend = [{"date": k, "count": v} for k, v in sorted(offer_trend_data.items())]

    # ── AI usage trend (graceful) ──
    ai_rows, ai_err = _safe(
        lambda: admin_client.table("ai_usage_logs")
        .select("tokens_used, created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    ai_trend: list | None = None
    if not ai_err and ai_rows is not None:
        ai_by_day: dict[str, int] = defaultdict(int)
        for r in ai_rows:
            day = _date_bucket(r.get("created_at") or "", bucket)
            ai_by_day[day] += r.get("tokens_used", 0)
        ai_trend = [{"date": k, "tokens": v} for k, v in sorted(ai_by_day.items())]

    # ── Mock test trend (graceful) ──
    test_rows, test_err = _safe(
        lambda: admin_client.table("test_history")
        .select("created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    test_trend: list | None = None
    if not test_err and test_rows is not None:
        test_by_day: dict[str, int] = defaultdict(int)
        for r in test_rows:
            day = _date_bucket(r.get("created_at") or "", bucket)
            test_by_day[day] += 1
        test_trend = [{"date": k, "count": v} for k, v in sorted(test_by_day.items())]

    return {
        "success": True,
        "period_days": days,
        "bucket": bucket,
        "signup_trend": signup_trend,
        "payment_trend": payment_trend,
        "subscription_activation_trend": activation_trend if not tl_err else None,
        "offer_redemption_trend": offer_trend,
        "ai_usage_trend": ai_trend,          # None if table unavailable
        "mock_test_trend": test_trend,        # None if table unavailable
        "data_availability": {
            "ai_usage_logs": ai_err is None,
            "test_history": test_err is None,
            "subscription_timeline": tl_err is None,
        },
    }
