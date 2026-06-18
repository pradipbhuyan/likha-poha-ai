"""
offer_access_service.py
───────────────────────
Helpers for determining whether a user is on an offer-code (free-tier) access
rather than a paid subscription.

Offer-code users get DKB-only doubt answers.  If the DKB cannot answer, the
platform returns an upgrade prompt instead of calling the LLM, keeping token
cost at zero for free users.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.auth_service import admin_client

# Message shown to offer-code users when a doubt is outside the DKB (Option 2)
OFFER_GATE_MESSAGE = (
    "🔒 **This doubt is outside your current access**\n\n"
    "Your offer gives you a taste of Likha Poha AI across select topics. "
    "To ask the AI anything — any subject, any chapter, any question — "
    "a paid subscription unlocks it all."
)

OFFER_GATE_SOURCE_TYPE = "OFFER_GATE"


def is_offer_code_user(user_id: str) -> bool:
    """
    Return True if the user's only active access is via an offer-code redemption
    and they do NOT have a paid CBSE or SOF subscription.

    Logic:
      1. Profile must NOT have access_cbse, access_sof_science,
         access_sof_maths, or access_sof_english set to True.
      2. User must have at least one non-expired offer_redemptions row.

    Admins and test accounts always return False (no gating).
    """
    if not user_id:
        return False

    try:
        profile_result = (
            admin_client
            .table("profiles")
            .select(
                "id, role, username, access_cbse, "
                "access_sof_science, access_sof_maths, access_sof_english"
            )
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = profile_result.data
        if not profile:
            return False

        # Admins and test accounts are never gated
        if profile.get("role") == "admin":
            return False

        username = str(profile.get("username") or "").strip().casefold()
        if username == "akshita.teststudent":
            return False

        # If user has any paid access flag → not offer-only
        if (
            profile.get("access_cbse")
            or profile.get("access_sof_science")
            or profile.get("access_sof_maths")
            or profile.get("access_sof_english")
        ):
            return False

        # Check for a valid (non-expired) offer redemption
        now_iso = datetime.now(timezone.utc).isoformat()
        redemption_result = (
            admin_client
            .table("offer_redemptions")
            .select("id")
            .eq("user_id", user_id)
            .gte("valid_until", now_iso)
            .limit(1)
            .execute()
        )

        return bool(redemption_result.data)

    except Exception:
        # If the check fails for any reason, do not gate — fail open to avoid
        # blocking legitimate users.
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
