"""
audit_log_service.py
─────────────────────────────────────────────────────────────────────────────
Lightweight audit logging service.

Writes to the platform_audit_logs table.
All writes are fire-and-forget: errors are logged but NEVER propagate to
the caller — audit failures must never break payments, signups, or
student creation.

Event types (non-exhaustive):
  payment.order_created
  payment.verified
  payment.verify_idempotent    — duplicate verify call, returned existing state
  payment.admin_test_created
  payment.admin_test_verified
  subscription.activated
  subscription.expired
  subscription.fallback_applied
  student.created
  student.credentials_emailed
  parent_child.linked
  parent_child.unlinked
  rate_limit.exceeded
  expiry_job.ran
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.auth_service import admin_client

logger = logging.getLogger(__name__)


def write_audit_event(
    *,
    event_type: str,
    actor_user_id: str | None = None,
    target_user_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Write an audit event to platform_audit_logs.

    Safe to call from any endpoint — failures are silently logged, never raised.
    Do NOT include plaintext passwords or API secrets in metadata.
    """
    try:
        row = {
            "event_type": event_type,
            "actor_user_id": actor_user_id,
            "target_user_id": target_user_id,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "metadata": _sanitize_metadata(metadata or {}),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        admin_client.table("platform_audit_logs").insert(row).execute()
    except Exception as exc:
        # Audit failure must NEVER break the calling business flow
        logger.warning("audit_log.write_failed event=%s error=%s", event_type, exc)


def _sanitize_metadata(metadata: dict) -> dict:
    """
    Strip any field that might accidentally contain sensitive data.

    Keys matching the patterns below are removed before writing.
    """
    _BLOCKED_KEYS = {
        "password", "passwd", "secret", "token", "api_key", "api_secret",
        "razorpay_key_secret", "key_secret", "webhook_secret",
    }
    return {
        k: v
        for k, v in metadata.items()
        if k.lower() not in _BLOCKED_KEYS
    }
