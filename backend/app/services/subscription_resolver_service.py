"""
subscription_resolver_service.py
─────────────────────────────────────────────────────────────────────────────
Single canonical subscription resolver for the backend.

This is the authoritative function for determining a user's subscription state.
All access-control checks, the /api/subscription/resolve endpoint, and any
other backend logic that needs to know a user's tier must call this function.

Precedence (highest → lowest):
  1. Active paid subscription  — subscription_expires_at in future
  2. Perpetual paid plan       — access_cbse=True + plan key != "free" + no expiry
  3. Valid offer / free-trial  — offer_redemptions row with valid_until > now
  4. Admin-granted access      — access_cbse set, no offer, no expiry
  5. Default free              — no access

Why offer (3) is checked AFTER paid (1, 2):
  A user may have both a paid subscription_expires_at AND a prior offer
  redemption row.  The paid plan must win while it is active.

Why admin-grant (4) is last:
  An admin may grant access_cbse=True to any user, including offer-code users.
  We still want offer-code users to display "Offer / Free Access" and be subject
  to DKB gating as long as their offer is active (step 3 fires first).
  Once the offer expires the admin-grant provides a clean fallback.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.services.auth_service import admin_client

logger = logging.getLogger(__name__)


class AccessSource:
    PAID = "PAID"
    OFFER_CODE = "OFFER_CODE"
    ADMIN_GRANT = "ADMIN_GRANT"
    NONE = "NONE"


class Tier:
    FREE = "FREE"
    PREMIUM = "PREMIUM"


# ── Canonical plan limits keyed by canonical_plan_key ────────────────────────
# child_limit   — max children per parent subscription (None = unlimited)
# student_limit — max students per teacher roster
# restrictions  — list of feature restriction labels for limited-access tiers
_PLAN_LIMITS: dict[str, dict] = {
    "FREE_TIER": {
        "child_limit": None,
        "student_limit": None,
        "restrictions": ["lessons_limited", "mock_tests_5_per_day", "no_exemplar"],
    },
    "NANO": {
        "child_limit": 1,
        "student_limit": None,
        "restrictions": [],
    },
    "PREMIUM": {
        "child_limit": 1,
        "student_limit": None,
        "restrictions": [],
    },
    "FAMILY_PREMIUM": {
        "child_limit": 2,
        "student_limit": None,
        "restrictions": [],
    },
    "ADMIN_GRANT": {
        "child_limit": None,
        "student_limit": None,
        "restrictions": [],
    },
    # Bundled Grade 11–12 annual exam-prep plan (₹1,999/yr) — JEE Main, NEET UG,
    # CUET UG, SAT, IELTS & TOEFL iBT together. Deliberately excludes CBSE
    # lessons/doubts/mock tests/exemplar — see feature_authorization_service.py
    # where EXAM_PREP_CENTER is added to `limited_on` for those CBSE features.
    "EXAM_PREP_CENTER": {
        "child_limit": 1,
        "student_limit": None,
        "restrictions": ["no_cbse_lessons", "no_exemplar"],
    },
}


def resolve_user_subscription(user_id: str) -> dict:
    """
    Return the canonical subscription state for a single user.

    Parameters
    ----------
    user_id : str
        The Supabase auth / profile UUID.

    Returns
    -------
    dict with keys:
        active_tier   : "FREE" | "PREMIUM"
        plan_name     : human-readable plan label
        access_source : "PAID" | "OFFER_CODE" | "ADMIN_GRANT" | "NONE"
        has_full_access : bool   (False for offer/free users → DKB gate applies)
        valid_until   : ISO string | None
        days_remaining: int | None
        expiring_soon : bool
    """
    if not user_id:
        return _free_result()

    try:
        profile_resp = (
            admin_client
            .table("profiles")
            .select(
                "id, role, subscription_plan, subscription_expires_at, "
                "access_cbse, parent_id"
            )
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not profile_resp.data:
            return _free_result()

        profile = profile_resp.data[0]
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # ── 1. Active paid subscription (time-limited) ──────────────────────
        # subscription_expires_at is ONLY written by profile_access_from_plan()
        # after a confirmed Razorpay payment — never by offer-code redemption.
        # subscription_expires_at is ONLY written by profile_access_from_plan()
        # after a confirmed Razorpay payment — never by offer-code redemption.
        expires_at_str = profile.get("subscription_expires_at")
        had_expired_subscription = False
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
                if expires_at > now:
                    plan_key = profile.get("subscription_plan") or "free"
                    days_left = (expires_at - now).days
                    ck = _canonical_plan_key(plan_key)
                    return {
                        "active_tier": Tier.PREMIUM,
                        "plan_name": _paid_plan_name(plan_key),
                        "canonical_plan_key": ck,
                        "access_source": AccessSource.PAID,
                        "has_full_access": True,
                        "valid_until": expires_at_str,
                        "days_remaining": max(0, days_left),
                        "expiring_soon": days_left <= 3,
                        **_plan_limits(ck),
                    }
                had_expired_subscription = True
            except Exception:
                pass

        # ── 2. Perpetual paid plan (non-"free" key + access flag, no expiry) ─
        plan_key = profile.get("subscription_plan") or "free"
        has_access_flag = bool(profile.get("access_cbse"))
        if has_access_flag and plan_key != "free" and not expires_at_str:
            ck = _canonical_plan_key(plan_key)
            return {
                "active_tier": Tier.PREMIUM,
                "plan_name": _paid_plan_name(plan_key),
                "canonical_plan_key": ck,
                "access_source": AccessSource.PAID,
                "has_full_access": True,
                "valid_until": None,
                "days_remaining": None,
                "expiring_soon": False,
                **_plan_limits(ck),
            }

        # ── 2b. Legacy Nano user: plan_key="free" + access_cbse + no expiry ─
        # These users paid for Nano before subscription_expires_at was introduced.
        # They would incorrectly show "Admin Access" without this check.
        # Safety rule: only resolve as NANO if plan_key is "free" AND access_cbse=True.
        # Parents with access_cbse=True + plan_key="free" are excluded because
        # role="parent" does not go through the student subscription resolver path.
        if (
            has_access_flag
            and plan_key == "free"
            and not expires_at_str
            and profile.get("role") not in ("parent",)
        ):
            return {
                "active_tier": Tier.PREMIUM,
                "plan_name": "Premium Nano",
                "canonical_plan_key": "NANO",
                "access_source": AccessSource.PAID,
                "has_full_access": True,
                "valid_until": None,
                "days_remaining": None,
                "expiring_soon": False,
                **_plan_limits("NANO"),
            }

        # ── 3. Valid offer / free-trial access ──────────────────────────────
        # Check own redemptions, then parent's (for child accounts that inherit
        # their parent's offer validity).
        parent_id = profile.get("parent_id")
        candidate_ids = [user_id]
        if parent_id:
            candidate_ids.append(parent_id)

        for cid in candidate_ids:
            redemption_resp = (
                admin_client
                .table("offer_redemptions")
                .select("id, valid_until, code_id")
                .eq("user_id", cid)
                .gte("valid_until", now_iso)
                .order("valid_until", desc=True)
                .limit(1)
                .execute()
            )
            if redemption_resp.data:
                valid_until = redemption_resp.data[0]["valid_until"]
                exp = datetime.fromisoformat(
                    valid_until.replace("Z", "+00:00")
                )
                days_left = (exp - now).days
                return {
                    "active_tier": Tier.FREE,
                    "plan_name": "Offer / Free Access",
                    "canonical_plan_key": "FREE_TIER",
                    "access_source": AccessSource.OFFER_CODE,
                    "has_full_access": False,
                    "valid_until": valid_until,
                    "days_remaining": max(0, days_left),
                    "expiring_soon": days_left <= 7,
                    **_plan_limits("FREE_TIER"),
                }

        # ── 4. Admin-granted access (access flags set, no expiry, no offer) ─
        # Skip if subscription_expires_at was set — access_cbse may still be
        # True pending backend revocation; don't show "Admin Access" for that.
        # Also skip for parents — their access_cbse reflects child plan state,
        # not the parent's own subscription. A parent is always "Free Tier"
        # until they purchase, even if access_cbse=True was set by admin grant.
        if has_access_flag and not had_expired_subscription and profile.get("role") != "parent":
            return {
                "active_tier": Tier.PREMIUM,
                "plan_name": "Admin Access",
                "canonical_plan_key": "ADMIN_GRANT",
                "access_source": AccessSource.ADMIN_GRANT,
                "has_full_access": True,
                "valid_until": None,
                "days_remaining": None,
                "expiring_soon": False,
                **_plan_limits("ADMIN_GRANT"),
            }

        # ── 5. Default free tier ────────────────────────────────────────────
        return _free_result()

    except Exception as exc:
        logger.warning(
            "resolve_user_subscription failed for user_id=%s: %s",
            user_id,
            exc,
        )
        return _free_result()


def _free_result() -> dict:
    return {
        "active_tier": Tier.FREE,
        "plan_name": "Free Tier",
        "canonical_plan_key": "FREE_TIER",
        "access_source": AccessSource.NONE,
        "has_full_access": False,
        "valid_until": None,
        "days_remaining": None,
        "expiring_soon": False,
        **_plan_limits("FREE_TIER"),
    }


def _plan_limits(canonical_key: str) -> dict:
    """Return child_limit, student_limit, restrictions for a canonical plan key."""
    limits = _PLAN_LIMITS.get(canonical_key, _PLAN_LIMITS["FREE_TIER"])
    return {
        "child_limit": limits["child_limit"],
        "student_limit": limits["student_limit"],
        "restrictions": limits["restrictions"],
    }


def _paid_plan_name(plan_key: str) -> str:
    names = {
        "free": "Premium Nano",
        "family_premium": "Family Premium",
        "family_annual": "Family Premium — Annual",
        "standard_6month": "Premium — 6 Months",
        "standard_annual": "Premium — Annual",
        "exam_prep_center": "Exam Prep Center",
    }
    return names.get(plan_key, "Premium")


def _canonical_plan_key(plan_key: str) -> str:
    """
    Map raw DB plan key to canonical unambiguous key.

    The "free" DB key is shared by Free Tier users (never paid) and Nano paid
    users (subscription_plan="free" after ₹99 payment). The resolver determines
    which is which from subscription_expires_at and access_cbse before calling
    this — so callers of _canonical_plan_key always know the user IS on a paid
    plan; "free" here means Nano.

    Same pattern applies to "starter" vs "premium" below: two raw DB keys,
    one canonical tier. "starter" is current; "premium" is a legacy raw
    value some profile rows may still carry, kept mapped here rather than
    removed (see the "premium" entry's comment in
    app/data/subscription_plans.py for the full explanation — this isn't
    dead code, don't delete it as part of a "duplicate cleanup").
    """
    mapping = {
        "free": "NANO",
        "starter": "PREMIUM",
        "premium": "PREMIUM",
        "family_premium": "FAMILY_PREMIUM",
        "family_annual": "FAMILY_ANNUAL",
        "standard_6month": "PREMIUM_6MONTH",
        "standard_annual": "PREMIUM_ANNUAL",
        "exam_prep_center": "EXAM_PREP_CENTER",
    }
    return mapping.get(plan_key, "PREMIUM")
