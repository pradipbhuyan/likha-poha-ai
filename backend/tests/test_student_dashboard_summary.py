"""
test_student_dashboard_summary.py
─────────────────────────────────────────────────────────────────────────────
Regression test for a bug in GET /api/student/dashboard/summary:

study_streak_days / lessons_completed were read from `student["profile"]`,
which comes from auth_service.get_user_profile() — a query against the
`profiles` table that explicitly selects only
"id, email, username, role, parent_id, family_id, grade, stream,
cbse_subjects". Those two columns (and xp_points/student_level/rank_title)
live on a completely different table, `student_profiles`, reachable via
profile_service.get_student_profile(username). Because the wrong dict was
being read, study_streak_days and lessons_completed silently defaulted to 0
on every real request — the "Day Streak" achievement could never appear on
the happy path, no matter how much a student actually studied.

Fix: fetch the real gamified profile via get_student_profile(username) and
read streak/lessons_completed/xp_points/student_level/rank_title from it.
"""
from unittest.mock import MagicMock

import app.routes.student_dashboard as sd


def _student(**overrides):
    profile = {
        "id": "u1",
        "username": "aisha",
        "role": "student",
        "grade": "Grade 9",
        "board": "CBSE",
    }
    profile.update(overrides)
    return {"profile": profile}


def _patch_common(monkeypatch):
    """Make every admin_client.table(...) call raise, so every _safe_query()
    call in the endpoint deterministically returns ([], error) — no real DB
    needed for this regression test."""
    monkeypatch.setattr(
        sd, "admin_client",
        MagicMock(table=MagicMock(side_effect=Exception("no db in test"))),
    )
    monkeypatch.setattr(
        sd, "resolve_user_subscription",
        lambda uid: {"canonical_plan_key": "FREE_TIER", "has_full_access": False},
    )
    monkeypatch.setattr(sd, "get_feature_summary", lambda uid: {"features": {}})


def test_streak_and_xp_come_from_gamified_profile_not_auth_profile(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        sd, "get_student_profile",
        lambda username: {
            "study_streak_days": 7,
            "lessons_completed": 4,
            "xp_points": 225,
            "student_level": 3,
            "rank_title": "Active Learner",
        },
    )

    result = sd.get_student_dashboard_summary(student=_student())

    assert result["student"]["study_streak_days"] == 7
    assert result["student"]["lessons_completed"] == 4
    assert result["student"]["xp_points"] == 225
    assert result["student"]["student_level"] == 3
    assert result["student"]["rank_title"] == "Active Learner"

    # The streak achievement is only ever appended when study_streak > 0 —
    # this was unreachable before the fix, since the source was always 0.
    streak_achievements = [a for a in result["achievements"] if a["type"] == "streak"]
    assert streak_achievements and streak_achievements[0]["value"] == 7


def test_missing_gamified_profile_defaults_safely(monkeypatch):
    """A brand-new student with no student_profiles row yet must not crash,
    and must show honest zeros/defaults rather than any fabricated value."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(sd, "get_student_profile", lambda username: None)

    result = sd.get_student_dashboard_summary(student=_student())

    assert result["student"]["study_streak_days"] == 0
    assert result["student"]["xp_points"] == 0
    assert result["student"]["student_level"] == 1
    assert result["student"]["rank_title"] == "Beginner"
    assert all(a["type"] != "streak" for a in result["achievements"])
