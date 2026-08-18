"""
feedback_eligibility_service.py — "Serious user" gating for the feedback prompt.

The feedback prompt is never a persistent floating button — it is offered
only right after a user completes a meaningful action (lesson, mock test,
ask-doubt, formula sheet, exam prep, a resource from Learn More), and only
to users who have shown real engagement with the platform:

  - activity_count (lessons completed + mock tests taken + exam prep
    sessions submitted) must meet ACTIVITY_THRESHOLD, and
  - the user must not have been shown the prompt within COOLDOWN_DAYS.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .auth_service import admin_client

ACTIVITY_THRESHOLD = 3
COOLDOWN_DAYS = 7


def _count(table: str, filters: dict) -> int:
    q = admin_client.table(table).select("*", count="exact")
    for key, value in filters.items():
        q = q.eq(key, value)
    r = q.limit(1).execute()
    return r.count or 0


def get_activity_count(username: Optional[str], user_id: str) -> int:
    """Total meaningful actions completed: lessons + mock tests + exam prep."""
    lessons = _count("student_progress", {"username": username, "completed": True}) if username else 0
    tests = _count("test_history", {"username": username}) if username else 0
    exam_prep = _count("exam_prep_simulated_tests", {"user_id": user_id, "status": "submitted"})
    return lessons + tests + exam_prep


def _cooldown_ok(last_prompt_at: Optional[str]) -> bool:
    if not last_prompt_at:
        return True
    try:
        last_dt = datetime.fromisoformat(last_prompt_at.replace("Z", "+00:00"))
    except Exception:
        return True
    return (datetime.now(timezone.utc) - last_dt) >= timedelta(days=COOLDOWN_DAYS)


def check_eligibility(user_id: str, username: Optional[str], last_prompt_at: Optional[str]) -> dict:
    activity_count = get_activity_count(username, user_id)
    threshold_met = activity_count >= ACTIVITY_THRESHOLD
    cooldown_ok = _cooldown_ok(last_prompt_at)
    return {
        "eligible": threshold_met and cooldown_ok,
        "activity_count": activity_count,
        "threshold": ACTIVITY_THRESHOLD,
        "cooldown_ok": cooldown_ok,
    }


def mark_prompt_shown(user_id: str) -> None:
    admin_client.table("profiles").update({
        "last_feedback_prompt_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", user_id).execute()
