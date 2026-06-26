"""
test_analytics_diagnostics.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for GET /api/admin/analytics/diagnostics.

Verifies:
  - endpoint is admin-only
  - diagnostics reports table exists vs missing
  - diagnostics reports row counts correctly
  - diagnostics NEVER exposes service role key or raw secrets
  - warnings are generated for empty profiles / missing required tables
  - permission_error state is detected and reported
  - data_source_appears_correct flag is accurate
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import app.routes.admin_analytics as analytics
from app.routes.admin_analytics import (
    STATE_ERROR,
    STATE_MISSING,
    STATE_OK,
    STATE_PERMISSION,
    _count_rows,
    _is_permission_error,
    analytics_diagnostics,
)

ADMIN_CTX = {"id": "admin-1", "role": "admin", "username": "TestAdmin"}


# ── _is_permission_error ──────────────────────────────────────────────────────

class TestIsPermissionError:
    def test_permission_denied(self):
        assert _is_permission_error("ERROR: permission denied for table profiles") is True

    def test_insufficient_privilege(self):
        assert _is_permission_error("insufficient_privilege on relation") is True

    def test_pg_42501(self):
        assert _is_permission_error("SQLSTATE 42501: permission denied") is True

    def test_403(self):
        assert _is_permission_error("403 Forbidden") is True

    def test_normal_errors_not_matched(self):
        assert _is_permission_error("network timeout") is False
        assert _is_permission_error("relation does not exist") is False
        assert _is_permission_error("PGRST205") is False


# ── _count_rows ───────────────────────────────────────────────────────────────

class TestCountRows:
    def test_count_ok_with_rows(self, monkeypatch):
        """Table exists with rows → STATE_OK, count > 0."""
        mock_r = MagicMock()
        mock_r.count = 42
        mock_r.data = []
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_r
        monkeypatch.setattr(analytics, "admin_client", mock_client)
        count, err, state = _count_rows("profiles")
        assert state == STATE_OK
        assert count == 42
        assert err is None

    def test_count_ok_empty_table(self, monkeypatch):
        """Table exists but empty → STATE_OK, count = 0."""
        mock_r = MagicMock()
        mock_r.count = 0
        mock_r.data = []
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_r
        monkeypatch.setattr(analytics, "admin_client", mock_client)
        count, err, state = _count_rows("profiles")
        assert state == STATE_OK
        assert count == 0

    def test_count_missing_table(self, monkeypatch):
        """PGRST205 → STATE_MISSING, count = None."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = \
            Exception("PGRST205 relation does not exist")
        monkeypatch.setattr(analytics, "admin_client", mock_client)
        count, err, state = _count_rows("ai_usage_logs")
        assert state == STATE_MISSING
        assert count is None
        assert err is None

    def test_count_permission_error(self, monkeypatch):
        """Permission denied → STATE_PERMISSION, count = None."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = \
            Exception("permission denied for table profiles")
        monkeypatch.setattr(analytics, "admin_client", mock_client)
        count, err, state = _count_rows("profiles")
        assert state == STATE_PERMISSION
        assert count is None

    def test_count_query_error(self, monkeypatch):
        """Network/other error → STATE_ERROR, count = None."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = \
            Exception("network timeout")
        monkeypatch.setattr(analytics, "admin_client", mock_client)
        count, err, state = _count_rows("profiles")
        assert state == STATE_ERROR
        assert count is None
        assert "network timeout" in (err or "")


# ── analytics_diagnostics ─────────────────────────────────────────────────────

class TestAnalyticsDiagnostics:
    def _make_count_fn(self, table_map: dict):
        """Build a _count_rows mock that returns per-table results."""
        def count_rows(table):
            entry = table_map.get(table, (None, None, STATE_MISSING))
            return entry
        return count_rows

    def test_diagnostics_admin_only(self):
        """diagnostics function has admin dependency."""
        import inspect
        assert "admin" in inspect.signature(analytics_diagnostics).parameters

    def test_diagnostics_does_not_expose_service_key(self, monkeypatch):
        """Response must never contain the actual service role key value."""
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret-key-12345")
        monkeypatch.setattr(analytics, "_SERVICE_ROLE_KEY", "super-secret-key-12345")
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({}))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        result_str = str(result)
        assert "super-secret-key-12345" not in result_str
        assert "service_role_configured" in result
        assert result["service_role_configured"] is True  # just boolean
        # Aliases dict present — boolean only, no values
        assert "service_key_aliases" in result
        assert isinstance(result["service_key_aliases"]["SUPABASE_SERVICE_ROLE_KEY"], bool)

    def test_diagnostics_configured_true_when_auth_service_has_key(self, monkeypatch):
        """service_role_configured=True uses the auth_service variable directly."""
        # Simulate: env var not in os.environ but _SERVICE_ROLE_KEY is set
        # (deployment loaded it at startup via a different mechanism)
        monkeypatch.setattr(analytics, "_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiJ9.test")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({}))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        # Must be True because _SERVICE_ROLE_KEY is set (= admin_client is configured)
        assert result["service_role_configured"] is True

    def test_diagnostics_configured_via_alias(self, monkeypatch):
        """service_role_configured=True when SUPABASE_SERVICE_KEY alias is set."""
        monkeypatch.setattr(analytics, "_SERVICE_ROLE_KEY", None)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "alias-service-key-value")
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({}))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert result["service_role_configured"] is True
        assert result["service_key_aliases"]["SUPABASE_SERVICE_KEY"] is True
        # Alias value must NOT appear in response
        assert "alias-service-key-value" not in str(result)

    def test_diagnostics_missing_when_no_key_set(self, monkeypatch):
        """service_role_configured=False when no alias is set."""
        monkeypatch.setattr(analytics, "_SERVICE_ROLE_KEY", None)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({}))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert result["service_role_configured"] is False

    def test_diagnostics_does_not_expose_supabase_url(self, monkeypatch):
        """project_ref is only the first ~12 chars of the host — never full URL."""
        monkeypatch.setenv("SUPABASE_URL", "https://abcdefghij1234567890.supabase.co")
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({}))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert "abcdefghij1234567890" not in result["project_ref"]  # truncated
        assert "abcdefghij12" in result["project_ref"]  # first 12 chars

    def test_diagnostics_reports_table_exists(self, monkeypatch):
        """Tables that exist are reported as STATE_OK with row count."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles":               (50, None, STATE_OK),
            "subscription_payments":  (12, None, STATE_OK),
            "offer_redemptions":      (5,  None, STATE_OK),
            "offer_codes":            (3,  None, STATE_OK),
            "teacher_student_assignments": (8, None, STATE_OK),
            "ai_usage_logs":          (None, None, STATE_MISSING),
            "test_history":           (None, None, STATE_MISSING),
            "subscription_timeline":  (None, None, STATE_MISSING),
            "platform_audit_logs":    (None, None, STATE_MISSING),
            "families":               (None, None, STATE_MISSING),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert result["success"] is True
        tables = {t["table"]: t for t in result["tables"]}
        assert tables["profiles"]["state"] == STATE_OK
        assert tables["profiles"]["row_count"] == 50
        assert tables["subscription_payments"]["state"] == STATE_OK
        assert tables["ai_usage_logs"]["state"] == STATE_MISSING

    def test_diagnostics_reports_missing_tables(self, monkeypatch):
        """Missing tables show STATE_MISSING with null row_count."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (10, None, STATE_OK),
            "subscription_payments": (2, None, STATE_OK),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        tables = {t["table"]: t for t in result["tables"]}
        for t in ["ai_usage_logs", "test_history", "subscription_timeline"]:
            assert tables[t]["state"] == STATE_MISSING
            assert tables[t]["row_count"] is None

    def test_diagnostics_data_source_correct_when_profiles_has_rows(self, monkeypatch):
        """data_source_appears_correct=True when profiles has > 0 rows."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (25, None, STATE_OK),
            "subscription_payments": (5, None, STATE_OK),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert result["data_source_appears_correct"] is True
        assert result["profiles_row_count"] == 25

    def test_diagnostics_profiles_empty_triggers_critical_warning(self, monkeypatch):
        """profiles = 0 rows → critical warning: wrong project."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (0, None, STATE_OK),
            "subscription_payments": (0, None, STATE_OK),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        assert result["data_source_appears_correct"] is False
        warning_codes = [w["code"] for w in result["warnings"]]
        assert "profiles_empty" in warning_codes
        critical = [w for w in result["warnings"] if w["code"] == "profiles_empty"]
        assert critical[0]["level"] == "critical"

    def test_diagnostics_permission_error_on_profiles(self, monkeypatch):
        """Permission denied on profiles → critical warning."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (None, "permission denied", STATE_PERMISSION),
            "subscription_payments": (None, "permission denied", STATE_PERMISSION),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        tables = {t["table"]: t for t in result["tables"]}
        assert tables["profiles"]["state"] == STATE_PERMISSION
        assert tables["profiles"]["error_category"] == "permission_denied"
        warning_codes = [w["code"] for w in result["warnings"]]
        assert "profiles_permission_denied" in warning_codes

    def test_diagnostics_optional_tables_missing_info_warning(self, monkeypatch):
        """Missing optional tables → info-level warning."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (10, None, STATE_OK),
            "subscription_payments": (2, None, STATE_OK),
            # all optional tables default to MISSING
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        warning_codes = [w["code"] for w in result["warnings"]]
        assert "optional_tables_missing" in warning_codes
        info_warnings = [w for w in result["warnings"] if w["code"] == "optional_tables_missing"]
        assert info_warnings[0]["level"] == "info"

    def test_diagnostics_no_warnings_when_all_ok(self, monkeypatch):
        """No warnings when profiles has rows and no required tables missing."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (50, None, STATE_OK),
            "subscription_payments": (10, None, STATE_OK),
            "offer_redemptions": (5, None, STATE_OK),
            "offer_codes": (3, None, STATE_OK),
            "teacher_student_assignments": (8, None, STATE_OK),
            "ai_usage_logs": (100, None, STATE_OK),
            "test_history": (200, None, STATE_OK),
            "subscription_timeline": (50, None, STATE_OK),
            "platform_audit_logs": (300, None, STATE_OK),
            "families": (15, None, STATE_OK),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        # No critical/error warnings (only info is ok)
        critical = [w for w in result["warnings"] if w["level"] in ("critical", "error")]
        assert len(critical) == 0

    def test_diagnostics_required_tables_error_warning(self, monkeypatch):
        """If subscription_payments has query_error → required_tables_unavailable warning."""
        monkeypatch.setattr(analytics, "_count_rows", self._make_count_fn({
            "profiles": (20, None, STATE_OK),
            "subscription_payments": (None, "db error", STATE_ERROR),
        }))
        result = analytics_diagnostics(admin=ADMIN_CTX)
        warning_codes = [w["code"] for w in result["warnings"]]
        assert "required_tables_unavailable" in warning_codes
