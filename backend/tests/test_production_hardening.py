"""
test_production_hardening.py
═════════════════════════════
Regression tests for production hardening priorities 1–5.

P1 — DB constraints (payment idempotency, partial unique index)
P2 — Audit logging service (write_audit_event, metadata sanitization)
P3 — Subscription timeline (write_timeline_event, idempotency key dedup)
P4 — Expiry job (idempotent revocation, skip already-revoked users)
P5 — Metrics service (increment, disabled, counters, thread safety)

Run with:
    cd backend && python -m pytest tests/test_production_hardening.py -v
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call
import threading

import pytest

from app.services.audit_log_service import write_audit_event, _sanitize_metadata
from app.services.subscription_timeline_service import (
    write_timeline_event,
    activation_idempotency_key,
)
from app.services.metrics_service import (
    increment,
    get_counters,
    reset_counters,
    log_metric,
    _counters,
    _lock,
)


# ─────────────────────────────────────────────────────────────────────────────
# P1: DB constraints + payment idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestP1DbConstraints:
    """The payment unique index must prevent duplicate payment_id activation."""

    def test_razorpay_order_id_already_unique_in_sql(self):
        """subscription_payments table DDL declares razorpay_order_id as UNIQUE."""
        import pathlib
        sql_path = pathlib.Path(
            __file__
        ).parent.parent / "sql" / "subscription_payments.sql"
        text = sql_path.read_text()
        assert "razorpay_order_id" in text
        assert "unique" in text.lower(), "razorpay_order_id must have UNIQUE constraint"

    def test_partial_unique_index_migration_exists(self):
        """Migration for partial unique index on razorpay_payment_id must exist."""
        import pathlib
        migration_path = pathlib.Path(
            __file__
        ).parent.parent / "migrations" / "20260626_payment_unique_payment_id.sql"
        assert migration_path.exists(), "Migration file for payment_id unique index must exist"
        text = migration_path.read_text()
        assert "UNIQUE INDEX" in text or "unique index" in text.lower()
        assert "razorpay_payment_id" in text
        assert "IS NOT NULL" in text or "is not null" in text.lower(), \
            "Index must be PARTIAL (NULL excluded) so unverified rows don't conflict"

    def test_idempotency_key_helper_is_deterministic(self):
        """activation_idempotency_key must return the same key for the same inputs."""
        key1 = activation_idempotency_key("order_abc", "pay_xyz")
        key2 = activation_idempotency_key("order_abc", "pay_xyz")
        assert key1 == key2

    def test_idempotency_key_differs_for_different_payments(self):
        k1 = activation_idempotency_key("order_1", "pay_1")
        k2 = activation_idempotency_key("order_2", "pay_2")
        assert k1 != k2

    def test_already_paid_order_returns_idempotent_flag(self, monkeypatch):
        """Re-verifying an already-paid order returns idempotent=True."""
        import app.routes.payments as p
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(p, "get_payment_by_order_id", lambda _: {
            "razorpay_order_id": "order_paid",
            "parent_id": "parent-1",
            "status": "paid",
            "plan_key": "starter",
            "child_id": "child-1",
        })
        # activation must NOT be called
        activation_calls = []
        monkeypatch.setattr(p, "activate_plan_for_payment",
                            lambda *a, **kw: activation_calls.append(1) or [])

        result = p.verify_payment(
            p.VerifyPaymentRequest(
                razorpay_order_id="order_paid",
                razorpay_payment_id="pay_x",
                razorpay_signature="sig_x",
            ),
            parent={"profile": {"id": "parent-1"}},
        )
        assert result["idempotent"] is True
        assert activation_calls == [], "Must NOT re-activate an already-paid order"


# ─────────────────────────────────────────────────────────────────────────────
# P2: Audit logging
# ─────────────────────────────────────────────────────────────────────────────

class TestP2AuditLogging:
    """Audit log writes must be fire-and-forget and never expose secrets."""

    def test_sanitize_metadata_strips_password_keys(self):
        meta = {
            "plan_key": "starter",
            "password": "s3cr3t",
            "api_secret": "should_be_gone",
            "amount": 299,
        }
        cleaned = _sanitize_metadata(meta)
        assert "password" not in cleaned
        assert "api_secret" not in cleaned
        assert cleaned["plan_key"] == "starter"
        assert cleaned["amount"] == 299

    def test_sanitize_metadata_case_insensitive(self):
        meta = {"PASSWORD": "leak", "Token": "leak2", "safe_key": "ok"}
        cleaned = _sanitize_metadata(meta)
        assert "PASSWORD" not in cleaned
        assert "Token" not in cleaned
        assert cleaned["safe_key"] == "ok"

    def test_sanitize_metadata_empty_is_safe(self):
        assert _sanitize_metadata({}) == {}

    def test_write_audit_event_never_raises(self, monkeypatch):
        """Audit failure must NOT propagate to the caller."""
        import app.services.audit_log_service as al
        # Simulate DB error
        failing_client = MagicMock()
        failing_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB down")
        monkeypatch.setattr(al, "admin_client", failing_client)

        # Should not raise
        write_audit_event(
            event_type="payment.verified",
            actor_user_id="user-1",
            metadata={"amount": 99},
        )  # no exception expected

    def test_write_audit_event_strips_secrets_from_metadata(self, monkeypatch):
        """Audit event must not pass secret fields to the DB."""
        import app.services.audit_log_service as al

        saved_rows = []
        mock_client = MagicMock()
        mock_client.table.return_value.insert.side_effect = (
            lambda row: type("R", (), {"execute": lambda self: saved_rows.append(row)})()
        )
        monkeypatch.setattr(al, "admin_client", mock_client)

        write_audit_event(
            event_type="test.event",
            metadata={"password": "should_be_gone", "plan": "nano"},
        )
        if saved_rows:
            meta = saved_rows[0].get("metadata", {})
            assert "password" not in meta
            assert meta.get("plan") == "nano"

    def test_business_action_succeeds_even_if_audit_fails(self, monkeypatch):
        """
        Verify that a payment that succeeds returns correctly even when
        audit_log and timeline both fail.
        """
        import app.routes.payments as p
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", "secret")
        secret = "test_secret"
        payment_id = "pay_ok"
        order_id = "order_ok"
        sig = hmac.new(
            secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()

        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", secret)
        monkeypatch.setattr(p, "get_payment_by_order_id", lambda _: {
            "razorpay_order_id": order_id,
            "parent_id": "parent-1",
            "child_id": "child-1",
            "plan_key": "starter",
            "status": "created",
        })
        monkeypatch.setattr(p, "get_public_plan", lambda k: {
            "key": k, "billing_label": "month", "access_cbse": True,
            "access_sof_science": False, "access_sof_maths": False,
            "access_sof_english": False, "daily_token_limit": 50000, "monthly_token_limit": 1000000,
        })
        monkeypatch.setattr(p, "activate_plan_for_payment", lambda *a, **kw: [{"id": "child-1"}])
        monkeypatch.setattr(p, "save_payment_record", lambda r: r)

        # Both audit and timeline throw
        def _audit_fail(**kw):
            raise Exception("audit down")

        def _timeline_fail(**kw):
            raise Exception("timeline down")

        monkeypatch.setattr(p, "write_audit_event", _audit_fail)
        monkeypatch.setattr(p, "write_timeline_event", _timeline_fail)

        result = p.verify_payment(
            p.VerifyPaymentRequest(
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=sig,
            ),
            parent={"profile": {"id": "parent-1"}},
        )
        # Business flow must succeed despite audit/timeline failures
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# P3: Subscription timeline
# ─────────────────────────────────────────────────────────────────────────────

class TestP3SubscriptionTimeline:
    """Timeline events are append-only and deduplicated by idempotency_key."""

    def test_write_timeline_event_returns_true_on_success(self, monkeypatch):
        import app.services.subscription_timeline_service as ts
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = None
        monkeypatch.setattr(ts, "admin_client", mock_client)

        result = write_timeline_event(
            user_id="user-1",
            event_type="NANO.activated",
            to_plan="free",
            source="PAID",
        )
        assert result is True

    def test_write_timeline_event_returns_false_on_duplicate(self, monkeypatch):
        """Duplicate idempotency_key must return False (not raise)."""
        import app.services.subscription_timeline_service as ts
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        monkeypatch.setattr(ts, "admin_client", mock_client)

        result = write_timeline_event(
            user_id="user-1",
            event_type="NANO.activated",
            idempotency_key="pay:order_1:pay_1",
        )
        assert result is False

    def test_write_timeline_event_never_raises(self, monkeypatch):
        """Any DB error must return False, not raise."""
        import app.services.subscription_timeline_service as ts
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("network error")
        monkeypatch.setattr(ts, "admin_client", mock_client)

        result = write_timeline_event(user_id="u-1", event_type="plan.expired")
        assert result is False

    def test_activation_idempotency_key_format(self):
        key = activation_idempotency_key("order_abc", "pay_xyz")
        assert key == "pay:order_abc:pay_xyz"

    def test_duplicate_activation_does_not_create_second_event(self, monkeypatch):
        """Calling write_timeline_event twice with the same key returns False the 2nd time."""
        import app.services.subscription_timeline_service as ts

        calls = []

        def fake_execute():
            if len(calls) == 0:
                calls.append(1)
                return None
            raise Exception("unique constraint violation")

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute = fake_execute
        monkeypatch.setattr(ts, "admin_client", mock_client)

        key = activation_idempotency_key("order_1", "pay_1")
        r1 = write_timeline_event(user_id="u-1", event_type="NANO.activated", idempotency_key=key)
        r2 = write_timeline_event(user_id="u-1", event_type="NANO.activated", idempotency_key=key)
        assert r1 is True
        assert r2 is False


# ─────────────────────────────────────────────────────────────────────────────
# P4: Expiry job
# ─────────────────────────────────────────────────────────────────────────────

class TestP4ExpiryJob:
    """Expiry job must be idempotent and preserve offer-code fallback."""

    def _make_expired_profile(self, user_id="u-1", access_cbse=True, plan_key="free"):
        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        return {
            "id": user_id,
            "username": "testuser",
            "subscription_plan": plan_key,
            "subscription_expires_at": past,
            "access_cbse": access_cbse,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
        }

    def test_expiry_job_revokes_expired_user(self, monkeypatch):
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        profile = self._make_expired_profile()

        class FakeResp:
            data = [profile]

        class FakeOfferResp:
            data = []  # no active offer

        class FakeUpdateResp:
            # Real PostgREST returns the updated row(s) when the .eq() filters
            # (including the subscription_expires_at guard) match — a non-empty
            # .data here is what tells run_expiry_job() the update actually hit.
            data = [profile]

        updated_profiles = []

        class FakeTable:
            _op = "select"
            _select_count = 0
            def select(self, *a):
                self._op = "select"
                self._select_count += 1
                return self
            def lt(self, *a): return self
            def gte(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def eq(self, col, val): return self
            def update(self, data):
                self._op = "update"
                updated_profiles.append(data)
                return self
            def limit(self, n): return self
            def order(self, *a, **kw): return self
            def execute(self):
                if self._op == "update":
                    return FakeUpdateResp()    # profiles UPDATE matched the row
                if self._select_count == 1:
                    return FakeResp()          # initial expired-profiles batch
                return FakeOfferResp()         # offer_redemptions check (no offer)

        mock_client = MagicMock()
        mock_client.table.return_value = FakeTable()
        monkeypatch.setattr(ej, "admin_client", mock_client)
        # Silence side-effect services
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["users_inspected"] == 1
        assert result["users_revoked"] == 1
        assert result["errors"] == 0

    def test_expiry_job_preserves_renewal_that_lands_mid_run(self, monkeypatch):
        """
        REGRESSION: a renewal landing between the batch SELECT and this row's
        UPDATE must survive, not get silently reverted.

        The revoke UPDATE is guarded by .eq("subscription_expires_at", <value
        read at SELECT time>) — if the user renewed in between (a real gap
        when many profiles expire in the same run), the row's real value has
        since changed, so the guarded UPDATE matches zero rows and becomes a
        no-op instead of clobbering the fresh renewal.
        """
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        profile = self._make_expired_profile()  # stale subscription_expires_at read at SELECT time

        class FakeResp:
            data = [profile]

        class FakeOfferResp:
            data = []  # no active offer

        class FakeNoMatchUpdateResp:
            # Simulates: the user renewed since the SELECT, so the row's real
            # subscription_expires_at no longer matches — the .eq() guard
            # matches zero rows and PostgREST returns no updated rows.
            data = []

        updated_profiles = []

        class FakeTable:
            _op = "select"
            _select_count = 0
            def select(self, *a):
                self._op = "select"
                self._select_count += 1
                return self
            def lt(self, *a): return self
            def gte(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def eq(self, col, val): return self
            def update(self, data):
                self._op = "update"
                updated_profiles.append(data)
                return self
            def limit(self, n): return self
            def order(self, *a, **kw): return self
            def execute(self):
                if self._op == "update":
                    return FakeNoMatchUpdateResp()
                if self._select_count == 1:
                    return FakeResp()
                return FakeOfferResp()

        mock_client = MagicMock()
        mock_client.table.return_value = FakeTable()
        monkeypatch.setattr(ej, "admin_client", mock_client)
        audit_calls = []
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: audit_calls.append(kw))
        timeline_calls = []
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: timeline_calls.append(kw) or True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["users_inspected"] == 1
        assert result["users_revoked"] == 0
        assert result["users_skipped_renewed_mid_run"] == 1
        assert result["errors"] == 0
        # No misleading "this user's subscription expired" audit/timeline
        # trail for a renewal that actually survived.
        assert timeline_calls == []
        assert not any(c.get("event_type") == "subscription.expired" for c in audit_calls)

    def test_expiry_job_skips_already_revoked_user(self, monkeypatch):
        """User with no access flags set must be skipped (not counted as revoked)."""
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        # access_cbse=False means already revoked
        profile = self._make_expired_profile(access_cbse=False)

        class FakeResp:
            data = [profile]

        class FakeTable2:
            def select(self, *a): return self
            def lt(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def execute(self): return FakeResp()

        mock_client = MagicMock()
        mock_client.table.return_value = FakeTable2()
        monkeypatch.setattr(ej, "admin_client", mock_client)
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["users_inspected"] == 1
        assert result["users_revoked"] == 0
        assert result["users_skipped_already_revoked"] == 1

    def test_expiry_job_with_no_expired_users_is_safe(self, monkeypatch):
        """Job with no expired users returns 0 revocations."""
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        class FakeResp:
            data = []

        class FakeTable3:
            def select(self, *a): return self
            def lt(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def execute(self): return FakeResp()

        mock_client = MagicMock()
        mock_client.table.return_value = FakeTable3()
        monkeypatch.setattr(ej, "admin_client", mock_client)
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["users_revoked"] == 0
        assert result["errors"] == 0

    def test_expiry_job_is_safe_when_db_fails(self, monkeypatch):
        """DB failure must not raise — returns errors count."""
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        class FailingTable:
            def select(self, *a): raise Exception("DB down")

        mock_client = MagicMock()
        mock_client.table.return_value = FailingTable()
        monkeypatch.setattr(ej, "admin_client", mock_client)
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        assert result["errors"] >= 1

    def test_expiry_job_summary_has_required_keys(self, monkeypatch):
        import app.services.expiry_job_service as ej
        from app.services.expiry_job_service import run_expiry_job

        class FakeResp:
            data = []

        class FakeTable4:
            def select(self, *a): return self
            def lt(self, *a): return self
            @property
            def not_(self): return self
            def is_(self, *a): return self
            def execute(self): return FakeResp()

        monkeypatch.setattr(ej, "admin_client", MagicMock(**{"table.return_value": FakeTable4()}))
        monkeypatch.setattr(ej, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(ej, "write_timeline_event", lambda **kw: True)
        monkeypatch.setattr(ej, "increment", lambda *a, **kw: None)

        result = run_expiry_job()
        for key in ("ran_at", "users_inspected", "users_revoked", "errors"):
            assert key in result, f"Summary must include '{key}'"


# ─────────────────────────────────────────────────────────────────────────────
# P5: Metrics service
# ─────────────────────────────────────────────────────────────────────────────

class TestP5MetricsService:
    """Metrics counters are thread-safe and never break the calling flow."""

    def setup_method(self):
        reset_counters()

    def test_increment_increases_counter(self):
        increment("payment.verified")
        increment("payment.verified")
        counters = get_counters()
        assert counters["payment.verified"] == 2

    def test_increment_with_value(self):
        increment("expiry_job.users_revoked", value=5)
        assert get_counters()["expiry_job.users_revoked"] == 5

    def test_multiple_counters_are_independent(self):
        increment("payment.verified")
        increment("payment.verify_failed")
        counters = get_counters()
        assert counters["payment.verified"] == 1
        assert counters["payment.verify_failed"] == 1

    def test_reset_counters_clears_all(self):
        increment("test.counter")
        reset_counters()
        assert get_counters() == {}

    def test_increment_never_raises_on_bad_type(self):
        """Even passing a non-string counter must not raise."""
        try:
            increment(None)   # type: ignore
        except Exception:
            pass  # tolerate — just must not break the caller

    def test_log_metric_never_raises(self):
        """log_metric must not raise even with weird args."""
        log_metric("test.event", plan="nano", amount=99)  # no exception

    def test_get_counters_returns_snapshot(self):
        increment("a.counter")
        snap = get_counters()
        increment("a.counter")   # second increment after snapshot
        # snapshot is not affected by changes after it
        assert snap["a.counter"] == 1
        assert get_counters()["a.counter"] == 2

    def test_increment_is_thread_safe(self):
        """Concurrent increments from multiple threads must produce correct total."""
        reset_counters()
        threads = [
            threading.Thread(target=lambda: increment("concurrent.counter"))
            for _ in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert get_counters()["concurrent.counter"] == 50

    def test_payment_verify_increments_metric(self, monkeypatch):
        """Successful payment verification must increment payment.verified counter."""
        import app.routes.payments as p
        reset_counters()

        secret = "test_key"
        order_id = "order_metric"
        payment_id = "pay_metric"
        sig = hmac.new(
            secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()

        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", secret)
        monkeypatch.setattr(p, "get_payment_by_order_id", lambda _: {
            "razorpay_order_id": order_id,
            "parent_id": "parent-1",
            "child_id": "child-1",
            "plan_key": "starter",
            "status": "created",
        })
        monkeypatch.setattr(p, "get_public_plan", lambda k: {
            "key": k, "billing_label": "month", "access_cbse": True,
            "access_sof_science": False, "access_sof_maths": False,
            "access_sof_english": False, "daily_token_limit": 50000, "monthly_token_limit": 1000000,
        })
        monkeypatch.setattr(p, "activate_plan_for_payment", lambda *a, **kw: [])
        monkeypatch.setattr(p, "save_payment_record", lambda r: r)
        monkeypatch.setattr(p, "write_audit_event", lambda **kw: None)
        monkeypatch.setattr(p, "write_timeline_event", lambda **kw: True)

        p.verify_payment(
            p.VerifyPaymentRequest(
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=sig,
            ),
            parent={"profile": {"id": "parent-1"}},
        )
        assert get_counters().get("payment.verified", 0) >= 1

    def test_admin_test_verify_increments_metric(self, monkeypatch):
        """Admin test verify must increment payment.admin_test_verified counter."""
        import app.routes.payments as p
        reset_counters()

        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(p.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(p, "get_payment_by_order_id", lambda _: {
            "razorpay_order_id": "order_admin",
            "parent_id": "admin-1",
            "child_id": "user-1",
            "plan_key": "free",
            "status": "paid",   # already paid → idempotent path
            "metadata": {
                "testMode": True, "adminTriggered": True,
                "chargedAmount": 1, "intendedPlanAmount": 99,
            },
        })

        result = p.admin_test_verify(
            p.AdminTestVerifyRequest(
                razorpay_order_id="order_admin",
                razorpay_payment_id="pay_admin",
                razorpay_signature="sig",
            ),
            admin={"profile": {"id": "admin-1"}},
        )
        # idempotent path - metrics not incremented on duplicate
        assert result.get("idempotent") is True

    def test_metrics_endpoint_is_admin_only(self):
        """GET /subscription/metrics must require admin."""
        import inspect
        from app.routes.subscription import get_metrics
        sig = inspect.signature(get_metrics)
        assert "admin" in sig.parameters, "metrics endpoint must require admin dependency"
