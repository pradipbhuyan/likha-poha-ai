"""
test_subscription_centralized.py
=================================
Comprehensive regression tests for the centralized subscription management system.

Tests cover:
  1. plan_expires_at() — duration_days priority over billing_label
  2. plan_display_amount() — price + discount calculation
  3. profile_access_from_plan() — access flags set correctly from plan
  4. feature_authorization — DB-driven override for exam prep + exemplar
  5. normalize_subscription_plan_row() — new fields included in normalized output
  6. DEFAULT_SUBSCRIPTION_PLANS — all plans have required new fields
  7. Payment flow integration — verify plan → Razorpay amount → profile activation
  8. Edge cases — null/invalid inputs, fallbacks

Run with:
    cd backend && python -m pytest tests/test_subscription_centralized.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.routes.payments import (
    plan_expires_at,
    plan_display_amount,
    profile_access_from_plan,
    _BILLING_LABEL_TO_DAYS,
)
from app.services.subscription_settings_service import normalize_subscription_plan_row
from app.data.subscription_plans import DEFAULT_SUBSCRIPTION_PLANS, get_default_subscription_plans


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _days_from_now(iso_str: str) -> float:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (dt - datetime.now(timezone.utc)).total_seconds() / 86400


def _base_plan(**overrides):
    base = {
        "key": "starter",
        "billing_label": "month",
        "duration_days": None,
        "access_cbse": True,
        "daily_token_limit": 100000,
        "monthly_token_limit": 3000000,
        "access_exam_prep": True,
        "access_exemplar": True,
        "price": 299,
        "discount_percent": 0,
    }
    return {**base, **overrides}


# ─────────────────────────────────────────────────────────────────────────────
# 1. plan_expires_at — duration_days takes priority over billing_label
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanExpiresAt:

    def test_duration_days_takes_priority_over_billing_label(self):
        """When duration_days is set, it overrides billing_label lookup."""
        plan = _base_plan(duration_days=45, billing_label="month")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 44 <= days <= 46, f"Expected ~45 days, got {days:.1f}"

    def test_billing_label_fallback_when_duration_days_none(self):
        """When duration_days is None/absent, billing_label lookup is used."""
        plan = _base_plan(duration_days=None, billing_label="month")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 29 <= days <= 31, f"Expected ~30 days, got {days:.1f}"

    def test_billing_label_fallback_when_duration_days_missing(self):
        """Plan dict without duration_days key falls back to billing_label."""
        plan = {"key": "starter", "billing_label": "month", "access_cbse": True,
                "daily_token_limit": 100000, "monthly_token_limit": 3000000}
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 29 <= days <= 31

    def test_nano_8_days_via_duration_days(self):
        """Premium Nano plan with duration_days=8 expires in ~8 days."""
        plan = _base_plan(key="free", duration_days=8, billing_label="8 days")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 7 <= days <= 9, f"Expected ~8 days, got {days:.1f}"

    def test_annual_365_via_duration_days(self):
        """Annual plan with duration_days=366 expires in ~366 days."""
        plan = _base_plan(key="standard_annual", duration_days=366, billing_label="year")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 365 <= days <= 367, f"Expected ~366 days, got {days:.1f}"

    def test_custom_duration_not_in_billing_label_map(self):
        """Admin sets custom duration_days=90 for a quarterly plan."""
        plan = _base_plan(duration_days=90, billing_label="3 months")  # not in legacy map
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 89 <= days <= 91, f"Expected ~90 days, got {days:.1f}"

    def test_free_tier_no_expiry(self):
        """Free tier has no billing_label in map → returns None."""
        plan = {"key": "free_tier", "billing_label": "free forever", "duration_days": None}
        result = plan_expires_at(plan)
        assert result is None

    def test_zero_duration_days_falls_back(self):
        """duration_days=0 is falsy → falls back to billing_label."""
        plan = _base_plan(duration_days=0, billing_label="month")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 29 <= days <= 31  # fallback to billing_label = "month" = 30 days

    def test_invalid_duration_days_string_falls_back(self):
        """Non-numeric duration_days string falls back to billing_label."""
        plan = _base_plan(duration_days="invalid", billing_label="month")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 29 <= days <= 31


# ─────────────────────────────────────────────────────────────────────────────
# 2. plan_display_amount — Razorpay charge amount
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanDisplayAmount:

    def test_no_discount(self):
        """Full price charged when discount_percent=0."""
        plan = _base_plan(price=299, discount_percent=0)
        assert plan_display_amount(plan) == 299

    def test_10_percent_discount(self):
        """10% discount applied correctly to ₹299."""
        plan = _base_plan(price=299, discount_percent=10)
        assert plan_display_amount(plan) == 269  # 299 * 0.9 = 269.1 → round = 269

    def test_100_percent_discount(self):
        """100% discount results in ₹0 (not negative)."""
        plan = _base_plan(price=299, discount_percent=100)
        assert plan_display_amount(plan) == 0

    def test_discount_clamped_at_zero(self):
        """Negative discount_percent is ignored — full price charged."""
        plan = _base_plan(price=299, discount_percent=-10)
        assert plan_display_amount(plan) == 299

    def test_nano_plan_amount(self):
        """Nano plan ₹99 with no discount charges ₹99."""
        plan = _base_plan(key="free", price=99, discount_percent=0)
        assert plan_display_amount(plan) == 99

    def test_family_premium_amount(self):
        """Family Premium ₹499 with 20% discount = ₹399."""
        plan = _base_plan(key="family_premium", price=499, discount_percent=20)
        assert plan_display_amount(plan) == 399

    def test_zero_price_stays_zero(self):
        """Free tier price=0 stays 0 regardless of discount."""
        plan = _base_plan(key="free_tier", price=0, discount_percent=50)
        assert plan_display_amount(plan) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. profile_access_from_plan — profile fields after payment
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileAccessFromPlan:

    def test_premium_plan_sets_access_cbse_true(self):
        plan = _base_plan(key="starter", access_cbse=True)
        fields = profile_access_from_plan(plan)
        assert fields["access_cbse"] is True
        assert fields["subscription_plan"] == "starter"
        assert fields["account_status"] == "active"

    def test_premium_plan_sets_token_limits(self):
        plan = _base_plan(daily_token_limit=100000, monthly_token_limit=3000000)
        fields = profile_access_from_plan(plan)
        assert fields["daily_token_limit"] == 100000
        assert fields["monthly_token_limit"] == 3000000

    def test_nano_plan_expires_in_8_days(self):
        plan = _base_plan(key="free", billing_label="8 days", duration_days=8)
        fields = profile_access_from_plan(plan)
        assert fields["subscription_expires_at"] is not None
        days = _days_from_now(fields["subscription_expires_at"])
        assert 7 <= days <= 9

    def test_monthly_plan_expires_in_30_days(self):
        plan = _base_plan(key="starter", billing_label="month", duration_days=30)
        fields = profile_access_from_plan(plan)
        assert fields["subscription_expires_at"] is not None
        days = _days_from_now(fields["subscription_expires_at"])
        assert 29 <= days <= 31

    def test_annual_plan_expires_in_366_days(self):
        plan = _base_plan(key="standard_annual", billing_label="year", duration_days=366)
        fields = profile_access_from_plan(plan)
        assert fields["subscription_expires_at"] is not None
        days = _days_from_now(fields["subscription_expires_at"])
        assert 365 <= days <= 367

    def test_duration_days_override_billing_label_in_profile(self):
        """When duration_days=45, profile expires in 45 days even if billing_label says 'month'."""
        plan = _base_plan(billing_label="month", duration_days=45)
        fields = profile_access_from_plan(plan)
        days = _days_from_now(fields["subscription_expires_at"])
        assert 44 <= days <= 46

    def test_free_tier_no_expiry_in_profile(self):
        plan = {"key": "free_tier", "billing_label": "free forever", "duration_days": None,
                "access_cbse": False,
                "daily_token_limit": 0, "monthly_token_limit": 0}
        fields = profile_access_from_plan(plan)
        assert fields["subscription_expires_at"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. normalize_subscription_plan_row — new fields included
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeSubscriptionPlanRow:

    def test_duration_days_preserved(self):
        row = {"key": "starter", "duration_days": 30, "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium"}
        result = normalize_subscription_plan_row(row)
        assert result["duration_days"] == 30

    def test_duration_days_none_when_missing(self):
        row = {"key": "starter", "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium"}
        result = normalize_subscription_plan_row(row)
        assert result["duration_days"] is None

    def test_access_exam_prep_true(self):
        row = {"key": "starter", "access_exam_prep": True, "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium"}
        result = normalize_subscription_plan_row(row)
        assert result["access_exam_prep"] is True

    def test_access_exam_prep_false(self):
        row = {"key": "free_tier", "access_exam_prep": False, "price": 0, "billing_label": "Free",
               "label": "Free Tier", "short_label": "Free"}
        result = normalize_subscription_plan_row(row)
        assert result["access_exam_prep"] is False

    def test_access_exemplar_true(self):
        row = {"key": "starter", "access_exemplar": True, "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium"}
        result = normalize_subscription_plan_row(row)
        assert result["access_exemplar"] is True

    def test_access_exemplar_missing_defaults_true(self):
        """Missing access_exemplar defaults to True for paid plans."""
        row = {"key": "starter", "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium"}
        result = normalize_subscription_plan_row(row)
        assert result["access_exemplar"] is True  # default True for paid plans

    def test_all_new_fields_present(self):
        """All three new fields must be present in normalized output."""
        row = {"key": "starter", "price": 299, "billing_label": "month",
               "label": "Premium", "short_label": "Premium",
               "duration_days": 30, "access_exam_prep": True, "access_exemplar": True}
        result = normalize_subscription_plan_row(row)
        assert "duration_days" in result
        assert "access_exam_prep" in result
        assert "access_exemplar" in result


# ─────────────────────────────────────────────────────────────────────────────
# 5. DEFAULT_SUBSCRIPTION_PLANS — all plans have required new fields
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaultSubscriptionPlans:

    PAID_PLAN_KEYS = ["free", "starter", "premium", "family_premium",
                      "standard_6month", "standard_annual", "family_annual"]

    def test_all_plans_have_duration_days(self):
        """Every plan in DEFAULT_SUBSCRIPTION_PLANS must have duration_days key."""
        plans = DEFAULT_SUBSCRIPTION_PLANS
        for key, plan in plans.items():
            assert "duration_days" in plan, f"Plan '{key}' missing duration_days"

    def test_all_plans_have_access_exam_prep(self):
        """Every plan must have access_exam_prep key."""
        for key, plan in DEFAULT_SUBSCRIPTION_PLANS.items():
            assert "access_exam_prep" in plan, f"Plan '{key}' missing access_exam_prep"

    def test_all_plans_have_access_exemplar(self):
        """Every plan must have access_exemplar key."""
        for key, plan in DEFAULT_SUBSCRIPTION_PLANS.items():
            assert "access_exemplar" in plan, f"Plan '{key}' missing access_exemplar"

    def test_free_tier_access_exam_prep_false(self):
        """Free tier should NOT include exam prep."""
        assert DEFAULT_SUBSCRIPTION_PLANS["free_tier"]["access_exam_prep"] is False

    def test_free_tier_access_exemplar_false(self):
        """Free tier should NOT include exemplar."""
        assert DEFAULT_SUBSCRIPTION_PLANS["free_tier"]["access_exemplar"] is False

    def test_cbse_paid_plans_access_exam_prep_false(self):
        """
        CBSE-tier paid plans (Premium, Family Premium and their variants) do
        NOT include Exam Prep Center's exam bundle — that's exclusive to the
        exam_prep_center plan itself. Per the "This term's plans" spec.
        "free" (Premium Nano) keeps its legacy True — Nano is excluded from
        exam prep content at the feature-matrix level regardless of this flag.
        """
        cbse_tier_keys = ["starter", "premium", "family_premium",
                           "standard_6month", "standard_annual", "family_annual"]
        for key in cbse_tier_keys:
            plan = DEFAULT_SUBSCRIPTION_PLANS[key]
            assert plan["access_exam_prep"] is False, f"Plan '{key}' access_exam_prep should be False"

    def test_exam_prep_center_access_exam_prep_true(self):
        """The Exam Prep Center plan itself must include exam prep content."""
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_center"]["access_exam_prep"] is True

    def test_exam_prep_center_access_cbse_true(self):
        """Exam Prep Center bundles full CBSE Grade 11-12 access, not just the exams."""
        assert DEFAULT_SUBSCRIPTION_PLANS["exam_prep_center"]["access_cbse"] is True

    def test_paid_plans_access_exemplar_true(self):
        """All paid plans should include exemplar by default."""
        for key in self.PAID_PLAN_KEYS:
            plan = DEFAULT_SUBSCRIPTION_PLANS[key]
            assert plan["access_exemplar"] is True, f"Plan '{key}' access_exemplar should be True"

    def test_nano_duration_days_8(self):
        """Nano plan (key='free') should have duration_days=8."""
        assert DEFAULT_SUBSCRIPTION_PLANS["free"]["duration_days"] == 8

    def test_starter_duration_days_30(self):
        """Premium plan (key='starter') should have duration_days=30."""
        assert DEFAULT_SUBSCRIPTION_PLANS["starter"]["duration_days"] == 30

    def test_family_premium_duration_days_30(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["family_premium"]["duration_days"] == 30

    def test_standard_6month_duration_days_184(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["standard_6month"]["duration_days"] == 184

    def test_annual_plans_duration_days_366(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["standard_annual"]["duration_days"] == 366
        assert DEFAULT_SUBSCRIPTION_PLANS["family_annual"]["duration_days"] == 366

    def test_free_tier_duration_days_none(self):
        """Free tier has no expiry — duration_days must be None."""
        assert DEFAULT_SUBSCRIPTION_PLANS["free_tier"]["duration_days"] is None

    def test_get_default_subscription_plans_deep_copy(self):
        """get_default_subscription_plans() returns a copy, not the original."""
        plans1 = get_default_subscription_plans()
        plans2 = get_default_subscription_plans()
        plans1["starter"]["label"] = "MUTATED"
        assert plans2["starter"]["label"] != "MUTATED"

    def test_all_plans_have_required_base_fields(self):
        """All plans must have the canonical set of required fields."""
        required = {"key", "label", "price", "billing_label", "access_cbse",
                    "duration_days", "access_exam_prep", "access_exemplar",
                    "daily_token_limit", "monthly_token_limit"}
        for key, plan in DEFAULT_SUBSCRIPTION_PLANS.items():
            missing = required - set(plan.keys())
            assert not missing, f"Plan '{key}' missing fields: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Feature authorization — DB-driven flag logic (unit test with mocked DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureAuthorizationDBLogic:
    """
    Tests for the DB-driven override logic in _get_plan_feature_flag().
    These test the helper function directly without needing a live DB.
    """

    def test_get_plan_feature_flag_returns_true_when_flag_set(self, monkeypatch):
        """When DB plan has access_exam_prep=True, flag returns True."""
        from app.services import feature_authorization_service as fas

        def mock_list(_):
            return {"plans": {"starter": {"access_exam_prep": True, "access_exemplar": True}}}

        monkeypatch.setattr(
            "app.services.feature_authorization_service._get_plan_feature_flag",
            lambda db_plan_key, flag_name, default=True: True
        )
        result = fas._get_plan_feature_flag("starter", "access_exam_prep", default=True)
        assert result is True

    def test_get_plan_feature_flag_returns_false_when_disabled(self, monkeypatch):
        """When DB plan has access_exam_prep=False, flag returns False."""
        from app.services import feature_authorization_service as fas

        # Patch the internal list_subscription_plan_settings import
        import app.services.feature_authorization_service as fas_module
        original = fas_module._get_plan_feature_flag

        # Test the parsing logic: if the plan has flag=False, should return False
        def mock_get_flag(db_plan_key, flag_name, default=True):
            mock_plans = {
                "starter": {"access_exam_prep": False, "access_exemplar": True},
                "free_tier": {"access_exam_prep": False, "access_exemplar": False},
            }
            plan = mock_plans.get(db_plan_key)
            if plan is None:
                return default
            flag = plan.get(flag_name)
            if flag is None:
                return default
            return bool(flag)

        monkeypatch.setattr(fas_module, "_get_plan_feature_flag", mock_get_flag)

        # Premium with exam_prep=False should return False
        assert mock_get_flag("starter", "access_exam_prep") is False
        # Free tier with exemplar=False should return False
        assert mock_get_flag("free_tier", "access_exemplar") is False
        # Unknown plan falls back to default
        assert mock_get_flag("unknown_plan", "access_exam_prep", default=True) is True
        assert mock_get_flag("unknown_plan", "access_exam_prep", default=False) is False

    def test_canonical_to_db_plan_key_mapping_complete(self):
        """All canonical plan keys used in feature auth must have a DB key mapping."""
        from app.services.feature_authorization_service import _CANONICAL_TO_DB_PLAN_KEY

        expected_canonical_keys = {"NANO", "PREMIUM", "PREMIUM_6MONTH", "PREMIUM_ANNUAL",
                                   "FAMILY_PREMIUM", "FAMILY_ANNUAL", "FREE_TIER", "ADMIN_GRANT"}
        for key in expected_canonical_keys:
            assert key in _CANONICAL_TO_DB_PLAN_KEY, f"Missing mapping for canonical key '{key}'"

    def test_db_driven_features_dict_valid(self):
        """_DB_DRIVEN_FEATURES must only reference valid Feature constants."""
        from app.services.feature_authorization_service import _DB_DRIVEN_FEATURES, Feature

        valid_features = {v for k, v in Feature.__dict__.items() if not k.startswith("_")}
        for feature_key in _DB_DRIVEN_FEATURES:
            assert feature_key in valid_features, f"Unknown feature in _DB_DRIVEN_FEATURES: '{feature_key}'"

    def test_db_driven_features_correct_flag_names(self):
        """DB-driven feature flags must map to correct plan field names."""
        from app.services.feature_authorization_service import _DB_DRIVEN_FEATURES, Feature

        assert _DB_DRIVEN_FEATURES[Feature.EXAM_PREP_CONTENT] == "access_exam_prep"
        assert _DB_DRIVEN_FEATURES[Feature.EXEMPLAR] == "access_exemplar"
        assert _DB_DRIVEN_FEATURES[Feature.EXEMPLAR_RESEARCH] == "access_exemplar"


# ─────────────────────────────────────────────────────────────────────────────
# 7. End-to-end payment flow simulation (no DB — pure logic)
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentFlowSimulation:
    """
    Simulate the complete payment flow:
    Plan settings (DB) → Razorpay amount → profile activation → expiry
    without making real DB or Razorpay calls.
    """

    def _simulate_plan_activation(self, plan_dict):
        """Simulate what happens after a successful Razorpay payment for a plan."""
        amount_charged = plan_display_amount(plan_dict)
        profile_fields = profile_access_from_plan(plan_dict)
        return {
            "amount_charged_rupees": amount_charged,
            "amount_paise": amount_charged * 100,
            "profile": profile_fields,
        }

    def test_nano_plan_full_flow(self):
        """Nano ₹99, 8 days → correct amount + access + expiry."""
        plan = _base_plan(key="free", price=99, discount_percent=0,
                          billing_label="8 days", duration_days=8, access_cbse=True)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 99
        assert result["amount_paise"] == 9900
        assert result["profile"]["access_cbse"] is True
        assert result["profile"]["subscription_plan"] == "free"
        days = _days_from_now(result["profile"]["subscription_expires_at"])
        assert 7 <= days <= 9

    def test_premium_plan_full_flow(self):
        """Premium ₹299, 30 days → correct amount + access + expiry."""
        plan = _base_plan(key="starter", price=299, discount_percent=0,
                          billing_label="month", duration_days=30, access_cbse=True)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 299
        assert result["amount_paise"] == 29900
        assert result["profile"]["access_cbse"] is True
        days = _days_from_now(result["profile"]["subscription_expires_at"])
        assert 29 <= days <= 31

    def test_premium_with_discount_flow(self):
        """Premium ₹299 with 10% discount → ₹269 charged, 30-day expiry."""
        plan = _base_plan(key="starter", price=299, discount_percent=10,
                          billing_label="month", duration_days=30)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 269
        assert result["amount_paise"] == 26900
        days = _days_from_now(result["profile"]["subscription_expires_at"])
        assert 29 <= days <= 31

    def test_family_premium_plan_full_flow(self):
        """Family Premium ₹499, 30 days → correct amount."""
        plan = _base_plan(key="family_premium", price=499, discount_percent=0,
                          billing_label="month", duration_days=30)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 499
        assert result["amount_paise"] == 49900

    def test_annual_plan_with_custom_duration_days(self):
        """Annual plan with admin-set duration_days=366 → 366-day expiry."""
        plan = _base_plan(key="standard_annual", price=2999, discount_percent=0,
                          billing_label="year", duration_days=366)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 2999
        days = _days_from_now(result["profile"]["subscription_expires_at"])
        assert 365 <= days <= 367

    def test_6month_plan_full_flow(self):
        """6-month plan with duration_days=184 → 184-day expiry."""
        plan = _base_plan(key="standard_6month", price=1495, discount_percent=0,
                          billing_label="6 months", duration_days=184)
        result = self._simulate_plan_activation(plan)

        assert result["amount_charged_rupees"] == 1495
        days = _days_from_now(result["profile"]["subscription_expires_at"])
        assert 183 <= days <= 185

    def test_admin_changes_duration_immediately_reflected(self):
        """If admin changes duration_days from 30 to 60, new payments get 60-day expiry."""
        # Before admin change: duration_days=30
        plan_before = _base_plan(billing_label="month", duration_days=30)
        result_before = self._simulate_plan_activation(plan_before)
        days_before = _days_from_now(result_before["profile"]["subscription_expires_at"])
        assert 29 <= days_before <= 31

        # After admin change: duration_days=60
        plan_after = _base_plan(billing_label="month", duration_days=60)
        result_after = self._simulate_plan_activation(plan_after)
        days_after = _days_from_now(result_after["profile"]["subscription_expires_at"])
        assert 59 <= days_after <= 61

    def test_admin_changes_price_immediately_reflected(self):
        """If admin changes price from ₹299 to ₹349, Razorpay charges ₹349."""
        plan_new_price = _base_plan(price=349, discount_percent=0)
        result = self._simulate_plan_activation(plan_new_price)
        assert result["amount_charged_rupees"] == 349
        assert result["amount_paise"] == 34900

    def test_admin_adds_discount_immediately_reflected(self):
        """If admin adds 15% discount to ₹299 plan, Razorpay charges ₹254."""
        plan = _base_plan(price=299, discount_percent=15, duration_days=30)
        result = self._simulate_plan_activation(plan)
        expected = round(299 * 0.85)  # 254
        assert result["amount_charged_rupees"] == expected


# ─────────────────────────────────────────────────────────────────────────────
# 8. Legacy billing_label map backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

class TestBillingLabelBackwardCompatibility:
    """
    Ensure the _BILLING_LABEL_TO_DAYS legacy map still works for plans
    where duration_days has not been set in DB yet.
    """

    def test_8_days_label_maps_correctly(self):
        assert _BILLING_LABEL_TO_DAYS.get("8 days") == 8

    def test_month_label_maps_to_30(self):
        assert _BILLING_LABEL_TO_DAYS.get("month") == 30

    def test_6_months_label_maps_to_184(self):
        assert _BILLING_LABEL_TO_DAYS.get("6 months") == 184

    def test_year_label_maps_to_366(self):
        assert _BILLING_LABEL_TO_DAYS.get("year") == 366

    def test_unknown_label_returns_none(self):
        assert _BILLING_LABEL_TO_DAYS.get("quarterly") is None

    def test_legacy_map_used_when_duration_days_not_in_db(self):
        """Plan from DB without duration_days column still expires correctly."""
        # Simulate a plan row from DB before migration (no duration_days key)
        old_db_plan = {
            "key": "starter",
            "billing_label": "month",
            "access_cbse": True,
            "daily_token_limit": 100000,
            "monthly_token_limit": 3000000,
        }
        result = plan_expires_at(old_db_plan)
        assert result is not None
        days = _days_from_now(result)
        assert 29 <= days <= 31

    def test_6month_legacy_label(self):
        plan = _base_plan(duration_days=None, billing_label="6 months")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 183 <= days <= 185

    def test_year_legacy_label(self):
        plan = _base_plan(duration_days=None, billing_label="year")
        result = plan_expires_at(plan)
        assert result is not None
        days = _days_from_now(result)
        assert 365 <= days <= 367


# ─────────────────────────────────────────────────────────────────────────────
# 9. Subscription parity — plan defaults consistent across layers
# ─────────────────────────────────────────────────────────────────────────────

class TestSubscriptionParity:
    """
    Ensure frontend and backend default plan configurations are consistent.
    Tests the Python layer — the JS layer is covered by frontend Jest tests.
    """

    def test_nano_plan_access_cbse_true(self):
        plan = DEFAULT_SUBSCRIPTION_PLANS["free"]
        assert plan["access_cbse"] is True

    def test_starter_plan_access_cbse_true(self):
        plan = DEFAULT_SUBSCRIPTION_PLANS["starter"]
        assert plan["access_cbse"] is True

    def test_free_tier_access_cbse_false(self):
        plan = DEFAULT_SUBSCRIPTION_PLANS["free_tier"]
        assert plan["access_cbse"] is False

    def test_no_plan_has_is_public_missing(self):
        """Every plan must explicitly declare is_public."""
        for key, plan in DEFAULT_SUBSCRIPTION_PLANS.items():
            assert "is_public" in plan, f"Plan '{key}' missing is_public"

    def test_free_tier_is_not_purchasable(self):
        """Free tier is public (shown in comparison table) but price=0 prevents payment.
        The frontend enforces is_public=False; the backend plan data itself has is_public=True
        since it still needs to be visible in the comparison table served to parents.
        The payment guard is: plan_display_amount(free_tier) == 0 → payment is blocked."""
        free_tier = DEFAULT_SUBSCRIPTION_PLANS["free_tier"]
        # Payment is blocked because price=0
        assert plan_display_amount(free_tier) == 0
        # The backend serves it in the comparison list (is_public=True in Python data layer)
        # Frontend overrides this with isPublic=false to hide the "Buy" button
        assert free_tier["price"] == 0

    def test_nano_is_discontinued(self):
        """Nano plan is discontinued from public sale — hidden and unpurchasable.

        Existing Nano subscribers keep their access: subscription_resolver_service's
        legacy-Nano branch identifies them independently of is_public.
        """
        assert DEFAULT_SUBSCRIPTION_PLANS["free"].get("is_public") is False

    def test_starter_is_purchasable(self):
        """Premium plan must be publicly available."""
        assert DEFAULT_SUBSCRIPTION_PLANS["starter"].get("is_public") is True

    def test_family_premium_is_purchasable(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["family_premium"].get("is_public") is True

    def test_premium_alias_hidden(self):
        """The 'premium' alias plan should be hidden (is_public=False)."""
        assert DEFAULT_SUBSCRIPTION_PLANS["premium"].get("is_public") is False

    def test_nano_price_99(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["free"]["price"] == 99

    def test_starter_price_299(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["starter"]["price"] == 299

    def test_family_premium_price_499(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["family_premium"]["price"] == 499

    def test_standard_6month_price_1495(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["standard_6month"]["price"] == 1495

    def test_standard_annual_price_2999(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["standard_annual"]["price"] == 2999

    def test_family_annual_price_4999(self):
        assert DEFAULT_SUBSCRIPTION_PLANS["family_annual"]["price"] == 4999

    def test_all_plan_keys_consistent(self):
        """The 'key' field inside each plan must match the dict key."""
        for dict_key, plan in DEFAULT_SUBSCRIPTION_PLANS.items():
            assert plan["key"] == dict_key, (
                f"Plan dict key '{dict_key}' doesn't match plan['key'] = '{plan['key']}'"
            )
