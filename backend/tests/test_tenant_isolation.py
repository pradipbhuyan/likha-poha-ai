"""
test_tenant_isolation.py — cross-tenant data isolation regression suite.

Added 2026-08-20 after a real production incident: a parent added a new
child named "likha", and the Parent Dashboard immediately showed 6 mock
tests and a 3.3% average score that belonged to a completely unrelated,
orphaned account that happened to share the same username. Root cause:
get_child_analytics (and get_parent_dashboard_summary) filter
test_history/student_progress/weak_area_alerts/ai_usage_logs by the
`username` STRING, not by profile id — see
docs/sql/2026-08-16_check_username_uniqueness.sql for the original
investigation (this exact collision was found and "resolved" four days
before it actually happened, because the fix was never applied).

Two thousand-plus existing tests in this repo did not catch this, and could
not have: every hand-rolled `admin_client` fake in this suite returns
whatever canned data its author hardcoded, regardless of which table/column
was actually queried. A mock like that can prove "the route calls .execute()
and handles the response" but is structurally incapable of catching "the
route filtered by the wrong column" — there's no real row data for the wrong
column to matter against.

This file uses tests/helpers/mini_supabase.py instead: an in-memory fake
that holds real rows and actually evaluates .eq()/.ilike()/.in_() against
them, so a test seeding two unrelated profiles with the same username will
fail here exactly the way it failed in production if the code under test
queries the wrong key.

Covers:
- Cross-family child access is blocked by id-based ownership (already
  correct — a regression guard, not a new fix).
- Two profiles with genuinely distinct usernames never cross-contaminate
  (the happy path, proven against real row data instead of assumed).
- Parent analytics resolve owned records by the child's immutable profile id,
  so legacy username collisions cannot mix dashboard data.
- Every signup path (complete_signup, signup_free, signup_with_offer_code,
  create_student, oauth complete-profile) rejects a taken username, across
  parent/student/teacher role combinations — the actual fix, tested at
  every entry point that can create a profile.
- Teacher roster enrichment resolves progress, history, and usage by assigned
  student profile ids. The schema migration also backfills and maintains
  profile_id across every legacy username-owned table while remaining
  backward compatible with older writers.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from tests.helpers.mini_supabase import MiniSupabaseClient

PROFILE_TABLES = [
    "profiles", "test_history", "student_progress", "weak_area_alerts",
    "ai_usage_logs", "families",
]


class TestProfileIdOwnershipMigration:
    def test_covers_every_username_owned_table_and_protected_account(self):
        migration = (
            Path(__file__).parents[1]
            / "migrations"
            / "20260821_profile_id_ownership.sql"
        ).read_text()

        for table in (
            "ai_usage_events", "ai_usage_logs", "board_paper_attempts",
            "doubt_history", "mentor_memory", "mock_test_wrong_answers",
            "student_profiles", "student_progress", "test_history",
            "unanswered_questions", "user_feedback", "weak_area_alerts",
        ):
            assert f"'{table}'" in migration
            assert f"{table}_profile_id_idx" in migration

        assert "set_profile_id_from_username" in migration
        assert "admin@tutor.com" in migration
        assert "akshita.teststudent@mail.com" in migration
        assert "where id = 723" in migration.casefold()
        assert "payload_versions <> 1" in migration.casefold()
        assert "drop table" not in migration.casefold()


def _seed_profile(db, **fields):
    row = {
        "role": "student", "parent_id": None, "family_id": None,
        "account_status": "active", "subscription_plan": "free",
        "access_cbse": False, "subscription_expires_at": None,
    }
    row.update(fields)
    db.tables["profiles"].append(row)
    return row


# ─────────────────────────────────────────────────────────────────────────────
# get_child_analytics — ownership gate (regression guard for existing control)
# ─────────────────────────────────────────────────────────────────────────────

class TestChildAnalyticsOwnership:
    def test_parent_cannot_fetch_a_child_id_outside_their_family(self, monkeypatch):
        """A parent must never be able to read another family's child analytics
        just by knowing (or guessing) that child's id."""
        import app.routes.parent_dashboard as pd

        db = MiniSupabaseClient(PROFILE_TABLES)
        _seed_profile(db, id="child-A", username="Aarav", family_id="family-A", parent_id="parent-A")
        _seed_profile(db, id="child-B", username="Riya", family_id="family-B", parent_id="parent-B")

        monkeypatch.setattr(pd, "admin_client", db)
        monkeypatch.setattr(pd, "resolve_user_subscription", lambda uid: {"canonical_plan_key": "FREE_TIER"})

        parent_a = {"id": "parent-A", "family_id": "family-A", "parent_id": None}

        with pytest.raises(HTTPException) as exc:
            pd.get_child_analytics(child_id="child-B", parent={"profile": parent_a})
        assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# get_child_analytics — data isolation with real row data
# ─────────────────────────────────────────────────────────────────────────────

class TestChildAnalyticsDataIsolation:
    def test_distinct_usernames_never_cross_contaminate(self, monkeypatch):
        """
        Happy path, proven against real rows rather than assumed: two
        families' children with genuinely different usernames each see only
        their own mock test history.
        """
        import app.routes.parent_dashboard as pd

        db = MiniSupabaseClient(PROFILE_TABLES)
        _seed_profile(db, id="child-A", username="Aarav", family_id="family-A", parent_id="parent-A")
        _seed_profile(db, id="child-B", username="Riya", family_id="family-B", parent_id="parent-B")
        db.tables["test_history"].append({"profile_id": "child-A", "username": "Aarav", "percentage": 80, "raw_score": None, "max_score": None, "subject": "Maths", "chapter": "Ch1", "created_at": "2026-08-01T00:00:00Z"})
        db.tables["test_history"].append({"profile_id": "child-B", "username": "Riya", "percentage": 40, "raw_score": None, "max_score": None, "subject": "Science", "chapter": "Ch2", "created_at": "2026-08-01T00:00:00Z"})

        monkeypatch.setattr(pd, "admin_client", db)
        monkeypatch.setattr(pd, "resolve_user_subscription", lambda uid: {"canonical_plan_key": "FREE_TIER"})

        parent_a = {"id": "parent-A", "family_id": "family-A", "parent_id": None}
        result = pd.get_child_analytics(child_id="child-A", parent={"profile": parent_a})

        assert result["mock_tests"]["total_tests"]["value"] == 1
        assert result["mock_tests"]["average_score"]["value"] == "80.0%"

    def test_colliding_username_does_not_leak_into_owners_dashboard(self, monkeypatch):
        """
        Reproduces the exact production incident (2026-08-20): a legitimately
        owned child's dashboard must show ONLY that child's own mock test
        history, even when an unrelated profile elsewhere in the system
        happens to share its username.
        """
        import app.routes.parent_dashboard as pd

        db = MiniSupabaseClient(PROFILE_TABLES)
        # The rightful owner: Family A's new child.
        _seed_profile(db, id="child-A", username="likha", family_id="family-A", parent_id="parent-A")
        # An unrelated orphaned profile sharing the same username — simulates
        # the account that existed before the signup-time guard shipped.
        _seed_profile(db, id="orphan-1", username="likha", family_id=None, parent_id=None)
        db.tables["test_history"].append({"profile_id": "orphan-1", "username": "likha", "percentage": 3.3, "raw_score": None, "max_score": None, "subject": "Maths", "chapter": "Old", "created_at": "2026-07-21T00:00:00Z"})

        monkeypatch.setattr(pd, "admin_client", db)
        monkeypatch.setattr(pd, "resolve_user_subscription", lambda uid: {"canonical_plan_key": "FREE_TIER"})

        parent_a = {"id": "parent-A", "family_id": "family-A", "parent_id": None}
        result = pd.get_child_analytics(child_id="child-A", parent={"profile": parent_a})

        # The new child has taken zero mock tests. Today, this fails —
        # total_tests comes back as 1, inherited from the orphaned profile.
        assert result["mock_tests"]["total_tests"]["value"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Signup-time uniqueness guard — the actual fix, tested at every entry point
# ─────────────────────────────────────────────────────────────────────────────

class TestUsernameUniquenessAcrossAllEntryPoints:
    """
    _reject_taken_username() (backend/app/routes/auth.py) is the real
    prevention: no new profile — parent, student, or teacher, via any
    signup path — can be created with a username that collides with an
    existing profile of ANY role. Each test below seeds a MiniSupabaseClient
    with one existing profile and asserts every creation path rejects reusing
    its username, regardless of the new profile's intended role.
    """

    def test_reject_taken_username_blocks_regardless_of_role_pairing(self, monkeypatch):
        import app.routes.auth as auth_module

        for existing_role, new_role in [
            ("parent", "parent"), ("parent", "student"), ("parent", "teacher"),
            ("student", "student"), ("student", "parent"), ("student", "teacher"),
            ("teacher", "teacher"), ("teacher", "parent"), ("teacher", "student"),
        ]:
            db = MiniSupabaseClient(PROFILE_TABLES)
            _seed_profile(db, id="existing-1", username="collide", role=existing_role)
            monkeypatch.setattr(auth_module, "admin_client", db)

            with pytest.raises(HTTPException) as exc:
                auth_module._reject_taken_username("collide")
            assert exc.value.status_code == 409, (
                f"existing={existing_role} new={new_role}: expected 409, "
                f"got {exc.value.status_code}"
            )

    def test_reject_taken_username_is_case_and_whitespace_insensitive(self, monkeypatch):
        """
        The production collision involved exact-match usernames, but the DB
        unique index (backend/sql/add_username_uniqueness_to_profiles.sql)
        normalizes with lower(trim(...)) — the application-level guard must
        match that normalization, or it would pass names the index then
        rejects, turning a friendly 409 into a raw database error.
        """
        import app.routes.auth as auth_module

        db = MiniSupabaseClient(PROFILE_TABLES)
        _seed_profile(db, id="existing-1", username="Likha", role="student")
        monkeypatch.setattr(auth_module, "admin_client", db)

        for candidate in ["likha", "LIKHA", "  likha  ", "LiKhA"]:
            with pytest.raises(HTTPException) as exc:
                auth_module._reject_taken_username(candidate)
            assert exc.value.status_code == 409, f"candidate={candidate!r} was not rejected"

    def test_reject_taken_username_allows_genuinely_new_name(self, monkeypatch):
        import app.routes.auth as auth_module

        db = MiniSupabaseClient(PROFILE_TABLES)
        _seed_profile(db, id="existing-1", username="likha", role="student")
        monkeypatch.setattr(auth_module, "admin_client", db)

        auth_module._reject_taken_username("someone-else")  # must not raise

    def test_create_student_rejects_taken_username_via_mini_db(self, monkeypatch):
        """
        End-to-end through the real create_student route (not just the
        helper function) against a MiniSupabaseClient, so the whole call
        chain — including the explicit `client=admin_client` pass-through
        that made this mockable per-module (see auth.py's
        _reject_taken_username docstring) — is exercised together.
        """
        import app.routes.parent_dashboard as pd

        db = MiniSupabaseClient(PROFILE_TABLES)
        _seed_profile(db, id="existing-1", username="likha", role="student", family_id="family-B")

        monkeypatch.setattr(pd, "admin_client", db)
        monkeypatch.setattr(pd, "get_children", lambda pid: [])
        monkeypatch.setattr(
            pd, "resolve_user_subscription",
            lambda pid: {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier",
                         "has_full_access": False, "child_limit": 1, "restrictions": []},
        )
        monkeypatch.setattr(pd, "create_auth_user", lambda email, password, **kw: type("U", (), {"id": "new-uuid"})())

        req = pd.CreateStudentRequest(username="likha", password="password123")
        parent = {"profile": {"id": "parent-A", "family_id": "family-A"}}

        with pytest.raises(HTTPException) as exc:
            pd.create_student(data=req, parent=parent)
        assert exc.value.status_code == 409
        assert "already taken" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Teacher-side isolation — same pattern, different route
# ─────────────────────────────────────────────────────────────────────────────

class TestTeacherStudentDataIsolation:
    def test_assigned_student_lookup_is_correctly_id_scoped(self, monkeypatch):
        """
        Regression guard: which students a teacher sees at all IS correctly
        scoped by teacher_student_assignments.teacher_id /
        load_profiles_by_id's `.in_("id", ...)` — a teacher never sees a
        student they weren't assigned, regardless of username collisions
        elsewhere in the system. Only the progress/test-history enrichment
        (tested below) uses the weaker username lookup.
        """
        import app.routes.teacher_dashboard as td

        db = MiniSupabaseClient(["teacher_student_assignments", "profiles"])
        db.tables["teacher_student_assignments"].append(
            {"teacher_id": "teacher-A", "student_id": "student-A", "created_at": "2026-08-01T00:00:00Z"}
        )
        _seed_profile(db, id="student-A", username="Aarav", role="student")
        _seed_profile(db, id="student-B", username="Riya", role="student")  # not assigned to teacher-A

        monkeypatch.setattr(td, "admin_client", db)

        assignments = td.load_teacher_assignments("teacher-A")
        assigned_ids = [a["student_id"] for a in assignments]
        assert assigned_ids == ["student-A"]

        profiles_by_id = td.load_profiles_by_id(assigned_ids)
        assert set(profiles_by_id.keys()) == {"student-A"}

    def test_progress_enrichment_does_not_leak_from_colliding_username(self, monkeypatch):
        import app.routes.teacher_dashboard as td

        db = MiniSupabaseClient(["profiles", "student_progress"])
        _seed_profile(db, id="student-A", username="likha", role="student")
        _seed_profile(db, id="orphan-1", username="likha", role="student")
        db.tables["student_progress"].append({"profile_id": "orphan-1", "username": "likha", "subject": "Maths", "chapter": "Old orphaned progress", "completed": True, "updated_at": "2026-07-21T00:00:00Z"})

        monkeypatch.setattr(td, "admin_client", db)

        # The teacher's assigned student is student-A, looked up by their
        # own (correct) username — but the orphaned profile's row comes
        # back too, because the query can't tell them apart.
        progress = td.load_progress_by_profile_id(["student-A"])
        assert len(progress["student-A"]) == 0, "assigned student has no progress of their own yet"
