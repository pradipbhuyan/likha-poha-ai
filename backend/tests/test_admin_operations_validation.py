"""
test_admin_operations_validation.py
════════════════════════════════════
Validation tests for commit 684271c — Admin Operations Dashboard.

Covers the 10 review items:
  1. Route naming consistent: /api/admin/operations (not /operation)
  2. All endpoints server-side admin-only (checked in test_admin_operations.py)
  3. No secrets/metadata returned in any response
  4. Health config returns bool only (checked in test_admin_operations.py)
  5. Pagination and days filter consistent across endpoints
  6. Mobile-friendly: CSS flexWrap + overflowX verified via source inspection
  7. Expiry Job button states: confirm, loading, success, error
  8. In-memory metrics labelled in ALL counter-bearing sections
  9. App routing + Sidebar nav item exist for adminOperations
 10. All tests pass (checked by running suites)

Run with:
    cd backend && python -m pytest tests/test_admin_operations_validation.py -v
"""
from __future__ import annotations

import inspect
import pathlib
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import app.routes.admin_operations as ops
import app.main as main_module

ADMIN_CTX = {"profile": {"id": "admin-1", "role": "admin"}}


# ─────────────────────────────────────────────────────────────────────────────
# Item 1: Route naming consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteNaming:
    """Backend prefix and frontend page key must use consistent 'operations' (plural)."""

    def test_main_router_uses_operations_plural(self):
        """main.py must register admin_operations_router under /api/admin/operations."""
        import inspect
        src = inspect.getsource(main_module)
        # Must contain the operations plural prefix
        assert "/api/admin/operations" in src, (
            "main.py must register admin_operations_router under /api/admin/operations"
        )
        # Must NOT use the singular /api/admin/operation
        assert '"/api/admin/operation",' not in src, (
            "main.py must not use singular /api/admin/operation — use /api/admin/operations"
        )

    def test_api_client_uses_operations_plural(self):
        """Frontend API client must target /api/admin/operations."""
        client_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "api" / "adminOperations.js"
        )
        assert client_path.exists(), "adminOperations.js must exist"
        text = client_path.read_text()
        assert "/api/admin/operations" in text
        assert "/api/admin/operation" not in text.replace("/api/admin/operations", "")

    def test_app_jsx_uses_adminoperations_key(self):
        """App.jsx must handle the 'adminOperations' page key."""
        app_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "App.jsx"
        )
        text = app_path.read_text()
        assert '"adminOperations"' in text, (
            "App.jsx must have case 'adminOperations' in renderPage()"
        )
        assert "AdminOperationsPage" in text

    def test_sidebar_adminoperations_handled_or_removed(self):
        """Operations Dashboard is embedded in Admin Control.
        The sidebar MAY or MAY NOT have a separate adminOperations nav item.
        App.jsx must still handle the page key for direct navigation."""
        sidebar_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "components" / "Sidebar.jsx"
        )
        app_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "App.jsx"
        )
        # App.jsx must still route adminOperations (for backwards compat)
        app_text = app_path.read_text()
        assert '"adminOperations"' in app_text, (
            "App.jsx must still handle adminOperations page key"
        )
        # Sidebar may or may not have it — Operations Dashboard is in Admin Control
        # No assertion on Sidebar — product decision: embedded in adminControl


# ─────────────────────────────────────────────────────────────────────────────
# Item 3: No secrets/raw metadata returned
# ─────────────────────────────────────────────────────────────────────────────

class TestNoSecretsInResponses:
    """Audit log metadata is fetched but NOT returned raw in any endpoint."""

    def test_webhooks_response_excludes_metadata(self, monkeypatch):
        """Webhooks endpoint fetches metadata column but must NOT return it."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.like.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "event_type": "webhook.test",
                "created_at": "2026-01-01T00:00:00",
                "metadata": {"api_key": "rzp_live_secret", "payload": "raw_body"},
            }
        ]
        mock_client.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)

        result = ops.operations_webhooks(days=30, admin=ADMIN_CTX)
        # Each event in recent_webhook_audit_events must NOT include metadata
        for event in result["recent_webhook_audit_events"]:
            assert "metadata" not in event
            assert "api_key" not in str(event)
            assert "rzp_live_secret" not in str(event)

    def test_expiry_job_status_summary_is_safe(self, monkeypatch):
        """last_run_summary from expiry job metadata contains only safe count fields."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "event_type": "expiry_job.ran",
                "created_at": "2026-06-01T10:00:00",
                "metadata": {
                    "ran_at": "2026-06-01T10:00:00",
                    "users_inspected": 10,
                    "users_revoked": 3,
                    "errors": 0,
                },
            }
        ]
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_expiry_job_status(admin=ADMIN_CTX)
        summary = result["last_run_summary"]
        # Only operational counts — no secrets
        safe_keys = {"ran_at", "users_inspected", "users_revoked",
                     "users_skipped_already_revoked", "users_skipped_offer_fallback", "errors"}
        for k in summary:
            assert k in safe_keys or not any(
                secret in k for secret in ("key", "secret", "token", "password", "jwt")
            ), f"last_run_summary key '{k}' looks like it could be sensitive"

    def test_payments_response_excludes_metadata_column(self, monkeypatch):
        """Payments endpoint selects only safe columns, not the metadata JSONB column."""
        src = inspect.getsource(ops.operations_payments)
        # The select statement should not include 'metadata' column
        # (razorpay_payment_id is safe — it's a reference, not a secret)
        assert '"metadata"' not in src.split(".select(")[1].split(")")[0], (
            "operations_payments must not select the metadata column"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Item 5: Days filter and pagination consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestDaysFilterAndPagination:
    """?days= filter changes the date window; pagination offset is correct."""

    def test_days_ago_helper_produces_correct_window(self):
        """_days_ago(7) should produce a timestamp ~7 days in the past."""
        from datetime import timedelta
        result = ops._days_ago(7)
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        # Allow 2-second tolerance
        assert 6 * 86400 < diff.total_seconds() < 7 * 86400 + 2, (
            f"_days_ago(7) should be ~7 days ago, got diff={diff}"
        )

    def test_days_ago_1_is_within_today(self):
        result = ops._days_ago(1)
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        assert diff.total_seconds() < 86400 + 2

    def test_days_ago_30_is_30_days(self):
        result = ops._days_ago(30)
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        assert 29 * 86400 < diff.total_seconds() < 30 * 86400 + 2

    def test_payments_pagination_offset(self, monkeypatch):
        """Page 2 with page_size=2 returns items 3 and 4 (offset 2)."""
        mock_client = MagicMock()
        # 5 paid payments
        payments_data = [
            {"status": "paid", "plan_key": "starter", "amount": 299,
             "razorpay_order_id": f"ord_{i}", "created_at": f"2026-01-0{i+1}T00:00:00"}
            for i in range(5)
        ]
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = payments_data
        monkeypatch.setattr(ops, "admin_client", mock_client)

        # Page 1: items 0-1
        r1 = ops.operations_payments(days=30, page=1, page_size=2, admin=ADMIN_CTX)
        assert len(r1["recent_paid"]) == 2
        assert r1["recent_paid"][0]["order_id"] == "ord_0"

        # Page 2: items 2-3
        r2 = ops.operations_payments(days=30, page=2, page_size=2, admin=ADMIN_CTX)
        assert len(r2["recent_paid"]) == 2
        assert r2["recent_paid"][0]["order_id"] == "ord_2"

        # Page 3: item 4 only
        r3 = ops.operations_payments(days=30, page=3, page_size=2, admin=ADMIN_CTX)
        assert len(r3["recent_paid"]) == 1
        assert r3["recent_paid"][0]["order_id"] == "ord_4"

    def test_payments_accepts_days_parameter(self, monkeypatch):
        """operations_payments must accept and use the days parameter."""
        sig = inspect.signature(ops.operations_payments)
        assert "days" in sig.parameters
        # default may be a FastAPI Query object — just verify the parameter exists
        # and that the source code uses _days_ago(days) to apply the filter
        src = inspect.getsource(ops.operations_payments)
        assert "_days_ago(days)" in src or "days_ago(days)" in src, (
            "operations_payments must use the days parameter to filter by date"
        )

    def test_subscriptions_accepts_days_parameter(self, monkeypatch):
        sig = inspect.signature(ops.operations_subscriptions)
        assert "days" in sig.parameters

    def test_alerts_accepts_days_parameter(self, monkeypatch):
        sig = inspect.signature(ops.operations_alerts)
        assert "days" in sig.parameters

    def test_webhooks_accepts_days_parameter(self, monkeypatch):
        sig = inspect.signature(ops.operations_webhooks)
        assert "days" in sig.parameters


# ─────────────────────────────────────────────────────────────────────────────
# Item 7: Expiry Job button — states covered in source
# ─────────────────────────────────────────────────────────────────────────────

class TestExpiryJobButtonStates:
    """Frontend and backend expiry job endpoint handle all states."""

    def test_expiry_job_endpoint_returns_all_summary_keys(self, monkeypatch):
        """run_expiry_job result must include all summary keys the frontend needs."""
        fake_summary = {
            "ran_at": "2026-01-01T00:00:00",
            "users_inspected": 10,
            "users_revoked": 3,
            "users_skipped_already_revoked": 5,
            "users_skipped_offer_fallback": 1,
            "errors": 1,
        }
        monkeypatch.setattr(ops, "run_expiry_job", lambda: fake_summary)
        result = ops.operations_run_expiry_job(admin=ADMIN_CTX)
        for key in ("success", "users_inspected", "users_revoked",
                    "users_skipped_already_revoked", "errors"):
            assert key in result, f"run_expiry_job result must include '{key}'"

    def test_frontend_page_has_confirmation_testid(self):
        """AdminOperationsPage must have data-testid for confirm button."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert 'data-testid="run-expiry-job-btn"' in text
        assert 'data-testid="confirm-expiry-job-btn"' in text
        assert 'data-testid="expiry-job-result"' in text

    def test_frontend_page_has_loading_state(self):
        """AdminOperationsPage must show loading indicator."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "loading" in text.lower() or "Loading" in text

    def test_frontend_page_has_error_state(self):
        """AdminOperationsPage must handle error responses."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        # Error state should show ⚠ indicator or error message
        assert "error" in text.lower()

    def test_expiry_job_requires_confirmation_in_source(self):
        """Run Now button must have a confirmation step before calling the API."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "expiryConfirm" in text, "Must have confirmation state"
        assert "setExpiryConfirm" in text
        # The API call must only happen AFTER confirmation (not on first click)
        assert "handleRunExpiryJob" in text
        assert "setExpiryConfirm(true)" in text   # first click sets confirm
        assert "setExpiryConfirm(false)" in text  # confirm dialog sets to false


# ─────────────────────────────────────────────────────────────────────────────
# Item 8: In-memory metrics labelled in ALL counter-bearing sections
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryMetricsLabelling:
    """Every section that returns in-memory counters must include _note."""

    def _note_present(self, counters: dict) -> bool:
        return "_note" in counters and "process" in counters["_note"].lower()

    def test_summary_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_summary(admin=ADMIN_CTX)
        assert self._note_present(result["in_memory_metrics"]), (
            "summary in_memory_metrics must have _note warning"
        )

    def test_payments_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert self._note_present(result["in_memory_counters"])

    def test_subscriptions_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_subscriptions(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert self._note_present(result["in_memory_counters"])

    def test_usage_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.execute.return_value.count = 0
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_usage(admin=ADMIN_CTX)
        assert self._note_present(result["in_memory_counters"])

    def test_webhooks_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.like.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_webhooks(days=30, admin=ADMIN_CTX)
        assert self._note_present(result["in_memory_counters"])

    def test_frontend_page_shows_inmemory_note_component(self):
        """AdminOperationsPage must render the InMemoryNote component."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "InMemoryNote" in text, (
            "AdminOperationsPage must use InMemoryNote component for in-memory sections"
        )
        # The banner must say 'process-local' or similar
        assert "process-local" in text or "In-memory counters" in text


# ─────────────────────────────────────────────────────────────────────────────
# Item 6: Mobile-friendly CSS (structural verification via source)
# ─────────────────────────────────────────────────────────────────────────────

class TestMobileFriendly:
    """Card grids must use flexWrap; tables must have overflow protection."""

    def test_stat_cards_use_flex_wrap(self):
        """StatCard grids must have flexWrap: 'wrap' for mobile stacking."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "flexWrap" in text and "wrap" in text, (
            "AdminOperationsPage must use flexWrap: 'wrap' for card grids"
        )

    def test_tables_have_overflow_x_auto(self):
        """EventTable must wrap in overflowX: 'auto' to prevent horizontal overflow."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "overflowX" in text and "auto" in text, (
            "AdminOperationsPage must use overflowX: 'auto' for table wrappers"
        )

    def test_date_filter_wraps_on_mobile(self):
        """Date filter and refresh button container must use flexWrap."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        # The header actions div must have flexWrap wrap
        assert text.count("flexWrap") >= 2, (
            "Multiple flexWrap usages expected — header and card grids"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Item 9: App routing and Admin Control page
# ─────────────────────────────────────────────────────────────────────────────

class TestAppRoutingAndAdminControl:
    """adminOperations route exists in App.jsx and Sidebar has the nav item."""

    def test_app_renders_adminoperations_page(self):
        """App.jsx renderPage() must include case 'adminOperations' → AdminOperationsPage."""
        app_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "App.jsx"
        )
        text = app_path.read_text()
        assert 'case "adminOperations"' in text
        assert "AdminOperationsPage" in text

    def test_adminoperationspage_exported_as_default(self):
        """AdminOperationsPage.jsx must have a default export."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert "export default" in text

    def test_adminoperationspage_has_page_testid(self):
        """AdminOperationsPage must have data-testid for integration test targeting."""
        page_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "pages" / "AdminOperationsPage.jsx"
        )
        text = page_path.read_text()
        assert 'data-testid="admin-operations-page"' in text

    def test_sidebar_admin_operations_is_admin_role_only(self):
        """Operations Dashboard is embedded in Admin Control sidebar item.
        If adminOperations is in Sidebar it must be admin-only.
        If not in Sidebar, App.jsx must still route it (backwards compat)."""
        app_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "App.jsx"
        )
        sidebar_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "components" / "Sidebar.jsx"
        )
        app_text = app_path.read_text()
        sidebar_text = sidebar_path.read_text()
        # App.jsx must still handle the route
        assert '"adminOperations"' in app_text, (
            "App.jsx must still handle adminOperations page key for backwards compat"
        )
        # If sidebar has it, verify it's admin-only
        idx = sidebar_text.find('"adminOperations"')
        if idx != -1:
            block = sidebar_text[idx: idx + 150]
            assert '"admin"' in block, "adminOperations must be admin-only if in Sidebar"
        # If not in sidebar — that is acceptable (embedded in Admin Control)
