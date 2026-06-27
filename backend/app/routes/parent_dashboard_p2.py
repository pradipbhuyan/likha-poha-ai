"""
parent_dashboard_p2.py  —  /api/parent/*  (Phase 2)
─────────────────────────────────────────────────────────────────────────────
Parent Experience Platform — Phase 2

New endpoints:
  GET  /api/parent/children/{id}/analytics      — richer progress analytics
  GET  /api/parent/children/{id}/academic-insights — homework/exam insights
  GET  /api/parent/children/{id}/progress-report   — print-friendly report
  GET  /api/parent/notifications                — notification center
  POST /api/parent/notifications/{id}/read      — mark one read
  POST /api/parent/notifications/read-all       — mark all read

Safety rules:
- Parent ownership enforced on every child endpoint
- Teacher-private notes NEVER exposed
- Admin audit metadata NEVER exposed
- Missing tables return available=false (never crash)
- Parent can only access own notifications
- Notification metadata is sanitized (no secrets/tokens)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth_service import require_parent, admin_client
from app.services.subscription_resolver_service import resolve_user_subscription
from app.services.feature_authorization_service import (
    get_feature_summary,
    Feature,
    FREE_MOCK_TEST_DAILY_LIMIT,
)
from app.routes.parent_dashboard_v2 import (
    _safe_query, _safe_one, _verify_child_ownership,
    _build_recommendations, _plan_display,
)

router = APIRouter()
_log = logging.getLogger("likhapoha.parent.p2")


# ── Structured metric helper ──────────────────────────────────────────────────
def _metric(label: str, value, available: bool = True, explanation: str = "") -> dict:
    return {"label": label, "value": value, "available": available, "explanation": explanation}


def _unavailable(label: str, explanation: str = "Not available yet.") -> dict:
    return {"label": label, "value": None, "available": False, "explanation": explanation}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/analytics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/analytics")
def get_child_analytics(child_id: str, parent=Depends(require_parent)):
    """
    Richer progress analytics for a parent's child.
    Parent ownership enforced. Missing data returns available=false.
    Teacher-private notes and admin audit data NEVER exposed.
    """
    parent_id = parent["profile"]["id"]
    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")

    # ── Mock test analytics ───────────────────────────────────────────────────
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, subject, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    mock_count = len(test_rows)
    pct_scores = [
        round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1)
        for r in test_rows if (r.get("total_questions") or 0) > 0
    ]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Subject averages
    subj_scores: dict = {}
    for r in test_rows:
        subj = r.get("subject") or "Unknown"
        pct = round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1) if (r.get("total_questions") or 0) > 0 else None
        if pct is not None:
            subj_scores.setdefault(subj, []).append(pct)
    subject_avgs = {s: round(sum(v)/len(v), 1) for s, v in subj_scores.items()}

    # Mock test trend (last 10)
    trend = []
    for i, r in enumerate(reversed(test_rows[:10])):
        total = r.get("total_questions") or 0
        score = r.get("score") or 0
        pct = round(score / total * 100, 1) if total > 0 else 0
        trend.append({"index": i + 1, "subject": r.get("subject", ""), "score": pct, "at": r.get("created_at")})

    # ── Chapter progress analytics ────────────────────────────────────────────
    prog_rows, _ = _safe_query(
        lambda: admin_client.table("chapter_progress")
        .select("subject, chapter, completed, current_step_index")
        .eq("username", username)
        .execute()
    )
    completed_ch = [r for r in prog_rows if r.get("completed")]
    in_progress_ch = [r for r in prog_rows if not r.get("completed") and (r.get("current_step_index") or 0) > 0]
    not_started = len(prog_rows) - len(completed_ch) - len(in_progress_ch)

    # Subject-wise progress
    subj_progress: dict = {}
    for r in prog_rows:
        subj = r.get("subject") or "Unknown"
        entry = subj_progress.setdefault(subj, {"total": 0, "completed": 0, "in_progress": 0})
        entry["total"] += 1
        if r.get("completed"):
            entry["completed"] += 1
        elif (r.get("current_step_index") or 0) > 0:
            entry["in_progress"] += 1

    # ── Weak areas ────────────────────────────────────────────────────────────
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, step_title, best_score, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # ── AI/doubt activity ─────────────────────────────────────────────────────
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    act_rows, _ = _safe_query(
        lambda: admin_client.table("ai_usage_logs")
        .select("created_at, feature")
        .eq("username", username)
        .gte("created_at", thirty_days_ago)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    last_active = act_rows[0]["created_at"] if act_rows else None
    feature_counts: dict = {}
    for r in act_rows:
        f = r.get("feature", "other")
        feature_counts[f] = feature_counts.get(f, 0) + 1
    lessons_count = feature_counts.get("lesson", 0)
    doubts_count = feature_counts.get("doubt", 0)

    # ── Strengths (subjects with avg score ≥ 70%) ────────────────────────────
    strong_subjects = [s for s, avg in subject_avgs.items() if avg >= 70]
    weak_subjects = [s for s, avg in subject_avgs.items() if avg < 50]

    # ── Data availability flags ───────────────────────────────────────────────
    has_mock_data = mock_count > 0
    has_progress_data = len(prog_rows) > 0
    has_activity_data = len(act_rows) > 0
    has_weak_data = len(weak_rows) > 0

    return {
        "success": True,
        "child_id": child_id,
        "child_name": username,

        "progress": {
            "available": has_progress_data,
            "total_chapters_tracked": _metric("Chapters Tracked", len(prog_rows), has_progress_data),
            "completed_chapters": _metric("Completed", len(completed_ch), has_progress_data),
            "in_progress_chapters": _metric("In Progress", len(in_progress_ch), has_progress_data),
            "not_started": _metric("Not Started", not_started if has_progress_data else None, has_progress_data),
            "subject_wise": subj_progress if has_progress_data else {},
        },

        "mock_tests": {
            "available": has_mock_data,
            "total_tests": _metric("Tests Taken", mock_count, has_mock_data),
            "average_score": _metric("Average Score", f"{avg_score}%" if avg_score else None, has_mock_data,
                                     "Based on all mock tests taken"),
            "subject_averages": subject_avgs if has_mock_data else {},
            "trend": trend,
            "free_daily_limit": FREE_MOCK_TEST_DAILY_LIMIT,
        },

        "strengths": {
            "available": has_mock_data and len(strong_subjects) > 0,
            "strong_subjects": strong_subjects,
            "completed_topics": [
                {"subject": r.get("subject"), "chapter": r.get("chapter")}
                for r in completed_ch[:5]
            ],
        },

        "weaknesses": {
            "available": has_weak_data or (has_mock_data and len(weak_subjects) > 0),
            "weak_subjects": weak_subjects,
            "weak_topics": [
                {
                    "subject": r.get("subject"),
                    "chapter": r.get("chapter"),
                    "score": r.get("best_score"),
                    "explanation": "Scored below average on this topic",
                }
                for r in weak_rows
            ],
        },

        "activity": {
            "available": has_activity_data,
            "last_active": last_active,
            "lessons_this_month": _metric("Lessons Generated", lessons_count, has_activity_data),
            "doubts_this_month": _metric("Doubts Asked", doubts_count, has_activity_data),
            "active_days": _metric(
                "Active Days (30d)",
                len({r["created_at"][:10] for r in act_rows if r.get("created_at")}),
                has_activity_data,
            ),
        },

        "ai_usage": {
            "available": has_activity_data,
            "feature_breakdown": feature_counts,
            "total_ai_requests": len(act_rows),
            "is_limited": resolve_user_subscription(child_id).get("canonical_plan_key") == "FREE_TIER",
        },

        "data_availability": {
            "progress": has_progress_data,
            "mock_tests": has_mock_data,
            "activity": has_activity_data,
            "weak_areas": has_weak_data,
            "homework": False,
            "exams": False,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/academic-insights
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/academic-insights")
def get_academic_insights(child_id: str, parent=Depends(require_parent)):
    """
    Homework and exam insights for a parent's child.
    Homework/exam tables do not exist yet — returns available=false gracefully.
    Mock test recommendations returned if data exists.
    """
    parent_id = parent["profile"]["id"]
    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")

    # Mock test data for recommendations
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, subject, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    mock_count = len(test_rows)
    pct_scores = [
        round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1)
        for r in test_rows if (r.get("total_questions") or 0) > 0
    ]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Weak areas for revision suggestions
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, best_score")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # Mock test recommendations
    mock_recommendations = []
    if mock_count == 0:
        mock_recommendations.append({
            "type": "start_mock_test",
            "title": "Start your first mock test",
            "description": "Mock tests help identify weak areas early. Try a chapter-wise test today.",
            "priority": "high",
        })
    elif avg_score is not None and avg_score < 50:
        mock_recommendations.append({
            "type": "improve_score",
            "title": "Focus on revision",
            "description": f"Average mock test score is {avg_score}%. Review weak topics before the next test.",
            "priority": "high",
        })
        for w in weak_rows[:3]:
            mock_recommendations.append({
                "type": "revise_topic",
                "title": f"Revise: {w.get('chapter', 'Unknown')}",
                "description": f"Subject: {w.get('subject', '')}. Practice more questions on this topic.",
                "priority": "medium",
            })
    elif avg_score is not None and avg_score >= 70:
        mock_recommendations.append({
            "type": "maintain_progress",
            "title": "Great progress — keep the streak going",
            "description": f"Average score is {avg_score}%. Maintain consistent practice to keep improving.",
            "priority": "low",
        })

    return {
        "success": True,
        "child_id": child_id,

        "homework": {
            "available": False,
            "message": "Homework tracking is not enabled yet. Homework assignments will appear here when available.",
            "upcoming": [],
            "overdue": [],
            "completed": [],
        },

        "exams": {
            "available": False,
            "message": "Exam schedule is not available yet. Upcoming exams will appear here when scheduled.",
            "upcoming": [],
        },

        "mock_test_recommendations": {
            "available": True,
            "recommendations": mock_recommendations,
            "total_tests": mock_count,
            "average_score": avg_score,
        },

        "revision_suggestions": {
            "available": len(weak_rows) > 0,
            "topics": [
                {
                    "subject": r.get("subject"),
                    "chapter": r.get("chapter"),
                    "description": "Review and practice this topic again.",
                }
                for r in weak_rows[:5]
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/children/{child_id}/progress-report
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/children/{child_id}/progress-report")
def get_progress_report(child_id: str, parent=Depends(require_parent)):
    """
    Print-friendly progress report for a parent's child.
    Excludes teacher-private notes and admin audit data entirely.
    """
    parent_id = parent["profile"]["id"]
    child = _verify_child_ownership(parent_id, child_id)
    if not child:
        raise HTTPException(status_code=403, detail="Child not found or not linked to this parent.")

    username = child.get("username", "")
    child_sub = resolve_user_subscription(child_id)
    child_cpk = child_sub.get("canonical_plan_key", "FREE_TIER")
    feat_summary = get_feature_summary(child_id)
    features = feat_summary.get("features", {})

    plan = _plan_display(
        child_cpk, child_sub.get("plan_name", "Free Tier"),
        child_sub.get("has_full_access", False),
        child_sub.get("valid_until"), child_sub.get("days_remaining"),
    )

    # Progress
    prog_rows, _ = _safe_query(
        lambda: admin_client.table("chapter_progress")
        .select("subject, chapter, completed, current_step_index")
        .eq("username", username)
        .execute()
    )
    completed_ch = [r for r in prog_rows if r.get("completed")]

    # Mock tests
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("score, total_questions, subject, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    pct_scores = [
        round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1)
        for r in test_rows if (r.get("total_questions") or 0) > 0
    ]
    avg_score = round(sum(pct_scores) / len(pct_scores), 1) if pct_scores else None

    # Weak areas
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, best_score")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # Strengths/weaknesses from subject averages
    subj_scores: dict = {}
    for r in test_rows:
        subj = r.get("subject") or "Unknown"
        pct = round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1) if (r.get("total_questions") or 0) > 0 else None
        if pct is not None:
            subj_scores.setdefault(subj, []).append(pct)
    subject_avgs = {s: round(sum(v)/len(v), 1) for s, v in subj_scores.items()}

    # Recommendations (no teacher notes, no audit data)
    recs = _build_recommendations(
        username,
        {**child_sub, "expiry_warning": child_sub.get("expiring_soon", False)},
        features, len(test_rows), None,
    )

    return {
        "success": True,
        "report_type": "parent_progress_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "child": {
            "id": child_id,
            "name": username,
            "grade": child.get("grade", "—"),
            "board": child.get("board", "CBSE"),
        },

        "access_summary": {
            "plan": plan,
            "feature_highlights": [
                {"feature": k, "state": "full" if v.get("allowed") and not v.get("limited") else ("limited" if v.get("allowed") else "locked")}
                for k, v in features.items()
                if k in ("LESSONS", "MOCK_TEST", "EXEMPLAR", "ASK_DOUBTS")
            ],
        },

        "progress_summary": {
            "available": len(prog_rows) > 0,
            "completed_chapters": len(completed_ch),
            "total_tracked": len(prog_rows),
            "recent_completions": [
                {"subject": r.get("subject"), "chapter": r.get("chapter")}
                for r in completed_ch[:5]
            ],
        },

        "mock_test_summary": {
            "available": len(test_rows) > 0,
            "tests_taken": len(test_rows),
            "average_score": avg_score,
            "subject_averages": subject_avgs,
            "recent_tests": [
                {
                    "subject": r.get("subject"),
                    "score": round((r.get("score") or 0) / (r.get("total_questions") or 1) * 100, 1) if (r.get("total_questions") or 0) > 0 else 0,
                    "date": (r.get("created_at") or "")[:10],
                }
                for r in test_rows[:5]
            ],
        },

        "strengths": [s for s, avg in subject_avgs.items() if avg >= 70],
        "areas_for_improvement": [
            {"subject": r.get("subject"), "chapter": r.get("chapter")}
            for r in weak_rows
        ],

        "recommendations": recs[:5],

        "disclaimer": "Teacher-private notes and internal audit data are not included in this report.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Notification helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_rule_based_notifications(parent_id: str, children_rows: list) -> list:
    """
    Generate rule-based notifications when parent_notifications table is empty/unavailable.
    Never exposes secrets, raw audit data, or teacher-private notes.
    """
    notifs = []
    now_iso = datetime.now(timezone.utc).isoformat()
    fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    for child in children_rows:
        child_id = child.get("id")
        child_name = child.get("username", "Child")
        username = child.get("username", "")

        # Resolve child subscription
        sub = resolve_user_subscription(child_id)
        cpk = sub.get("canonical_plan_key", "FREE_TIER")

        # Plan expiring soon
        if sub.get("expiring_soon") and sub.get("days_remaining") is not None:
            days = sub["days_remaining"]
            notifs.append({
                "id": f"rule-expiry-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "plan_expiring",
                "title": f"{child_name}: Plan expires in {days} day{'s' if days != 1 else ''}",
                "message": "Renew your subscription to maintain full access without interruption.",
                "severity": "warning",
                "status": "unread",
                "created_at": now_iso,
                "action": "upgrade",
            })

        # Free Tier restriction
        if cpk == "FREE_TIER":
            notifs.append({
                "id": f"rule-free-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "feature_locked",
                "title": f"{child_name} is on Free Tier",
                "message": "Exemplar lessons, unlimited mock tests, and full AI access are locked. Upgrade for full CBSE coverage.",
                "severity": "info",
                "status": "unread",
                "created_at": now_iso,
                "action": "upgrade",
            })

        # Inactivity check
        act_rows, _ = _safe_query(
            lambda: admin_client.table("ai_usage_logs")
            .select("created_at")
            .eq("username", username)
            .gte("created_at", fourteen_days_ago)
            .limit(1)
            .execute()
        )
        if len(act_rows) == 0:
            notifs.append({
                "id": f"rule-inactive-{child_id}",
                "parent_id": parent_id,
                "child_id": child_id,
                "child_name": child_name,
                "type": "child_inactive",
                "title": f"{child_name} hasn't logged in recently",
                "message": "No activity recorded in the last 14 days. Encourage a 15-minute revision session.",
                "severity": "warning",
                "status": "unread",
                "created_at": now_iso,
                "action": "view_child",
            })

        # Low mock score
        test_rows, _ = _safe_query(
            lambda: admin_client.table("test_history")
            .select("score, total_questions")
            .eq("username", username)
            .limit(10)
            .execute()
        )
        pct_scores = [
            (r.get("score") or 0) / (r.get("total_questions") or 1) * 100
            for r in test_rows if (r.get("total_questions") or 0) > 0
        ]
        if pct_scores:
            avg = sum(pct_scores) / len(pct_scores)
            if avg < 40:
                notifs.append({
                    "id": f"rule-lowscore-{child_id}",
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "child_name": child_name,
                    "type": "low_mock_score",
                    "title": f"{child_name} needs help with mock tests",
                    "message": f"Average mock test score is {round(avg, 1)}%. Review weak topics together.",
                    "severity": "warning",
                    "status": "unread",
                    "created_at": now_iso,
                    "action": "view_analytics",
                })
            elif avg >= 70:
                notifs.append({
                    "id": f"rule-goodscore-{child_id}",
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "child_name": child_name,
                    "type": "strong_improvement",
                    "title": f"Great progress — {child_name}!",
                    "message": f"Average mock test score is {round(avg, 1)}%. Keep the momentum going!",
                    "severity": "success",
                    "status": "unread",
                    "created_at": now_iso,
                    "action": "view_analytics",
                })

    return notifs


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/parent/notifications
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(
    status: str = "all",
    notif_type: str = "all",
    parent=Depends(require_parent),
):
    """
    Parent notification center.
    Tries persistent table first; falls back to rule-based generation.
    Parent can only access own notifications.
    """
    parent_id = parent["profile"]["id"]

    # Try persistent notifications table
    query = (
        admin_client.table("parent_notifications")
        .select("*")
        .eq("parent_id", parent_id)
        .order("created_at", desc=True)
        .limit(50)
    )
    if status != "all":
        query = query.eq("status", status)
    if notif_type != "all":
        query = query.eq("type", notif_type)

    db_notifs, db_err = _safe_query(lambda: query.execute())

    if db_err or len(db_notifs) == 0:
        # Table doesn't exist or no persisted notifications — generate rule-based
        children_rows, _ = _safe_query(
            lambda: admin_client.table("profiles")
            .select("id, username, grade")
            .eq("parent_id", parent_id)
            .execute()
        )
        all_notifs = _generate_rule_based_notifications(parent_id, children_rows)

        # Apply filters
        if status != "all":
            all_notifs = [n for n in all_notifs if n.get("status") == status]
        if notif_type != "all":
            all_notifs = [n for n in all_notifs if n.get("type") == notif_type]

        unread_count = sum(1 for n in all_notifs if n.get("status") == "unread")
        return {
            "success": True,
            "source": "rule_based",
            "unread_count": unread_count,
            "total": len(all_notifs),
            "notifications": all_notifs,
        }

    unread_count = sum(1 for n in db_notifs if n.get("status") == "unread")
    # Sanitize: strip raw metadata keys that could contain secrets
    safe_notifs = []
    for n in db_notifs:
        safe_meta = {k: v for k, v in (n.get("metadata") or {}).items()
                     if k not in ("token", "secret", "key", "password", "audit_detail")}
        safe_notifs.append({**n, "metadata": safe_meta})

    return {
        "success": True,
        "source": "database",
        "unread_count": unread_count,
        "total": len(safe_notifs),
        "notifications": safe_notifs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/parent/notifications/{notification_id}/read
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, parent=Depends(require_parent)):
    """Mark a single notification as read. Parent can only update own notifications."""
    parent_id = parent["profile"]["id"]

    # Verify ownership before updating
    existing, err = _safe_one(
        lambda: admin_client.table("parent_notifications")
        .select("id, parent_id")
        .eq("id", notification_id)
        .eq("parent_id", parent_id)
        .limit(1)
        .execute()
    )
    if err or not existing:
        # Rule-based notification IDs start with "rule-" — they're stateless
        # Just acknowledge without DB write
        return {"success": True, "id": notification_id, "status": "read", "note": "Stateless notification acknowledged."}

    try:
        admin_client.table("parent_notifications").update({
            "status": "read",
            "read_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", notification_id).eq("parent_id", parent_id).execute()
    except Exception as exc:
        _log.warning("mark_notification_read failed: %s", exc)
        return {"success": False, "error": "Could not update notification."}

    return {"success": True, "id": notification_id, "status": "read"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/parent/notifications/read-all
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/notifications/read-all")
def mark_all_notifications_read(parent=Depends(require_parent)):
    """Mark all notifications for this parent as read. Only affects own notifications."""
    parent_id = parent["profile"]["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    rows, err = _safe_query(
        lambda: admin_client.table("parent_notifications")
        .select("id")
        .eq("parent_id", parent_id)
        .eq("status", "unread")
        .execute()
    )

    if err:
        # Table unavailable — rule-based notifications are stateless, nothing to update
        return {"success": True, "updated": 0, "note": "Stateless notifications acknowledged."}

    if not rows:
        return {"success": True, "updated": 0}

    try:
        admin_client.table("parent_notifications").update({
            "status": "read",
            "read_at": now_iso,
        }).eq("parent_id", parent_id).eq("status", "unread").execute()
    except Exception as exc:
        _log.warning("mark_all_notifications_read failed: %s", exc)
        return {"success": False, "error": "Could not update notifications."}

    return {"success": True, "updated": len(rows)}
