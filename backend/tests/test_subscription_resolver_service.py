"""
Direct tests for resolve_user_subscription() in
app/services/subscription_resolver_service.py.

test_subscription_resolver_regression.py deliberately tests only this
module's pure helpers (_canonical_plan_key, _paid_plan_name) rather than
resolve_user_subscription() itself, since exercising it needs a mocked DB
round-trip — see that file's own comment on this. This file fills that gap
with the actual orchestration function: all 5 precedence branches, their
edge cases, and the exception fallback.

Precedence under test (see the module docstring for the full rationale):
  1. Active paid subscription (subscription_expires_at in the future)
  2. Perpetual paid plan (access_cbse=True, plan_key != "free", no expiry)
  2b. Legacy Nano (plan_key="free", access_cbse=True, no expiry, non-parent)
  3. Valid offer/free-trial (own or inherited from a parent)
  4. Admin-granted access (access_cbse set, no expiry, no offer, non-parent)
  5. Default free
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import app.services.subscription_resolver_service as resolver_module
from app.services.subscription_resolver_service import (
    AccessSource,
    Tier,
    resolve_user_subscription,
)


def _iso(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat()


class _ProfileQuery:
    def __init__(self, profile_row):
        self._profile_row = profile_row
        self._id = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        if col == "id":
            self._id = val
        return self

    def limit(self, _n):
        return self

    def execute(self):
        data = [self._profile_row] if self._profile_row and self._profile_row.get("id") == self._id else []
        return type("R", (), {"data": data})()


class _OfferQuery:
    def __init__(self, offers_by_user_id):
        self._offers_by_user_id = offers_by_user_id
        self._user_id = None
        self._min_valid_until = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        if col == "user_id":
            self._user_id = val
        return self

    def gte(self, col, val):
        if col == "valid_until":
            self._min_valid_until = val
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, _n):
        return self

    def execute(self):
        rows = self._offers_by_user_id.get(self._user_id, [])
        matched = [r for r in rows if r["valid_until"] >= self._min_valid_until] if self._min_valid_until else rows
        return type("R", (), {"data": matched[:1]})()


class FakeResolverClient:
    """Fake admin_client covering the "profiles" and "offer_redemptions" queries
    resolve_user_subscription() issues."""

    def __init__(self, profile_row=None, offers_by_user_id=None, raise_on_table=None):
        self.profile_row = profile_row
        self.offers_by_user_id = offers_by_user_id or {}
        self.raise_on_table = raise_on_table

    def table(self, name):
        if name == self.raise_on_table:
            raise Exception("simulated DB failure")
        if name == "profiles":
            return _ProfileQuery(self.profile_row)
        if name == "offer_redemptions":
            return _OfferQuery(self.offers_by_user_id)
        raise AssertionError(f"unexpected table: {name}")


def _profile(**overrides):
    base = {
        "id": "user-1",
        "role": "student",
        "subscription_plan": "free",
        "subscription_expires_at": None,
        "access_cbse": False,
        "parent_id": None,
    }
    base.update(overrides)
    return base


# ── Missing user_id / profile ─────────────────────────────────────────────────

def test_no_user_id_returns_free_result():
    result = resolve_user_subscription("")
    assert result["access_source"] == AccessSource.NONE
    assert result["active_tier"] == Tier.FREE


def test_profile_not_found_returns_free_result(monkeypatch):
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=None))
    result = resolve_user_subscription("ghost-user")
    assert result["access_source"] == AccessSource.NONE
    assert result["has_full_access"] is False


# ── Branch 1: active paid subscription ────────────────────────────────────────

def test_active_paid_subscription_future_expiry(monkeypatch):
    profile = _profile(subscription_plan="starter", subscription_expires_at=_iso(timedelta(days=25)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")

    assert result["access_source"] == AccessSource.PAID
    assert result["active_tier"] == Tier.PREMIUM
    assert result["canonical_plan_key"] == "PREMIUM"
    assert result["has_full_access"] is True
    assert result["valid_until"] is not None
    assert 23 <= result["days_remaining"] <= 25
    assert result["expiring_soon"] is False


def test_active_paid_subscription_expiring_soon_within_3_days(monkeypatch):
    profile = _profile(subscription_plan="starter", subscription_expires_at=_iso(timedelta(days=2)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["expiring_soon"] is True


def test_active_paid_subscription_legacy_nano_key(monkeypatch):
    """plan_key='free' with a future expiry is the legacy Nano DB representation."""
    profile = _profile(subscription_plan="free", subscription_expires_at=_iso(timedelta(days=5)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["canonical_plan_key"] == "NANO"
    assert result["plan_name"] == "Premium Nano"
    assert result["access_source"] == AccessSource.PAID


def test_days_remaining_never_negative(monkeypatch):
    """A subscription expiring in the next few hours must clamp days_remaining to >= 0."""
    profile = _profile(subscription_plan="starter", subscription_expires_at=_iso(timedelta(hours=2)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["days_remaining"] >= 0


# ── Branch 2: perpetual paid plan (no expiry) ─────────────────────────────────

def test_perpetual_paid_plan_no_expiry(monkeypatch):
    profile = _profile(subscription_plan="starter", access_cbse=True, subscription_expires_at=None)
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")

    assert result["access_source"] == AccessSource.PAID
    assert result["canonical_plan_key"] == "PREMIUM"
    assert result["valid_until"] is None
    assert result["days_remaining"] is None
    assert result["has_full_access"] is True


def test_perpetual_paid_plan_family_premium_canonical_key(monkeypatch):
    profile = _profile(subscription_plan="family_premium", access_cbse=True, subscription_expires_at=None)
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["canonical_plan_key"] == "FAMILY_PREMIUM"
    assert result["child_limit"] == 2


def test_perpetual_paid_plan_unrecognized_key_defaults_to_premium(monkeypatch):
    """
    _canonical_plan_key() falls back to PREMIUM for any plan_key it doesn't
    recognize. Documents this default explicitly — an unmapped key silently
    inheriting full PREMIUM-tier feature access is exactly the shape of the
    (separately fixed) exam-prep-pack canonical-key bug, so this behavior
    needs a test locking it in, not just implicit trust.
    """
    profile = _profile(subscription_plan="some_future_plan_key", access_cbse=True, subscription_expires_at=None)
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["canonical_plan_key"] == "PREMIUM"
    assert result["has_full_access"] is True


# ── Branch 2b: legacy Nano (plan_key="free", no expiry) ───────────────────────

def test_legacy_nano_student_no_expiry(monkeypatch):
    profile = _profile(subscription_plan="free", access_cbse=True, subscription_expires_at=None, role="student")
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["canonical_plan_key"] == "NANO"
    assert result["access_source"] == AccessSource.PAID


def test_legacy_nano_excludes_parent_role(monkeypatch):
    """
    A parent's access_cbse reflects their child's plan state, not their own —
    a parent must never resolve as NANO/PAID from this branch. With no offer
    and no other paid signal, they fall all the way through to free.
    """
    profile = _profile(subscription_plan="free", access_cbse=True, subscription_expires_at=None,
                        role="parent", id="parent-1")
    client = FakeResolverClient(profile_row=profile, offers_by_user_id={})
    monkeypatch.setattr(resolver_module, "admin_client", client)

    result = resolve_user_subscription("parent-1")
    assert result["access_source"] == AccessSource.NONE
    assert result["canonical_plan_key"] != "NANO"


# ── Branch 3: offer / free-trial access ───────────────────────────────────────

def test_own_active_offer_redemption(monkeypatch):
    profile = _profile()
    offers = {"user-1": [{"id": "off-1", "valid_until": _iso(timedelta(days=10)), "code_id": "c1"}]}
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile, offers_by_user_id=offers))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.OFFER_CODE
    assert result["active_tier"] == Tier.FREE
    assert result["has_full_access"] is False
    assert result["expiring_soon"] is False


def test_offer_expiring_soon_within_7_days(monkeypatch):
    profile = _profile()
    offers = {"user-1": [{"id": "off-1", "valid_until": _iso(timedelta(days=5)), "code_id": "c1"}]}
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile, offers_by_user_id=offers))

    result = resolve_user_subscription("user-1")
    assert result["expiring_soon"] is True


def test_child_inherits_parent_active_offer(monkeypatch):
    """A child with no offer of their own but a parent with an active one → OFFER_CODE."""
    profile = _profile(id="child-1", parent_id="parent-1")
    offers = {"parent-1": [{"id": "off-1", "valid_until": _iso(timedelta(days=20)), "code_id": "c1"}]}
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile, offers_by_user_id=offers))

    result = resolve_user_subscription("child-1")
    assert result["access_source"] == AccessSource.OFFER_CODE


def test_expired_offer_does_not_grant_access(monkeypatch):
    """An offer_redemptions row with valid_until in the past must not match the .gte() filter."""
    profile = _profile()
    offers = {"user-1": [{"id": "off-1", "valid_until": _iso(timedelta(days=-5)), "code_id": "c1"}]}
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile, offers_by_user_id=offers))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.NONE


# ── Branch 4: admin-granted access ────────────────────────────────────────────

def test_admin_grant_when_expiry_is_unparseable(monkeypatch):
    """
    A malformed subscription_expires_at (not a valid ISO string) can't be
    parsed by branch 1, but its mere presence (a non-empty string) also
    prevents branches 2 and 2b from matching, since both require
    `not expires_at_str`. With access_cbse set and no offer, this falls
    through to ADMIN_GRANT — the resolver's own except/pass documents this
    is deliberately swallowed rather than raised.
    """
    profile = _profile(subscription_plan="starter", access_cbse=True,
                        subscription_expires_at="not-a-real-date", role="teacher")
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.ADMIN_GRANT
    assert result["canonical_plan_key"] == "ADMIN_GRANT"
    assert result["has_full_access"] is True


def test_admin_grant_excludes_parent_role(monkeypatch):
    profile = _profile(subscription_plan="starter", access_cbse=True,
                        subscription_expires_at="not-a-real-date", role="parent", id="parent-1")
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("parent-1")
    assert result["access_source"] != AccessSource.ADMIN_GRANT


# ── Branch 5: default free ────────────────────────────────────────────────────

def test_never_paid_user_resolves_to_free(monkeypatch):
    profile = _profile()
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.NONE
    assert result["plan_name"] == "Free Tier"
    assert result["has_full_access"] is False


# ── Expired subscription — precedence interactions ────────────────────────────

def test_expired_subscription_no_offer_falls_through_to_free(monkeypatch):
    """Expiry job already revoked access_cbse — the common post-expiry state."""
    profile = _profile(subscription_plan="starter", access_cbse=False,
                        subscription_expires_at=_iso(timedelta(days=-3)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.NONE


def test_expired_subscription_with_stale_access_cbse_does_not_get_admin_grant(monkeypatch):
    """
    REGRESSION: an expired subscription with access_cbse still True (stale —
    the nightly expiry job hasn't revoked it yet) must NOT be upgraded to
    ADMIN_GRANT. had_expired_subscription is exactly the guard that prevents
    this — without it, a lapsed plan would misleadingly show "Admin Access"
    for the window between expiry and the revocation job running.
    """
    profile = _profile(subscription_plan="starter", access_cbse=True,
                        subscription_expires_at=_iso(timedelta(days=-1)))
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] != AccessSource.ADMIN_GRANT
    assert result["access_source"] == AccessSource.NONE


def test_expired_subscription_with_active_offer_falls_back_to_offer(monkeypatch):
    """Paid access wins while active, but once expired, an active offer still applies."""
    profile = _profile(subscription_plan="starter", access_cbse=False,
                        subscription_expires_at=_iso(timedelta(days=-3)))
    offers = {"user-1": [{"id": "off-1", "valid_until": _iso(timedelta(days=10)), "code_id": "c1"}]}
    monkeypatch.setattr(resolver_module, "admin_client", FakeResolverClient(profile_row=profile, offers_by_user_id=offers))

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.OFFER_CODE


# ── Exception handling ─────────────────────────────────────────────────────────

def test_db_exception_returns_free_result_not_raise(monkeypatch):
    client = FakeResolverClient(profile_row=_profile(), raise_on_table="profiles")
    monkeypatch.setattr(resolver_module, "admin_client", client)

    result = resolve_user_subscription("user-1")
    assert result["access_source"] == AccessSource.NONE
    assert result["has_full_access"] is False
