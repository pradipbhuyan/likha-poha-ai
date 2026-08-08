"""
test_weekly_digest_service.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for the weekly parent email digest job and its unsubscribe
route.

Covers:
  1. _child_week_stats — pure per-child stat computation
  2. _group_by_username — grouping helper
  3. run_weekly_digest_job — end-to-end job behavior (sends, skips, failures)
  4. unsubscribe_email_digest — unauthenticated opt-out route
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.services.weekly_digest_service import (
    _child_week_stats,
    _group_by_username,
    run_weekly_digest_job,
)
from app.routes.parent_dashboard import unsubscribe_email_digest


def _sub(cpk="FREE_TIER", has_full=False):
    return {
        "canonical_plan_key": cpk,
        "plan_name": "Free Tier" if cpk == "FREE_TIER" else "Premium",
        "has_full_access": has_full,
        "valid_until": None,
        "days_remaining": None,
    }


# ── 1. _child_week_stats ───────────────────────────────────────────────────

class TestChildWeekStats:
    def test_empty_rows_gives_zeroed_stats(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub(),
        )
        stats = _child_week_stats({"id": "c1", "username": "Aarav", "grade": "Grade 9"}, [], [], [])
        assert stats["mock_tests_count"] == 0
        assert stats["avg_score"] is None
        assert stats["weak_areas"] == []
        assert stats["activity_count"] == 0
        assert stats["name"] == "Aarav"

    def test_mixed_scores_averaged_correctly(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub(),
        )
        test_rows = [
            {"percentage": 80, "subject": "Science"},
            {"percentage": 60, "subject": "Maths"},
        ]
        stats = _child_week_stats({"id": "c1", "username": "Aarav"}, test_rows, [], [])
        assert stats["mock_tests_count"] == 2
        assert stats["avg_score"] == 70.0

    def test_weak_areas_from_alerts_when_present(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub(),
        )
        weak_rows = [{"subject": "Maths", "chapter": "Geometry"}]
        stats = _child_week_stats({"id": "c1", "username": "Aarav"}, [], [], weak_rows)
        assert stats["weak_areas"] == ["Maths — Geometry"]

    def test_weak_areas_fallback_to_low_scoring_subjects(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub(),
        )
        test_rows = [
            {"percentage": 30, "subject": "Maths"},
            {"percentage": 90, "subject": "Science"},
        ]
        stats = _child_week_stats({"id": "c1", "username": "Aarav"}, test_rows, [], [])
        assert stats["weak_areas"] == ["Maths"]

    def test_plan_status_from_resolver(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub("PREMIUM", True),
        )
        stats = _child_week_stats({"id": "c1", "username": "Aarav"}, [], [], [])
        assert stats["has_full_access"] is True
        assert stats["plan_status_label"] == "Full Access"


# ── 2. _group_by_username ──────────────────────────────────────────────────

class TestGroupByUsername:
    def test_groups_rows_by_username(self):
        rows = [{"username": "a", "x": 1}, {"username": "b", "x": 2}, {"username": "a", "x": 3}]
        grouped = _group_by_username(rows)
        assert len(grouped["a"]) == 2
        assert len(grouped["b"]) == 1

    def test_skips_rows_with_no_username(self):
        rows = [{"x": 1}, {"username": None, "x": 2}, {"username": "a", "x": 3}]
        grouped = _group_by_username(rows)
        assert list(grouped.keys()) == ["a"]


# ── 3. run_weekly_digest_job ───────────────────────────────────────────────

class _FakeQuery:
    """Minimal chainable Supabase query-builder double over a fixed row set."""
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def lte(self, *a, **k): return self
    def lt(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return SimpleNamespace(data=self._data)


class _RoleAwareProfilesQuery:
    """
    profiles is queried twice with different .eq("role", ...) filters
    (students, then opted-in parents) — this double tracks which role was
    filtered on and returns the matching fixture set, rather than relying on
    call order (which would break if the query order ever changes).
    """
    def __init__(self, students, parents):
        self._students = students
        self._parents = parents
        self._role = None

    def select(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def eq(self, field, value=None, *a, **k):
        if field == "role":
            self._role = value
        return self

    def execute(self):
        data = self._students if self._role == "student" else self._parents if self._role == "parent" else []
        return SimpleNamespace(data=data)


class _FakeAdminClient:
    """
    students/parents drive the profiles table; other_tables (dict) covers
    test_history/ai_usage_logs/weak_area_alerts. raise_on: table name to
    raise for (simulates a query failure).
    """
    def __init__(self, students=None, parents=None, other_tables=None, raise_on=None):
        self._students = students or []
        self._parents = parents or []
        self._other = other_tables or {}
        self._raise_on = raise_on

    def table(self, name):
        if name == self._raise_on:
            raise Exception(f"simulated failure for {name}")
        if name == "profiles":
            return _RoleAwareProfilesQuery(self._students, self._parents)
        return _FakeQuery(self._other.get(name, []))


PARENT_A = {"id": "parent-a", "email": "a@example.com", "username": "Parent A", "family_id": None}
PARENT_B = {"id": "parent-b", "email": "b@example.com", "username": "Parent B", "family_id": "fam-1"}
PARENT_C = {"id": "parent-c", "email": "c@example.com", "username": "Parent C", "family_id": "fam-1"}
CHILD_A = {"id": "child-a", "username": "Aarav", "grade": "Grade 9", "parent_id": "parent-a", "family_id": None}
CHILD_B = {"id": "child-b", "username": "Riya", "grade": "Grade 8", "parent_id": None, "family_id": "fam-1"}


class TestRunWeeklyDigestJob:
    def _mock_common(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.weekly_digest_service.resolve_user_subscription",
            lambda uid: _sub(),
        )
        monkeypatch.setattr("app.services.weekly_digest_service.write_audit_event", lambda **k: None)

    def test_parent_with_one_child_sends_blocking(self, monkeypatch):
        self._mock_common(monkeypatch)
        monkeypatch.setattr(
            "app.services.weekly_digest_service.admin_client",
            _FakeAdminClient(students=[CHILD_A], parents=[PARENT_A]),
        )
        sent = []
        monkeypatch.setattr(
            "app.services.weekly_digest_service.send_weekly_digest_email",
            lambda **kwargs: (sent.append(kwargs) or True),
        )

        result = run_weekly_digest_job()
        assert result["emails_sent"] == 1
        assert result["parents_processed"] == 1
        assert sent[0]["blocking"] is True
        assert "parent-a" in sent[0]["unsubscribe_url"]

    def test_parent_with_zero_children_is_skipped(self, monkeypatch):
        self._mock_common(monkeypatch)
        monkeypatch.setattr(
            "app.services.weekly_digest_service.admin_client",
            _FakeAdminClient(students=[], parents=[PARENT_A]),
        )
        sent = []
        monkeypatch.setattr(
            "app.services.weekly_digest_service.send_weekly_digest_email",
            lambda **kwargs: (sent.append(kwargs) or True),
        )

        result = run_weekly_digest_job()
        assert result["parents_skipped_no_children"] == 1
        assert result["emails_sent"] == 0
        assert sent == []

    def test_two_coparents_on_same_family_each_get_own_send(self, monkeypatch):
        self._mock_common(monkeypatch)
        monkeypatch.setattr(
            "app.services.weekly_digest_service.admin_client",
            _FakeAdminClient(students=[CHILD_B], parents=[PARENT_B, PARENT_C]),
        )
        sent = []
        monkeypatch.setattr(
            "app.services.weekly_digest_service.send_weekly_digest_email",
            lambda **kwargs: (sent.append(kwargs) or True),
        )

        result = run_weekly_digest_job()
        assert result["emails_sent"] == 2
        recipients = {s["to"] for s in sent}
        assert recipients == {"b@example.com", "c@example.com"}

    def test_failed_send_increments_emails_failed_without_crashing(self, monkeypatch):
        self._mock_common(monkeypatch)
        monkeypatch.setattr(
            "app.services.weekly_digest_service.admin_client",
            _FakeAdminClient(students=[CHILD_A], parents=[PARENT_A]),
        )
        monkeypatch.setattr(
            "app.services.weekly_digest_service.send_weekly_digest_email",
            lambda **kwargs: False,
        )

        result = run_weekly_digest_job()
        assert result["emails_failed"] == 1
        assert result["emails_sent"] == 0
        assert result["errors"] == 0

    def test_initial_query_exception_increments_errors_and_returns_early(self, monkeypatch):
        self._mock_common(monkeypatch)
        monkeypatch.setattr(
            "app.services.weekly_digest_service.admin_client",
            _FakeAdminClient(raise_on="profiles"),
        )

        result = run_weekly_digest_job()
        assert result["errors"] == 1
        assert result["parents_processed"] == 0


# ── 4. unsubscribe_email_digest ────────────────────────────────────────────

class TestUnsubscribeRoute:
    def test_sets_opt_out_flag_and_returns_html(self, monkeypatch):
        calls = {}

        class _FakeTable:
            def update(self, payload):
                calls["payload"] = payload
                return self
            def eq(self, *a, **k):
                calls.setdefault("eq", []).append(a)
                return self
            def execute(self): return SimpleNamespace(data=[{"id": "parent-a"}])

        class _FakeClient:
            def table(self, name):
                calls["table"] = name
                return _FakeTable()

        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", _FakeClient())
        monkeypatch.setattr("app.routes.parent_dashboard.write_audit_event", lambda **k: None)

        html = unsubscribe_email_digest("parent-a")
        assert "unsubscribed" in html.lower()
        assert calls["payload"] == {"email_digest_opt_out": True}
        assert calls["table"] == "profiles"

    def test_is_unauthenticated_no_parent_dependency(self):
        import inspect
        sig = inspect.signature(unsubscribe_email_digest)
        assert "parent" not in sig.parameters

    def test_db_failure_does_not_raise(self, monkeypatch):
        class _FakeClient:
            def table(self, name):
                raise Exception("db unavailable")

        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", _FakeClient())
        html = unsubscribe_email_digest("parent-a")
        assert "unsubscribed" in html.lower()
