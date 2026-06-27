"""
parent_dashboard_v2.py  —  /api/parent/*
─────────────────────────────────────────────────────────────────────────────
Parent Experience Platform — Phase 1

New endpoints:
  GET  /api/parent/dashboard/summary   — canonical parent dashboard
  GET  /api/parent/children/{id}/detail — enriched child detail

Safety rules:
- Parent can only see own linked children (parent_id match).
- parentId NEVER implies paid access.
- feature authorization uses canonical feature_authorization_service.
- teacher-private notes NEVER exposed.
- admin audit metadata NEVER exposed.
- Missing data sources return graceful empty/null (never crash).
- create-student child limit enforced from subscription resolver, not hardcoded.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth_service import require_parent, admin_client
from app.services.subscription_resolver_service import resolve_user_subscription
from app.services.feature_authorization_service import (
    get_feature_summary,
    Feature,
    FREE_MOCK_TEST_DAILY_LIMIT,
)

router = APIRouter()
_log = logging.getLogger("likhapoha.parent.v2")

_SAFE_Q = lambda fn: _safe_query(fn)  # noqa: E731

def _safe_query(fn):
    """Execute a Supabase query; return (data_list, error_str) — never crash."""
    try:
        r = fn()
        return (r.data or [], None)
    except Exception as exc:
        _log.warning("parent_dashboard_v2 query failed: %s", exc)
        return ([], str(exc)[:120])


def _safe_one(fn):
    """Execute a Supabase query; return (first_row | None, error_str)."""
    rows, err = _safe_query(fn)
    return (rows[0] if rows else None, err)


def _plan_display(cpk: str, plan_name: str, has_full: bool, expires_at, days_remaining) -> dict:
    """Build a human-friendly plan summary for parent UI."""
    expiry_warning = False
    if expires_at and days_remaining is not None:
        expiry_warning = days_remaining <= 3

    if cpk == "FREE_TIER":
        status_label = "Free Tier — Restricted"
        status_color = "restricted"
        description = "This child is on Free Tier with limited access."
    elif cpk == "NANO":
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for 8 days.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk in ("PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL"):
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for one child, 30 days.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL"):
        status_label = "Full Access"
        status_color = "paid"
        description = f"Full access for up to two children.{' Expiring soon!' if expiry_warning else ''}"
    elif cpk == "ADMIN_GRANT":
        status_label = "Admin Override / Full Access"
        status_color = "admin"
        description = "Full access granted by admin."
    else:
        status_label = "Free Tier — Restricted" if not has_full else "Full Access"
        status_color = "restricted" if not has_full else "paid"
        description = ""

    return {
        "canonical_plan_key": cpk,
        "plan_name": plan_name,
        "has_full_access": has_full,
        "status_label": status_label,
        "status_color": status_color,  # "restricted" | "paid" | "admin"
        "description": description,
        "expires_at": expires_at,
        "days_remaining": days_remaining,
        "expiry_warning": expiry_warning,
    }


def _build_feature_badges(features: dict) -> list:
    """Build UI-ready feature badge list from get_feature_summary output."""
    badge_map = [
        (Feature.LESSONS,           "Lessons",           "📖"),
        (Feature.MOCK_TEST,         "Mock Tests",        "📝"),
        (Feature.EXEMPLAR,          "Exemplar",          "🔬"),
        (Feature.EXEMPLAR_RESEARCH, "Exemplar Research", "🧪"),
        (Feature.ASK_DOUBTS,        "Ask Doubts",        "❓"),
        (Feature.AI_ASSISTANT,      "AI Assistant",      "🤖"),
    ]
    badges = []
    for feat_key, label, icon in badge_map:
        feat = features.get(feat_key, {})
        allowed = feat.get("allowed", False)
        limited = feat.get("limited", False)
        if allowed and not limited:
            state = "full"
        elif allowed and limited:
            state = "limited"
        else:
            state = "locked"
        badges.append({
            "feature": feat_key,
            "label": label,
            "icon": icon,
            "state": state,  # "full" | "limited" | "locked"
        })
    return badges


def _build_recommendations(child_username: str, sub: dict, features: dict,
                            mock_count: int, last_active: str | None) -> list:
    """Rule-based recommendations from available data. No external AI."""
    recs = []
    cpk = sub.get("canonical_plan_key", "FREE_TIER")
    has_full = sub.get("has_full_access", False)

    # Inactivity check
    if not last_active:
        recs.append({
            "type": "inactive",
            "title": "Encourage your child to log in",
            "body": "No recent activity recorded. Regular practice improves results.",
            "action": "view_progress",
            "priority": "medium",
        })
    else:
        try:
            la_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            if la_dt.tzinfo is None:
                la_dt = la_dt.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - la_dt).days
            if days_ago >= 7:
                recs.append({
                    "type": "inactive",
                    "title": f"Your child hasn't logged in for {days_ago} days",
                    "body": "Regular daily study leads to better exam results.",
                    "action": "view_progress",
                    "priority": "high" if days_ago >= 14 else "medium",
                })
        except Exception:
            pass

    # Free Tier upgrade nudge
    if cpk == "FREE_TIER":
        recs.append({
            "type": "upgrade",
            "title": "Unlock full platform access",
            "body": "Your child is on Free Tier with limited lessons, mock tests, and no Exemplar access. Upgrade to Premium for full CBSE coverage.",
            "action": "upgrade",
            "priority": "high",
        })

    # No mock tests
    if mock_count == 0:
        recs.append({
            "type": "mock_test",
            "title": "Try the first mock test",
            "body": "Mock tests help identify weak areas early. Attempt the first test today.",
            "action": "mock_tests",
            "priority": "medium",
        })

    # Exemplar locked
    if not features.get(Feature.EXEMPLAR, {}).get("allowed", False):
        recs.append({
            "type": "exemplar",
            "title": "Unlock NCERT Exemplar practice",
            "body": "Exemplar problems are key for scoring above 90% in CBSE. Upgrade to access them.",
            "action": "upgrade",
            "priority": "low",
        })

    # Expiry warning
    if sub.get("expiry_warning"):
        days = sub.get("days_remaining", 0)
        recs.append({
            "type": "expiry",
            "title": f"Plan expires in {days} day{'s' if days != 1 else ''}",
            "body": "Renew your subscription to maintain full access without interruption.",
            "action": "upgrade",
            "priority": "high",
        })

    return recs


def _build_notifications(child_name: str, sub: dict, mock_count: int,
                          last_active: str | None, avg_score: float | None) -> list:
    """Build parent notification list from available data."""
    notes = []
    cpk = sub.get("canonical_plan_key", "FREE_TIER")

    if sub.get("expiry_warning"):
        days = sub.get("days_remaining", 0)
        notes.append({
            "type": "expiry_warning",
            "icon": "⚠️",
            "title": f"{child_name}: Plan expires in {days} day{'s' if days != 1 else ''}",
            "body": "Renew now to avoid access interruption.",
            "priority": "high",
        })

    if not last_active:
        notes.append({
            "type": "inactive",
            "icon": "😴",
            "title": f"{child_name} hasn't logged in yet",
            "body": "Encourage daily study for best results.",
            "priority": "medium",
        })

    if avg_score is not None and avg_score < 40:
        notes.append({
            "type": "low_score",
            "icon": "📉",
            "title": f"{child_name} needs attention",
            "body": f"Average mock test score is {avg_score}%. Help identify weak chapters.",
            "priority": "high",
        })

    if cpk == "FREE_TIER":
        notes.append({
            "type": "upgrade",
            "icon": "🔒",
            "title": f"{child_name} is on Free Tier",
            "body": "Upgrade to unlock Exemplar, unlimited mock tests, and full AI lessons.",
            "priority": "low",
        })

    return notes


def _verify_child_ownership(parent_id: str, child_id: str) -> dict | None:
    """Return child profile if parent owns it, else None."""
    child, _ = _safe_one(
        lambda: admin_client.table("profiles")
        .select("id, username, grade, email, parent_id, family_id, account_status, subscription_plan, access_cbse, subscription_expires_at")
        .eq("id", child_id)
        .eq("parent_id", parent_id)
        .limit(1)
        .execute()
    )
    return child


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/dashboard/summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard/summary")
def get_parent_dashboard_summary(parent=Depends(require_parent)):
    """
    Canonical parent dashboard summary.

    Returns:
    - parent profile
    - children[] with subscription, feature summary, activity, recommendations, notifications
    - child_limit from subscription resolver
    - upgrade_eligible flag
    """
    parent_profile = parent["profile"]
    parent_id = parent_profile["id"]

    # Resolve parent's own subscription to determine child limit.
    # child_limit from resolver:
    #   FREE_TIER  → None (no explicit limit in resolver, defaults to 1 below)
    #   NANO       → 1
    #   PREMIUM    → 1
    #   FAMILY_PREMIUM → 2
    #   ADMIN_GRANT → None (unlimited — do NOT convert to 1)
    parent_sub = resolve_user_subscription(parent_id)
    parent_cpk = parent_sub.get("canonical_plan_key", "FREE_TIER")
    raw_child_limit = parent_sub.get("child_limit")  # may be None
    if raw_child_limit is not None:
        child_limit = raw_child_limit  # explicit value from resolver (1 or 2)
    elif parent_cpk == "ADMIN_GRANT":
        child_limit = None  # unlimited — admin can add any number of children
    elif parent_cpk in ("FAMILY_PREMIUM", "FAMILY_ANNUAL"):
        child_limit = 2
    else:
        child_limit = 1  # FREE_TIER, NANO, PREMIUM, expired = 1 child

    # Load children
    children_rows, _ = _safe_query(
        lambda: admin_client.table("profiles")
        .select("id, username, grade, email, parent_id, family_id, account_status, subscription_plan, access_cbse, subscription_expires_at")
        .eq("parent_id", parent_id)
        .execute()
    )

    children_summary = []
    all_notifications = []

    for child in children_rows:
        child_id = child["id"]
        child_username = child.get("username", "")

        # Canonical subscription from child's OWN profile
        child_sub = resolve_user_subscription(child_id)
        child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
        child_plan_name = child_sub.get("plan_name", "Free Tier")
        child_has_full = child_sub.get("has_full_access", False)
        child_expires = child_sub.get("valid_until")
        child_days_remaining = child_sub.get("days_remaining")
        child_expiry_warning = child_sub.get("expiring_soon", False)

        # Feature summary from canonical service
        feat_summary = get_feature_summary(child_id)
        features = feat_summary.get("features", {})
        feature_badges = _build_feature_badges(features)

        # Last active from ai_usage_logs
        now_iso = datetime.now(timezone.utc).isoformat()
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        activity_rows, _ = _safe_query(
            lambda: admin_client.table("ai_usage_logs")
            .select("created_at, feature")
            .eq("username", child_username)
            .gte("created_at", thirty_days_ago)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        last_active = activity_rows[0]["created_at"] if activity_rows else None
        recent_activity = [{"feature": r.get("feature"), "at": r.get("created_at")} for r in activity_rows[:3]]

        # Mock test summary from test_history
        test_rows, _ = _safe_query(
            lambda: admin_client.table("test_history")
            .select("score, total_questions, subject, created_at")
            .eq("username", child_username)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        mock_count = len(test_rows)
        scores = [(r.get("score") or 0) / (r.get("total_questions") or 1) * 100
                  for r in test_rows if (r.get("total_questions") or 0) > 0]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Plan display
        plan_display = _plan_display(
            child_cpk, child_plan_name, child_has_full,
            child_expires, child_days_remaining
        )
        plan_display["expiry_warning"] = child_expiry_warning

        # Recommendations
        recs = _build_recommendations(
            child_username, {**child_sub, "expiry_warning": child_expiry_warning},
            features, mock_count, last_active
        )

        # Notifications
        child_notes = _build_notifications(
            child.get("username", "Child"), child_sub,
            mock_count, last_active, avg_score
        )
        all_notifications.extend(child_notes)

        children_summary.append({
            "id": child_id,
            "name": child.get("username", ""),
            "grade": child.get("grade", "—"),
            "account_status": child.get("account_status", "active"),
            "plan": plan_display,
            "subscription": child_sub,
            "features": features,
            "feature_badges": feature_badges,
            "mock_test_summary": {
                "count": mock_count,
                "average_score": avg_score,
                "recent": [
                    {"subject": r.get("subject"), "score": r.get("score"),
                     "total": r.get("total_questions"), "at": r.get("created_at")}
                    for r in test_rows[:5]
                ],
                "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT if child_cpk == "FREE_TIER" else None,
            },
            "activity_summary": {
                "last_active": last_active,
                "recent": recent_activity,
            },
            "recommendations": recs,
            "notifications": child_notes,
        })

    # Sort notifications by priority
    prio_order = {"high": 0, "medium": 1, "low": 2}
    all_notifications.sort(key=lambda n: prio_order.get(n.get("priority", "low"), 3))

    # Parent plan display
    parent_plan = _plan_display(
        parent_cpk, parent_sub.get("plan_name", "Free Tier"),
        parent_sub.get("has_full_access", False),
        parent_sub.get("valid_until"), parent_sub.get("days_remaining"),
    )

    return {
        "success": True,
        "parent": {
            "id": parent_id,
            "username": parent_profile.get("username"),
            "email": parent_profile.get("email"),
            "family_id": parent_profile.get("family_id"),
        },
        "parent_plan": parent_plan,
        "parent_canonical_plan_key": parent_cpk,
        "child_limit": child_limit,
        "children_count": len(children_summary),
        "can_add_child": len(children_summary) < (child_limit if child_limit is not None else 999),
        "children": children_summary,
        "notifications": all_notifications,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/detail")
def get_child_detail(child_id: str, parent=Depends(require_parent)):
    """
    Enriched child detail for the parent's child detail view.
    Includes subscription, all feature access, progress, mock tests, doubts, recommendations.
    Teacher-private notes are NEVER included.
    """
    parent_profile = parent["profile"]
    parent_id = parent_profile["id"]

    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    child_username = child.get("username", "")

    # Canonical subscription
    child_sub = resolve_user_subscription(child_id)
    child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
    child_expiry_warning = child_sub.get("expiring_soon", False)

    # Feature summary
    feat_summary = get_feature_summary(child_id)
    features = feat_summary.get("features", {})
    feature_badges = _build_feature_badges(features)

    # Plan display
    plan_display = _plan_display(
        child_cpk, child_sub.get("plan_name", "Free Tier"),
        child_sub.get("has_full_access", False),
        child_sub.get("valid_until"), child_sub.get("days_remaining"),
    )
    plan_display["expiry_warning"] = child_expiry_warning

    # Activity
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    activity_rows, _ = _safe_query(
        lambda: admin_client.table("ai_usage_logs")
        .select("created_at, feature")
        .eq("username", child_username)
        .gte("created_at", thirty_days_ago)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    last_active = activity_rows[0]["created_at"] if activity_rows else None
    feature_counts: dict = {}
    for r in activity_rows:
        f = r.get("feature", "other")
        feature_counts[f] = feature_counts.get(f, 0) + 1

    # Mock tests
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, subject, created_at")
        .eq("username", child_username)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    mock_count = len(test_rows)
    scores = [(r.get("score") or 0) / (r.get("total_questions") or 1) * 100
              for r in test_rows if (r.get("total_questions") or 0) > 0]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Progress (chapter completions)
    progress_rows, _ = _safe_query(
        lambda: admin_client.table("chapter_progress")
        .select("subject, chapter, completed, current_step_index")
        .eq("username", child_username)
        .execute()
    )
    completed_chapters = [r for r in progress_rows if r.get("completed")]
    in_progress = [r for r in progress_rows if not r.get("completed") and (r.get("current_step_index") or 0) > 0]

    # Weak area alerts
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, step_title, best_score, created_at")
        .eq("username", child_username)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # Recommendations
    recs = _build_recommendations(
        child_username,
        {**child_sub, "expiry_warning": child_expiry_warning},
        features, mock_count, last_active,
    )

    # Notifications
    notifications = _build_notifications(
        child.get("username", "Child"), child_sub,
        mock_count, last_active, avg_score,
    )

    return {
        "success": True,
        "child": {
            "id": child_id,
            "name": child_username,
            "grade": child.get("grade", "—"),
            "account_status": child.get("account_status", "active"),
        },
        "plan": plan_display,
        "subscription": child_sub,
        "features": features,
        "feature_badges": feature_badges,
        "progress": {
            "available": len(progress_rows) > 0,
            "completed_chapters": len(completed_chapters),
            "in_progress_chapters": len(in_progress),
            "weak_topics": [
                {"subject": r.get("subject"), "chapter": r.get("chapter"), "score": r.get("best_score")}
                for r in weak_rows
            ],
        },
        "mock_tests": {
            "available": mock_count > 0,
            "count": mock_count,
            "average_score": avg_score,
            "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT if child_cpk == "FREE_TIER" else None,
            "recent": [
                {"subject": r.get("subject"), "score": r.get("score"),
                 "total": r.get("total_questions"), "at": r.get("created_at")}
                for r in test_rows[:5]
            ],
        },
        "ai_activity": {
            "available": len(activity_rows) > 0,
            "last_active": last_active,
            "feature_counts": feature_counts,
            "is_limited": child_cpk == "FREE_TIER",
        },
        "recommendations": recs,
        "notifications": notifications,
    }
