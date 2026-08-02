"""
offer_access_service.py
───────────────────────
Helpers for determining whether a user is on Free Tier (limited access).

Ask Doubt (both the in-lesson widget and the standalone Doubt page) never
calls an LLM for either tier — every answer comes from the Doubt Knowledge
Base (DKB) cache or an extractive textbook (RAG) excerpt, with a warm
NCERT-reference fallback when neither finds a match. There is no per-topic
restriction any more: free-tier users may ask about any subject/chapter.
The only free-tier control is a shared cap of 5 doubt questions per day,
counted with one counter across both surfaces (see enforce_daily_limit in
usage_service.py, feature="doubt_answer_free_tier"). Paid users have no
daily cap.

Free Tier = any user who does NOT have an active paid subscription:
  - No access_cbse flag set from payment
  - No subscription_expires_at in the future

Offer codes are kept as an optional upgrade path but are NOT required for
free access.  All new users start on the Free Tier automatically.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.services.auth_service import admin_client

logger = logging.getLogger(__name__)

# Message shown to offer-code users when a doubt is outside the DKB (Option 2)
OFFER_GATE_MESSAGE = (
    "🔒 **This doubt is outside your current access**\n\n"
    "Your offer gives you a taste of Likha Poha AI across select topics. "
    "To ask the AI anything — any subject, any chapter, any question — "
    "a paid subscription unlocks it all."
)

OFFER_GATE_SOURCE_TYPE = "OFFER_GATE"


def is_free_tier_user(user_id: str) -> bool:
    """
    Return True if the user is on the Free Tier (limited, DKB-only access).

    Free Tier = user has NO active paid subscription:
      • access_cbse is False (not set by payment or admin)
      • subscription_expires_at is absent or in the past

    This replaces the old is_offer_code_user() gate.  Now ALL free users get
    DKB-only access regardless of whether they have an offer code.  Offer codes
    remain available as an optional upgrade path but are not required.

    Admins and test accounts always return False (never gated).
    """
    if not user_id:
        return False

    try:
        profile_result = (
            admin_client
            .table("profiles")
            .select(
                "id, role, access_cbse, subscription_expires_at"
            )
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_result.data
        if not profile:
            return False

        # Admins are never gated
        if profile.get("role") == "admin":
            return False

        # If user has any paid access flag → not free tier
        has_paid_access = bool(profile.get("access_cbse"))
        if has_paid_access:
            # Also verify subscription_expires_at is still in the future
            # (the profile endpoint revokes flags on expiry, but check here too)
            expires_at_str = profile.get("subscription_expires_at")
            if not expires_at_str:
                return False  # perpetual paid access (admin grant or monthly)
            try:
                from datetime import datetime, timezone  # noqa: PLC0415
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
                if expires_at > datetime.now(timezone.utc):
                    return False  # active paid subscription
                # Subscription expired — treat as free tier
            except Exception:
                return False  # If parse fails, don't gate

        return True  # No paid access → Free Tier

    except Exception as exc:
        # Fail open: never block a user if the check itself errors
        logger.warning("is_free_tier_user check failed for user_id=%s: %s", user_id, exc)
        return False


def is_offer_code_user(user_id: str) -> bool:
    """
    Backwards-compatible alias for is_free_tier_user().

    The old name is kept so existing callers continue to work without changes.
    The semantics have broadened: any free-tier user (including those without
    an offer code) is now gated in the same way as the old offer-code-only gate.
    """
    return is_free_tier_user(user_id)


def _parent_is_free_trial_offer_user(parent_id: str, now_iso: str) -> bool:
    """
    Return True if the given parent_id has a valid non-expired free_trial
    offer redemption.  Used to gate children of offer-code parents.
    """
    try:
        redemption = (
            admin_client
            .table("offer_redemptions")
            .select("id, code_id")
            .eq("user_id", parent_id)
            .gte("valid_until", now_iso)
            .limit(10)
            .execute()
        )
        if not redemption.data:
            return False
        code_ids = [r["code_id"] for r in redemption.data if r.get("code_id")]
        if not code_ids:
            return True
        codes = (
            admin_client
            .table("offer_codes")
            .select("id, code_type")
            .in_("id", code_ids)
            .execute()
        )
        for code in (codes.data or []):
            if code.get("code_type") == "discount":
                return False
        return True
    except Exception:
        return False


def build_offer_gate_response() -> dict:
    """Return the standard upgrade-prompt payload for offer-gated doubts."""
    return {
        "answer": OFFER_GATE_MESSAGE,
        "source_type": OFFER_GATE_SOURCE_TYPE,
        "sources": [],
        "textbook_visuals": [],
        "mentor_suggestions": [],
    }


# Message shown to a free-tier user who has used all 5 of today's doubt
# questions (shared cap across the in-lesson widget and the standalone
# Doubt page — see enforce_daily_limit(feature="doubt_answer_free_tier")).
DAILY_LIMIT_MESSAGE = (
    "🎉 You've used all 5 of your free questions for today!\n\n"
    "Come back tomorrow for 5 more, or upgrade to ask unlimited questions "
    "any time — any subject, any chapter."
)

DAILY_LIMIT_SOURCE_TYPE = "DAILY_LIMIT_REACHED"


def build_daily_limit_response() -> dict:
    """Return the standard payload for a free-tier student who has used all
    5 daily doubt questions. Shared by /api/doubt/answer and
    /api/lesson/follow-up so both surfaces show identical copy."""
    return {
        "answer": DAILY_LIMIT_MESSAGE,
        "source_type": DAILY_LIMIT_SOURCE_TYPE,
        "sources": [],
        "textbook_visuals": [],
        "mentor_suggestions": [],
    }
