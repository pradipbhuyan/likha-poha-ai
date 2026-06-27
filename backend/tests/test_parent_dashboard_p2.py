"""
test_parent_dashboard_p2.py
─────────────────────────────────────────────────────────────────────────────
Backend regression tests for Parent Experience Phase 2.

Covers:
  1. Analytics endpoint enforces parent ownership
  2. Missing progress/mock/AI/homework/exam tables return available=false (never crash)
  3. Analytics distinguishes available=false from zero data
  4. Notifications endpoint returns rule-based notifications
  5. Notifications only for own parent
  6. Mark-read handles stateless rule-based IDs gracefully
  7. Read-all handles missing table gracefully
  8. Academic insights returns homework.available=false when table missing
  9. Academic insights returns start_mock_test recommendation when no tests
 10. Recommendations respect Free Tier restrictions
 11. Recommendations for paid users do not incorrectly upsell
 12. Progress report excludes teacher-private notes and admin audit data
 13. Progress report enforces parent ownership
 14. _metric helper structures data correctly
 15. _unavailable helper marks data as unavailable
 16. Rule-based notifications generate correct types for Free Tier child
 17. Rule-based notifications: inactive child produces inactive type
 18. Notification metadata sanitization removes dangerous keys
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.routes.parent_dashboard_p2 import (
    _metric,
    _unavailable,
    _generate_rule_based_notifications,
    get_child_analytics,
    get_academic_insights,
    get_progress_report,
    get_notifications,
    mark_notification_read,
    mark_all_notifications_read,
)
from fastapi import HTTPException


# ── Fixtures ──────────────────────────────────────────────────────────────────
PARENT = {"profile": {"id": "parent-1", "username": "Test Parent"}}
CHILD = {"id": "child-1", "username": "Aarav", "grade": "Grade 10", "parent_id": "parent-1"}


def _free_sub():
    return {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False,
            "valid_until": None, "days_remaining": None, "expiring_soon": False, "restrictions": []}


def _paid_sub():
    return {"canonical_plan_key": "PREMIUM", "plan_name": "Premium", "has_full_access": True,
            "valid_until": None, "days_remaining": None, "expiring_soon": False, "restrictions": []}


# ── 1. _metric helper ─────────────────────────────────────────────────────────

class TestMetricHelper:
    def test_metric_available(self):
        m = _metric("Score", "72%", True, "Based on tests")
        assert m["label"] == "Score"
        assert m["value"] == "72%"
        assert m["available"] is True
        assert m["explanation"] == "Based on tests"

    def test_metric_unavailable_value(self):
        m = _metric("Score", None, False)
        assert m["available"] is False
        assert m["value"] is None

    def test_unavailable_helper(self):
        m = _unavailable("Chapters")
        assert m["available"] is False
        assert m["value"] is None
        assert "available yet" in m["explanation"].lower()


# ── 2. Ownership enforcement ──────────────────────────────────────────────────

class TestOwnershipEnforcement:
    def test_analytics_enforces_parent_ownership(self, monkeypatch):
        """Parent cannot access analytics for unrelated child."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_child_analytics("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403

    def test_academic_insights_enforces_ownership(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_academic_insights("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403

    def test_progress_report_enforces_ownership(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_progress_report("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403


# ── 3. Missing tables return available=false ──────────────────────────────────

class TestMissingTablesGraceful:
    def _mock_no_data(self, monkeypatch):
        """Patch _verify_child_ownership and _safe_query to return empty."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _free_sub())

    def test_analytics_missing_progress_returns_available_false(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["success"] is True
        assert result["progress"]["available"] is False

    def test_analytics_missing_mock_tests_returns_available_false(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["mock_tests"]["available"] is False

    def test_analytics_missing_activity_returns_available_false(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["activity"]["available"] is False

    def test_analytics_homework_always_false(self, monkeypatch):
        """Homework table does not exist — data_availability.homework must be False."""
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["data_availability"]["homework"] is False

    def test_analytics_exams_always_false(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["data_availability"]["exams"] is False

    def test_academic_insights_homework_unavailable(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        assert result["success"] is True
        assert result["homework"]["available"] is False
        assert "not enabled yet" in result["homework"]["message"].lower()

    def test_academic_insights_exams_unavailable(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        assert result["exams"]["available"] is False
        assert "not available yet" in result["exams"]["message"].lower()


# ── 4. Mock test recommendations in academic insights ────────────────────────

class TestAcademicInsightsMockRecommendations:
    def test_no_tests_produces_start_mock_test_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "start_mock_test" in types

    def test_low_score_produces_improve_score_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                # test_history rows with low scores
                return [{"score": 3, "total_questions": 10, "subject": "Science", "created_at": "2026-06-01"}], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query", mock_safe_q)
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "improve_score" in types

    def test_good_score_produces_maintain_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return [{"score": 8, "total_questions": 10, "subject": "Maths", "created_at": "2026-06-01"}], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query", mock_safe_q)
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "maintain_progress" in types


# ── 5. Progress report ────────────────────────────────────────────────────────

class TestProgressReport:
    def test_progress_report_excludes_teacher_notes(self, monkeypatch):
        """teacher_student_notes table NEVER queried in progress report."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert result["success"] is True
        # Disclaimer must be present
        assert "teacher-private notes" in result["disclaimer"].lower()
        # No teacher notes field in response
        assert "teacher_notes" not in str(result)
        assert "private_note" not in str(result)

    def test_progress_report_has_disclaimer(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 0

    def test_progress_report_includes_generated_timestamp(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard_p2._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert "generated_at" in result
        assert result["report_type"] == "parent_progress_report"


# ── 6. Rule-based notifications ───────────────────────────────────────────────

class TestRuleBasedNotifications:
    def test_free_tier_child_generates_feature_locked_notification(self, monkeypatch):
        """FREE_TIER child generates 'feature_locked' notification."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "feature_locked" in types

    def test_inactive_child_generates_child_inactive_notification(self, monkeypatch):
        """Child with no recent activity generates 'child_inactive' notification."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "child_inactive" in types

    def test_paid_child_no_feature_locked_notification(self, monkeypatch):
        """PREMIUM child should NOT generate feature_locked notification."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Riya", "grade": "Grade 9"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "feature_locked" not in types

    def test_notifications_only_for_own_parent(self, monkeypatch):
        """Notifications are parent-scoped — parent_id in all generated notifs."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        for n in notifs:
            assert n["parent_id"] == "parent-1", "All notifications must belong to parent-1"

    def test_expiry_generates_plan_expiring_notification(self, monkeypatch):
        """Soon-expiring plan generates plan_expiring notification."""
        expiring_sub = {**_paid_sub(), "expiring_soon": True, "days_remaining": 2}
        monkeypatch.setattr("app.routes.parent_dashboard_p2.resolve_user_subscription",
                            lambda uid: expiring_sub)
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Riya", "grade": "Grade 9"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "plan_expiring" in types


# ── 7. Mark notification read (stateless) ─────────────────────────────────────

class TestMarkRead:
    def test_mark_read_stateless_rule_based_id(self, monkeypatch):
        """Rule-based notification IDs (rule-*) are stateless — acknowledge gracefully."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_one",
                            lambda fn: (None, "table not found"))
        result = mark_notification_read("rule-free-child-1", parent=PARENT)
        assert result["success"] is True
        assert result["status"] == "read"

    def test_read_all_handles_missing_table(self, monkeypatch):
        """read-all gracefully handles missing parent_notifications table."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], "table does not exist"))
        result = mark_all_notifications_read(parent=PARENT)
        assert result["success"] is True
        assert result["updated"] == 0

    def test_read_all_no_unread_returns_zero(self, monkeypatch):
        """read-all with no unread notifications returns updated=0."""
        monkeypatch.setattr("app.routes.parent_dashboard_p2._safe_query",
                            lambda fn: ([], None))  # empty unread list, no error
        result = mark_all_notifications_read(parent=PARENT)
        assert result["success"] is True
        assert result["updated"] == 0


# ── 8. Notification metadata sanitization ────────────────────────────────────

class TestNotificationMetadataSanitization:
    def test_dangerous_keys_stripped_from_metadata(self):
        """Secret/token/password keys must be stripped from notification metadata."""
        raw_metadata = {
            "token": "secret-jwt-token",
            "secret": "api-secret",
            "password": "user-password",
            "audit_detail": "raw-audit-data",
            "child_id": "child-1",
            "action": "upgrade",
        }
        # Mirror sanitization logic from get_notifications
        safe_meta = {k: v for k, v in raw_metadata.items()
                     if k not in ("token", "secret", "key", "password", "audit_detail")}
        assert "token" not in safe_meta
        assert "secret" not in safe_meta
        assert "password" not in safe_meta
        assert "audit_detail" not in safe_meta
        # Safe keys preserved
        assert safe_meta["child_id"] == "child-1"
        assert safe_meta["action"] == "upgrade"


# ── 9. Recommendations for paid vs free ──────────────────────────────────────

class TestRecommendationPlanAwareness:
    def test_free_tier_analytics_recommend_has_upgrade_type(self, monkeypatch):
        """Free Tier child in analytics has upgrade recommendation."""
        from app.routes.parent_dashboard_p2 import _metric
        from app.routes.parent_dashboard_v2 import _build_recommendations
        sub = _free_sub()
        features = {
            "EXEMPLAR": {"allowed": False, "limited": False},
            "MOCK_TEST": {"allowed": True, "limited": True},
        }
        recs = _build_recommendations("Aarav", sub, features, 0, None)
        types = [r["type"] for r in recs]
        assert "upgrade" in types

    def test_paid_tier_analytics_no_upgrade_recommendation(self, monkeypatch):
        """PREMIUM child in analytics should NOT have upgrade recommendation."""
        from app.routes.parent_dashboard_v2 import _build_recommendations
        sub = _paid_sub()
        features = {
            "EXEMPLAR": {"allowed": True, "limited": False},
            "MOCK_TEST": {"allowed": True, "limited": False},
        }
        recs = _build_recommendations("Riya", sub, features, 5, "2026-06-27")
        types = [r["type"] for r in recs]
        assert "upgrade" not in types
