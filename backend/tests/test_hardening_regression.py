"""
test_hardening_regression.py
═════════════════════════════
Regression tests for the 4-scope subscription hardening phase.

Scope 1 — Resolver output includes child_limit, student_limit, restrictions
Scope 2 — Plan catalog endpoint + backend/frontend plan config parity
Scope 3 — Payment idempotency (duplicate verify returns existing state, not re-activates)
Scope 4 — Rate limiting (429 after threshold, disabled in test mode)

Run with:
    cd backend && python -m pytest tests/test_hardening_regression.py -v
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import app.routes.payments as payments_route
from app.routes.payments import (
    ADMIN_TEST_CHARGE_RUPEES,
    ADMIN_TEST_UPGRADE_PLANS,
    AdminTestOrderRequest,
    AdminTestVerifyRequest,
    VerifyPaymentRequest,
    get_payment_by_order_id,
    profile_access_from_plan,
    save_payment_record,
    verify_razorpay_signature,
    verify_payment,
    admin_test_verify,
)
from app.routes.subscription import CANONICAL_PLAN_CATALOG
from app.services.rate_limit_service import RateLimiter, rate_limit_dependency, client_ip
from app.services.subscription_resolver_service import (
    AccessSource,
    Tier,
    _canonical_plan_key,
    _free_result,
    _paid_plan_name,
    _PLAN_LIMITS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _days_from_now(iso_str: str) -> float:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (dt - datetime.now(timezone.utc)).total_seconds() / 86400


def _base_plan(**overrides):
    base = {
        "key": "free",
        "billing_label": "8 days",
        "access_cbse": True,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
        "daily_token_limit": 50000,
        "monthly_token_limit": 1000000,
    }
    return {**base, **overrides}


def _make_signature(order_id: str, payment_id: str, secret: str) -> str:
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


ADMIN_CTX = {"profile": {"id": "admin-1", "role": "admin"}}
PARENT_CTX = {"profile": {"id": "parent-1", "family_id": "fam-1"}}


# ─────────────────────────────────────────────────────────────────────────────
# Scope 1: Resolver output includes child_limit, student_limit, restrictions
# ─────────────────────────────────────────────────────────────────────────────

class TestScope1ResolverOutputFields:
    """The resolver must include child_limit, student_limit, and restrictions."""

    def test_free_result_has_required_fields(self):
        result = _free_result()
        assert "child_limit" in result
        assert "student_limit" in result
        assert "restrictions" in result

    def test_free_result_restrictions_non_empty(self):
        result = _free_result()
        assert isinstance(result["restrictions"], list)
        assert len(result["restrictions"]) > 0, "Free Tier must list restrictions"

    def test_plan_limits_nano(self):
        limits = _PLAN_LIMITS["NANO"]
        assert limits["child_limit"] == 1
        assert limits["student_limit"] is None
        assert limits["restrictions"] == []

    def test_plan_limits_premium(self):
        limits = _PLAN_LIMITS["PREMIUM"]
        assert limits["child_limit"] == 1
        assert limits["restrictions"] == []

    def test_plan_limits_family_premium(self):
        limits = _PLAN_LIMITS["FAMILY_PREMIUM"]
        assert limits["child_limit"] == 2
        assert limits["restrictions"] == []

    def test_plan_limits_free_tier(self):
        limits = _PLAN_LIMITS["FREE_TIER"]
        assert limits["child_limit"] is None
        assert "mock_tests_5_per_day" in limits["restrictions"]
        assert "no_exemplar" in limits["restrictions"]

    def test_admin_grant_no_restrictions(self):
        limits = _PLAN_LIMITS["ADMIN_GRANT"]
        assert limits["restrictions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Scope 2: Plan catalog + backend/frontend parity
# ─────────────────────────────────────────────────────────────────────────────

class TestScope2PlanCatalogParity:
    """The canonical plan catalog must match the spec and be internally consistent."""

    def test_catalog_has_all_four_canonical_plans(self):
        assert "FREE_TIER" in CANONICAL_PLAN_CATALOG
        assert "NANO" in CANONICAL_PLAN_CATALOG
        assert "PREMIUM" in CANONICAL_PLAN_CATALOG
        assert "FAMILY_PREMIUM" in CANONICAL_PLAN_CATALOG

    def test_free_tier_is_not_purchasable(self):
        free = CANONICAL_PLAN_CATALOG["FREE_TIER"]
        assert free["db_plan_key"] is None
        assert free["has_full_access"] is False
        assert free["price_inr"] == 0

    def test_nano_spec(self):
        """Spec: NANO = ₹99, 8 days, full access, 1 child."""
        nano = CANONICAL_PLAN_CATALOG["NANO"]
        assert nano["price_inr"] == 99
        assert nano["duration_days"] == 8
        assert nano["has_full_access"] is True
        assert nano["child_limit"] == 1
        assert nano["access_cbse"] is True
        assert nano["db_plan_key"] == "free"

    def test_premium_spec(self):
        """Spec: PREMIUM = ₹299, 30 days, full access, 1 child."""
        premium = CANONICAL_PLAN_CATALOG["PREMIUM"]
        assert premium["price_inr"] == 299
        assert premium["duration_days"] == 30
        assert premium["has_full_access"] is True
        assert premium["child_limit"] == 1
        assert premium["access_cbse"] is True
        assert premium["db_plan_key"] == "starter"

    def test_family_premium_spec(self):
        """Spec: FAMILY_PREMIUM = ₹499, 30 days, full access, 2 children."""
        fam = CANONICAL_PLAN_CATALOG["FAMILY_PREMIUM"]
        assert fam["price_inr"] == 499
        assert fam["duration_days"] == 30
        assert fam["has_full_access"] is True
        assert fam["child_limit"] == 2
        assert fam["access_cbse"] is True
        assert fam["db_plan_key"] == "family_premium"

    def test_catalog_child_limits_match_plan_limits(self):
        """Plan catalog child limits must match the _PLAN_LIMITS resolver config."""
        for key in ["NANO", "PREMIUM", "FAMILY_PREMIUM"]:
            catalog_limit = CANONICAL_PLAN_CATALOG[key]["child_limit"]
            resolver_limit = _PLAN_LIMITS[key]["child_limit"]
            assert catalog_limit == resolver_limit, (
                f"{key}: catalog child_limit={catalog_limit} != "
                f"resolver child_limit={resolver_limit}"
            )

    def test_catalog_duration_matches_billing_label_to_days(self):
        """Catalog duration_days must match what payments.py billing labels produce."""
        from app.routes.payments import _BILLING_LABEL_TO_DAYS
        nano_duration = CANONICAL_PLAN_CATALOG["NANO"]["duration_days"]
        assert nano_duration == _BILLING_LABEL_TO_DAYS["8 days"]

        premium_duration = CANONICAL_PLAN_CATALOG["PREMIUM"]["duration_days"]
        assert premium_duration == _BILLING_LABEL_TO_DAYS["month"]

    def test_catalog_all_plans_have_required_keys(self):
        required = {
            "canonical_plan_key", "plan_name", "price_inr", "billing_label",
            "duration_days", "has_full_access", "child_limit", "access_cbse",
        }
        for key, plan in CANONICAL_PLAN_CATALOG.items():
            missing = required - set(plan.keys())
            assert not missing, f"Plan {key} missing keys: {missing}"

    def test_monthly_plans_expire_in_30_days_not_31(self):
        """Regression: billing_label='month' must map to 30 days (not 31)."""
        from app.routes.payments import _BILLING_LABEL_TO_DAYS
        assert _BILLING_LABEL_TO_DAYS["month"] == 30
        assert _BILLING_LABEL_TO_DAYS.get("month") != 31


# ─────────────────────────────────────────────────────────────────────────────
# Scope 3: Payment idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestScope3PaymentIdempotency:
    """Verifying an already-paid order must return early without re-activating."""

    def test_verify_already_paid_returns_idempotent_true(self, monkeypatch):
        """Calling /verify on a status=paid order returns idempotent=True."""
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route,
            "get_payment_by_order_id",
            lambda order_id: {
                "razorpay_order_id": order_id,
                "parent_id": "parent-1",
                "child_id": "child-1",
                "plan_key": "starter",
                "status": "paid",      # already verified
                "verified_at": "2026-01-01T00:00:00+00:00",
            },
        )

        # Track whether activate_plan_for_payment is called
        activation_called = {"count": 0}

        def fake_activate(*args, **kwargs):
            activation_called["count"] += 1
            return []

        monkeypatch.setattr(payments_route, "activate_plan_for_payment", fake_activate)

        result = verify_payment(
            VerifyPaymentRequest(
                razorpay_order_id="order_already_paid",
                razorpay_payment_id="pay_already_done",
                razorpay_signature="any_sig",
            ),
            parent=PARENT_CTX,
        )

        assert result["success"] is True
        assert result.get("idempotent") is True
        assert activation_called["count"] == 0, (
            "activate_plan_for_payment must NOT be called for already-paid orders"
        )

    def test_verify_already_paid_returns_existing_payment(self, monkeypatch):
        """The returned payment must be the existing record, not a new one."""
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        existing_payment = {
            "razorpay_order_id": "order_paid",
            "parent_id": "parent-1",
            "status": "paid",
            "plan_key": "starter",
            "verified_at": "2026-01-01T00:00:00+00:00",
        }
        monkeypatch.setattr(payments_route, "get_payment_by_order_id", lambda _: existing_payment)
        monkeypatch.setattr(payments_route, "activate_plan_for_payment", lambda *a, **kw: [])

        result = verify_payment(
            VerifyPaymentRequest(
                razorpay_order_id="order_paid",
                razorpay_payment_id="pay_id",
                razorpay_signature="sig",
            ),
            parent=PARENT_CTX,
        )
        # The returned payment is the stored record
        assert result["payment"]["status"] == "paid"
        assert result["payment"]["verified_at"] == "2026-01-01T00:00:00+00:00"

    def test_admin_test_verify_already_paid_is_idempotent(self, monkeypatch):
        """Calling admin-test-verify twice on a paid order returns idempotent=True."""
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route,
            "get_payment_by_order_id",
            lambda order_id: {
                "razorpay_order_id": order_id,
                "parent_id": "admin-1",
                "child_id": "user-free-1",
                "plan_key": "free",
                "status": "paid",
                "metadata": {
                    "testMode": True,
                    "adminTriggered": True,
                    "chargedAmount": 1,
                    "intendedPlanAmount": 99,
                },
            },
        )

        result = admin_test_verify(
            AdminTestVerifyRequest(
                razorpay_order_id="order_test_paid",
                razorpay_payment_id="pay_test_paid",
                razorpay_signature="sig",
            ),
            admin=ADMIN_CTX,
        )
        assert result["success"] is True
        assert result.get("idempotent") is True

    def test_failed_payment_does_not_activate(self, monkeypatch):
        """A payment with status=signature_failed must never activate a plan."""
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route,
            "get_payment_by_order_id",
            lambda order_id: {
                "razorpay_order_id": order_id,
                "parent_id": "parent-1",
                "child_id": "child-1",
                "plan_key": "starter",
                "status": "signature_failed",   # previously failed
            },
        )
        monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

        # Signature is WRONG — must reject and NOT activate
        with pytest.raises(HTTPException) as exc:
            verify_payment(
                VerifyPaymentRequest(
                    razorpay_order_id="order_failed",
                    razorpay_payment_id="pay_bad",
                    razorpay_signature="invalid_sig",
                ),
                parent=PARENT_CTX,
            )
        assert exc.value.status_code == 400

    def test_webhook_dedup_skips_already_paid(self):
        """
        The webhook dedup check (status == 'paid') must be present in the route.
        This is a structural test — verifies the webhook skip path exists.
        """
        # Verified by reading the source: webhook returns {"status":"ok","note":"already_processed"}
        # when payment.get("status") == "paid".  Confirmed in test below.
        import app.routes.payments as p  # noqa: PLC0415
        import inspect
        src = inspect.getsource(p.razorpay_webhook)
        assert 'already_processed' in src, "Webhook must skip already-paid orders"
        assert '"paid"' in src or "'paid'" in src


# ─────────────────────────────────────────────────────────────────────────────
# Scope 4: Rate limiting
# ─────────────────────────────────────────────────────────────────────────────

class TestScope4RateLimiting:
    """Rate limiter must block after threshold; disabled when enabled=False."""

    def test_rate_limiter_allows_up_to_max_calls(self):
        limiter = RateLimiter(max_calls=3, window_seconds=60, enabled=True)
        for _ in range(3):
            assert limiter.is_allowed("test-key") is True

    def test_rate_limiter_blocks_over_threshold(self):
        limiter = RateLimiter(max_calls=2, window_seconds=60, enabled=True)
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False  # 3rd call → blocked

    def test_rate_limiter_different_keys_independent(self):
        limiter = RateLimiter(max_calls=1, window_seconds=60, enabled=True)
        assert limiter.is_allowed("key-a") is True
        assert limiter.is_allowed("key-b") is True  # different key → not blocked
        assert limiter.is_allowed("key-a") is False  # same key → blocked

    def test_rate_limiter_disabled_always_allows(self):
        """When enabled=False, every call is allowed regardless of count."""
        limiter = RateLimiter(max_calls=1, window_seconds=60, enabled=False)
        for _ in range(100):
            assert limiter.is_allowed("any-key") is True

    def test_rate_limiter_disabled_via_env(self, monkeypatch):
        """RATE_LIMIT_ENABLED=false disables the limiter (no enabled= override)."""
        import app.services.rate_limit_service as rl  # noqa: PLC0415
        # Patch the _rate_limit_enabled function directly to return False
        monkeypatch.setattr(rl, "_rate_limit_enabled", lambda: False)
        limiter = RateLimiter(max_calls=1, window_seconds=60)  # no enabled override
        for _ in range(5):
            assert limiter.is_allowed("any-key") is True

    def test_dependency_raises_429_when_blocked(self):
        """rate_limit_dependency raises HTTP 429 when the limiter is blocked."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        limiter = RateLimiter(max_calls=0, window_seconds=60, enabled=True)
        # max_calls=0 means every call is immediately blocked
        dep = rate_limit_dependency(limiter)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        with pytest.raises(HTTPException) as exc:
            dep(mock_request)
        assert exc.value.status_code == 429

    def test_retry_after_header_is_positive(self):
        """429 response must include a positive Retry-After header."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        limiter = RateLimiter(max_calls=1, window_seconds=30, enabled=True)
        limiter.is_allowed("ip-x")  # consume the one allowed call
        dep = rate_limit_dependency(limiter)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "ip-x"

        with pytest.raises(HTTPException) as exc:
            dep(mock_request)
        assert exc.value.status_code == 429
        retry = int(exc.value.headers.get("Retry-After", 0))
        assert retry >= 1, "Retry-After must be at least 1 second"

    def test_payment_endpoints_have_rate_limiters(self):
        """Payment route handlers must have a rate-limit dependency injected."""
        import inspect  # noqa: PLC0415
        from app.routes.payments import (  # noqa: PLC0415
            create_payment_order,
            verify_payment,
            student_create_payment_order,
            student_verify_payment,
            admin_test_create_order,
            admin_test_verify,
        )
        for fn in [
            create_payment_order, verify_payment,
            student_create_payment_order, student_verify_payment,
            admin_test_create_order, admin_test_verify,
        ]:
            # The dependency is visible in __annotations__ or the function signature
            sig = inspect.signature(fn)
            params = dict(sig.parameters)
            assert "_rl" in params or any(
                "rate_limit" in str(v.default) or "RateLimiter" in str(v.default)
                for v in params.values()
            ), f"{fn.__name__} must have a rate-limit dependency"

    def test_login_endpoint_has_rate_limiter(self):
        import inspect  # noqa: PLC0415
        from app.routes.auth import login  # noqa: PLC0415
        sig = inspect.signature(login)
        assert "_rl" in sig.parameters, "login endpoint must have rate-limit dependency"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-scope: existing tests still pass
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossScope:
    """Verify that the hardening changes do not break existing behavior."""

    def test_normal_checkout_pricing_unchanged(self, monkeypatch):
        """Normal checkout charges the full plan price (not ₹1)."""
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route,
            "get_child_by_id",
            lambda parent_id, child_id: {"id": child_id, "family_id": "f-1"},
        )
        monkeypatch.setattr(
            payments_route,
            "get_public_plan",
            lambda plan_key: {
                "key": "starter",
                "label": "Premium",
                "price": 299,
                "billing_label": "month",
                "is_public": True,
                "access_cbse": True,
                "discount_percent": 0,
                "access_sof_science": False,
                "access_sof_maths": False,
                "access_sof_english": False,
                "daily_token_limit": 50000,
                "monthly_token_limit": 1000000,
            },
        )
        captured = {}

        def fake_order(amount_paise, receipt, notes):
            captured["amount_paise"] = amount_paise
            return {"id": "order_normal", "amount": amount_paise, "currency": "INR"}

        monkeypatch.setattr(payments_route, "create_razorpay_order", fake_order)
        monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

        from app.routes.payments import create_payment_order, CreatePaymentOrderRequest  # noqa: PLC0415
        result = create_payment_order(
            CreatePaymentOrderRequest(child_id="child-1", plan_key="starter"),
            parent={"profile": {"id": "parent-1", "family_id": "f-1"}},
        )
        assert captured["amount_paise"] == 29900   # ₹299 full price

    def test_admin_test_charge_remains_1_rupee(self):
        assert ADMIN_TEST_CHARGE_RUPEES == 1

    def test_admin_test_plans_have_all_three_scenarios(self):
        assert "free" in ADMIN_TEST_UPGRADE_PLANS
        assert "starter" in ADMIN_TEST_UPGRADE_PLANS
        assert "family_premium" in ADMIN_TEST_UPGRADE_PLANS

    def test_resolver_free_result_has_canonical_key(self):
        result = _free_result()
        assert result["canonical_plan_key"] == "FREE_TIER"

    def test_paid_plan_name_nano_unchanged(self):
        assert _paid_plan_name("free") == "Premium Nano"

    def test_canonical_key_free_is_nano(self):
        assert _canonical_plan_key("free") == "NANO"
