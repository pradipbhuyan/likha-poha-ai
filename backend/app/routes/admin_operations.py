"""
admin_operations.py  —  /api/admin/operations/*
─────────────────────────────────────────────────────────────────────────────
Operations Dashboard endpoints — admin only.

All endpoints require role=admin via require_admin dependency.
No secrets, tokens, API keys, passwords, JWTs, or raw webhook payloads
are returned from any endpoint.

Endpoints:
  GET  /summary       — combined health + payment + subscription + usage snapshot
  GET  /health        — app and dependency health
  GET  /payments      — payment metrics and recent events
  GET  /webhooks      — webhook event metrics (from audit_logs)
  GET  /subscriptions — subscription plan counts + timeline events
  GET  /usage         — user/signup/teacher/student counts + rate-limit events
  GET  /alerts        — recent audit events for failures and alerts
  POST /run-expiry-job — trigger the expiry job (also available at /api/subscription/)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.services.auth_service import admin_client, require_admin
from app.services.metrics_service import get_counters
from app.services.expiry_job_service import run_expiry_job

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _safe_query(fn):
    """Execute a Supabase query and return data + any error string."""
    try:
        result = fn()
        return (result.data or []), None
    except Exception as exc:
        return [], str(exc)


def _safe_count(table: str, filters: dict | None = None) -> int:
    """Count rows in a table with optional equality filters. Returns 0 on error."""
    try:
        q = admin_client.table(table).select("id", count="exact")
        for col, val in (filters or {}).items():
            q = q.eq(col, val)
        r = q.execute()
        return r.count or 0
    except Exception:
        return 0


# ── 1. System Health ──────────────────────────────────────────────────────────

@router.get("/health")
def operations_health(admin=Depends(require_admin)):
    """
    Return application health, dependency connectivity, and config readiness.
    Never exposes secret values — only presence/absence.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Supabase connectivity check
    db_ok = False
    db_error = None
    try:
        resp = admin_client.table("profiles").select("id").limit(1).execute()
        db_ok = True
    except Exception as exc:
        db_error = str(exc)[:120]

    # Config presence check (no values exposed)
    from app.config import settings  # noqa: PLC0415
    config_status = {
        "SUPABASE_URL": bool(getattr(settings, "SUPABASE_URL", None)),
        "SUPABASE_SERVICE_KEY": bool(getattr(settings, "SUPABASE_SERVICE_KEY", None)),
        "RAZORPAY_KEY_ID": bool(getattr(settings, "RAZORPAY_KEY_ID", None)),
        "RAZORPAY_KEY_SECRET": bool(getattr(settings, "RAZORPAY_KEY_SECRET", None)),
        "RAZORPAY_WEBHOOK_SECRET": bool(getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)),
        "OPENAI_API_KEY": bool(getattr(settings, "OPENAI_API_KEY", None)),
    }
    all_critical = config_status["SUPABASE_URL"] and config_status["SUPABASE_SERVICE_KEY"]

    return {
        "success": True,
        "checked_at": now_iso,
        "app": {
            "status": "ok",
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
        "config": config_status,
        "config_critical_ok": all_critical,
        "overall_healthy": db_ok and all_critical,
    }


# ── 2. Payment Monitoring ─────────────────────────────────────────────────────

@router.get("/payments")
def operations_payments(
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin=Depends(require_admin),
):
    """
    Payment success/failure counts, recent failures, duplicate/idempotent events.
    Uses subscription_payments table + in-memory metrics counters.
    """
    since = _days_ago(days)
    offset = (page - 1) * page_size

    # Total payments in period
    payments, pay_err = _safe_query(
        lambda: admin_client.table("subscription_payments")
        .select("id, status, plan_key, amount, created_at, razorpay_order_id, razorpay_payment_id")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .execute()
    )

    # Counts by status
    status_counts: dict[str, int] = {}
    for p in payments:
        s = p.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    paid = status_counts.get("paid", 0)
    failed = status_counts.get("signature_failed", 0) + status_counts.get("failed", 0)
    total = len(payments)
    success_rate = round(paid / total * 100, 1) if total > 0 else None

    # Recent failures (last 20)
    recent_failures = [
        {
            "order_id": p.get("razorpay_order_id"),
            "status": p.get("status"),
            "plan_key": p.get("plan_key"),
            "amount": p.get("amount"),
            "created_at": (p.get("created_at") or "")[:19],
        }
        for p in payments
        if p.get("status") not in ("paid", "created")
    ][:20]

    # Recent paid payments (paginated)
    recent_paid = [
        {
            "order_id": p.get("razorpay_order_id"),
            "plan_key": p.get("plan_key"),
            "amount": p.get("amount"),
            "created_at": (p.get("created_at") or "")[:19],
        }
        for p in payments
        if p.get("status") == "paid"
    ][offset: offset + page_size]

    # In-memory counters (labelled clearly as process-local)
    counters = get_counters()

    return {
        "success": True,
        "period_days": days,
        "data_source": "database",
        "summary": {
            "total_payments": total,
            "paid": paid,
            "signature_failed": status_counts.get("signature_failed", 0),
            "failed": failed,
            "created_pending": status_counts.get("created", 0),
            "success_rate_percent": success_rate,
        },
        "in_memory_counters": {
            "_note": "Process-local counters — resets on server restart",
            "payment.verified": counters.get("payment.verified", 0),
            "payment.verify_idempotent": counters.get("payment.verify_idempotent", 0),
            "payment.admin_test_verified": counters.get("payment.admin_test_verified", 0),
        },
        "recent_failures": recent_failures,
        "recent_paid": recent_paid,
        "page": page,
        "page_size": page_size,
        "error": pay_err,
    }


# ── 3. Webhook Monitoring ─────────────────────────────────────────────────────

@router.get("/webhooks")
def operations_webhooks(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_admin),
):
    """
    Webhook metrics from audit_logs + in-memory counters.
    Returns counts, recent errors, and last received timestamp.
    """
    since = _days_ago(days)
    counters = get_counters()

    # Webhook events from audit logs
    webhook_events, wh_err = _safe_query(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, created_at, metadata")
        .like("event_type", "webhook%")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    # Also check subscription_payments for webhook-confirmed events
    wh_confirmed, _ = _safe_query(
        lambda: admin_client.table("subscription_payments")
        .select("id, created_at, razorpay_order_id, plan_key")
        .gte("created_at", since)
        .eq("status", "paid")
        .execute()
    )
    webhook_confirmed_count = sum(
        1 for p in wh_confirmed
        if (p.get("metadata") or {}).get("webhook_confirmed")
    )

    last_received = webhook_events[0].get("created_at") if webhook_events else None

    return {
        "success": True,
        "period_days": days,
        "data_source_audit": "database",
        "in_memory_counters": {
            "_note": "Process-local counters — resets on server restart",
        },
        "webhook_confirmed_via_db": webhook_confirmed_count,
        "recent_webhook_audit_events": [
            {
                "event_type": e.get("event_type"),
                "created_at": (e.get("created_at") or "")[:19],
            }
            for e in webhook_events[:10]
        ],
        "last_received": (last_received or "")[:19] or None,
        "error": wh_err,
    }


# ── 4. Subscription Monitoring ────────────────────────────────────────────────

@router.get("/subscriptions")
def operations_subscriptions(
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    admin=Depends(require_admin),
):
    """
    Active subscription counts by plan + timeline events.
    Plan-key mapping: free→Nano, starter→Premium, family_premium→Family Premium.
    """
    since = _days_ago(days)
    counters = get_counters()

    # Active subscriptions by plan key
    # Count profiles by subscription_plan (students + parents with access_cbse)
    plan_names = {
        "free": "Nano",
        "starter": "Premium",
        "premium": "Premium",
        "family_premium": "Family Premium",
    }
    plan_counts: dict[str, int] = {}
    free_tier_count = 0

    profiles, prof_err = _safe_query(
        lambda: admin_client.table("profiles")
        .select("subscription_plan, access_cbse, subscription_expires_at, role")
        .in_("role", ["student", "parent"])
        .execute()
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    for p in profiles:
        plan = p.get("subscription_plan") or "free"
        has_access = bool(p.get("access_cbse"))
        expires = p.get("subscription_expires_at")
        is_active = has_access and (not expires or expires > now_iso)

        if not has_access:
            free_tier_count += 1
        elif is_active:
            label = plan_names.get(plan, plan)
            plan_counts[label] = plan_counts.get(label, 0) + 1

    # Recent timeline events
    timeline_events, tl_err = _safe_query(
        lambda: admin_client.table("subscription_timeline")
        .select("user_id, event_type, from_plan, to_plan, source, created_at")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(page_size)
        .execute()
    )

    # Timeline event type counts
    tl_counts: dict[str, int] = {}
    for e in timeline_events:
        k = e.get("event_type", "unknown")
        tl_counts[k] = tl_counts.get(k, 0) + 1

    return {
        "success": True,
        "period_days": days,
        "data_source": "database",
        "active_subscriptions": {
            "FREE_TIER": free_tier_count,
            **plan_counts,
        },
        "timeline_event_counts": tl_counts,
        "recent_timeline_events": [
            {
                "event_type": e.get("event_type"),
                "from_plan": e.get("from_plan"),
                "to_plan": e.get("to_plan"),
                "source": e.get("source"),
                "created_at": (e.get("created_at") or "")[:19],
            }
            for e in timeline_events
        ],
        "in_memory_counters": {
            "_note": "Process-local counters — resets on server restart",
            "subscription.activated": counters.get("subscription.activated", 0),
            "subscription.expired": counters.get("subscription.expired", 0),
            "subscription.fallback_applied": counters.get("subscription.fallback_applied", 0),
        },
        "error": prof_err or tl_err,
    }


# ── 5. User & Usage Metrics ───────────────────────────────────────────────────

@router.get("/usage")
def operations_usage(admin=Depends(require_admin)):
    """
    Signup counts by role, teacher/student assignments, and rate-limit events.
    """
    counters = get_counters()

    # Profile counts by role
    profiles, prof_err = _safe_query(
        lambda: admin_client.table("profiles")
        .select("role, created_at")
        .execute()
    )
    role_counts: dict[str, int] = {"student": 0, "parent": 0, "teacher": 0, "admin": 0}
    for p in profiles:
        r = p.get("role", "student")
        role_counts[r] = role_counts.get(r, 0) + 1

    # Teacher-student assignments
    assignment_count = _safe_count("teacher_student_assignments")

    # Offer redemptions
    offer_count = _safe_count("offer_redemptions")

    return {
        "success": True,
        "data_source": "database",
        "users": {
            "total": len(profiles),
            **role_counts,
        },
        "teacher_student_assignments": assignment_count,
        "offer_redemptions": offer_count,
        "in_memory_counters": {
            "_note": "Process-local counters — resets on server restart",
            "rate_limit.exceeded": counters.get("rate_limit.exceeded", 0),
            "signup.success": counters.get("signup.success", 0),
            "login.success": counters.get("login.success", 0),
            "login.failure": counters.get("login.failure", 0),
            "teacher.student_created": counters.get("teacher.student_created", 0),
        },
        "error": prof_err,
    }


# ── 6. Alerts & Incidents ─────────────────────────────────────────────────────

@router.get("/alerts")
def operations_alerts(
    days: int = Query(default=7, ge=1, le=90),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    admin=Depends(require_admin),
):
    """
    Recent audit log events for failures, expiry job, and rate-limit spikes.
    Returns only event_type, created_at, entity_id — no secret metadata.
    """
    since = _days_ago(days)
    offset = (page - 1) * page_size

    # Alert-level event types we care about
    alert_event_types = [
        "payment.verify_failed",
        "subscription.expired",
        "expiry_job.ran",
        "rate_limit.exceeded",
    ]

    all_alerts, alert_err = _safe_query(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, entity_type, entity_id, created_at")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )

    # Filter to alert events
    filtered = [
        e for e in all_alerts
        if any(e.get("event_type", "").startswith(t.split(".")[0]) for t in alert_event_types)
        or e.get("event_type") in alert_event_types
    ]

    paginated = filtered[offset: offset + page_size]
    type_counts: dict[str, int] = {}
    for e in filtered:
        k = e.get("event_type", "unknown")
        type_counts[k] = type_counts.get(k, 0) + 1

    counters = get_counters()

    return {
        "success": True,
        "period_days": days,
        "data_source": "database",
        "alert_counts": type_counts,
        "recent_alerts": [
            {
                "event_type": e.get("event_type"),
                "entity_type": e.get("entity_type"),
                "entity_id": e.get("entity_id"),
                "created_at": (e.get("created_at") or "")[:19],
            }
            for e in paginated
        ],
        "in_memory_rate_limit_exceeded": counters.get("rate_limit.exceeded", 0),
        "page": page,
        "page_size": page_size,
        "total_alerts_in_period": len(filtered),
        "error": alert_err,
    }


# ── 7. Expiry Job ─────────────────────────────────────────────────────────────

@router.get("/expiry-job-status")
def operations_expiry_job_status(admin=Depends(require_admin)):
    """
    Return the last expiry job run info from audit logs.
    """
    events, err = _safe_query(
        lambda: admin_client.table("platform_audit_logs")
        .select("event_type, metadata, created_at")
        .eq("event_type", "expiry_job.ran")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    last_run = None
    last_run_summary = None
    if events:
        last_run = (events[0].get("created_at") or "")[:19]
        last_run_summary = events[0].get("metadata") or {}

    counters = get_counters()
    return {
        "success": True,
        "last_run": last_run,
        "last_run_summary": last_run_summary,
        "in_memory_counters": {
            "expiry_job.ran": counters.get("expiry_job.ran", 0),
            "expiry_job.users_revoked": counters.get("expiry_job.users_revoked", 0),
            "subscription.expired": counters.get("subscription.expired", 0),
        },
        "recent_runs": [
            {
                "ran_at": (e.get("created_at") or "")[:19],
                "summary": e.get("metadata") or {},
            }
            for e in events
        ],
        "error": err,
    }


@router.post("/run-expiry-job")
def operations_run_expiry_job(admin=Depends(require_admin)):
    """
    Admin-only: trigger the subscription expiry job immediately.
    Idempotent — safe to run multiple times.
    """
    summary = run_expiry_job()
    return {"success": True, **summary}


# ── 8. Summary (combined snapshot) ───────────────────────────────────────────

@router.get("/summary")
def operations_summary(admin=Depends(require_admin)):
    """
    Combined snapshot for the Operations Dashboard landing card.
    Returns health + payment totals + subscription counts + user counts.
    All data is safe — no secrets.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    since_30 = _days_ago(30)

    # Health
    db_ok = False
    try:
        admin_client.table("profiles").select("id").limit(1).execute()
        db_ok = True
    except Exception:
        pass

    # Payments (30-day)
    payments, _ = _safe_query(
        lambda: admin_client.table("subscription_payments")
        .select("status, amount")
        .gte("created_at", since_30)
        .execute()
    )
    status_counts: dict[str, int] = {}
    for p in payments:
        s = p.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    paid = status_counts.get("paid", 0)
    total_pay = len(payments)
    success_rate = round(paid / total_pay * 100, 1) if total_pay > 0 else None

    # Users
    profiles, _ = _safe_query(
        lambda: admin_client.table("profiles").select("role").execute()
    )
    role_counts: dict[str, int] = {"student": 0, "parent": 0, "teacher": 0}
    for p in profiles:
        r = p.get("role", "student")
        if r in role_counts:
            role_counts[r] += 1

    # Active subscriptions
    now = datetime.now(timezone.utc).isoformat()
    active_paid = sum(
        1 for p in profiles
        if p.get("access_cbse")
        and (not p.get("subscription_expires_at") or p.get("subscription_expires_at", "") > now)
    )

    counters = get_counters()

    return {
        "success": True,
        "generated_at": now_iso,
        "health": {
            "database_connected": db_ok,
            "overall_ok": db_ok,
        },
        "payments_30d": {
            "total": total_pay,
            "paid": paid,
            "failed": status_counts.get("signature_failed", 0),
            "success_rate_percent": success_rate,
        },
        "users": {
            "total": len(profiles),
            **role_counts,
        },
        "in_memory_metrics": {
            "_note": "Process-local — resets on restart",
            "payment.verified": counters.get("payment.verified", 0),
            "subscription.expired": counters.get("subscription.expired", 0),
            "rate_limit.exceeded": counters.get("rate_limit.exceeded", 0),
            "expiry_job.ran": counters.get("expiry_job.ran", 0),
        },
    }
