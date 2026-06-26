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
  4. Admin-granted access      — access_cbse (or SOF flags) set, no offer, no expiry
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
                "access_cbse, access_sof_science, access_sof_maths, "
                "access_sof_english, parent_id"
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
        expires_at_str = profile.get("subscription_expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
                if expires_at > now:
                    plan_key = profile.get("subscription_plan") or "free"
                    days_left = (expires_at - now).days
                    return {
                        "active_tier": Tier.PREMIUM,
                        "plan_name": _paid_plan_name(plan_key),
                        "access_source": AccessSource.PAID,
                        "has_full_access": True,
                        "valid_until": expires_at_str,
                        "days_remaining": max(0, days_left),
                        "expiring_soon": days_left <= 3,
                    }
                # Past expiry — fall through (backend revokes flags on /profile load)
            except Exception:
                pass

        # ── 2. Perpetual paid plan (non-"free" key + access flag, no expiry) ─
        plan_key = profile.get("subscription_plan") or "free"
        has_access_flag = bool(
            profile.get("access_cbse")
            or profile.get("access_sof_science")
            or profile.get("access_sof_maths")
            or profile.get("access_sof_english")
        )
        if has_access_flag and plan_key != "free" and not expires_at_str:
            return {
                "active_tier": Tier.PREMIUM,
                "plan_name": _paid_plan_name(plan_key),
                "access_source": AccessSource.PAID,
                "has_full_access": True,
                "valid_until": None,
                "days_remaining": None,
                "expiring_soon": False,
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
                    "access_source": AccessSource.OFFER_CODE,
                    "has_full_access": False,
                    "valid_until": valid_until,
                    "days_remaining": max(0, days_left),
                    "expiring_soon": days_left <= 7,
                }

        # ── 4. Admin-granted access (access flags set, no expiry, no offer) ─
        if has_access_flag:
            return {
                "active_tier": Tier.PREMIUM,
                "plan_name": "Admin Access",
                "access_source": AccessSource.ADMIN_GRANT,
                "has_full_access": True,
                "valid_until": None,
                "days_remaining": None,
                "expiring_soon": False,
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
        "plan_name": "Free",
        "access_source": AccessSource.NONE,
        "has_full_access": False,
        "valid_until": None,
        "days_remaining": None,
        "expiring_soon": False,
    }


def _paid_plan_name(plan_key: str) -> str:
    names = {
        "free": "Premium Nano",
        "family_premium": "Family Premium",
        "family_annual": "Family Premium — Annual",
        "standard_6month": "Premium — 6 Months",
        "standard_annual": "Premium — Annual",
    }
    return names.get(plan_key, "Premium")
