"""
student_dashboard.py  —  GET /api/student/dashboard/summary
─────────────────────────────────────────────────────────────────────────────
Student Dashboard Summary endpoint — Phase 1

Returns:
  - profile (safe fields only)
  - progress summary from student_progress table
  - mock test summary from test_history (using percentage column)
  - weak topics from weak_area_alerts
  - achievements (computed)
  - recommendations (rule-based)
  - feature access summary (from canonical feature_authorization_service)

Safety:
  - Only current authenticated student's data
  - No teacher-private notes
  - No admin audit metadata
  - Missing tables return graceful empty (never crash)
  - Mock scores always 0-100 (uses canonical normalize_score_pct)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from app.services.auth_service import require_student, admin_client
from app.services.subscription_resolver_service import resolve_user_subscription
from app.services.feature_authorization_service import get_feature_summary, Feature
from app.routes.parent_dashboard_v2 import _safe_query, _normalize_score_pct

router = APIRouter()
_log = logging.getLogger("likhapoha.student.dashboard")


def _safe_pct(row: dict) -> float | None:
    return _normalize_score_pct(row.get("percentage"), row.get("raw_score"), row.get("max_score"))


@router.get("/dashboard/summary")
def get_student_dashboard_summary(student=Depends(require_student)):
    """
    Canonical student dashboard summary.
    Returns all data needed to render the redesigned dashboard in one call.
    """
    profile = student["profile"]
    uid = profile["id"]
    username = profile.get("username", "")

    # ── Subscription / Feature access ────────────────────────────────────────
    sub = resolve_user_subscription(uid)
    feat_summary = get_feature_summary(uid)
    features = feat_summary.get("features", {})
    cpk = sub.get("canonical_plan_key", "FREE_TIER")
    has_full = sub.get("has_full_access", False)

    # ── Mock test history (test_history table) ────────────────────────────────
    test_rows, _ = _safe_query(
        lambda: admin_client.table("test_history")
        .select("percentage, raw_score, max_score, subject, chapter, created_at, mode")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    scores = [s for s in (_safe_pct(r) for r in test_rows) if s is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Subject averages
    subj_map: dict = {}
    for r in test_rows:
        s = r.get("subject") or "Unknown"
        p = _safe_pct(r)
        if p is not None:
            subj_map.setdefault(s, []).append(p)
    subject_avgs = {s: round(sum(v)/len(v), 1) for s, v in subj_map.items()}

    # Recent tests
    recent_tests = [
        {
            "subject": r.get("subject", ""),
            "chapter": r.get("chapter", ""),
            "score": _safe_pct(r),
            "date": (r.get("created_at") or "")[:10],
            "mode": r.get("mode", "CBSE"),
        }
        for r in test_rows[:5]
    ]

    # Score trend (last 10 tests ordered oldest→newest)
    score_trend = [
        {"index": i+1, "score": _safe_pct(r), "subject": r.get("subject", "")}
        for i, r in enumerate(reversed(test_rows[:10]))
    ]

    # ── Student progress (student_progress table) ─────────────────────────────
    prog_rows, _ = _safe_query(
        lambda: admin_client.table("student_progress")
        .select("subject, chapter, completed, current_step_index, updated_at")
        .eq("username", username)
        .execute()
    )
    completed_ch = [r for r in prog_rows if r.get("completed")]
    in_progress_ch = [r for r in prog_rows if not r.get("completed") and (r.get("current_step_index") or 0) > 0]

    # Last started chapter for "Continue Learning"
    last_chapter = None
    if in_progress_ch:
        sorted_prog = sorted(in_progress_ch, key=lambda r: r.get("updated_at") or "", reverse=True)
        lc = sorted_prog[0]
        last_chapter = {
            "subject": lc.get("subject", ""),
            "chapter": lc.get("chapter", ""),
            "step_index": lc.get("current_step_index", 0),
            "progress_pct": min(round((lc.get("current_step_index", 0) / 5) * 100), 95),
        }

    # Subject-wise progress
    subj_prog: dict = {}
    for r in prog_rows:
        subj = r.get("subject") or "Unknown"
        entry = subj_prog.setdefault(subj, {"total": 0, "completed": 0, "in_progress": 0})
        entry["total"] += 1
        if r.get("completed"):
            entry["completed"] += 1
        elif (r.get("current_step_index") or 0) > 0:
            entry["in_progress"] += 1

    # ── Weak area alerts ──────────────────────────────────────────────────────
    weak_rows, _ = _safe_query(
        lambda: admin_client.table("weak_area_alerts")
        .select("subject, chapter, best_score, status, created_at")
        .eq("username", username)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    # ── AI activity (90d) ─────────────────────────────────────────────────────
    ninety_ago = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    act_rows, _ = _safe_query(
        lambda: admin_client.table("ai_usage_logs")
        .select("feature, created_at")
        .eq("username", username)
        .gte("created_at", ninety_ago)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    last_active = act_rows[0]["created_at"] if act_rows else None
    feat_counts: dict = {}
    for r in act_rows:
        f = r.get("feature", "other")
        feat_counts[f] = feat_counts.get(f, 0) + 1

    # ── Achievements (computed) ───────────────────────────────────────────────
    achievements = []
    study_streak = profile.get("study_streak_days", 0) or 0
    lessons_completed = profile.get("lessons_completed", 0) or len(completed_ch)

    if study_streak > 0:
        achievements.append({"type":"streak","title":f"{study_streak} Day Streak","icon":"🔥","value":study_streak})
    if lessons_completed >= 50:
        achievements.append({"type":"lessons","title":"Completed 50 Lessons","icon":"📚","value":lessons_completed})
    elif lessons_completed > 0:
        achievements.append({"type":"lessons","title":f"Completed {lessons_completed} Lessons","icon":"📖","value":lessons_completed})
    if len(test_rows) >= 1:
        achievements.append({"type":"first_test","title":"First Mock Test","icon":"🏆","value":len(test_rows)})
    if avg_score and avg_score >= 70:
        achievements.append({"type":"high_score","title":"Scoring Above 70%","icon":"⭐","value":avg_score})

    # ── Recommendations (rule-based) ──────────────────────────────────────────
    recommendations = []
    if not last_active:
        recommendations.append({"type":"inactive","title":"Start your learning journey","body":"Begin your first AI lesson today — pick a subject and get started!","priority":"high","action":"lessons"})
    elif weak_rows:
        top_weak = weak_rows[0]
        recommendations.append({"type":"practice","title":f"Revise: {top_weak.get('chapter','Unknown')}","body":f"Practice {top_weak.get('subject','')} — this topic needs attention.","priority":"high","action":"lessons"})
    if len(test_rows) == 0:
        recommendations.append({"type":"mock_test","title":"Try your first mock test","body":"Mock tests help identify gaps early. Attempt a chapter-wise test today.","priority":"medium","action":"mock_test"})
    elif avg_score and avg_score < 50:
        recommendations.append({"type":"improve","title":"Focus on weak subjects","body":f"Average score is {avg_score}%. Review weak topics and retry tests.","priority":"high","action":"mock_test"})
    if cpk == "FREE_TIER" and not has_full:
        recommendations.append({"type":"upgrade","title":"Unlock full platform access","body":"Upgrade to access Exemplar problems, unlimited mock tests, and full AI lessons.","priority":"low","action":"subscription"})

    # ── Today's plan (rule-based) ─────────────────────────────────────────────
    plan_tasks = []
    if last_chapter:
        plan_tasks.append({"task":f"Continue {last_chapter['subject']} lesson","done":False,"type":"lesson"})
    if len(test_rows) == 0 or (avg_score and avg_score < 60):
        plan_tasks.append({"task":"Attempt one mock test","done":False,"type":"mock_test"})
    if weak_rows:
        plan_tasks.append({"task":f"Revise: {weak_rows[0].get('chapter','weak topic')}","done":False,"type":"revise"})
    if not plan_tasks:
        plan_tasks.append({"task":"Start a new lesson","done":False,"type":"lesson"})

    return {
        "success": True,
        "student": {
            "id": uid,
            "username": username,
            "display_name": profile.get("display_name") or profile.get("full_name") or username or "",
            "grade": profile.get("grade", "Grade 9"),
            "board": profile.get("board", "CBSE"),
            "avatar": profile.get("avatar", ""),
            "study_streak_days": study_streak,
            "lessons_completed": lessons_completed,
        },
        "subscription": {
            "canonical_plan_key": cpk,
            "plan_name": sub.get("plan_name", "Free Tier"),
            "has_full_access": has_full,
            "expiring_soon": sub.get("expiring_soon", False),
            "days_remaining": sub.get("days_remaining"),
        },
        "features": {
            "exemplar_locked": not features.get(Feature.EXEMPLAR, {}).get("allowed", False),
            "mock_test_limited": features.get(Feature.MOCK_TEST, {}).get("limited", False),
            "ask_doubts_limited": features.get(Feature.ASK_DOUBTS, {}).get("limited", False),
            "has_full_access": has_full,
        },
        "mock_tests": {
            "available": len(test_rows) > 0,
            "total": len(test_rows),
            "average_score": avg_score,
            "best_score": max(scores) if scores else None,
            "subject_averages": subject_avgs,
            "recent": recent_tests,
            "score_trend": score_trend,
        },
        "progress": {
            "available": len(prog_rows) > 0,
            "total_chapters": len(prog_rows),
            "completed_chapters": len(completed_ch),
            "in_progress_chapters": len(in_progress_ch),
            "subject_progress": subj_prog,
            "last_chapter": last_chapter,
            "overall_pct": round(len(completed_ch) / max(len(prog_rows), 1) * 100, 1) if prog_rows else 0,
        },
        "weak_topics": [
            {"subject": r.get("subject"), "chapter": r.get("chapter"), "score": r.get("best_score")}
            for r in weak_rows
        ],
        "activity": {
            "last_active": last_active,
            "feature_counts": feat_counts,
            "total_90d": len(act_rows),
        },
        "achievements": achievements,
        "recommendations": recommendations,
        "plan": {
            "tasks": plan_tasks[:4],
            "estimated_minutes": len(plan_tasks) * 15,
        },
    }
