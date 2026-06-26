"""
test_analytics_correctness.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for admin_analytics.py state-aware query results.

Tests the four cases for every metric:
  1. Successful query with data   → state="ok", value > 0
  2. Successful query, zero rows  → state="ok", value = 0
  3. Missing table (PGRST205)     → state="table_missing"
  4. Query error (other)          → state="query_error", error logged

Also verifies:
  - errors are never silently swallowed
  - individual metric errors do not poison unrelated metrics
  - _is_missing_table detection covers all PostgREST / Postgres variants
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.routes.admin_analytics as analytics
from app.routes.admin_analytics import (
    STATE_ERROR,
    STATE_MISSING,
    STATE_OK,
    _is_missing_table,
    _safe,
)

ADMIN_CTX = {"id": "admin-1", "role": "admin", "username": "TestAdmin"}


# ── _is_missing_table ─────────────────────────────────────────────────────────

class TestIsMissingTable:
    def test_pgrst205(self):
        assert _is_missing_table("PGRST205: schema cache") is True

    def test_schema_cache(self):
        assert _is_missing_table("Could not find a relationship: schema cache lookup failed") is True

    def test_relation_does_not_exist(self):
        assert _is_missing_table('ERROR: relation "ai_usage_logs" does not exist') is True

    def test_undefined_table(self):
        assert _is_missing_table("undefined_table in query") is True

    def test_real_error_not_matched(self):
        assert _is_missing_table("network timeout") is False
        assert _is_missing_table("connection refused") is False
        assert _is_missing_table("permission denied") is False


# ── _safe ─────────────────────────────────────────────────────────────────────

class TestSafe:
    def test_ok_with_data(self):
        mock_result = MagicMock()
        mock_result.data = [{"id": "u1"}]
        data, err, state = _safe(lambda: mock_result, context="test")
        assert state == STATE_OK
        assert err is None
        assert data == [{"id": "u1"}]

    def test_ok_empty_rows(self):
        mock_result = MagicMock()
        mock_result.data = []
        data, err, state = _safe(lambda: mock_result, context="test")
        assert state == STATE_OK
        assert err is None
        assert data == []

    def test_none_data_treated_as_empty(self):
        mock_result = MagicMock()
        mock_result.data = None
        data, err, state = _safe(lambda: mock_result, context="test")
        assert state == STATE_OK
        assert data == []

    def test_missing_table_pgrst205(self):
        def raise_pgrst():
            raise Exception("PGRST205 schema cache not found")
        data, err, state = _safe(raise_pgrst, context="test")
        assert state == STATE_MISSING
        assert err is None
        assert data == []

    def test_missing_table_relation(self):
        def raise_relation():
            raise Exception('relation "ai_usage_logs" does not exist')
        data, err, state = _safe(raise_relation, context="test")
        assert state == STATE_MISSING
        assert data == []

    def test_query_error_returns_error_state(self):
        def raise_other():
            raise Exception("network timeout after 30s")
        data, err, state = _safe(raise_other, context="test")
        assert state == STATE_ERROR
        assert "network timeout" in err
        assert data == []

    def test_query_error_is_logged(self):
        def raise_other():
            raise Exception("connection refused")
        with patch.object(analytics.logger, "warning") as mock_log:
            _safe(raise_other, context="profiles")
        mock_log.assert_called_once()
        call_args = str(mock_log.call_args)
        assert "profiles" in call_args or "connection refused" in call_args


# ── analytics_summary ─────────────────────────────────────────────────────────

class TestAnalyticsSummary:
    """Uses monkeypatch to inject _safe results per query."""

    def _profiles_data(self):
        future = "2099-01-01T00:00:00+00:00"
        return [
            {"role": "student", "access_cbse": True,  "subscription_plan": "starter",
             "subscription_expires_at": future, "created_at": "2026-01-15T00:00:00+00:00"},
            {"role": "parent",  "access_cbse": False, "subscription_plan": "free",
             "subscription_expires_at": None, "created_at": "2025-06-01T00:00:00+00:00"},
            {"role": "teacher", "access_cbse": True,  "subscription_plan": "free",
             "subscription_expires_at": None, "created_at": "2025-06-01T00:00:00+00:00"},
        ]

    def test_summary_with_all_tables_present(self, monkeypatch):
        """When all tables exist, every metric has state=ok and correct values."""
        payments = [
            {"status": "paid",   "amount": 499, "created_at": "2026-06-01T00:00:00"},
            {"status": "failed", "amount": 0,   "created_at": "2026-06-02T00:00:00"},
        ]
        redemptions  = [{"enrolled_at": "2026-06-01"}]
        assignments  = [{"created_at": "2026-06-01"}]
        ai_rows      = [{"tokens_used": 1000, "created_at": "2026-06-01"}]
        test_rows    = [{"created_at": "2026-06-01"}]

        calls = iter([
            (self._profiles_data(), None, STATE_OK),
            (payments, None, STATE_OK),
            (redemptions, None, STATE_OK),
            (assignments, None, STATE_OK),
            (ai_rows, None, STATE_OK),
            (test_rows, None, STATE_OK),
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)

        assert result["success"] is True
        assert result["users"]["total"] == 3
        assert result["users"]["query_ok"] is True
        assert result["users"]["query_error"] is None
        assert result["payments"]["paid"] == 1
        assert result["payments"]["failed"] == 1
        assert result["payments"]["query_ok"] is True
        assert result["offer_redemptions_in_period"] == 1
        assert result["offer_redemptions_state"] == STATE_OK
        assert result["teacher_student_assignments_total"] == 1
        assert result["teacher_assignments_state"] == STATE_OK
        assert result["ai_usage"]["requests_in_period"] == 1
        assert result["ai_usage"]["tokens_in_period"] == 1000
        assert result["ai_usage"]["state"] == STATE_OK
        assert result["mock_tests_completed_in_period"] == 1
        assert result["mock_tests_state"] == STATE_OK

    def test_summary_zero_rows_shows_zero_not_dash(self, monkeypatch):
        """Empty tables return 0, not None, for state=ok metrics."""
        calls = iter([
            ([], None, STATE_OK),   # profiles
            ([], None, STATE_OK),   # payments
            ([], None, STATE_OK),   # offer_redemptions
            ([], None, STATE_OK),   # teacher_assignments
            ([], None, STATE_OK),   # ai_usage_logs
            ([], None, STATE_OK),   # test_history
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)

        assert result["users"]["total"] == 0
        assert result["users"]["query_ok"] is True
        assert result["payments"]["total_in_period"] == 0
        assert result["payments"]["query_ok"] is True
        assert result["offer_redemptions_in_period"] == 0
        assert result["offer_redemptions_state"] == STATE_OK
        assert result["ai_usage"]["requests_in_period"] == 0
        assert result["ai_usage"]["state"] == STATE_OK
        assert result["mock_tests_completed_in_period"] == 0

    def test_optional_table_missing_returns_table_missing_state(self, monkeypatch):
        """Optional missing tables return state=table_missing, not 0."""
        calls = iter([
            (self._profiles_data(), None, STATE_OK),      # profiles OK
            ([{"status": "paid", "amount": 100, "created_at": "2026-01-01"}], None, STATE_OK),  # payments OK
            ([], None, STATE_MISSING),                     # offer_redemptions missing
            ([], None, STATE_MISSING),                     # teacher_assignments missing
            ([], None, STATE_MISSING),                     # ai_usage_logs missing
            ([], None, STATE_MISSING),                     # test_history missing
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)

        # Core metrics still work
        assert result["users"]["total"] == 3
        assert result["users"]["query_ok"] is True
        assert result["payments"]["query_ok"] is True
        # Optional metrics show missing state, NOT 0
        assert result["offer_redemptions_in_period"] is None
        assert result["offer_redemptions_state"] == STATE_MISSING
        assert result["teacher_student_assignments_total"] is None
        assert result["teacher_assignments_state"] == STATE_MISSING
        assert result["ai_usage"]["available"] is False
        assert result["ai_usage"]["state"] == STATE_MISSING
        assert result["mock_tests_completed_in_period"] is None
        assert result["mock_tests_state"] == STATE_MISSING

    def test_profiles_query_error_surfaces_in_response(self, monkeypatch):
        """If profiles query fails, query_ok=False and query_error is set."""
        calls = iter([
            ([], "connection refused", STATE_ERROR),   # profiles ERROR
            ([], None, STATE_OK),                      # payments
            ([], None, STATE_MISSING),                 # offer_redemptions
            ([], None, STATE_MISSING),                 # teacher_assignments
            ([], None, STATE_MISSING),                 # ai
            ([], None, STATE_MISSING),                 # tests
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)

        assert result["users"]["query_ok"] is False
        assert result["users"]["query_error"] is not None
        assert "refused" in result["users"]["query_error"]
        # Other metrics are independent
        assert result["payments"]["query_ok"] is True

    def test_payments_error_does_not_infect_users(self, monkeypatch):
        """Payments query error only sets payments.query_ok=False."""
        calls = iter([
            (self._profiles_data(), None, STATE_OK),   # profiles OK
            ([], "timeout", STATE_ERROR),               # payments ERROR
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)

        assert result["users"]["query_ok"] is True
        assert result["users"]["total"] == 3
        assert result["payments"]["query_ok"] is False
        assert result["payments"]["total_in_period"] is None
        assert result["payments"]["paid"] is None


# ── analytics_trends ─────────────────────────────────────────────────────────

class TestAnalyticsTrends:
    def test_trends_with_data(self, monkeypatch):
        """Trends return sorted buckets when data is present."""
        profiles = [
            {"created_at": "2026-06-01T10:00:00", "role": "student"},
            {"created_at": "2026-06-01T11:00:00", "role": "student"},
            {"created_at": "2026-06-03T09:00:00", "role": "parent"},
        ]
        payments = [
            {"status": "paid", "created_at": "2026-06-01T10:00:00"},
            {"status": "failed", "created_at": "2026-06-02T10:00:00"},
        ]
        calls = iter([
            (profiles, None, STATE_OK),                # profiles trend
            (payments, None, STATE_OK),                # payments trend
            ([], None, STATE_MISSING),                 # subscription_timeline
            ([], None, STATE_MISSING),                 # offer_redemptions
            ([], None, STATE_MISSING),                 # ai_usage_logs
            ([], None, STATE_MISSING),                 # test_history
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_trends(days=30, admin=ADMIN_CTX)

        assert result["success"] is True
        assert len(result["signup_trend"]) == 2         # two distinct days
        assert result["signup_trend"][0]["count"] == 2  # 2026-06-01 has 2
        assert result["payment_trend"][0]["paid"] == 1
        assert result["signup_trend_state"] == STATE_OK
        assert result["payment_trend_state"] == STATE_OK

    def test_missing_optional_tables_in_trends(self, monkeypatch):
        """Missing optional trend tables return state=table_missing, trend=None."""
        calls = iter([
            ([], None, STATE_OK),      # profiles (no signups in period = empty list)
            ([], None, STATE_OK),      # payments
            ([], None, STATE_MISSING), # subscription_timeline
            ([], None, STATE_MISSING), # offer_redemptions
            ([], None, STATE_MISSING), # ai_usage_logs
            ([], None, STATE_MISSING), # test_history
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_trends(days=30, admin=ADMIN_CTX)

        assert result["ai_usage_trend"] is None
        assert result["ai_usage_trend_state"] == STATE_MISSING
        assert result["mock_test_trend"] is None
        assert result["mock_test_trend_state"] == STATE_MISSING
        assert result["data_availability"]["ai_usage_logs"] is False
        assert result["data_availability"]["ai_usage_logs_state"] == STATE_MISSING

    def test_zero_signups_in_period_returns_empty_list(self, monkeypatch):
        """Zero signups in period → signup_trend is [] not None, state=ok."""
        calls = iter([
            ([], None, STATE_OK),      # profiles — no signups in period
            ([], None, STATE_OK),      # payments
            ([], None, STATE_MISSING), # subscription_timeline
            ([], None, STATE_MISSING), # offer_redemptions
            ([], None, STATE_MISSING), # ai_usage_logs
            ([], None, STATE_MISSING), # test_history
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_trends(days=30, admin=ADMIN_CTX)

        assert result["signup_trend"] == []            # empty list, not None
        assert result["signup_trend_state"] == STATE_OK

    def test_payment_query_error_in_trends(self, monkeypatch):
        """Payment trend query error sets payment_trend_state=query_error."""
        calls = iter([
            ([{"created_at": "2026-06-01T10:00:00", "role": "student"}], None, STATE_OK),
            ([], "pg error", STATE_ERROR),   # payments failed
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
            ([], None, STATE_MISSING),
        ])
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: next(calls))

        result = analytics.analytics_trends(days=30, admin=ADMIN_CTX)

        # Signup trend still works
        assert result["signup_trend_state"] == STATE_OK
        assert len(result["signup_trend"]) == 1
        # Payment trend reflects error
        assert result["payment_trend_state"] == STATE_ERROR
        assert result["payment_trend_error"] == "pg error"
        # Payment trend is empty (no data from errored query)
        assert result["payment_trend"] == []
