"""
test_exam_prep_upgrade_journey.py
==================================
Coverage for the Grade 11/12 upgrade-path features:

1. Free-tier Grade 11/12 student picking Premium is nudged toward Exam Prep
   Center (frontend-only advisory — see exam_prep_upgrade_discount_rupees()
   for the underlying eligibility rule reused by the discount feature).
2. An existing Premium/Family Premium Grade 11/12 subscriber upgrading to
   Exam Prep Center gets a ₹200 loyalty discount.
3. The free -> premium -> exam_prep_center access journey (CBSE lessons vs.
   Exam Prep Content availability at each stage).
4. The admin ₹1 test-harness correctly previews the discount for Exam Prep
   Center without changing the actual ₹1 charge.

Follows house style from test_payments.py / test_admin_payment_upgrade.py /
test_exam_prep_access_rules.py: no HTTP client, monkeypatch on the route
module for helper functions, small FakeTable/FakeResp classes for direct
admin_client.table(...) calls.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

import app.routes.payments as payments_route
from app.routes.payments import (
    AdminTestOrderRequest,
    CreatePaymentOrderRequest,
    StudentCreateOrderRequest,
)
from app.services.exam_prep_service import (
    EXAM_PREP_UPGRADE_DISCOUNT_RUPEES,
    exam_prep_upgrade_discount_rupees,
)

ADMIN_CONTEXT = {"profile": {"id": "admin-1", "role": "admin"}}

EXAM_PREP_CENTER_PLAN = {
    "key": "exam_prep_center",
    "label": "Exam Prep Center",
    "price": 1999,
    "billing_label": "year",
    "is_public": True,
    "access_cbse": True,
    "daily_token_limit": 100000,
    "monthly_token_limit": 3000000,
    "discount_percent": 0,
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. exam_prep_upgrade_discount_rupees() unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExamPrepUpgradeDiscountRupees:
    def test_premium_grade11_gets_discount(self):
        assert exam_prep_upgrade_discount_rupees("starter", "Grade 11") == EXAM_PREP_UPGRADE_DISCOUNT_RUPEES

    def test_family_premium_grade12_gets_discount(self):
        assert exam_prep_upgrade_discount_rupees("family_premium", "Grade 12") == EXAM_PREP_UPGRADE_DISCOUNT_RUPEES

    def test_premium_grade9_no_discount(self):
        """Grade gate: discount is Grade 11/12 only."""
        assert exam_prep_upgrade_discount_rupees("starter", "Grade 9") == 0

    def test_free_tier_grade11_no_discount(self):
        """Plan gate: must currently be on Premium/Family Premium, not free tier."""
        assert exam_prep_upgrade_discount_rupees("free_tier", "Grade 11") == 0

    def test_none_plan_no_discount(self):
        assert exam_prep_upgrade_discount_rupees(None, "Grade 11") == 0

    def test_none_grade_no_discount(self):
        assert exam_prep_upgrade_discount_rupees("starter", None) == 0

    def test_standard_annual_not_eligible(self):
        """
        Literal scope per product decision: only "starter"/"family_premium"
        qualify, not the 6-month/annual billing-cadence variants.
        """
        assert exam_prep_upgrade_discount_rupees("standard_annual", "Grade 11") == 0
        assert exam_prep_upgrade_discount_rupees("standard_6month", "Grade 12") == 0
        assert exam_prep_upgrade_discount_rupees("family_annual", "Grade 11") == 0

    def test_exam_prep_center_current_plan_no_discount(self):
        """A student already on Exam Prep Center isn't "upgrading" to it."""
        assert exam_prep_upgrade_discount_rupees("exam_prep_center", "Grade 11") == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2a. student_create_payment_order — standalone student self-checkout
# ─────────────────────────────────────────────────────────────────────────────

class _FakeSingleTable:
    """Mirrors admin_client.table("profiles").select(...).eq(...).single().execute()."""

    def __init__(self, row):
        self._row = row

    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def single(self):
        return self

    def execute(self):
        class _Resp:
            def __init__(self, data):
                self.data = data
        return _Resp(self._row)


def _patch_student_order_deps(monkeypatch, profile_row, plan=EXAM_PREP_CENTER_PLAN):
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setattr(payments_route.admin_client, "table", lambda t: _FakeSingleTable(profile_row))
    monkeypatch.setattr(payments_route, "get_public_plan", lambda plan_key: plan)
    monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)

    captured = {}

    def fake_create_razorpay_order(amount_paise, receipt, notes):
        captured["amount_paise"] = amount_paise
        return {"id": "order_exam_prep", "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)
    return captured


class TestStudentCreatePaymentOrderDiscount:
    def test_premium_grade11_student_gets_discounted_charge(self, monkeypatch):
        profile = {
            "id": "stu-1", "role": "student", "parent_id": None,
            "email": "s@test.com", "username": "s1",
            "subscription_plan": "starter", "grade": "Grade 11",
        }
        captured = _patch_student_order_deps(monkeypatch, profile)

        result = payments_route.student_create_payment_order(
            StudentCreateOrderRequest(plan_key="exam_prep_center"),
            user=type("U", (), {"id": "stu-1"})(),
        )

        assert captured["amount_paise"] == 179900   # (1999 - 200) * 100
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 200

    def test_free_tier_student_full_price(self, monkeypatch):
        profile = {
            "id": "stu-2", "role": "student", "parent_id": None,
            "email": "s2@test.com", "username": "s2",
            "subscription_plan": "free_tier", "grade": "Grade 11",
        }
        captured = _patch_student_order_deps(monkeypatch, profile)

        result = payments_route.student_create_payment_order(
            StudentCreateOrderRequest(plan_key="exam_prep_center"),
            user=type("U", (), {"id": "stu-2"})(),
        )

        assert captured["amount_paise"] == 199900
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 0

    def test_premium_grade9_student_full_price(self, monkeypatch):
        """Grade gate blocks the discount even though the plan matches."""
        profile = {
            "id": "stu-3", "role": "student", "parent_id": None,
            "email": "s3@test.com", "username": "s3",
            "subscription_plan": "starter", "grade": "Grade 9",
        }
        captured = _patch_student_order_deps(monkeypatch, profile)

        result = payments_route.student_create_payment_order(
            StudentCreateOrderRequest(plan_key="exam_prep_center"),
            user=type("U", (), {"id": "stu-3"})(),
        )

        assert captured["amount_paise"] == 199900
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 0

    def test_discount_not_applied_to_starter_plan_itself(self, monkeypatch):
        """The discount only ever applies to an exam_prep_center purchase."""
        profile = {
            "id": "stu-4", "role": "student", "parent_id": None,
            "email": "s4@test.com", "username": "s4",
            "subscription_plan": "free_tier", "grade": "Grade 11",
        }
        starter_plan = {
            "key": "starter", "label": "Premium", "price": 299,
            "billing_label": "month", "is_public": True, "access_cbse": True,
            "daily_token_limit": 50000, "monthly_token_limit": 1000000,
            "discount_percent": 0,
        }
        captured = _patch_student_order_deps(monkeypatch, profile, plan=starter_plan)

        result = payments_route.student_create_payment_order(
            StudentCreateOrderRequest(plan_key="starter"),
            user=type("U", (), {"id": "stu-4"})(),
        )

        assert captured["amount_paise"] == 29900
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2b. create_payment_order — parent-driven checkout for a child
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatePaymentOrderDiscount:
    def test_premium_grade12_child_gets_discounted_charge(self, monkeypatch):
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route, "get_child_by_id",
            lambda parent_id, child_id: {
                "id": child_id, "family_id": "family-1", "role": "student",
                "subscription_plan": "family_premium", "grade": "Grade 12",
            },
        )
        monkeypatch.setattr(payments_route, "get_public_plan", lambda plan_key: EXAM_PREP_CENTER_PLAN)
        monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)

        captured = {}

        def fake_create_razorpay_order(amount_paise, receipt, notes):
            captured["amount_paise"] = amount_paise
            return {"id": "order_1", "amount": amount_paise, "currency": "INR"}

        monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)

        result = payments_route.create_payment_order(
            CreatePaymentOrderRequest(child_id="child-1", plan_key="exam_prep_center"),
            parent={"profile": {"id": "parent-1", "family_id": "family-1"}},
        )

        assert captured["amount_paise"] == 179900
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 200

    def test_free_tier_child_full_price(self, monkeypatch):
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")
        monkeypatch.setattr(
            payments_route, "get_child_by_id",
            lambda parent_id, child_id: {
                "id": child_id, "family_id": "family-1", "role": "student",
                "subscription_plan": "free_tier", "grade": "Grade 12",
            },
        )
        monkeypatch.setattr(payments_route, "get_public_plan", lambda plan_key: EXAM_PREP_CENTER_PLAN)
        monkeypatch.setattr(payments_route, "save_payment_record", lambda record: record)

        captured = {}

        def fake_create_razorpay_order(amount_paise, receipt, notes):
            captured["amount_paise"] = amount_paise
            return {"id": "order_2", "amount": amount_paise, "currency": "INR"}

        monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)

        result = payments_route.create_payment_order(
            CreatePaymentOrderRequest(child_id="child-2", plan_key="exam_prep_center"),
            parent={"profile": {"id": "parent-2", "family_id": "family-2"}},
        )

        assert captured["amount_paise"] == 199900
        assert result["payment"]["metadata"]["discount_applied_rupees"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Admin ₹1 test-harness discount preview
# ─────────────────────────────────────────────────────────────────────────────

class _FakeLimitTable:
    """Mirrors admin_client.table("profiles").select(...).eq(...).limit(1).execute()."""

    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        class _Resp:
            def __init__(self, data):
                self.data = data
        return _Resp(self._rows)


class TestAdminTestCreateOrderExamPrepDiscount:
    def test_charges_1_rupee_but_previews_discounted_amount(self, monkeypatch):
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

        target = {
            "id": "user-premium-1", "username": "premiumstudent", "email": "p@test.com",
            "role": "student", "subscription_plan": "starter", "access_cbse": True,
            "grade": "Grade 11",
        }
        monkeypatch.setattr(payments_route.admin_client, "table", lambda t: _FakeLimitTable([target]))
        monkeypatch.setattr(
            payments_route, "list_subscription_plan_settings",
            lambda: {"plans": {"exam_prep_center": EXAM_PREP_CENTER_PLAN}},
        )
        monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)

        captured = {}

        def fake_create_razorpay_order(amount_paise, receipt, notes):
            captured["amount_paise"] = amount_paise
            return {"id": "order_admtest", "amount": amount_paise, "currency": "INR"}

        monkeypatch.setattr(payments_route, "create_razorpay_order", fake_create_razorpay_order)

        result = payments_route.admin_test_create_order(
            AdminTestOrderRequest(target_user_id="user-premium-1", intended_plan_key="exam_prep_center"),
            admin=ADMIN_CONTEXT,
        )

        # Real charge is still ₹1 — the discount never changes the test amount.
        assert captured["amount_paise"] == 100
        assert result["charged_amount"] == 1
        # Preview reflects the loyalty discount.
        assert result["intended_plan"]["actual_price"] == 1799
        assert result["intended_plan"]["discount_applied_rupees"] == 200

    def test_free_tier_target_previews_full_price(self, monkeypatch):
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_ID", "rzp_test")
        monkeypatch.setattr(payments_route.settings, "RAZORPAY_KEY_SECRET", "secret")

        target = {
            "id": "user-free-2", "username": "freestudent", "email": "f@test.com",
            "role": "student", "subscription_plan": "free_tier", "access_cbse": False,
            "grade": "Grade 11",
        }
        monkeypatch.setattr(payments_route.admin_client, "table", lambda t: _FakeLimitTable([target]))
        monkeypatch.setattr(
            payments_route, "list_subscription_plan_settings",
            lambda: {"plans": {"exam_prep_center": EXAM_PREP_CENTER_PLAN}},
        )
        monkeypatch.setattr(payments_route, "save_payment_record", lambda r: r)
        monkeypatch.setattr(
            payments_route, "create_razorpay_order",
            lambda amount_paise, receipt, notes: {"id": "order_x", "amount": amount_paise, "currency": "INR"},
        )

        result = payments_route.admin_test_create_order(
            AdminTestOrderRequest(target_user_id="user-free-2", intended_plan_key="exam_prep_center"),
            admin=ADMIN_CONTEXT,
        )

        assert result["intended_plan"]["actual_price"] == 1999
        assert result["intended_plan"]["discount_applied_rupees"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Access journey: free_tier -> premium -> exam_prep_center
# ─────────────────────────────────────────────────────────────────────────────

class TestGrade11UpgradeJourneyAccess:
    """
    Simulates one Grade 11 student's progression through three plan states,
    asserting CBSE (LESSONS) vs. Exam Prep Content availability at each
    stage. Matches the mocking style of test_exam_prep_access_rules.py —
    resolve_user_subscription is patched directly rather than the DB.
    """

    def test_free_tier_stage(self):
        from app.services.feature_authorization_service import authorize_feature, Feature

        with patch("app.services.feature_authorization_service.resolve_user_subscription") as mock_sub:
            mock_sub.return_value = {
                "canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier", "has_full_access": False,
            }
            lessons = authorize_feature("uid-journey", Feature.LESSONS)
            content = authorize_feature("uid-journey", Feature.EXAM_PREP_CONTENT)

        assert lessons["allowed"] is True
        assert lessons["limited"] is True   # free tier: limited, not denied
        assert content["allowed"] is False

    def test_premium_stage(self):
        from app.services.feature_authorization_service import authorize_feature, Feature

        with patch("app.services.feature_authorization_service.resolve_user_subscription") as mock_sub:
            mock_sub.return_value = {
                "canonical_plan_key": "PREMIUM", "plan_name": "Premium", "has_full_access": True,
            }
            lessons = authorize_feature("uid-journey", Feature.LESSONS)
            content = authorize_feature("uid-journey", Feature.EXAM_PREP_CONTENT)

        assert lessons["allowed"] is True
        assert lessons["limited"] is False
        assert content["allowed"] is False   # Premium does NOT include Exam Prep Content

    def test_exam_prep_center_stage(self):
        from app.services.feature_authorization_service import authorize_feature, Feature

        with patch("app.services.feature_authorization_service.resolve_user_subscription") as mock_sub:
            mock_sub.return_value = {
                "canonical_plan_key": "EXAM_PREP_CENTER", "plan_name": "Exam Prep Center", "has_full_access": True,
            }
            lessons = authorize_feature("uid-journey", Feature.LESSONS)
            content = authorize_feature("uid-journey", Feature.EXAM_PREP_CONTENT)

        assert lessons["allowed"] is True
        assert lessons["limited"] is False
        assert content["allowed"] is True   # Exam Prep Center includes both
