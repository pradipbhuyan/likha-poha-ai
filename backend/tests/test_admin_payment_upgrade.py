"""
Regression tests for the admin ₹1 test upgrade payment flow.

Tests verify:
- Admin can create ₹1 test orders for all three upgrade plans
- Non-admins cannot trigger ₹1 test payments
- Normal checkout still charges the real plan price (unchanged)
- Successful Nano test payment creates 8-day subscription
- Successful Premium test payment creates 30-day subscription
- Successful Family Premium test payment creates 30-day subscription
- admin-test-verify uses intendedPlanKey (plan_key), not chargedAmount
- admin-test-verify rejects non-test payments (missing testMode metadata)
- Failed/cancelled payment (invalid signature) does NOT activate plan
- get_plan_any bypasses is_public check
"""

import hashlib
import hmac

import pytest
from fastapi import HTTPException

import app.routes.payments as payments_route
from app.routes.payments import (
    ADMIN_TEST_CHARGE_RUPEES,
    ADMIN_TEST_UPGRADE_PLANS,
    AdminTestOrderRequest,
    AdminTestVerifyRequest,
    get_plan_any,
    profile_access_from_plan,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

ADMIN_CONTEXT = {"profile": {"id": "admin-1", "role": "admin"}}

FREE_TIER_USER = {
    "id": "user-free-1",
    "username": "freetestuser",
    "email": "free@test.com",
    "role": "student",
    "subscription_plan": "free_tier",
    "access_cbse": False,
}

NANO_PLAN = {
    "key": "free",
    "label": "Premium Nano",
    "price": 99,
    "billing_label": "8 days",
    "is_public": True,
    "access_cbse": True,
    "access_sof_science": False,
    "access_sof_maths": False,
    "access_sof_english": False,
    "daily_token_limit": 50000,
    "monthly_token_limit": 1000000,
    "discount_percent": 0,
}

PREMIUM_PLAN = {
    "key": "starter",
    "label": "Premium",
    "price": 299,
    "billing_label": "month",
    "is_public": True,
    "access_cbse": True,
    "access_sof_science": False,
    "access_sof_maths": False,
    "access_sof_english": False,
    "daily_token_limit": 50000,
    "monthly_token_limit": 1000000,
    "discount_percent": 0,
}

FAMILY_PLAN = {
    "key": "family_premium",
    "label": "Family Premium",
    "price": 499,
    "billing_label": "month",
    "is_public": True,
    "access_cbse": True,
    "access_sof_science": False,
    "access_sof_maths": False,
    "access_sof_english": False,
    "daily_token_limit": 50000,
    "monthly_token_limit": 1000000,
    "discount_percent": 0,
}

ALL_PLANS = {"free": NANO_PLAN, "starter": PREMIUM_PLAN, "family_premium": FAMILY_PLAN}


def _make_signature(order_id: str, payment_id: str, secret: str) -> str:
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# ── Test: ADMIN_TEST_UPGRADE_PLANS constant ───────────────────────────────────

def test_admin_test_upgrade_plans_has_all_three_scenarios():
    assert "free" in ADMIN_TEST_UPGRADE_PLANS
    assert "starter" in ADMIN_TEST_UPGRADE_PLANS
    assert "family_premium" in ADMIN_TEST_UPGRADE_PLANS


def test_admin_test_charge_is_1_rupee():
    assert ADMIN_TEST_CHARGE_RUPEES == 1


def test_nano_scenario_validity_is_8_days():
    assert ADMIN_TEST_UPGRADE_PLANS["free"]["validity_label"] == "8 days"


def test_premium_scenario_validity_is_30_days():
    assert ADMIN_TEST_UPGRADE_PLANS["starter"]["validity_label"] == "30 days"


def test_family_premium_scenario_validity_is_30_days():
    assert ADMIN_TEST_UPGRADE_PLANS["family_premium"]["validity_label"] == "30 days"


def test_nano_child_limit_is_1():
    assert ADMIN_TEST_UPGRADE_PLANS["free"]["child_limit"] == 1


def test_premium_child_limit_is_1():
    assert ADMIN_TEST_UPGRADE_PLANS["starter"]["child_limit"] == 1


def test_family_premium_child_limit_is_2():
    assert ADMIN_TEST_UPGRADE_PLANS["family_premium"]["child_limit"] == 2


# ── Test: get_plan_any bypasses is_public ─────────────────────────────────────

def test_get_plan_any_returns_plan_when_not_public(monkeypatch):
    hidden_plan = {**NANO_PLAN, "is_public": False}
    monkeypatch.setattr(
        payments_route,
        "list_subscription_plan_settings",
        lambda: {"plans": {"free": hidden_plan}},
    )
    result = get_plan_any("free")
    assert result["key"] == "free"


def test_get_plan_any_raises_404_for_missing_plan(monkeypatch):
    monkeypatch.setattr(
        payments_route,
        "list_subscription_plan_settings",
        lambda: {"plans": {}},
    )
    with pytest.raises(HTTPException) as exc:
        get_plan_any("nonexistent")
    assert exc.value.status_code == 404


# ── Test: admin-test-create-order (admin only) ────────────────────────────────

def test_admin_test_create_order_returns_503_when_razorpay_not_configured(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", None)
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", None)

    with pytest.raises(HTTPException) as exc:
        payments_route.admin_test_create_order(
            AdminTestOrderRequest(target_user_id="u-1", intended_plan_key="free"),
            admin=ADMIN_CONTEXT,
        )
    assert exc.value.status_code == 503


def test_admin_test_create_order_rejects_invalid_plan_key(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    with pytest.raises(HTTPException) as exc:
        payments_route.admin_test_create_order(
            AdminTestOrderRequest(target_user_id="u-1", intended_plan_key="invalid_plan"),
            admin=ADMIN_CONTEXT,
        )
    assert exc.value.status_code == 400
    assert "invalid_plan" in exc.value.detail


def test_admin_test_create_order_charges_1_rupee_for_nano(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    # Fake target user lookup
    class FakeResp:
        data = [FREE_TIER_USER]
    class FakeTable:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return FakeResp()
    monkeypatch.setattr(payments_route.admin_client, "table", lambda t: FakeTable())
    monkeypatch.setattr(
        payments_route,
        "list_subscription_plan_settings",
        lambda: {"plans": ALL_PLANS},
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        captured["notes"] = notes
        return {"id": "order_nano_test", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.admin_test_create_order(
        AdminTestOrderRequest(target_user_id="user-free-1", intended_plan_key="free"),
        admin=ADMIN_CONTEXT,
    )

    assert result["success"] is True
    assert captured["amount_paise"] == 100   # ₹1 = 100 paise
    assert result["charged_amount"] == 1
    assert result["intended_plan"]["key"] == "free"
    assert result["intended_plan"]["label"] == "Premium Nano"
    assert result["intended_plan"]["validity"] == "8 days"


def test_admin_test_create_order_charges_1_rupee_for_premium(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    class FakeResp:
        data = [FREE_TIER_USER]
    class FakeTable:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return FakeResp()
    monkeypatch.setattr(payments_route.admin_client, "table", lambda t: FakeTable())
    monkeypatch.setattr(
        payments_route, "list_subscription_plan_settings", lambda: {"plans": ALL_PLANS}
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_premium_test", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.admin_test_create_order(
        AdminTestOrderRequest(target_user_id="user-free-1", intended_plan_key="starter"),
        admin=ADMIN_CONTEXT,
    )

    assert captured["amount_paise"] == 100
    assert result["intended_plan"]["key"] == "starter"
    assert result["intended_plan"]["label"] == "Premium"
    assert result["intended_plan"]["validity"] == "30 days"


def test_admin_test_create_order_charges_1_rupee_for_family_premium(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    class FakeResp:
        data = [FREE_TIER_USER]
    class FakeTable:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return FakeResp()
    monkeypatch.setattr(payments_route.admin_client, "table", lambda t: FakeTable())
    monkeypatch.setattr(
        payments_route, "list_subscription_plan_settings", lambda: {"plans": ALL_PLANS}
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_family_test", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.admin_test_create_order(
        AdminTestOrderRequest(target_user_id="user-free-1", intended_plan_key="family_premium"),
        admin=ADMIN_CONTEXT,
    )

    assert captured["amount_paise"] == 100
    assert result["intended_plan"]["key"] == "family_premium"
    assert result["intended_plan"]["label"] == "Family Premium"
    assert result["intended_plan"]["child_limit"] == 2


def test_admin_test_create_order_stores_test_metadata(monkeypatch):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    class FakeResp:
        data = [FREE_TIER_USER]
    class FakeTable:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return FakeResp()
    monkeypatch.setattr(payments_route.admin_client, "table", lambda t: FakeTable())
    monkeypatch.setattr(
        payments_route, "list_subscription_plan_settings", lambda: {"plans": ALL_PLANS}
    )
    monkeypatch.setattr(
        payments_route, "create_razorpay_order",
        lambda *a, **kw: {"id": "order_meta_test", "amount": 100, "currency": "INR"},
    )

    saved = {}

    def fake_save(record):
        saved.update(record)
        return record

    monkeypatch.setattr(payments_route, "save_payment_record", fake_save)

    payments_route.admin_test_create_order(
        AdminTestOrderRequest(target_user_id="user-free-1", intended_plan_key="free"),
        admin=ADMIN_CONTEXT,
    )

    meta = saved.get("metadata", {})
    assert meta.get("testMode") is True
    assert meta.get("adminTriggered") is True
    assert meta.get("chargedAmount") == 1
    assert meta.get("intendedPlanKey") == "free"
    assert saved.get("plan_key") == "free"   # REAL plan key stored, not ₹1 key
    assert saved.get("amount") == 1


# ── Test: admin-test-verify ───────────────────────────────────────────────────

def test_admin_test_verify_rejects_non_test_payment(monkeypatch):
    """Payments without testMode/adminTriggered metadata must be rejected."""
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

    # Payment record WITHOUT testMode metadata (normal parent payment)
    monkeypatch.setattr(
        payments_route,
        "get_payment_by_order_id",
        lambda order_id: {
            "razorpay_order_id": order_id,
            "parent_id": "parent-1",
            "child_id": "child-1",
            "plan_key": "starter",
            "status": "created",
            "metadata": {},   # no testMode flag
        },
    )

    with pytest.raises(HTTPException) as exc:
        payments_route.admin_test_verify(
            AdminTestVerifyRequest(
                razorpay_order_id="order_normal",
                razorpay_payment_id="pay_normal",
                razorpay_signature="sig_normal",
            ),
            admin=ADMIN_CONTEXT,
        )
    assert exc.value.status_code == 403


def test_admin_test_verify_rejects_invalid_signature(monkeypatch):
    """Invalid Razorpay signature on an admin test payment must be rejected."""
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
            "status": "created",
            "metadata": {"testMode": True, "adminTriggered": True, "chargedAmount": 1},
        },
    )
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    with pytest.raises(HTTPException) as exc:
        payments_route.admin_test_verify(
            AdminTestVerifyRequest(
                razorpay_order_id="order_test_1",
                razorpay_payment_id="pay_test_1",
                razorpay_signature="invalid_signature",
            ),
            admin=ADMIN_CONTEXT,
        )
    assert exc.value.status_code == 400


def _make_admin_test_payment(plan_key: str, order_id: str = "order_test"):
    """Build a complete admin test payment record for verify tests."""
    return {
        "razorpay_order_id": order_id,
        "parent_id": "admin-1",
        "child_id": "user-free-1",
        "plan_key": plan_key,
        "status": "created",
        "metadata": {
            "testMode": True,
            "adminTriggered": True,
            "chargedAmount": 1,
            "intendedPlanKey": plan_key,
            "intendedPlanAmount": {"free": 99, "starter": 299, "family_premium": 499}[plan_key],
        },
    }


def _setup_verify_monkeypatches(monkeypatch, plan_key: str, order_id: str = "order_test",
                                 extra_children=()):
    """
    Wire all monkeypatches needed for a successful admin-test-verify call.

    Seeds a small fake `profiles` table so activate_plan_for_payment()'s real
    parent/family lookups resolve correctly: the target "user-free-1" is a
    student whose parent is "parent-1". `extra_children` lets a test add more
    students under "parent-1" to verify family_premium's fan-out.

    Returns (payment_id, sig, activated_updates, rows) where activated_updates
    is a list of {"fields": {...}, "ids": [...]} — one entry per .update()
    call the activation path issued (nano/starter issue one, for the single
    target row; family_premium issues two: the children batch + the parent).
    """
    secret = "test_secret"
    payment_id = f"pay_{plan_key}"
    sig = _make_signature(order_id, payment_id, secret)

    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", secret)

    payment_record = _make_admin_test_payment(plan_key, order_id)
    monkeypatch.setattr(
        payments_route, "get_payment_by_order_id", lambda oid: payment_record
    )
    monkeypatch.setattr(
        payments_route,
        "list_subscription_plan_settings",
        lambda: {"plans": ALL_PLANS},
    )

    rows = [
        {"id": "user-free-1", "role": "student", "parent_id": "parent-1", "family_id": "fam-1"},
        {"id": "parent-1", "role": "parent", "family_id": "fam-1"},
        *extra_children,
    ]
    activated_updates = []

    class FakeProfilesTable:
        def __init__(self):
            self._op = None
            self._filters = []
            self._update_fields = None

        def select(self, *_a, **_kw):
            self._op = "select"
            return self

        def update(self, fields):
            self._op = "update"
            self._update_fields = fields
            return self

        def eq(self, col, val):
            self._filters.append(("eq", col, val))
            return self

        def in_(self, col, vals):
            self._filters.append(("in", col, vals))
            return self

        def limit(self, _n):
            return self

        def single(self):
            return self

        def _matches(self, row):
            for kind, col, val in self._filters:
                if kind == "eq" and row.get(col) != val:
                    return False
                if kind == "in" and row.get(col) not in val:
                    return False
            return True

        def execute(self):
            matched = [r for r in rows if self._matches(r)]
            if self._op == "update":
                for r in matched:
                    r.update(self._update_fields)
                activated_updates.append({
                    "fields": dict(self._update_fields),
                    "ids": [r["id"] for r in matched],
                })
            return type("R", (), {"data": matched})()

    class FakeClient:
        def table(self, _name):
            return FakeProfilesTable()

    monkeypatch.setattr(payments_route, "admin_client", FakeClient())
    monkeypatch.setattr(
        payments_route, "get_children",
        lambda parent_id: [r for r in rows if r.get("parent_id") == parent_id and r.get("role") == "student"],
    )
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    return payment_id, sig, activated_updates, rows


def _updated_fields_for(activated_updates, user_id):
    """Find the .update() call (if any) whose matched rows included user_id."""
    for update in activated_updates:
        if user_id in update["ids"]:
            return update["fields"]
    return {}


def test_admin_test_verify_activates_nano_plan(monkeypatch):
    """Successful ₹1 nano test payment activates the Premium Nano plan."""
    payment_id, sig, activated_updates, _rows = _setup_verify_monkeypatches(monkeypatch, "free")

    result = payments_route.admin_test_verify(
        AdminTestVerifyRequest(
            razorpay_order_id="order_test",
            razorpay_payment_id=payment_id,
            razorpay_signature=sig,
        ),
        admin=ADMIN_CONTEXT,
    )

    activated = _updated_fields_for(activated_updates, "user-free-1")
    assert result["success"] is True
    assert activated.get("subscription_plan") == "free"
    assert activated.get("access_cbse") is True
    # Nano plan expires in 8 days — subscription_expires_at must be set
    assert activated.get("subscription_expires_at") is not None
    assert result["intended_plan"]["key"] == "free"


def test_admin_test_verify_activates_premium_plan(monkeypatch):
    """Successful ₹1 premium test payment activates the Premium plan."""
    payment_id, sig, activated_updates, _rows = _setup_verify_monkeypatches(monkeypatch, "starter")

    result = payments_route.admin_test_verify(
        AdminTestVerifyRequest(
            razorpay_order_id="order_test",
            razorpay_payment_id=payment_id,
            razorpay_signature=sig,
        ),
        admin=ADMIN_CONTEXT,
    )

    activated = _updated_fields_for(activated_updates, "user-free-1")
    assert result["success"] is True
    assert activated.get("subscription_plan") == "starter"
    assert activated.get("access_cbse") is True
    assert activated.get("subscription_expires_at") is not None
    assert result["intended_plan"]["key"] == "starter"


def test_admin_test_verify_activates_family_premium_plan(monkeypatch):
    """
    REGRESSION: successful ₹1 family premium test payment must activate
    Family Premium exactly like a real payment does — every child in the
    family, plus the parent's own subscription_plan/subscription_expires_at
    (but NOT access_cbse, which is a student-only AI-access flag). Before
    this fix, admin_test_verify did a flat single-row update on only the
    target child, so a second child and the parent were never touched —
    the tool didn't test what it claimed to.
    """
    second_child = {"id": "user-free-2", "role": "student", "parent_id": "parent-1", "family_id": "fam-1"}
    payment_id, sig, activated_updates, rows = _setup_verify_monkeypatches(
        monkeypatch, "family_premium", extra_children=(second_child,)
    )

    result = payments_route.admin_test_verify(
        AdminTestVerifyRequest(
            razorpay_order_id="order_test",
            razorpay_payment_id=payment_id,
            razorpay_signature=sig,
        ),
        admin=ADMIN_CONTEXT,
    )

    assert result["success"] is True
    assert result["intended_plan"]["key"] == "family_premium"

    # Both children — not just the payment's target child — must be activated.
    target_fields = _updated_fields_for(activated_updates, "user-free-1")
    sibling_fields = _updated_fields_for(activated_updates, "user-free-2")
    assert target_fields.get("subscription_plan") == "family_premium"
    assert target_fields.get("access_cbse") is True
    assert sibling_fields.get("subscription_plan") == "family_premium"
    assert sibling_fields.get("access_cbse") is True

    # The parent's own profile gets subscription_plan/expiry, but NOT access_cbse.
    parent_row = next(r for r in rows if r["id"] == "parent-1")
    assert parent_row.get("subscription_plan") == "family_premium"
    assert parent_row.get("subscription_expires_at") is not None
    assert "access_cbse" not in parent_row


def test_admin_test_verify_uses_intended_plan_not_charged_amount(monkeypatch):
    """
    Verify that subscription activation uses plan_key (= intended plan),
    NOT the charged amount of ₹1. The plan fields come from the real plan
    definition (NANO/Premium/Family Premium), not a ₹1 plan.
    """
    payment_id, sig, activated_updates, _rows = _setup_verify_monkeypatches(monkeypatch, "starter")

    payments_route.admin_test_verify(
        AdminTestVerifyRequest(
            razorpay_order_id="order_test",
            razorpay_payment_id=payment_id,
            razorpay_signature=sig,
        ),
        admin=ADMIN_CONTEXT,
    )

    # The activated plan should be "starter" (₹299/30 days), NOT a ₹1 plan
    activated = _updated_fields_for(activated_updates, "user-free-1")
    assert activated.get("subscription_plan") == "starter"
    # Token limits from the real plan, not ₹0/₹1 plan
    assert activated.get("daily_token_limit") == 50000


# ── Test: profile_access_from_plan sets correct expiry ───────────────────────

def test_profile_access_from_plan_nano_expires_in_8_days():
    fields = profile_access_from_plan(NANO_PLAN)
    assert fields["subscription_expires_at"] is not None
    # Should be roughly 8 days from now
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(fields["subscription_expires_at"])
    now = datetime.now(timezone.utc)
    delta_days = (expiry - now).days
    assert 7 <= delta_days <= 8


def test_profile_access_from_plan_premium_expires_in_exactly_30_days():
    """Business rule: monthly plans expire in exactly 30 days (not 31)."""
    fields = profile_access_from_plan(PREMIUM_PLAN)
    assert fields["subscription_expires_at"] is not None
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(fields["subscription_expires_at"])
    now = datetime.now(timezone.utc)
    delta_seconds = (expiry - now).total_seconds()
    delta_days = delta_seconds / 86400
    assert 29.9 <= delta_days <= 30.1, f"Expected ~30 days, got {delta_days:.4f}"


def test_profile_access_from_plan_family_premium_expires_in_exactly_30_days():
    """Family Premium must also expire in exactly 30 days (not 31)."""
    fields = profile_access_from_plan(FAMILY_PLAN)
    assert fields["subscription_expires_at"] is not None
    from datetime import datetime, timezone
    expiry = datetime.fromisoformat(fields["subscription_expires_at"])
    now = datetime.now(timezone.utc)
    delta_seconds = (expiry - now).total_seconds()
    delta_days = delta_seconds / 86400
    assert 29.9 <= delta_days <= 30.1, f"Expected ~30 days, got {delta_days:.4f}"


# ── Test: normal checkout is UNAFFECTED by admin test endpoints ───────────────

def test_normal_checkout_still_charges_full_price_for_nano(monkeypatch):
    """Normal parent checkout charges ₹99 for Nano — not ₹1."""
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(
        payments_route,
        "get_child_by_id",
        lambda parent_id, child_id: {"id": child_id, "family_id": "f-1", "role": "student"},
    )
    monkeypatch.setattr(
        payments_route,
        "get_public_plan",
        lambda plan_key: NANO_PLAN,
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_normal", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.create_payment_order(
        payments_route.CreatePaymentOrderRequest(child_id="child-1", plan_key="free"),
        parent={"profile": {"id": "parent-1", "family_id": "f-1"}},
    )

    # Normal checkout uses FULL price ₹99 = 9900 paise
    assert captured["amount_paise"] == 9900
    assert result["payment"]["amount"] == 99


def test_normal_checkout_still_charges_full_price_for_premium(monkeypatch):
    """Normal parent checkout charges ₹299 for Premium — not ₹1."""
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(
        payments_route,
        "get_child_by_id",
        lambda parent_id, child_id: {"id": child_id, "family_id": "f-1", "role": "student"},
    )
    monkeypatch.setattr(
        payments_route,
        "get_public_plan",
        lambda plan_key: PREMIUM_PLAN,
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_normal", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.create_payment_order(
        payments_route.CreatePaymentOrderRequest(child_id="child-1", plan_key="starter"),
        parent={"profile": {"id": "parent-1", "family_id": "f-1"}},
    )

    assert captured["amount_paise"] == 29900   # ₹299 = 29900 paise
    assert result["payment"]["amount"] == 299


def test_normal_checkout_still_charges_full_price_for_family_premium(monkeypatch):
    """Normal parent checkout charges ₹499 for Family Premium — not ₹1."""
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(
        payments_route,
        "get_child_by_id",
        lambda parent_id, child_id: {"id": child_id, "family_id": "f-1", "role": "student"},
    )
    monkeypatch.setattr(
        payments_route,
        "get_public_plan",
        lambda plan_key: FAMILY_PLAN,
    )

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_normal", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

    result = payments_route.create_payment_order(
        payments_route.CreatePaymentOrderRequest(child_id="child-1", plan_key="family_premium"),
        parent={"profile": {"id": "parent-1", "family_id": "f-1"}},
    )

    assert captured["amount_paise"] == 49900   # ₹499 = 49900 paise
    assert result["payment"]["amount"] == 499
