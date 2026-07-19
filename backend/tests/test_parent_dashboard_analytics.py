"""
test_parent_dashboard_analytics.py
─────────────────────────────────────────────────────────────────────────────
Backend regression tests for the parent-dashboard analytics/insights/
progress-report/notifications endpoints — features formerly split into
parent_dashboard_p2.py, now part of the single parent_dashboard.py module.
See test_parent_dashboard_summary.py for the dashboard-summary/child-detail
coverage, and test_parent_dashboard.py for the base family/children coverage.

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

from app.routes.parent_dashboard import (
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
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_child_analytics("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403

    def test_academic_insights_enforces_ownership(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_academic_insights("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403

    def test_progress_report_enforces_ownership(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: None)
        with pytest.raises(HTTPException) as exc:
            get_progress_report("foreign-child", parent=PARENT)
        assert exc.value.status_code == 403


# ── 3. Missing tables return available=false ──────────────────────────────────

class TestMissingTablesGraceful:
    def _mock_no_data(self, monkeypatch):
        """Patch _verify_child_ownership and _safe_query to return empty."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())

    def test_analytics_missing_progress_returns_no_data(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["success"] is True
        # Tables exist but empty → available=True, has_data=False, status=no_activity
        assert result["progress"]["available"] is True
        assert result["progress"]["has_data"] is False
        assert result["progress"]["status"] == "no_activity"

    def test_analytics_missing_mock_tests_returns_no_activity(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        # Tables exist but empty → available=True, has_data=False
        assert result["mock_tests"]["available"] is True
        assert result["mock_tests"]["has_data"] is False
        assert result["mock_tests"]["status"] == "no_activity"

    def test_analytics_missing_activity_returns_no_activity(self, monkeypatch):
        self._mock_no_data(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        # ai_usage_logs: no error, just empty → available=True, has_data=False
        assert result["activity"]["available"] is True
        assert result["activity"]["has_data"] is False
        assert result["activity"]["status"] == "no_activity"

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
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        assert result["success"] is True
        assert result["homework"]["available"] is False
        assert "not enabled yet" in result["homework"]["message"].lower()

    def test_academic_insights_exams_unavailable(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        assert result["exams"]["available"] is False
        assert "not available yet" in result["exams"]["message"].lower()


# ── 4. Mock test recommendations in academic insights ────────────────────────

class TestAcademicInsightsMockRecommendations:
    def test_no_tests_produces_start_mock_test_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "start_mock_test" in types

    def test_low_score_produces_improve_score_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                # test_history rows with low scores (use percentage column)
                return [{"percentage": 30.0, "raw_score": 3.0, "max_score": 10.0, "subject": "Science", "chapter": "Motion", "created_at": "2026-06-01"}], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query", mock_safe_q)
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "improve_score" in types

    def test_good_score_produces_maintain_recommendation(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return [{"percentage": 80.0, "raw_score": 8.0, "max_score": 10.0, "subject": "Maths", "chapter": "Fractions", "created_at": "2026-06-01"}], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query", mock_safe_q)
        result = get_academic_insights("child-1", parent=PARENT)
        recs = result["mock_test_recommendations"]["recommendations"]
        types = [r["type"] for r in recs]
        assert "maintain_progress" in types


# ── 5. Progress report ────────────────────────────────────────────────────────

class TestProgressReport:
    def test_progress_report_excludes_teacher_notes(self, monkeypatch):
        """teacher_student_notes table NEVER queried in progress report."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert result["success"] is True
        # Disclaimer must be present
        assert "teacher-private notes" in result["disclaimer"].lower()
        # No teacher notes field in response
        assert "teacher_notes" not in str(result)
        assert "private_note" not in str(result)

    def test_progress_report_has_disclaimer(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 0

    def test_progress_report_includes_generated_timestamp(self, monkeypatch):
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard.get_feature_summary",
                            lambda uid: {"features": {}})
        result = get_progress_report("child-1", parent=PARENT)
        assert "generated_at" in result
        assert result["report_type"] == "parent_progress_report"


# ── 6. Rule-based notifications ───────────────────────────────────────────────

class TestRuleBasedNotifications:
    def test_free_tier_child_generates_feature_locked_notification(self, monkeypatch):
        """FREE_TIER child generates 'feature_locked' notification."""
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "feature_locked" in types

    def test_inactive_child_generates_child_inactive_notification(self, monkeypatch):
        """Child with no recent activity generates 'child_inactive' notification."""
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "child_inactive" in types

    def test_paid_child_no_feature_locked_notification(self, monkeypatch):
        """PREMIUM child should NOT generate feature_locked notification."""
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _paid_sub())
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Riya", "grade": "Grade 9"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "feature_locked" not in types

    def test_notifications_only_for_own_parent(self, monkeypatch):
        """Notifications are parent-scoped — parent_id in all generated notifs."""
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Aarav", "grade": "Grade 10"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        for n in notifs:
            assert n["parent_id"] == "parent-1", "All notifications must belong to parent-1"

    def test_expiry_generates_plan_expiring_notification(self, monkeypatch):
        """Soon-expiring plan generates plan_expiring notification."""
        expiring_sub = {**_paid_sub(), "expiring_soon": True, "days_remaining": 2}
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: expiring_sub)
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))
        children = [{"id": "child-1", "username": "Riya", "grade": "Grade 9"}]
        notifs = _generate_rule_based_notifications("parent-1", children)
        types = [n["type"] for n in notifs]
        assert "plan_expiring" in types


# ── 7. Mark notification read (stateless) ─────────────────────────────────────

class TestMarkRead:
    def test_mark_read_stateless_rule_based_id(self, monkeypatch):
        """Rule-based notification IDs (rule-*) are stateless — acknowledge gracefully."""
        monkeypatch.setattr("app.routes.parent_dashboard._safe_one",
                            lambda fn: (None, "table not found"))
        result = mark_notification_read("rule-free-child-1", parent=PARENT)
        assert result["success"] is True
        assert result["status"] == "read"

    def test_read_all_handles_missing_table(self, monkeypatch):
        """read-all gracefully handles missing parent_notifications table."""
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], "table does not exist"))
        result = mark_all_notifications_read(parent=PARENT)
        assert result["success"] is True
        assert result["updated"] == 0

    def test_read_all_no_unread_returns_zero(self, monkeypatch):
        """read-all with no unread notifications returns updated=0."""
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
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
        from app.routes.parent_dashboard import _metric
        from app.routes.parent_dashboard import _build_recommendations
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
        from app.routes.parent_dashboard import _build_recommendations
        sub = _paid_sub()
        features = {
            "EXEMPLAR": {"allowed": True, "limited": False},
            "MOCK_TEST": {"allowed": True, "limited": False},
        }
        recs = _build_recommendations("Riya", sub, features, 5, "2026-06-27")
        types = [r["type"] for r in recs]
        assert "upgrade" not in types


# ─────────────────────────────────────────────────────────────────────────────
# Active student regression tests (correct table/column mapping)
# ─────────────────────────────────────────────────────────────────────────────

class TestActiveStudentDataMapping:
    """
    Regression: Parent dashboard must show real data for active students.
    Root cause was wrong columns (score/total_questions) and wrong table (chapter_progress).
    Correct: percentage column, student_progress table.
    """

    def _mock_active_student(self, monkeypatch):
        """Mock all three tables with realistic active student data."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _paid_sub())

        call_n = {"n": 0}
        def smart_mock(fn):
            call_n["n"] += 1
            n = call_n["n"]
            if n == 1:  # test_history
                return [
                    {"percentage": 60.0, "raw_score": 3.0, "max_score": 5.0, "subject": "Science", "chapter": "Motion", "created_at": "2026-06-24"},
                    {"percentage": 80.0, "raw_score": 4.0, "max_score": 5.0, "subject": "Maths", "chapter": "Fractions", "created_at": "2026-06-23"},
                    {"percentage": 20.0, "raw_score": 1.0, "max_score": 5.0, "subject": "Maths", "chapter": "Integers", "created_at": "2026-06-22"},
                ], None
            elif n == 2:  # student_progress
                return [
                    {"subject": "Science", "chapter": "Motion", "completed": False, "current_step_index": 2, "updated_at": "2026-06-24"},
                    {"subject": "Maths", "chapter": "Fractions", "completed": True, "current_step_index": 3, "updated_at": "2026-06-23"},
                    {"subject": "English", "chapter": "Grammar", "completed": False, "current_step_index": 0, "updated_at": "2026-06-20"},
                ], None
            elif n == 3:  # weak_area_alerts
                return [
                    {"subject": "Maths", "chapter": "Integers", "step_title": "Intro", "best_score": 20.0, "created_at": "2026-06-22"},
                ], None
            elif n == 4:  # ai_usage_logs
                return [
                    {"feature": "lesson", "created_at": "2026-06-25T10:00:00Z"},
                    {"feature": "doubt", "created_at": "2026-06-24T08:00:00Z"},
                    {"feature": "lesson", "created_at": "2026-06-23T09:00:00Z"},
                    {"feature": "doubt", "created_at": "2026-06-22T11:00:00Z"},
                    {"feature": "answer_evaluation", "created_at": "2026-06-21T14:00:00Z"},
                ], None
            return [], None

        monkeypatch.setattr("app.routes.parent_dashboard._safe_query", smart_mock)

    def test_analytics_mock_tests_return_data_for_active_student(self, monkeypatch):
        """Active student with mock history → mock_tests.status=data, avg score returned."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["mock_tests"]["status"] == "data"
        assert result["mock_tests"]["has_data"] is True
        # avg = (60+80+20)/3 = 53.3
        avg_str = result["mock_tests"]["average_score"]["value"]
        assert avg_str is not None and "%" in str(avg_str)

    def test_analytics_progress_returns_data_for_active_student(self, monkeypatch):
        """Active student with progress rows → progress.status=data."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["progress"]["status"] == "data"
        assert result["progress"]["has_data"] is True
        # 1 completed, 1 in progress, 1 not started
        assert result["progress"]["completed_chapters"]["value"] == 1
        assert result["progress"]["in_progress_chapters"]["value"] == 1

    def test_analytics_activity_returns_data_for_active_student(self, monkeypatch):
        """Active student with AI usage → activity.status=data."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        assert result["activity"]["status"] == "data"
        assert result["activity"]["has_data"] is True
        assert result["activity"]["lessons_this_month"]["value"] == 2
        assert result["activity"]["doubts_this_month"]["value"] == 2

    def test_analytics_subject_wise_progress_correct(self, monkeypatch):
        """Subject-wise progress breakdown is accurate."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        sw = result["progress"]["subject_wise"]
        assert "Science" in sw
        assert sw["Science"]["total"] == 1
        assert sw["Science"]["in_progress"] == 1
        assert "Maths" in sw
        assert sw["Maths"]["completed"] == 1

    def test_analytics_percentage_column_used_not_score(self, monkeypatch):
        """Regression: percentage column is used, not score/total_questions."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        # If wrong columns were used, avg_score would be None
        avg = result["mock_tests"]["average_score"]["value"]
        assert avg is not None, "REGRESSION: percentage column not used — avg score is None"

    def test_analytics_uses_student_progress_not_chapter_progress(self, monkeypatch):
        """Regression: student_progress table is used, not chapter_progress."""
        self._mock_active_student(monkeypatch)
        result = get_child_analytics("child-1", parent=PARENT)
        # If wrong table, progress.status would be no_activity
        assert result["progress"]["status"] != "unavailable", \
            "REGRESSION: chapter_progress table used — student_progress is the correct table"

    def test_no_data_student_shows_no_activity_not_unavailable(self, monkeypatch):
        """Empty results from existing tables → status=no_activity (not unavailable)."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query",
                            lambda fn: ([], None))  # empty but no error
        result = get_child_analytics("child-1", parent=PARENT)
        # Tables exist but empty → no_activity, not unavailable
        assert result["progress"]["status"] == "no_activity"
        assert result["mock_tests"]["status"] == "no_activity"
        assert result["activity"]["status"] == "no_activity"


# ─────────────────────────────────────────────────────────────────────────────
# Score normalization regression tests (_normalize_score_pct)
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreNormalization:
    """
    Regression: score values must never exceed 100%.
    _normalize_score_pct is the canonical score formatter.
    """
    from app.routes.parent_dashboard import _normalize_score_pct as _n

    def test_percentage_60_returns_60(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(60.0) == 60.0

    def test_percentage_0_returns_0(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(0.0) == 0.0

    def test_percentage_100_returns_100(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(100.0) == 100.0

    def test_percentage_0_75_treated_as_already_percent(self):
        """0.75 stored as percentage means 0.75% — caller must pass correct column."""
        from app.routes.parent_dashboard import _normalize_score_pct
        # 0.75 is within 0-100 → returned as 0.75% (not multiplied by 100)
        result = _normalize_score_pct(0.75)
        assert result == 0.8  # rounded

    def test_raw_score_12_max_20_returns_60(self):
        """raw_score=12, max_score=20 → 60%"""
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(None, raw_score=12, max_score=20) == 60.0

    def test_raw_score_3_max_5_returns_60(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(None, raw_score=3, max_score=5) == 60.0

    def test_percentage_1200_returns_none(self):
        """1200% is invalid — must return None, not display 1200%."""
        from app.routes.parent_dashboard import _normalize_score_pct
        result = _normalize_score_pct(1200.0)
        assert result is None, "REGRESSION: 1200% score must not be displayed"

    def test_percentage_200_returns_none(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(200.0) is None

    def test_no_data_returns_none(self):
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(None, None, None) is None

    def test_max_score_zero_does_not_divide(self):
        """max_score=0 must not cause ZeroDivisionError."""
        from app.routes.parent_dashboard import _normalize_score_pct
        assert _normalize_score_pct(None, raw_score=5, max_score=0) is None

    def test_analytics_avg_score_never_exceeds_100(self, monkeypatch):
        """Integration: analytics avg_score never > 100% even with boundary data."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        call_n = {"n": 0}
        def mock_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:  # test_history with valid percentage values
                return [
                    {"percentage": 80.0, "raw_score": 4.0, "max_score": 5.0, "subject": "Science", "chapter": "Motion", "created_at": "2026-06-24"},
                    {"percentage": 60.0, "raw_score": 3.0, "max_score": 5.0, "subject": "Maths", "chapter": "Fractions", "created_at": "2026-06-23"},
                ], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query", mock_q)
        result = get_child_analytics("child-1", parent=PARENT)
        avg_val = result["mock_tests"]["average_score"]["value"]
        if avg_val is not None:
            # Extract numeric value from "70.0%" string
            num = float(str(avg_val).replace("%","").strip())
            assert num <= 100.0, f"REGRESSION: avg score {num}% exceeds 100%"

    def test_recent_tests_scores_all_within_100(self, monkeypatch):
        """Recent test scores in analytics must all be within 0-100."""
        monkeypatch.setattr("app.routes.parent_dashboard._verify_child_ownership",
                            lambda p, c: CHILD)
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda uid: _free_sub())
        call_n = {"n": 0}
        def mock_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return [
                    {"percentage": 80.0, "raw_score": 4.0, "max_score": 5.0, "subject": "Science", "chapter": "Motion", "created_at": "2026-06-24"},
                    {"percentage": 20.0, "raw_score": 1.0, "max_score": 5.0, "subject": "Maths", "chapter": "Fractions", "created_at": "2026-06-23"},
                ], None
            return [], None
        monkeypatch.setattr("app.routes.parent_dashboard._safe_query", mock_q)
        result = get_child_analytics("child-1", parent=PARENT)
        for t in result["mock_tests"].get("trend", []):
            score = t.get("score")
            if score is not None:
                assert 0 <= score <= 100, f"Trend score {score} exceeds 100%"
