"""
admin_analytics.py  —  /api/admin/analytics/*
─────────────────────────────────────────────────────────────────────────────
Admin analytics endpoints — admin only.
All data is aggregated; no individual user secrets are exposed.

Each metric now carries an explicit state so the frontend can render:
  "ok"            → value is accurate (may be 0)
  "table_missing" → optional table not yet migrated (not_available)
  "query_error"   → real DB/network error (unable_to_load)

Endpoints:
  GET /analytics/summary  — aggregate counts across all data sources
  GET /analytics/trends   — time-bucketed trends by days
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query

from app.services.auth_service import admin_client, require_admin

router = APIRouter()
logger = logging.getLogger("likhapoha.analytics")

# ── State constants ───────────────────────────────────────────────────────────
STATE_OK      = "ok"
STATE_MISSING = "table_missing"   # PGRST205 / relation does not exist
STATE_ERROR   = "query_error"     # real failure — should be logged + surfaced


# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_missing_table(err: str) -> bool:
    """Return True if error indicates the table does not exist."""
    err_lower = err.lower()
    return (
        "PGRST205" in err
        or "schema cache" in err_lower
        or "relation" in err_lower and "does not exist" in err_lower
        or "undefined_table" in err_lower
    )


def _safe(fn, *, context: str = ""):
    """
    Execute a Supabase query and return (data, error_message, state).

    States:
      STATE_OK       — query succeeded; data may be empty list
      STATE_MISSING  — table doesn't exist (PGRST205 / relation not found)
      STATE_ERROR    — unexpected failure; error is logged server-side
    """
    try:
        r = fn()
        return r.data or [], None, STATE_OK
    except Exception as exc:
        err = str(exc)
        if _is_missing_table(err):
            return [], None, STATE_MISSING
        # Real error — log it so it doesn't vanish silently
        logger.warning("analytics query error [%s]: %s", context or "?", err[:300])
        return [], err[:200], STATE_ERROR


def _date_bucket(iso_ts: str, bucket: str = "day") -> str:
    """Truncate ISO timestamp to day or week string for grouping."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if bucket == "week":
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

    Each section includes:
      query_ok    (bool)  — True if the DB query succeeded
      query_error (str|None) — error message if query_ok=False
    """
    since = _days_ago(days)
    now = _now()

    # ── Users (profiles — required table) ──────────────────────────────
    all_profiles, profiles_err, profiles_state = _safe(
        lambda: admin_client.table("profiles")
        .select("role, access_cbse, subscription_plan, subscription_expires_at, created_at")
        .execute(),
        context="profiles",
    )
    profiles_ok = profiles_state == STATE_OK

    total_users = len(all_profiles)
    roles: Counter = Counter()
    new_signups = 0
    free_users = 0
    paid_active = 0
    admin_granted = 0

    if profiles_ok:
        roles = Counter(p.get("role", "unknown") for p in all_profiles)
        new_signups = sum(1 for p in all_profiles if (p.get("created_at") or "") >= since)
        free_users  = sum(1 for p in all_profiles if not p.get("access_cbse"))
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

    # ── Payments (subscription_payments — required table) ──────────────
    payments, payments_err, payments_state = _safe(
        lambda: admin_client.table("subscription_payments")
        .select("status, amount, created_at")
        .gte("created_at", since)
        .execute(),
        context="subscription_payments",
    )
    payments_ok = payments_state == STATE_OK

    pay_counts: Counter = Counter()
    total_paid_count = 0
    total_failed_count = 0
    conversion_rate: float | None = None

    if payments_ok:
        pay_counts    = Counter(p.get("status", "unknown") for p in payments)
        total_paid_count   = pay_counts.get("paid", 0)
        total_failed_count = (
            pay_counts.get("signature_failed", 0)
            + pay_counts.get("failed", 0)
        )
        conversion_rate = (
            round(total_paid_count / len(payments) * 100, 1) if payments else 0.0
        )

    # ── Offer redemptions (optional) ───────────────────────────────────
    redemptions, redemptions_err, redemptions_state = _safe(
        lambda: admin_client.table("offer_redemptions")
        .select("enrolled_at")
        .gte("enrolled_at", since)
        .execute(),
        context="offer_redemptions",
    )

    # ── Teacher assignments (optional — may not exist yet) ─────────────
    assignments, assignments_err, assignments_state = _safe(
        lambda: admin_client.table("teacher_student_assignments")
        .select("created_at")
        .execute(),
        context="teacher_student_assignments",
    )

    # ── AI usage (optional) ────────────────────────────────────────────
    ai_rows, ai_err, ai_state = _safe(
        lambda: admin_client.table("ai_usage_logs")
        .select("tokens_used, created_at")
        .gte("created_at", since)
        .execute(),
        context="ai_usage_logs",
    )
    ai_available = ai_state == STATE_OK
    ai_tokens    = sum(r.get("tokens_used", 0) for r in ai_rows) if ai_available else None
    ai_requests  = len(ai_rows) if ai_available else None

    # ── Mock test history (optional) ───────────────────────────────────
    test_rows, test_err, test_state = _safe(
        lambda: admin_client.table("test_history")
        .select("created_at")
        .gte("created_at", since)
        .execute(),
        context="test_history",
    )
    test_available = test_state == STATE_OK
    mock_tests_completed = len(test_rows) if test_available else None

    return {
        "success": True,
        "period_days": days,
        # ── Users ──────────────────────────────────────────────────────
        "users": {
            "total": total_users,
            "by_role": dict(roles),
            "new_signups_in_period": new_signups,
            "free_no_access": free_users,
            "paid_active": paid_active,
            "admin_granted_access": admin_granted,
            "query_ok": profiles_ok,
            "query_error": profiles_err if not profiles_ok else None,
        },
        # ── Payments ───────────────────────────────────────────────────
        "payments": {
            "total_in_period": len(payments) if payments_ok else None,
            "paid": total_paid_count if payments_ok else None,
            "failed": total_failed_count if payments_ok else None,
            "conversion_rate_percent": conversion_rate,
            "query_ok": payments_ok,
            "query_error": payments_err if not payments_ok else None,
            "query_state": payments_state,
        },
        # ── Offer redemptions ──────────────────────────────────────────
        "offer_redemptions_in_period": len(redemptions) if redemptions_state == STATE_OK else None,
        "offer_redemptions_state": redemptions_state,
        "offer_redemptions_error": redemptions_err,
        # ── Teacher assignments ────────────────────────────────────────
        "teacher_student_assignments_total": len(assignments) if assignments_state == STATE_OK else None,
        "teacher_assignments_state": assignments_state,
        "teacher_assignments_error": assignments_err,
        # ── AI usage ───────────────────────────────────────────────────
        "ai_usage": {
            "requests_in_period": ai_requests,
            "tokens_in_period": ai_tokens,
            "available": ai_available,
            "state": ai_state,
            "error": ai_err,
        },
        # ── Mock tests ─────────────────────────────────────────────────
        "mock_tests_completed_in_period": mock_tests_completed,
        "mock_tests_state": test_state,
        "mock_tests_error": test_err,
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

    Every trend series includes a 'state' key:
      "ok"           — data present or zero for this period
      "table_missing" — table not yet migrated
      "query_error"  — DB error; 'error' key contains message
    """
    since = _days_ago(days)

    # ── Signup trend (required: profiles) ──────────────────────────────
    profiles, _, profiles_state = _safe(
        lambda: admin_client.table("profiles")
        .select("created_at, role")
        .gte("created_at", since)
        .order("created_at")
        .execute(),
        context="profiles (trend)",
    )
    signup_by_day: dict[str, int] = defaultdict(int)
    for p in profiles:
        day = _date_bucket(p.get("created_at") or "", bucket)
        signup_by_day[day] += 1
    signup_trend = [{"date": k, "count": v} for k, v in sorted(signup_by_day.items())]

    # ── Payment trend (required: subscription_payments) ─────────────────
    payments, payments_err, payments_state = _safe(
        lambda: admin_client.table("subscription_payments")
        .select("status, created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute(),
        context="subscription_payments (trend)",
    )
    pay_trend_paid: dict[str, int] = defaultdict(int)
    pay_trend_failed: dict[str, int] = defaultdict(int)
    for p in (payments if payments_state == STATE_OK else []):
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

    # ── Subscription activation trend (optional: subscription_timeline) ─
    timeline_rows, tl_err, tl_state = _safe(
        lambda: admin_client.table("subscription_timeline")
        .select("event_type, created_at")
        .eq("event_type", "activated")
        .gte("created_at", since)
        .order("created_at")
        .execute(),
        context="subscription_timeline",
    )
    activation_trend_data: dict[str, int] = defaultdict(int)
    for t in (timeline_rows if tl_state == STATE_OK else []):
        day = _date_bucket(t.get("created_at") or "", bucket)
        activation_trend_data[day] += 1
    activation_trend = [{"date": k, "count": v} for k, v in sorted(activation_trend_data.items())]

    # ── Offer redemption trend (optional: offer_redemptions) ────────────
    redemptions, redemptions_err, redemptions_state = _safe(
        lambda: admin_client.table("offer_redemptions")
        .select("enrolled_at")
        .gte("enrolled_at", since)
        .order("enrolled_at")
        .execute(),
        context="offer_redemptions (trend)",
    )
    offer_trend_data: dict[str, int] = defaultdict(int)
    for r in (redemptions if redemptions_state == STATE_OK else []):
        day = _date_bucket(r.get("enrolled_at") or "", bucket)
        offer_trend_data[day] += 1
    offer_trend = [{"date": k, "count": v} for k, v in sorted(offer_trend_data.items())]

    # ── AI usage trend (optional: ai_usage_logs) ────────────────────────
    ai_rows, ai_err, ai_state = _safe(
        lambda: admin_client.table("ai_usage_logs")
        .select("tokens_used, created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute(),
        context="ai_usage_logs (trend)",
    )
    ai_trend: list | None = None
    if ai_state == STATE_OK:
        ai_by_day: dict[str, int] = defaultdict(int)
        for r in ai_rows:
            day = _date_bucket(r.get("created_at") or "", bucket)
            ai_by_day[day] += r.get("tokens_used", 0)
        ai_trend = [{"date": k, "tokens": v} for k, v in sorted(ai_by_day.items())]

    # ── Mock test trend (optional: test_history) ────────────────────────
    test_rows, test_err, test_state = _safe(
        lambda: admin_client.table("test_history")
        .select("created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute(),
        context="test_history (trend)",
    )
    test_trend: list | None = None
    if test_state == STATE_OK:
        test_by_day: dict[str, int] = defaultdict(int)
        for r in test_rows:
            day = _date_bucket(r.get("created_at") or "", bucket)
            test_by_day[day] += 1
        test_trend = [{"date": k, "count": v} for k, v in sorted(test_by_day.items())]

    return {
        "success": True,
        "period_days": days,
        "bucket": bucket,
        # Signup trend
        "signup_trend": signup_trend,
        "signup_trend_state": profiles_state,
        # Payment trend
        "payment_trend": payment_trend,
        "payment_trend_state": payments_state,
        "payment_trend_error": payments_err,
        # Subscription activation trend
        "subscription_activation_trend": activation_trend,
        "subscription_activation_state": tl_state,
        # Offer redemptions trend
        "offer_redemption_trend": offer_trend,
        "offer_redemption_state": redemptions_state,
        # AI usage trend
        "ai_usage_trend": ai_trend,           # None if table missing/errored
        "ai_usage_trend_state": ai_state,
        "ai_usage_trend_error": ai_err,
        # Mock test trend
        "mock_test_trend": test_trend,         # None if table missing/errored
        "mock_test_trend_state": test_state,
        # Backwards-compatible data_availability block
        "data_availability": {
            "ai_usage_logs": ai_state == STATE_OK,
            "ai_usage_logs_state": ai_state,
            "test_history": test_state == STATE_OK,
            "test_history_state": test_state,
            "subscription_timeline": tl_state == STATE_OK,
            "subscription_timeline_state": tl_state,
            "offer_redemptions": redemptions_state == STATE_OK,
            "offer_redemptions_state": redemptions_state,
            "teacher_assignments": True,  # always from profiles/assignments
        },
    }
