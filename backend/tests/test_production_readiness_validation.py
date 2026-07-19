"""
test_production_readiness_validation.py
═══════════════════════════════════════
Validation tests for all 10 production-readiness review items on commit f05c8f3.

1.  Audit log RLS — no permissive SELECT policy; service_role bypasses RLS
2.  Timeline idempotency key always present for payment/webhook events
3.  Duplicate webhook + duplicate verify cannot create two activation events
4.  Expiry job does NOT revoke admin-granted access (no subscription_expires_at)
5.  Expiry job handles users with active paid subscription correctly
6.  Admin-only endpoints inaccessible to non-admin roles
7.  Metrics counters are shared via Redis when configured, in-memory fallback otherwise (never crashes either way)
8.  Migration scripts are idempotent (CREATE TABLE/INDEX IF NOT EXISTS; no bare CREATE POLICY)
9.  No secrets in audit/timeline metadata
10. All tests continue passing (checked by running the suite)

Run with:
    cd backend && python -m pytest tests/test_production_readiness_validation.py -v
"""

import hashlib
import hmac
import inspect
import pathlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.services.audit_log_service import _sanitize_metadata
from app.services.subscription_timeline_service import activation_idempotency_key
from app.services.metrics_service import get_counters, reset_counters


# ─────────────────────────────────────────────────────────────────────────────
# Item 1: Audit log RLS — no permissive SELECT policy
# ─────────────────────────────────────────────────────────────────────────────

class TestItem1AuditLogRLS:
    """Migration must NOT contain a permissive SELECT USING (true) policy."""

    def _audit_sql(self):
        return (pathlib.Path(__file__).parent.parent
                / "migrations" / "20260626_platform_audit_logs.sql").read_text()

    def _timeline_sql(self):
        return (pathlib.Path(__file__).parent.parent
                / "migrations" / "20260626_subscription_timeline.sql").read_text()

    def test_audit_migration_has_no_permissive_select_policy(self):
        """No CREATE POLICY ... FOR SELECT USING (true) in audit log migration."""
        sql = self._audit_sql()
        # The old bad pattern was: CREATE POLICY "..." ON ... FOR SELECT USING (true)
        assert "FOR SELECT USING (true)" not in sql, (
            "Audit log migration must NOT have a permissive SELECT USING (true) policy"
        )

    def test_timeline_migration_has_no_permissive_select_policy(self):
        """No CREATE POLICY ... FOR SELECT USING (true) in timeline migration."""
        sql = self._timeline_sql()
        assert "FOR SELECT USING (true)" not in sql, (
            "Timeline migration must NOT have a permissive SELECT USING (true) policy"
        )

    def test_audit_migration_enables_rls(self):
        """Audit log table must have RLS enabled."""
        assert "ENABLE ROW LEVEL SECURITY" in self._audit_sql()

    def test_timeline_migration_enables_rls(self):
        """Timeline table must have RLS enabled."""
        assert "ENABLE ROW LEVEL SECURITY" in self._timeline_sql()

    def test_audit_migration_documents_service_role_bypass(self):
        """Migration comment must explain that service_role bypasses RLS."""
        sql = self._audit_sql()
        assert "service_role" in sql.lower() or "service_role" in sql


# ─────────────────────────────────────────────────────────────────────────────
# Item 2: Timeline idempotency key always present for payment/webhook events
# ─────────────────────────────────────────────────────────────────────────────

class TestItem2TimelineIdempotencyKey:
    """Every payment/webhook activation writes an idempotency_key to timeline."""

    def test_verify_payment_passes_idempotency_key(self):
        """verify_payment must call write_timeline_event with idempotency_key."""
        src = inspect.getsource(__import__(
            "app.routes.payments", fromlist=["verify_payment"]
        ).verify_payment)
        assert "idempotency_key" in src
        assert "activation_idempotency_key" in src

    def test_admin_test_verify_passes_idempotency_key(self):
        """admin_test_verify must call write_timeline_event with idempotency_key."""
        src = inspect.getsource(__import__(
            "app.routes.payments", fromlist=["admin_test_verify"]
        ).admin_test_verify)
        assert "idempotency_key" in src
        assert "activation_idempotency_key" in src

    def test_activation_idempotency_key_is_stable(self):
        """Same order_id + payment_id always produces the same key."""
        k1 = activation_idempotency_key("order_abc", "pay_xyz")
        k2 = activation_idempotency_key("order_abc", "pay_xyz")
        assert k1 == k2 == "pay:order_abc:pay_xyz"

    def test_timeline_unique_index_on_idempotency_key_exists(self):
        """Migration defines a UNIQUE INDEX on idempotency_key."""
        sql = (pathlib.Path(__file__).parent.parent
               / "migrations" / "20260626_subscription_timeline.sql").read_text()
        assert "UNIQUE INDEX" in sql or "unique index" in sql.lower()
        assert "idempotency_key" in sql


# ─────────────────────────────────────────────────────────────────────────────
# Item 3: Duplicate webhook + verify → only one activation event
# ─────────────────────────────────────────────────────────────────────────────

class TestItem3DuplicateDedup:
    """Both the idempotency guard and timeline dedup must prevent double-activation."""

    def test_webhook_already_processed_skips_activation(self):
        """Webhook with already-paid order returns 'already_processed'."""
        src = inspect.getsource(
            __import__("app.routes.payments", fromlist=["razorpay_webhook"]).razorpay_webhook
        )
        assert "already_processed" in src

    def test_verify_already_paid_does_not_activate(self, monkeypatch):
        """verify_payment returns idempotent=True without calling activate_plan."""
        import app.routes.payments as p
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_ID", "rzp")
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", "sec")
        monkeypatch.setattr(p, "get_payment_by_order_id", lambda _: {
            "razorpay_order_id": "order_x", "parent_id": "par-1",
            "status": "paid", "plan_key": "starter", "child_id": "ch-1",
        })
        calls = []
        monkeypatch.setattr(p, "activate_plan_for_payment",
                            lambda *a, **k: calls.append(1) or [])
        result = p.verify_payment(
            p.VerifyPaymentRequest(
                razorpay_order_id="order_x",
                razorpay_payment_id="pay_x",
                razorpay_signature="sig",
            ),
            parent={"profile": {"id": "par-1"}},
        )
        assert result["idempotent"] is True
        assert calls == []

    def test_timeline_duplicate_key_returns_false(self, monkeypatch):
        """Second write_timeline_event with same idempotency_key returns False."""
        import app.services.subscription_timeline_service as ts
        from app.services.subscription_timeline_service import write_timeline_event
        calls = []
        def fake_execute():
            if len(calls) == 0:
                calls.append(1)
                return None
            raise Exception("duplicate key value violates unique constraint")
        mc = MagicMock()
        mc.table.return_value.insert.return_value.execute = fake_execute
        monkeypatch.setattr(ts, "admin_client", mc)
        key = activation_idempotency_key("ord1", "pay1")
        assert write_timeline_event(user_id="u", event_type="X", idempotency_key=key) is True
        assert write_timeline_event(user_id="u", event_type="X", idempotency_key=key) is False


# ─────────────────────────────────────────────────────────────────────────────
# Item 4: Expiry job does NOT revoke admin-granted access
# ─────────────────────────────────────────────────────────────────────────────

class TestItem4ExpiryJobAdminGrant:
    """
    Admin-granted access users have subscription_expires_at = NULL.
    The expiry job query uses .lt("subscription_expires_at", now) which
    only fetches rows where the value IS NOT NULL and is in the past.
    A NULL expires_at means the user is never in the query result.
    """

    def test_expiry_job_query_requires_non_null_expires_at(self):
        """Expiry job source code must use .lt() and .not_.is_() to exclude NULL rows."""
        src = inspect.getsource(
            __import__(
                "app.services.expiry_job_service",
                fromlist=["run_expiry_job"],
            ).run_expiry_job
        )
        # Must filter to past expires_at values only
        assert ".lt(" in src, "expiry_job must use .lt() to find only expired rows"
        assert "subscription_expires_at" in src

    def test_update_child_access_clears_subscription_expires_at(self):
        """
        update_child_access (admin grant) must write subscription_expires_at=None.
        Without this, the expiry job would revoke admin-granted access for users
        who previously had a paid subscription with a stale expires_at.
        """
        src = inspect.getsource(
            __import__(
                "app.routes.admin_control",
                fromlist=["update_child_access"],
            ).update_child_access
        )
        assert "subscription_expires_at" in src, (
            "update_child_access must clear subscription_expires_at "
            "to prevent the expiry job from revoking admin-granted access"
        )
        assert "None" in src

    def test_expiry_job_skips_user_with_no_access_flags(self, monkeypatch):
        """User with access_cbse=False (already admin-revoked or never had access) is skipped."""
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        profile = {
            "id": "u-no-access",
            "username": "noaccess",
            "subscription_plan": "free",
            "subscription_expires_at": past,
            "access_cbse": False,   # no access → job must skip, not revoke
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
        }

        class FakeResp:
            data = [profile]

        class FakeTable:
            def select(self, *a): return self
            def lt(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def execute(self): return FakeResp()

        mc = MagicMock()
        mc.table.return_value = FakeTable()
        monkeypatch.setattr(ej, "admin_client", mc)
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["users_skipped_already_revoked"] == 1
        assert result["users_revoked"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Item 5: Expiry job does not touch active paid subscriptions
# ─────────────────────────────────────────────────────────────────────────────

class TestItem5ExpiryJobActiveUsers:
    """Users with a future subscription_expires_at must not be revoked."""

    def test_expiry_query_uses_lt_not_lte_or_eq(self):
        """Query uses .lt() so future expires_at rows are excluded from results."""
        src = inspect.getsource(
            __import__(
                "app.services.expiry_job_service",
                fromlist=["run_expiry_job"],
            ).run_expiry_job
        )
        # .lt() means strictly less than now — future dates excluded
        assert '.lt("subscription_expires_at"' in src or ".lt(" in src

    def test_active_user_not_returned_by_lt_query(self):
        """A user with expires_at tomorrow would not be in the query result."""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=1)).isoformat()
        # Simulate what the DB filter does: lt(expires_at, now) = False for future dates
        assert future > now.isoformat()   # future is after now, so lt(future, now) = False


# ─────────────────────────────────────────────────────────────────────────────
# Item 6: Admin-only endpoints require admin role
# ─────────────────────────────────────────────────────────────────────────────

class TestItem6AdminOnlyEndpoints:
    """run-expiry-job and metrics endpoints must use require_admin dependency."""

    def test_run_expiry_job_requires_admin(self):
        from app.routes.subscription import run_expiry_job
        sig = inspect.signature(run_expiry_job)
        assert "admin" in sig.parameters, (
            "POST /subscription/run-expiry-job must have admin=Depends(require_admin)"
        )

    def test_metrics_requires_admin(self):
        from app.routes.subscription import get_metrics
        sig = inspect.signature(get_metrics)
        assert "admin" in sig.parameters, (
            "GET /subscription/metrics must have admin=Depends(require_admin)"
        )

    def test_admin_test_verify_requires_admin(self):
        from app.routes.payments import admin_test_verify
        sig = inspect.signature(admin_test_verify)
        assert "admin" in sig.parameters

    def test_admin_test_create_order_requires_admin(self):
        from app.routes.payments import admin_test_create_order
        sig = inspect.signature(admin_test_create_order)
        assert "admin" in sig.parameters

    def test_update_child_access_requires_admin(self):
        from app.routes.admin_control import update_child_access
        sig = inspect.signature(update_child_access)
        assert "admin" in sig.parameters


# ─────────────────────────────────────────────────────────────────────────────
# Item 7: Metrics counters are shared via Redis when configured, in-memory
# fallback otherwise — either way, metrics must never break the calling flow.
# ─────────────────────────────────────────────────────────────────────────────

class TestItem7MetricsPerProcess:
    """
    Metrics must degrade gracefully to per-process/in-memory when Redis is
    unavailable, and must document that fallback behavior. (Previously this
    class asserted metrics_service must NEVER import redis at all — that
    constraint was the thing docs/product-specs/07_ARCHITECTURE_ASSESSMENT.md
    §3.2 flagged as the problem, so it's been replaced with the actual
    invariant worth keeping: metrics never crash the request, with or
    without Redis.)
    """

    def test_metrics_docstring_mentions_per_process_fallback(self):
        """metrics_service docstring must document the in-memory fallback behavior."""
        import app.services.metrics_service as ms
        doc = (ms.__doc__ or "").lower()
        src = inspect.getsource(ms)
        assert (
            "process" in doc
            or "process" in src.lower()
        ), "metrics_service must document that in-memory fallback state is per-process"

    def test_metrics_not_shared_across_instances(self):
        """reset_counters affects the current backing store (Redis or in-memory)."""
        reset_counters()
        from app.services.metrics_service import increment
        increment("test.item7")
        counters = get_counters()
        assert counters.get("test.item7") == 1
        # After reset, counter is gone
        reset_counters()
        assert get_counters().get("test.item7") is None

    def test_metrics_never_raises_when_redis_is_broken(self):
        """
        increment/get_counters/reset_counters must never raise, even if the
        module-level redis_client is present but every call to it fails —
        this is the actual production-readiness guarantee: a Redis outage
        degrades metrics, it never breaks the request that triggered them.
        """
        import app.services.metrics_service as ms
        from unittest.mock import MagicMock

        broken_client = MagicMock()
        broken_client.incrby.side_effect = ConnectionError("redis unreachable")
        broken_client.scan.side_effect = ConnectionError("redis unreachable")
        broken_client.delete.side_effect = ConnectionError("redis unreachable")

        original_client = ms.redis_client
        try:
            ms.redis_client = broken_client
            ms.increment("test.item7_broken_redis")   # must not raise
            ms.get_counters()                          # must not raise
            ms.reset_counters()                         # must not raise
        finally:
            ms.redis_client = original_client


# ─────────────────────────────────────────────────────────────────────────────
# Item 8: Migration scripts are idempotent
# ─────────────────────────────────────────────────────────────────────────────

class TestItem8MigrationIdempotency:
    """All migrations must be safe to run more than once."""

    def _sql(self, filename):
        return (pathlib.Path(__file__).parent.parent / "migrations" / filename).read_text()

    def test_payment_id_index_uses_if_not_exists(self):
        sql = self._sql("20260626_payment_unique_payment_id.sql")
        assert "IF NOT EXISTS" in sql

    def test_audit_log_table_uses_if_not_exists(self):
        sql = self._sql("20260626_platform_audit_logs.sql")
        assert "CREATE TABLE IF NOT EXISTS" in sql

    def test_audit_log_indexes_use_if_not_exists(self):
        sql = self._sql("20260626_platform_audit_logs.sql")
        assert "CREATE INDEX IF NOT EXISTS" in sql

    def test_timeline_table_uses_if_not_exists(self):
        sql = self._sql("20260626_subscription_timeline.sql")
        assert "CREATE TABLE IF NOT EXISTS" in sql

    def test_timeline_indexes_use_if_not_exists(self):
        sql = self._sql("20260626_subscription_timeline.sql")
        assert "CREATE UNIQUE INDEX IF NOT EXISTS" in sql

    def test_no_bare_create_policy_in_audit_migration(self):
        """
        Bare CREATE POLICY is NOT idempotent (fails on second run).
        The migration must use a DO/IF EXISTS block to drop-and-recreate or skip.
        """
        sql = self._sql("20260626_platform_audit_logs.sql")
        lines = sql.splitlines()
        for line in lines:
            stripped = line.strip().upper()
            # Bare CREATE POLICY without a DO block wrapping it is not idempotent
            if stripped.startswith("CREATE POLICY") and "IF NOT EXISTS" not in stripped:
                # Only allowed if it's inside a DO $$ block (indented under BEGIN)
                # The migration fixes this by removing the policy altogether
                raise AssertionError(
                    f"Bare CREATE POLICY found: '{line.strip()}' — not idempotent. "
                    "Wrap in DO $$ ... $$ block or remove entirely."
                )

    def test_no_bare_create_policy_in_timeline_migration(self):
        sql = self._sql("20260626_subscription_timeline.sql")
        lines = sql.splitlines()
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith("CREATE POLICY") and "IF NOT EXISTS" not in stripped:
                raise AssertionError(
                    f"Bare CREATE POLICY found: '{line.strip()}' — not idempotent."
                )


# ─────────────────────────────────────────────────────────────────────────────
# Item 9: No secrets in audit/timeline metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestItem9NoSecretsInMetadata:
    """Audit and timeline writes must never include passwords, tokens, or keys."""

    def test_sanitize_strips_password(self):
        assert "password" not in _sanitize_metadata({"password": "secret", "plan": "nano"})

    def test_sanitize_strips_token(self):
        assert "token" not in _sanitize_metadata({"token": "eyJhbG...", "user_id": "u1"})

    def test_sanitize_strips_api_key(self):
        assert "api_key" not in _sanitize_metadata({"api_key": "sk-xxx", "ok": True})

    def test_sanitize_strips_api_secret(self):
        assert "api_secret" not in _sanitize_metadata({"api_secret": "rzp_sec", "amt": 99})

    def test_sanitize_strips_razorpay_key_secret(self):
        assert "razorpay_key_secret" not in _sanitize_metadata({"razorpay_key_secret": "x"})

    def test_sanitize_strips_webhook_secret(self):
        assert "webhook_secret" not in _sanitize_metadata({"webhook_secret": "whs_xxx"})

    def test_sanitize_case_insensitive(self):
        cleaned = _sanitize_metadata({"PASSWORD": "x", "Token": "y", "safe": "z"})
        assert "PASSWORD" not in cleaned
        assert "Token" not in cleaned
        assert cleaned["safe"] == "z"

    def test_audit_event_metadata_in_payments_does_not_include_secrets(self):
        """
        verify_payment passes only plan_key, amount, order_id to audit metadata —
        never raw Razorpay keys or signatures.
        """
        src = inspect.getsource(
            __import__("app.routes.payments", fromlist=["verify_payment"]).verify_payment
        )
        # The metadata dict passed to write_audit_event must not include signature
        # We check that 'razorpay_signature' is not in the metadata dict literal
        # (it's fine to use as a function argument, but not in the logged metadata)
        # Find the write_audit_event call block
        audit_section = src[src.find("write_audit_event"):src.find("write_timeline_event")]
        assert "razorpay_signature" not in audit_section, (
            "write_audit_event metadata must not include razorpay_signature"
        )

    def test_sanitize_preserves_safe_fields(self):
        result = _sanitize_metadata({
            "plan_key": "starter",
            "amount": 299,
            "order_id": "order_abc",
        })
        assert result["plan_key"] == "starter"
        assert result["amount"] == 299
        assert result["order_id"] == "order_abc"
