"""
subscription_timeline_service.py
─────────────────────────────────────────────────────────────────────────────
Append-only subscription history service.

Writes to the subscription_timeline table.
Events are deduplicated via idempotency_key so retried verifications or
webhook replays do not produce duplicate timeline rows.

All writes are fire-and-forget — errors never break the calling flow.

Event types:
  FREE_TIER.assigned           — signup / free account created
  NANO.activated               — ₹99 / 8-day Nano paid
  PREMIUM.activated            — ₹299 monthly Premium paid
  FAMILY_PREMIUM.activated     — ₹499 monthly Family Premium paid
  plan.expired                 — paid plan expiry window passed
  FREE_TIER.fallback_applied   — expiry revoked flags → free tier
  OFFER_CODE.fallback_applied  — offer-code access applied
  ADMIN_GRANT.applied          — admin manually granted access
  admin_test.activated         — admin ₹1 test payment activated a plan
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.auth_service import admin_client

logger = logging.getLogger(__name__)


def write_timeline_event(
    *,
    user_id: str,
    event_type: str,
    from_plan: str | None = None,
    to_plan: str | None = None,
    source: str | None = None,
    payment_id: str | None = None,
    order_id: str | None = None,
    expires_at: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Append a subscription timeline event.

    Returns True if the event was written, False if it was a duplicate
    (idempotency_key already exists) or if the write failed for any reason.
    Callers should NOT retry on False — it is expected for dedup scenarios.
    """
    try:
        row: dict[str, Any] = {
            "user_id": user_id,
            "event_type": event_type,
            "from_plan": from_plan,
            "to_plan": to_plan,
            "source": source,
            "payment_id": payment_id,
            "order_id": order_id,
            "expires_at": expires_at,
            "idempotency_key": idempotency_key,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        admin_client.table("subscription_timeline").insert(row).execute()
        return True
    except Exception as exc:
        err = str(exc)
        if "duplicate" in err.lower() or "unique" in err.lower():
            logger.debug(
                "subscription_timeline.duplicate_skipped event=%s key=%s",
                event_type,
                idempotency_key,
            )
        else:
            logger.warning(
                "subscription_timeline.write_failed event=%s user=%s error=%s",
                event_type,
                user_id,
                exc,
            )
        return False


def activation_idempotency_key(order_id: str, payment_id: str) -> str:
    """
    Build a stable idempotency key for a payment activation event.
    Ensures the same payment cannot create duplicate timeline rows.
    """
    return f"pay:{order_id}:{payment_id}"
