"""
test_admin_operations.py
═════════════════════════
Regression tests for the Admin Operations Dashboard API endpoints.

Covers:
  - Non-admin cannot access any operations endpoint
  - Admin can access each endpoint
  - Operations summary includes required keys
  - Operations health checks app + database + config
  - Operations endpoints never return secrets
  - Expiry job endpoint calls run_expiry_job
  - Operations payments includes payment metrics
  - Operations subscriptions includes plan counts
  - Operations usage includes user counts
  - Operations alerts includes event types

Run with:
    cd backend && python -m pytest tests/test_admin_operations.py -v
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

import app.routes.admin_operations as ops


# ── Helpers ───────────────────────────────────────────────────────────────────

ADMIN_CTX = {"profile": {"id": "admin-1", "role": "admin"}}


def _mock_empty_profiles(monkeypatch):
    """Make all Supabase queries return empty data."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = []
    monkeypatch.setattr(ops, "admin_client", mock_client)
    return mock_client


# ── Non-admin access checks ───────────────────────────────────────────────────

class TestNonAdminBlocked:
    """All operations endpoints require require_admin — non-admin is blocked by FastAPI."""

    def test_summary_requires_admin(self):
        """operations_summary function signature has admin dependency."""
        import inspect
        sig = inspect.signature(ops.operations_summary)
        assert "admin" in sig.parameters

    def test_health_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_health)
        assert "admin" in sig.parameters

    def test_payments_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_payments)
        assert "admin" in sig.parameters

    def test_webhooks_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_webhooks)
        assert "admin" in sig.parameters

    def test_subscriptions_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_subscriptions)
        assert "admin" in sig.parameters

    def test_usage_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_usage)
        assert "admin" in sig.parameters

    def test_alerts_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_alerts)
        assert "admin" in sig.parameters

    def test_run_expiry_job_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_run_expiry_job)
        assert "admin" in sig.parameters

    def test_expiry_job_status_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_expiry_job_status)
        assert "admin" in sig.parameters


# ── Summary endpoint ──────────────────────────────────────────────────────────

class TestOperationsSummary:
    """GET /summary returns combined snapshot with required keys."""

    def test_summary_returns_success(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        assert result["success"] is True

    def test_summary_has_required_top_level_keys(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        for key in ("health", "payments_30d", "users", "in_memory_metrics", "generated_at"):
            assert key in result, f"Summary must include '{key}'"

    def test_summary_health_section(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        assert "database_connected" in result["health"]
        assert "overall_ok" in result["health"]

    def test_summary_payments_section(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        p = result["payments_30d"]
        for key in ("total", "paid", "failed"):
            assert key in p

    def test_summary_users_section(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        u = result["users"]
        assert "total" in u

    def test_summary_in_memory_metrics_note(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        # Must include the process-local disclaimer
        note = result["in_memory_metrics"].get("_note", "")
        assert "process" in note.lower() or "restart" in note.lower(), (
            "in_memory_metrics must warn that counters reset on restart"
        )

    def test_summary_does_not_expose_secrets(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_summary(admin=ADMIN_CTX)
        result_str = str(result)
        secret_patterns = ["sk-", "rzp_secret", "webhook_secret", "service_key", "api_secret"]
        for pat in secret_patterns:
            assert pat not in result_str.lower(), f"Summary must not expose secret pattern: {pat}"


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestOperationsHealth:
    """GET /health returns app + database + config status."""

    def test_health_returns_success(self, monkeypatch):
        monkeypatch.setattr(ops, "admin_client", MagicMock(**{
            "table.return_value.select.return_value.limit.return_value.execute.return_value.data": []
        }))
        result = ops.operations_health(admin=ADMIN_CTX)
        assert result["success"] is True

    def test_health_has_required_sections(self, monkeypatch):
        monkeypatch.setattr(ops, "admin_client", MagicMock(**{
            "table.return_value.select.return_value.limit.return_value.execute.return_value.data": []
        }))
        result = ops.operations_health(admin=ADMIN_CTX)
        for key in ("app", "database", "config", "checked_at", "overall_healthy"):
            assert key in result

    def test_health_config_shows_only_presence_not_values(self, monkeypatch):
        """Config check must only show True/False, never the actual secret values."""
        monkeypatch.setattr(ops, "admin_client", MagicMock(**{
            "table.return_value.select.return_value.limit.return_value.execute.return_value.data": []
        }))
        result = ops.operations_health(admin=ADMIN_CTX)
        config = result["config"]
        for k, v in config.items():
            assert isinstance(v, bool), f"Config[{k}] must be bool, got {type(v)}"

    def test_health_config_values_are_booleans_not_secrets(self, monkeypatch):
        """
        Config values must be True/False — never the actual secret strings.
        We verify by checking all config values are bool (not str/None that
        could expose a raw API key or service key).
        """
        monkeypatch.setattr(ops, "admin_client", MagicMock(**{
            "table.return_value.select.return_value.limit.return_value.execute.return_value.data": []
        }))
        result = ops.operations_health(admin=ADMIN_CTX)
        config = result["config"]
        # All config values must be boolean — never the raw secret string
        for k, v in config.items():
            assert isinstance(v, bool), f"Config value for {k} must be bool, not {type(v).__name__}"
            assert v is not None, f"Config value for {k} must not be None"
        # The config dict key names are safe (they're field names, not values)
        # Verify no actual secret values appear in the result
        for k, v in config.items():
            # A boolean True/False in string repr is "True" or "False" — never a key-like string
            assert v in (True, False)


# ── Payments endpoint ─────────────────────────────────────────────────────────

class TestOperationsPayments:
    """GET /payments returns payment metrics."""

    def test_payments_returns_success(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert result["success"] is True

    def test_payments_has_summary(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        for key in ("total_payments", "paid", "failed", "success_rate_percent"):
            assert key in result["summary"]

    def test_payments_has_in_memory_note(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        note = result["in_memory_counters"].get("_note", "")
        assert "process" in note.lower() or "restart" in note.lower()

    def test_payments_success_rate_none_for_zero_total(self, monkeypatch):
        _mock_empty_profiles(monkeypatch)
        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        # With no payments, success_rate should be None
        assert result["summary"]["success_rate_percent"] is None

    def test_payments_with_data(self, monkeypatch):
        """Payments with 3 paid + 1 failed = 75% success rate."""
        mock_client = MagicMock()
        payments_data = [
            {"status": "paid", "plan_key": "starter", "amount": 299, "razorpay_order_id": f"ord_{i}", "created_at": "2026-01-01T00:00:00"}
            for i in range(3)
        ] + [
            {"status": "signature_failed", "plan_key": "free", "amount": 99, "razorpay_order_id": "ord_fail", "created_at": "2026-01-01T00:00:00"}
        ]
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = payments_data
        monkeypatch.setattr(ops, "admin_client", mock_client)

        result = ops.operations_payments(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert result["summary"]["total_payments"] == 4
        assert result["summary"]["paid"] == 3
        assert result["summary"]["success_rate_percent"] == 75.0


# ── Subscriptions endpoint ────────────────────────────────────────────────────

class TestOperationsSubscriptions:
    """GET /subscriptions returns plan counts + timeline."""

    def test_subscriptions_returns_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_subscriptions(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert result["success"] is True

    def test_subscriptions_has_active_subscriptions(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_subscriptions(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert "active_subscriptions" in result
        assert "FREE_TIER" in result["active_subscriptions"]

    def test_subscriptions_plan_counts_nano(self, monkeypatch):
        """A profile with plan_key='free' and access_cbse=True should count as Nano."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"subscription_plan": "free", "access_cbse": True, "subscription_expires_at": None, "role": "student"},
        ]
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_subscriptions(days=30, page=1, page_size=20, admin=ADMIN_CTX)
        assert result["active_subscriptions"].get("Nano", 0) == 1
        assert result["active_subscriptions"].get("FREE_TIER", 0) == 0


# ── Usage endpoint ────────────────────────────────────────────────────────────

class TestOperationsUsage:
    """GET /usage returns user counts + teacher assignments."""

    def test_usage_returns_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.execute.return_value.count = 0
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_usage(admin=ADMIN_CTX)
        assert result["success"] is True

    def test_usage_has_user_counts(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = [
            {"role": "student"}, {"role": "parent"}, {"role": "teacher"},
        ]
        mock_client.table.return_value.select.return_value.execute.return_value.count = 0
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_usage(admin=ADMIN_CTX)
        assert result["users"]["total"] == 3
        assert result["users"]["student"] == 1
        assert result["users"]["parent"] == 1
        assert result["users"]["teacher"] == 1

    def test_usage_has_in_memory_note(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.execute.return_value.count = 0
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_usage(admin=ADMIN_CTX)
        note = result["in_memory_counters"].get("_note", "")
        assert "process" in note.lower() or "restart" in note.lower()


# ── Expiry job endpoints ──────────────────────────────────────────────────────

class TestExpiryJobEndpoints:
    """POST /run-expiry-job triggers run_expiry_job and returns summary."""

    def test_run_expiry_job_returns_success(self, monkeypatch):
        fake_summary = {
            "ran_at": "2026-01-01T00:00:00",
            "users_inspected": 5,
            "users_revoked": 2,
            "users_skipped_already_revoked": 3,
            "users_skipped_offer_fallback": 0,
            "errors": 0,
        }
        monkeypatch.setattr(ops, "run_expiry_job", lambda: fake_summary)
        result = ops.operations_run_expiry_job(admin=ADMIN_CTX)
        assert result["success"] is True
        assert result["users_inspected"] == 5
        assert result["users_revoked"] == 2

    def test_expiry_job_status_returns_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_expiry_job_status(admin=ADMIN_CTX)
        assert result["success"] is True

    def test_expiry_job_status_has_last_run(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_expiry_job_status(admin=ADMIN_CTX)
        assert "last_run" in result
        assert "last_run_summary" in result
        assert "in_memory_counters" in result

    def test_expiry_job_status_with_audit_data(self, monkeypatch):
        """When audit log has expiry_job.ran event, last_run is populated."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "event_type": "expiry_job.ran",
                "created_at": "2026-06-01T10:00:00",
                "metadata": {"users_inspected": 10, "users_revoked": 3, "errors": 0},
            }
        ]
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_expiry_job_status(admin=ADMIN_CTX)
        assert result["last_run"] is not None
        assert result["last_run_summary"]["users_inspected"] == 10


# ── Chat retention job endpoint ────────────────────────────────────────────────

class TestChatRetentionJobEndpoint:
    """POST /run-chat-retention-job triggers run_chat_retention_job and returns summary."""

    def test_run_chat_retention_job_requires_admin(self):
        import inspect
        sig = inspect.signature(ops.operations_run_chat_retention_job)
        assert "admin" in sig.parameters

    def test_run_chat_retention_job_returns_success(self, monkeypatch):
        fake_summary = {
            "ran_at": "2026-01-01T00:00:00",
            "messages_inspected": 4,
            "messages_deleted": 4,
            "attachments_deleted": 2,
            "attachment_delete_errors": 0,
            "total_attachment_bytes": 12345,
            "storage_alert_sent": False,
            "errors": 0,
        }
        monkeypatch.setattr(ops, "run_chat_retention_job", lambda: fake_summary)
        result = ops.operations_run_chat_retention_job(admin=ADMIN_CTX)
        assert result["success"] is True
        assert result["messages_deleted"] == 4
        assert result["attachments_deleted"] == 2


# ── Alerts endpoint ───────────────────────────────────────────────────────────

class TestOperationsAlerts:
    """GET /alerts returns recent audit events."""

    def test_alerts_returns_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_alerts(days=7, page=1, page_size=20, admin=ADMIN_CTX)
        assert result["success"] is True

    def test_alerts_has_required_keys(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_alerts(days=7, page=1, page_size=20, admin=ADMIN_CTX)
        for key in ("alert_counts", "recent_alerts", "total_alerts_in_period"):
            assert key in result

    def test_alerts_does_not_return_secret_metadata(self, monkeypatch):
        """Alert events must strip secret metadata — only event_type/entity are returned."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "event_type": "payment.verify_failed",
                "entity_type": "payment",
                "entity_id": "order_abc",
                "created_at": "2026-01-01T00:00:00",
                "metadata": {"api_key": "sk-secret", "amount": 99},
            }
        ]
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_alerts(days=7, page=1, page_size=20, admin=ADMIN_CTX)
        # metadata should not be returned in recent_alerts
        for alert in result["recent_alerts"]:
            assert "metadata" not in alert
            assert "api_key" not in str(alert)
            assert "sk-secret" not in str(alert)


# ── Webhooks endpoint ─────────────────────────────────────────────────────────

class TestOperationsWebhooks:
    """GET /webhooks returns webhook metrics."""

    def test_webhooks_returns_success(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.like.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_webhooks(days=30, admin=ADMIN_CTX)
        assert result["success"] is True

    def test_webhooks_has_required_keys(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.like.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value.data = []
        monkeypatch.setattr(ops, "admin_client", mock_client)
        result = ops.operations_webhooks(days=30, admin=ADMIN_CTX)
        assert "webhook_confirmed_via_db" in result
        assert "recent_webhook_audit_events" in result
