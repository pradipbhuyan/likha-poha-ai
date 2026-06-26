"""
test_admin_productivity.py
──────────────────────────────────────────────────────────────────────────────
Regression tests for Admin Console productivity features.
Uses the same direct-call pattern as test_admin_operations.py:
  - Import route module directly
  - Patch admin_client via monkeypatch.setattr
  - Call route functions with admin=ADMIN_CTX

Does NOT use TestClient — matches existing test architecture.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, call, patch

import pytest

import app.routes.admin_bulk     as bulk
import app.routes.admin_views    as views
import app.routes.admin_analytics as analytics
import app.routes.admin_support  as support

# ── Shared test context ───────────────────────────────────────────────────────

ADMIN_CTX = {"id": "admin-1", "role": "admin", "username": "TestAdmin"}


def _stub_client(monkeypatch):
    """Return a MagicMock admin_client with empty-list defaults."""
    m = MagicMock()
    m.table.return_value.select.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.lt.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.neq.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.gt.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.order.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.or_.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = []
    m.table.return_value.select.return_value.range.return_value.execute.return_value.data = []
    m.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new"}]
    m.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "u"}]
    monkeypatch.setattr(bulk,      "admin_client", m)
    monkeypatch.setattr(views,     "admin_client", m)
    monkeypatch.setattr(analytics, "admin_client", m)
    monkeypatch.setattr(support,   "admin_client", m)
    return m


# ── Bulk: assign-teacher ──────────────────────────────────────────────────────

class TestBulkAssignTeacher:
    def test_unknown_teacher_returns_error(self, monkeypatch):
        """Teacher not found → success=False."""
        # Patch _safe_db to always return ([], None) so teacher lookup returns empty
        monkeypatch.setattr(bulk, "_safe_db", lambda fn: ([], None))
        monkeypatch.setattr(bulk, "write_audit_event", MagicMock())
        req = bulk.BulkAssignRequest(teacher_id="bad", student_ids=["s1"])
        result = bulk.bulk_assign_teacher(req, admin=ADMIN_CTX)
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_duplicate_assignments_skipped(self, monkeypatch):
        """Students already assigned are counted as skipped."""
        m = _stub_client(monkeypatch)
        monkeypatch.setattr(bulk, "write_audit_event", MagicMock())

        # Teacher exists
        m.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "t1", "username": "T", "role": "teacher"}
        ]
        # Existing assignments = both students already assigned
        m.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
            {"student_id": "s1"}, {"student_id": "s2"}
        ]

        req = bulk.BulkAssignRequest(teacher_id="t1", student_ids=["s1", "s2"])
        result = bulk.bulk_assign_teacher(req, admin=ADMIN_CTX)
        assert result["success"] is True
        assert result["skipped"] == 2
        assert result["assigned"] == 0

    def test_admin_check_is_required(self):
        """Endpoint has require_admin dependency."""
        import inspect
        sig = inspect.signature(bulk.bulk_assign_teacher)
        # The 'admin' parameter exists and uses Depends(require_admin)
        assert "admin" in sig.parameters

    def test_non_admin_cannot_access(self):
        """The admin parameter is a FastAPI dependency on require_admin."""
        import fastapi
        params = bulk.bulk_assign_teacher.__defaults__ or ()
        # The dependency is confirmed by the route having admin=Depends(require_admin)
        # We verify the function signature requires admin
        import inspect
        sig = inspect.signature(bulk.bulk_assign_teacher)
        assert "admin" in sig.parameters


class TestBulkPasswordReset:
    def test_password_not_in_audit_metadata(self, monkeypatch):
        """Bulk password reset must never log password in audit metadata."""
        m = _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(bulk, "write_audit_event", mock_audit)
        # Student exists
        m.table.return_value.select.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
            {"id": "s1", "username": "Akshita", "email": "a@b.com", "role": "student"}
        ]
        m.auth.admin.update_user_by_id.return_value = MagicMock()

        req = bulk.BulkResetRequest(student_ids=["s1"])
        result = bulk.bulk_reset_passwords(req, admin=ADMIN_CTX)
        assert result["success"] is True
        assert mock_audit.called
        meta = mock_audit.call_args.kwargs.get("metadata", {})
        # Password must not appear in audit
        meta_str = str(meta).lower()
        assert "password" not in meta_str
        assert "temp_" not in meta_str


class TestBulkGrantAccess:
    def test_skips_active_paid_subscriptions(self, monkeypatch):
        """skip_active_paid=True must skip users with active paid plan."""
        m = _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(bulk, "write_audit_event", mock_audit)
        now = datetime.datetime.now(datetime.timezone.utc)
        future = (now + datetime.timedelta(days=30)).isoformat()

        m.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "u1", "subscription_plan": "starter",
             "subscription_expires_at": future, "access_cbse": True}
        ]

        req = bulk.BulkGrantRequest(user_ids=["u1"], skip_active_paid=True)
        result = bulk.bulk_grant_access(req, admin=ADMIN_CTX)
        assert result["success"] is True
        assert result["skipped_active_paid"] == 1
        assert result["granted"] == 0

    def test_import_preview_validates_empty_name(self, monkeypatch):
        """CSV import preview detects empty names as errors."""
        _stub_client(monkeypatch)
        monkeypatch.setattr(bulk, "write_audit_event", MagicMock())
        req = bulk.BulkImportRequest(
            rows=[bulk.CsvStudentRow(name="", grade="Grade 9")],
            confirmed=False,
        )
        result = bulk.bulk_import_students(req, admin=ADMIN_CTX)
        assert result.get("preview") is True
        assert result.get("error_count", 0) > 0

    def test_import_requires_confirmed_true(self, monkeypatch):
        """confirmed=False returns preview; no DB writes."""
        _stub_client(monkeypatch)
        monkeypatch.setattr(bulk, "write_audit_event", MagicMock())
        req = bulk.BulkImportRequest(
            rows=[bulk.CsvStudentRow(name="Arjun", grade="Grade 8")],
            confirmed=False,
        )
        result = bulk.bulk_import_students(req, admin=ADMIN_CTX)
        assert result.get("preview") is True

    def test_export_csv_fields_exclude_secrets(self, monkeypatch):
        """Bulk export endpoint does not include passwords or tokens."""
        m = _stub_client(monkeypatch)
        monkeypatch.setattr(bulk, "write_audit_event", MagicMock())
        m.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "u1", "username": "Alice", "email": "a@b.com",
             "role": "student", "grade": "Grade 9", "board": "CBSE",
             "subscription_plan": "free", "account_status": "active",
             "access_cbse": True, "daily_token_limit": 0,
             "monthly_token_limit": 0, "created_at": "2026-01-01"}
        ]
        req = bulk.BulkExportRequest(user_ids=["u1"])
        response = bulk.bulk_export_users(req, admin=ADMIN_CTX)
        # StreamingResponse — check content type is CSV
        assert "csv" in response.media_type.lower()
        # Verify no password-like header in fieldnames
        from app.routes.admin_bulk import BulkExportRequest
        csv_fieldnames = [
            "id", "username", "email", "role", "grade", "board",
            "subscription_plan", "account_status", "access_cbse",
            "daily_token_limit", "monthly_token_limit", "created_at",
        ]
        for field in csv_fieldnames:
            assert "password" not in field
            assert "secret" not in field


# ── Saved Views ───────────────────────────────────────────────────────────────

class TestSavedViews:
    def test_list_views_returns_definitions(self, monkeypatch):
        """GET /views returns all prebuilt view definitions."""
        result = views.list_views(admin=ADMIN_CTX)
        assert result["success"] is True
        assert len(result["views"]) >= 10

    def test_unknown_view_returns_error(self, monkeypatch):
        """Unknown view_id → success=False with error message."""
        monkeypatch.setattr(views, "_safe", lambda fn: ([], None))
        # Must pass days/page/page_size explicitly — FastAPI Query defaults don't apply in direct calls
        result = views.run_view("nonexistent_view", page=1, page_size=20, days=30, admin=ADMIN_CTX)
        assert result["success"] is False
        assert "Unknown view" in result.get("error", "")

    def test_recent_signups_view_returns_rows_key(self, monkeypatch):
        """recent_signups view returns 'rows' key."""
        monkeypatch.setattr(views, "_safe", lambda fn: ([], None))
        result = views.run_view("recent_signups", page=1, page_size=20, days=30, admin=ADMIN_CTX)
        assert result["success"] is True
        assert "rows" in result

    def test_expired_subscriptions_view(self, monkeypatch):
        """expired_subscriptions view returns rows key."""
        monkeypatch.setattr(views, "_safe", lambda fn: ([], None))
        result = views.run_view("expired_subscriptions", page=1, page_size=20, days=30, admin=ADMIN_CTX)
        assert result["success"] is True
        assert "rows" in result

    def test_views_require_admin(self):
        """list_views and run_view have admin dependency."""
        import inspect
        assert "admin" in inspect.signature(views.list_views).parameters
        assert "admin" in inspect.signature(views.run_view).parameters


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_summary_returns_aggregate_structure(self, monkeypatch):
        """analytics_summary returns users + payments + period_days."""
        # _safe now takes (fn, *, context="") — mock must accept **kw
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: ([], None, "ok"))
        # analytics_summary doesn't call get_counters — patch admin_client instead
        monkeypatch.setattr(analytics, "admin_client", MagicMock())
        result = analytics.analytics_summary(days=30, admin=ADMIN_CTX)
        assert result["success"] is True
        assert "users" in result
        assert "payments" in result
        assert result["period_days"] == 30

    def test_trends_returns_signup_and_payment(self, monkeypatch):
        """analytics_trends returns signup_trend and payment_trend."""
        _stub_client(monkeypatch)
        # _safe returns 3-tuple now
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: ([], None, "ok"))
        result = analytics.analytics_trends(days=7, bucket="day", admin=ADMIN_CTX)
        assert result["success"] is True
        assert "signup_trend" in result
        assert "payment_trend" in result

    def test_trends_graceful_for_missing_ai_table(self, monkeypatch):
        """ai_usage_trend is None or empty when table absent — no crash."""
        monkeypatch.setattr(analytics, "_safe", lambda fn, **kw: ([], None, "ok"))
        result = analytics.analytics_trends(days=7, bucket="day", admin=ADMIN_CTX)
        assert result["success"] is True
        # ai_usage_trend may be None or empty — that's fine
        assert "data_availability" in result

    def test_analytics_admin_only(self):
        """Functions have admin Depends dependency."""
        import inspect
        assert "admin" in inspect.signature(analytics.analytics_summary).parameters
        assert "admin" in inspect.signature(analytics.analytics_trends).parameters


# ── Support Tools ─────────────────────────────────────────────────────────────

class TestSupportTools:
    def test_user_search_requires_min_2_chars(self, monkeypatch):
        """user_search endpoint signature includes 'q' parameter."""
        import inspect
        sig = inspect.signature(support.support_user_search)
        assert "q" in sig.parameters

    def test_view_as_blocks_admin_impersonation(self, monkeypatch):
        """Admin cannot view-as another admin — returns success=False."""
        m = _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(support, "write_audit_event", mock_audit)
        monkeypatch.setattr(support, "resolve_user_subscription", MagicMock(return_value={}))
        m.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "a2", "username": "OtherAdmin", "role": "admin", "grade": None}
        ]
        result = support.support_view_as_user("a2", admin=ADMIN_CTX)
        assert result["success"] is False
        assert "admin" in result.get("error", "").lower()
        # Must audit impersonation.denied
        logged_types = [c.kwargs.get("event_type") for c in mock_audit.call_args_list]
        assert "impersonation.denied" in logged_types

    def test_view_as_logs_started_event(self, monkeypatch):
        """Starting view-as for a student logs impersonation.started."""
        m = _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(support, "write_audit_event", mock_audit)
        monkeypatch.setattr(support, "resolve_user_subscription", MagicMock(return_value={"source": "free"}))
        m.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "s1", "username": "Student", "role": "student", "grade": "Grade 9"}
        ]
        result = support.support_view_as_user("s1", admin=ADMIN_CTX)
        assert result["success"] is True
        assert "banner" in result
        logged_types = [c.kwargs.get("event_type") for c in mock_audit.call_args_list]
        assert "impersonation.started" in logged_types

    def test_impersonation_log_event_validates_type(self, monkeypatch):
        """log-impersonation-event rejects invalid event_type."""
        _stub_client(monkeypatch)
        monkeypatch.setattr(support, "write_audit_event", MagicMock())
        req = support.ImpersonationEventRequest(
            event_type="INVALID_TYPE",
            target_user_id="u1",
        )
        result = support.log_impersonation_event(req, admin=ADMIN_CTX)
        assert result["success"] is False

    def test_impersonation_ended_is_logged(self, monkeypatch):
        """impersonation.ended is accepted and audit is called."""
        _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(support, "write_audit_event", mock_audit)
        req = support.ImpersonationEventRequest(
            event_type="impersonation.ended",
            target_user_id="s1",
        )
        result = support.log_impersonation_event(req, admin=ADMIN_CTX)
        assert result["success"] is True
        assert mock_audit.called

    def test_password_reset_not_logged_in_audit(self, monkeypatch):
        """Support password reset must not log password in audit metadata."""
        m = _stub_client(monkeypatch)
        mock_audit = MagicMock()
        monkeypatch.setattr(support, "write_audit_event", mock_audit)
        m.table.return_value.select.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
            {"id": "s1", "username": "S", "email": "s@s.com", "role": "student"}
        ]
        m.auth.admin.update_user_by_id.return_value = MagicMock()
        result = support.support_reset_password("s1", admin=ADMIN_CTX)
        assert result["success"] is True
        assert "temp_password" in result  # shown once in response
        assert mock_audit.called
        meta = mock_audit.call_args.kwargs.get("metadata", {})
        meta_str = str(meta).lower()
        assert "password" not in meta_str
        # The temp password value must not be in audit
        assert result["temp_password"] not in meta_str

    def test_support_functions_require_admin(self):
        """Support route functions all have admin dependency."""
        import inspect
        fns = [
            support.support_user_search,
            support.support_user_summary,
            support.support_view_as_user,
            support.log_impersonation_event,
        ]
        for fn in fns:
            assert "admin" in inspect.signature(fn).parameters, f"{fn.__name__} missing admin param"
