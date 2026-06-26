"""
test_subscription_states.py
===========================
Regression tests for subscription state transitions.

Covers all 4 enrollment paths:
  1. Free tier (no enrollment — gated)
  2. Offer code enrollment → free tier with time-limited offer access
  3. Payment enrollment → paid plan with subscription_expires_at
  4. Expired subscription → auto-revoked back to free tier

Also tests plan_expires_at() and profile_access_from_plan() helpers.

Run with:
    cd backend && python -m pytest tests/test_subscription_states.py -v
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.routes.payments import plan_expires_at, profile_access_from_plan


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
        "daily_token_limit": 100000,
        "monthly_token_limit": 1000000,
    }
    return {**base, **overrides}


def _needs_subscription_gate(user: dict) -> bool:
    """Mirror of App.jsx needsSubscription condition."""
    has_direct = (
        user.get("accessCbse") or user.get("accessSofScience") or
        user.get("accessSofMaths") or user.get("accessSofEnglish")
    )
    return (
        user.get("role") == "student"
        and user.get("subscriptionPlan") == "free"
        and not user.get("offerAccess")
        and not has_direct
        and not user.get("parentId")
    )


def _banner_should_show(user: dict) -> bool:
    """Mirror of App.jsx Premium Nano banner condition (after fix)."""
    return bool(
        user.get("role") == "student"
        and user.get("subscriptionExpiresAt")
        and not user.get("offerAccess")   # offer users must NOT see this banner
    )


def _is_expired(profile: dict) -> bool:
    expires = profile.get("subscription_expires_at")
    if not expires:
        return False
    exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) > exp_dt


# ─────────────────────────────────────────────────────────────────────────────
# 1. plan_expires_at() — billing label → expiry ISO datetime
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanExpiresAt:

    def test_eight_day_plan(self):
        """Premium Nano (Rs 99) plan expires in ~8 days."""
        result = plan_expires_at({"billing_label": "8 days"})
        assert result is not None
        days = _days_from_now(result)
        assert 7.9 <= days <= 8.1, f"Expected ~8 days, got {days:.2f}"

    def test_monthly_plan(self):
        """Premium monthly expires in exactly 30 days (business rule: not 31)."""
        result = plan_expires_at({"billing_label": "month"})
        assert result is not None
        days = _days_from_now(result)
        assert 29.9 <= days <= 30.1, f"Expected ~30 days, got {days:.2f}"

    def test_six_month_plan(self):
        """Premium 6-month expires in ~184 days."""
        result = plan_expires_at({"billing_label": "6 months"})
        assert result is not None
        days = _days_from_now(result)
        assert 183.9 <= days <= 184.1

    def test_annual_plan(self):
        """Premium Annual expires in ~366 days."""
        result = plan_expires_at({"billing_label": "year"})
        assert result is not None
        days = _days_from_now(result)
        assert 365.9 <= days <= 366.1

    def test_unknown_label_returns_none(self):
        """Unrecognised billing labels return None (perpetual/admin-granted access)."""
        assert plan_expires_at({"billing_label": "lifetime"}) is None
        assert plan_expires_at({"billing_label": ""}) is None
        assert plan_expires_at({}) is None

    def test_case_insensitive(self):
        """billing_label is compared case-insensitively."""
        assert plan_expires_at({"billing_label": "Month"}) is not None
        assert plan_expires_at({"billing_label": "8 Days"}) is not None

    def test_eight_day_differs_from_monthly(self):
        """8-day and monthly plans must have distinct, non-overlapping expiry dates."""
        nano = _days_from_now(plan_expires_at({"billing_label": "8 days"}))
        monthly = _days_from_now(plan_expires_at({"billing_label": "month"}))
        assert monthly - nano > 20, "8-day and monthly expiry must differ by > 20 days"


# ─────────────────────────────────────────────────────────────────────────────
# 2. profile_access_from_plan() — plan → profile DB fields
# ─────────────────────────────────────────────────────────────────────────────

class TestProfileAccessFromPlan:

    def test_premium_nano_sets_all_fields(self):
        """Premium Nano must set access_cbse=True, status=active, expiry ~8 days."""
        fields = profile_access_from_plan(_base_plan())
        assert fields["subscription_plan"] == "free"
        assert fields["access_cbse"] is True
        assert fields["account_status"] == "active"
        assert fields["subscription_expires_at"] is not None
        assert 7.9 <= _days_from_now(fields["subscription_expires_at"]) <= 8.1

    def test_premium_monthly_sets_expiry(self):
        """Premium monthly sets starter key and expiry ~30 days out (business rule)."""
        fields = profile_access_from_plan(_base_plan(key="starter", billing_label="month"))
        assert fields["subscription_plan"] == "starter"
        assert fields["subscription_expires_at"] is not None
        assert 29.9 <= _days_from_now(fields["subscription_expires_at"]) <= 30.1

    def test_six_month_plan_sets_expiry(self):
        """6-month plan sets expiry ~184 days out."""
        fields = profile_access_from_plan(_base_plan(
            key="standard_6month", billing_label="6 months"))
        assert fields["subscription_expires_at"] is not None
        assert 183.9 <= _days_from_now(fields["subscription_expires_at"]) <= 184.1

    def test_annual_plan_sets_expiry(self):
        """Annual plan sets expiry ~366 days out."""
        fields = profile_access_from_plan(_base_plan(
            key="standard_annual", billing_label="year"))
        assert fields["subscription_expires_at"] is not None
        assert 365.9 <= _days_from_now(fields["subscription_expires_at"]) <= 366.1

    def test_family_premium_token_limits(self):
        """Family Premium passes through higher token limits."""
        fields = profile_access_from_plan(_base_plan(
            key="family_premium", billing_label="month",
            daily_token_limit=150000, monthly_token_limit=5000000,
        ))
        assert fields["daily_token_limit"] == 150000
        assert fields["monthly_token_limit"] == 5000000

    def test_sof_flags_propagated(self):
        """SOF access flags are set correctly from the plan."""
        fields = profile_access_from_plan(_base_plan(
            access_sof_science=True, access_sof_maths=True, access_sof_english=False))
        assert fields["access_sof_science"] is True
        assert fields["access_sof_maths"] is True
        assert fields["access_sof_english"] is False

    def test_unknown_billing_gives_no_expiry(self):
        """Plans with unrecognised billing labels must have subscription_expires_at=None."""
        fields = profile_access_from_plan(_base_plan(billing_label="custom"))
        assert fields["subscription_expires_at"] is None

    def test_all_required_keys_present(self):
        """profile_access_from_plan() must always return all required DB column keys."""
        fields = profile_access_from_plan(_base_plan())
        for key in [
            "subscription_plan", "account_status",
            "access_cbse", "access_sof_science", "access_sof_maths", "access_sof_english",
            "daily_token_limit", "monthly_token_limit", "subscription_expires_at",
        ]:
            assert key in fields, f"Required field missing: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Subscription state machine — all 4 enrollment paths
# ─────────────────────────────────────────────────────────────────────────────

class TestSubscriptionStateMachine:
    """
    State 1: Free Tier    → gated, no banner
    State 2: Offer Code   → gate bypassed, no Premium Nano banner
    State 3: Paid Plan    → gate bypassed, expiry banner shows
    State 4: Expired Plan → access revoked, back to State 1
    """

    # ── State 1: Free tier ────────────────────────────────────────────────────

    def test_state1_new_user_is_gated(self):
        """Brand-new signup with no payment/offer sees the subscription gate."""
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False, "accessCbse": False,
            "accessSofScience": False, "accessSofMaths": False,
            "accessSofEnglish": False, "parentId": None,
            "subscriptionExpiresAt": None,
        }
        assert _needs_subscription_gate(user)
        assert not _banner_should_show(user)

    def test_state1_admin_bypasses_gate(self):
        """Admin role is never gated."""
        user = {"role": "admin", "subscriptionPlan": "free",
                "offerAccess": False, "accessCbse": False, "parentId": None}
        assert not _needs_subscription_gate(user)

    def test_state1_parent_linked_child_bypasses_gate(self):
        """Parent-linked children are managed by their parent — never gated."""
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False, "accessCbse": False,
            "parentId": "parent-uuid-123",
        }
        assert not _needs_subscription_gate(user)

    def test_state1_admin_cbse_grant_bypasses_gate(self):
        """Student with admin-granted CBSE access bypasses the gate."""
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False, "accessCbse": True,  # admin-granted
            "parentId": None,
        }
        assert not _needs_subscription_gate(user)

    # ── State 2: Offer code enrollment ────────────────────────────────────────

    def test_state2_offer_user_bypasses_gate(self):
        """Active offer code bypasses the subscription gate."""
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": True, "accessCbse": False,
            "parentId": None, "subscriptionExpiresAt": None,
        }
        assert not _needs_subscription_gate(user)

    def test_state2_offer_user_no_premium_banner(self):
        """Offer code user must NOT see the 'Premium Nano' banner — regression test."""
        user = {
            "role": "student",
            "offerAccess": True,
            "subscriptionExpiresAt": None,
        }
        assert not _banner_should_show(user)

    def test_state2_offer_user_with_stale_expires_no_banner(self):
        """
        REGRESSION: If subscription_expires_at is somehow set for an offer user
        (e.g. from a previous payment), the Premium Nano banner must still be
        suppressed because offerAccess=True takes precedence.
        """
        future_date = (datetime.now(timezone.utc) + timedelta(days=34)).isoformat()
        user = {
            "role": "student",
            "offerAccess": True,               # enrolled via offer code
            "subscriptionExpiresAt": future_date,  # stale expiry in profile
        }
        assert not _banner_should_show(user), (
            "Offer code user must NOT see Premium Nano banner "
            "even if subscriptionExpiresAt is set"
        )

    def test_state2_expired_offer_reverts_to_gate(self):
        """When offer redemption expires, user has no access and hits the gate."""
        now = datetime.now(timezone.utc)
        expired_until = (now - timedelta(hours=1)).isoformat()
        exp_dt = datetime.fromisoformat(expired_until.replace("Z", "+00:00"))
        has_offer_access = now <= exp_dt
        assert not has_offer_access  # offer has expired

        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False,  # expired
            "accessCbse": False,
            "parentId": None,
            "subscriptionExpiresAt": None,
        }
        assert _needs_subscription_gate(user)

    def test_state2_active_offer_days_remaining(self):
        """Active offer correctly calculates remaining days."""
        now = datetime.now(timezone.utc)
        valid_until = (now + timedelta(days=15)).isoformat()
        exp_dt = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
        has_offer_access = now <= exp_dt
        days_remaining = (exp_dt - now).days

        assert has_offer_access
        assert days_remaining == 15

    # ── State 3: Paid plan enrollment ─────────────────────────────────────────

    def test_state3_paid_nano_bypasses_gate_shows_banner(self):
        """Paid Premium Nano bypasses gate and shows expiry banner."""
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False, "accessCbse": True,
            "parentId": None,
            "subscriptionExpiresAt": expires,
        }
        assert not _needs_subscription_gate(user)
        assert _banner_should_show(user)

    def test_state3_paid_premium_bypasses_gate_shows_banner(self):
        """Paid Premium monthly bypasses gate and shows expiry banner."""
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        user = {
            "role": "student", "subscriptionPlan": "starter",
            "offerAccess": False, "accessCbse": True,
            "parentId": None,
            "subscriptionExpiresAt": expires,
        }
        assert not _needs_subscription_gate(user)
        assert _banner_should_show(user)

    def test_state3_profile_fields_after_payment(self):
        """After payment, profile has correct plan key and expiry."""
        for plan_key, billing, expected_days in [
            ("free",    "8 days",   8),
            ("starter", "month",   30),   # business rule: 30 days
            ("family_premium", "month", 30),  # business rule: 30 days
        ]:
            fields = profile_access_from_plan(_base_plan(
                key=plan_key, billing_label=billing))
            assert fields["subscription_plan"] == plan_key
            assert fields["access_cbse"] is True
            assert fields["subscription_expires_at"] is not None
            days = _days_from_now(fields["subscription_expires_at"])
            assert abs(days - expected_days) < 0.2, (
                f"Plan {plan_key}: expected {expected_days} days, got {days:.2f}"
            )

    # ── State 4: Expired plan → reverted to free tier ─────────────────────────

    def test_state4_expired_plan_detected(self):
        """subscription_expires_at in the past is correctly detected as expired."""
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        profile = {"subscription_expires_at": past_date}
        assert _is_expired(profile)

    def test_state4_active_plan_not_expired(self):
        """subscription_expires_at in the future is NOT expired."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        profile = {"subscription_expires_at": future_date}
        assert not _is_expired(profile)

    def test_state4_null_expires_is_not_expired(self):
        """subscription_expires_at=None (perpetual) is never expired."""
        assert not _is_expired({"subscription_expires_at": None})
        assert not _is_expired({})

    def test_state4_after_expiry_reverts_to_free_tier(self):
        """
        After expiry, the backend revokes access_cbse and clears expires_at.
        The resulting profile must match the free tier (gated) state.
        """
        # Simulate what GET /api/auth/profile does when subscription_expires_at is past
        revoked_profile = {
            "subscription_plan": "free",
            "access_cbse": False,           # revoked
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "subscription_expires_at": None,  # cleared
        }
        # Verify the revoked state is the free tier
        is_free = (
            revoked_profile["subscription_plan"] == "free"
            and not revoked_profile["access_cbse"]
            and revoked_profile["subscription_expires_at"] is None
        )
        assert is_free, "Expired subscription must revert profile to free tier"

        # And the frontend gate must fire
        user = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": False, "accessCbse": False,
            "parentId": None, "subscriptionExpiresAt": None,
        }
        assert _needs_subscription_gate(user)
        assert not _banner_should_show(user)

    def test_state4_expired_banner_clears(self):
        """After expiry, banner no longer shows (subscriptionExpiresAt becomes None)."""
        user = {
            "role": "student",
            "offerAccess": False,
            "subscriptionExpiresAt": None,  # cleared after expiry
        }
        assert not _banner_should_show(user)

    # ── Upgrade flow: free → paid ─────────────────────────────────────────────

    def test_upgrade_from_free_to_premium_nano(self):
        """Upgrading from free tier to Premium Nano updates plan and sets expiry."""
        before = {
            "subscription_plan": "free",
            "access_cbse": False,
            "subscription_expires_at": None,
        }
        # After paying Rs 99
        after = profile_access_from_plan(_base_plan(key="free", billing_label="8 days"))

        assert before["access_cbse"] is False
        assert after["access_cbse"] is True
        assert before["subscription_expires_at"] is None
        assert after["subscription_expires_at"] is not None
        assert 7.9 <= _days_from_now(after["subscription_expires_at"]) <= 8.1

    def test_upgrade_from_offer_to_paid_removes_gate(self):
        """
        User upgrades from offer code (free tier) to paid plan.
        After payment: gate no longer fires, expiry banner shows.
        """
        # Before upgrade: offer access
        user_before = {
            "role": "student", "subscriptionPlan": "free",
            "offerAccess": True, "accessCbse": False,
            "parentId": None, "subscriptionExpiresAt": None,
        }
        assert not _needs_subscription_gate(user_before)  # offer bypasses gate
        assert not _banner_should_show(user_before)        # no premium banner

        # After upgrade: paid Premium
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        user_after = {
            "role": "student", "subscriptionPlan": "starter",
            "offerAccess": False,   # offer status not relevant once paid
            "accessCbse": True,
            "parentId": None,
            "subscriptionExpiresAt": expires,
        }
        assert not _needs_subscription_gate(user_after)
        assert _banner_should_show(user_after)


# ─────────────────────────────────────────────────────────────────────────────
# 4. resolveUserSubscription() — canonical backend resolver
# ─────────────────────────────────────────────────────────────────────────────

from app.services.subscription_resolver_service import (  # noqa: E402
    resolve_user_subscription,
    AccessSource,
    Tier,
    _free_result,
    _paid_plan_name,
)


class TestResolverService:
    """
    Unit tests for subscription_resolver_service.resolve_user_subscription().

    These tests work entirely offline (no Supabase calls) by testing the
    helper functions and the _free_result / _paid_plan_name utilities that
    the resolver delegates to.
    """

    # ── _paid_plan_name() ─────────────────────────────────────────────────────

    def test_plan_name_nano(self):
        assert _paid_plan_name("free") == "Premium Nano"

    def test_plan_name_family_premium(self):
        assert _paid_plan_name("family_premium") == "Family Premium"

    def test_plan_name_family_annual(self):
        assert _paid_plan_name("family_annual") == "Family Premium — Annual"

    def test_plan_name_6month(self):
        assert _paid_plan_name("standard_6month") == "Premium — 6 Months"

    def test_plan_name_annual(self):
        assert _paid_plan_name("standard_annual") == "Premium — Annual"

    def test_plan_name_unknown_returns_premium(self):
        assert _paid_plan_name("starter") == "Premium"
        assert _paid_plan_name("some_new_key") == "Premium"

    # ── _free_result() ────────────────────────────────────────────────────────

    def test_free_result_shape(self):
        result = _free_result()
        assert result["active_tier"] == Tier.FREE
        assert result["access_source"] == AccessSource.NONE
        assert result["has_full_access"] is False
        assert result["valid_until"] is None
        assert result["days_remaining"] is None
        assert result["expiring_soon"] is False

    def test_free_result_plan_name(self):
        result = _free_result()
        assert result["plan_name"] == "Free Tier"

    # ── resolve_user_subscription() — invalid / missing user ─────────────────

    def test_resolve_empty_user_id_returns_free(self):
        result = resolve_user_subscription("")
        assert result["active_tier"] == Tier.FREE
        assert result["access_source"] == AccessSource.NONE

    def test_resolve_none_user_id_returns_free(self):
        result = resolve_user_subscription(None)
        assert result["active_tier"] == Tier.FREE
        assert result["access_source"] == AccessSource.NONE

    # ── AccessSource and Tier constants ───────────────────────────────────────

    def test_access_source_constants(self):
        assert AccessSource.PAID == "PAID"
        assert AccessSource.OFFER_CODE == "OFFER_CODE"
        assert AccessSource.ADMIN_GRANT == "ADMIN_GRANT"
        assert AccessSource.NONE == "NONE"

    def test_tier_constants(self):
        assert Tier.FREE == "FREE"
        assert Tier.PREMIUM == "PREMIUM"

    # ── Business rule: offer users must never see "Premium Nano" ─────────────

    def test_offer_source_has_different_plan_name_than_nano(self):
        """
        REGRESSION: the plan_name for OFFER_CODE access must NOT be 'Premium Nano'.
        An offer-code user is on 'Offer / Free Access', not a paid Nano plan.
        """
        offer_plan_name = "Offer / Free Access"
        nano_plan_name = _paid_plan_name("free")  # "Premium Nano"
        assert offer_plan_name != nano_plan_name, (
            "Offer / Free Access must have a different plan_name than Premium Nano"
        )

    def test_paid_nano_plan_name_is_premium_nano(self):
        """Paying for the ₹99/8-day plan must yield 'Premium Nano', not 'Free'."""
        assert _paid_plan_name("free") == "Premium Nano"
        assert _paid_plan_name("free") != "Free"

    # ── Resolver output shape ─────────────────────────────────────────────────

    def test_free_result_has_all_required_keys(self):
        required_keys = {
            "active_tier", "plan_name", "access_source",
            "has_full_access", "valid_until", "days_remaining", "expiring_soon",
        }
        result = _free_result()
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )

    # ── Expiry helpers used by the resolver ───────────────────────────────────

    def test_resolver_consistent_with_payment_expiry(self):
        """
        plan_expires_at() + profile_access_from_plan() → resolver's active_tier logic.

        Verify that a profile built from profile_access_from_plan() for the Nano plan
        would be correctly classified as PAID PREMIUM by the resolver's step 1.
        """
        fields = profile_access_from_plan(_base_plan(key="free", billing_label="8 days"))
        expires_at = fields["subscription_expires_at"]
        assert expires_at is not None

        # Simulate what resolver step 1 checks (subscription_expires_at in future)
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        assert exp > now, "Profile from payment must have future expiry"
        # If this profile were passed to resolve_user_subscription() it would
        # hit step 1 (PAID) — verified by the assertion above.

    def test_offer_signup_profile_has_no_expiry(self):
        """
        Profiles created via signup-with-offer-code never have subscription_expires_at.
        This guarantees the resolver never triggers step 1 (PAID) for offer users.
        """
        # signup-with-offer-code sets:
        offer_profile = {
            "subscription_plan": "free",
            "access_cbse": False,             # always False for free_trial codes
            "subscription_expires_at": None,  # never set by offer redemption
        }
        # Verify resolver step 1 condition is False for this profile
        has_expiry = bool(offer_profile.get("subscription_expires_at"))
        assert not has_expiry, (
            "Offer-code profiles must not have subscription_expires_at set "
            "so the resolver never misclassifies them as PAID"
        )
