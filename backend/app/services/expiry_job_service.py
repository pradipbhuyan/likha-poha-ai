"""
expiry_job_service.py
─────────────────────────────────────────────────────────────────────────────
Background expiry job: revokes premium flags for users whose paid subscription
has expired, and writes audit + timeline events for each revocation.

Design:
  - Idempotent: running twice is safe — already-revoked users are skipped.
  - Uses subscription_expires_at as the canonical expiry signal.
  - Uses the existing profile_access_from_plan / access flag logic.
  - Never re-invents access-control decisions — calls the canonical resolver
    after revocation to confirm the resulting state.
  - Preserves offer-code fallback: users with an active offer redemption
    are NOT fully reverted (their access is OFFER_CODE, not FREE_TIER).

Can be triggered:
  - via admin endpoint: POST /api/subscription/run-expiry-job
  - via a cron/scheduler (e.g. GitHub Actions, Supabase pg_cron)
  - via CLI:  python -m app.services.expiry_job_service
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.auth_service import admin_client
from app.services.audit_log_service import write_audit_event
from app.services.subscription_timeline_service import write_timeline_event
from app.services.metrics_service import increment

logger = logging.getLogger(__name__)


def run_expiry_job() -> dict[str, Any]:
    """
    Find expired paid subscriptions and revoke their access flags.

    Returns a summary dict with counts of users inspected / revoked / skipped.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    result: dict[str, Any] = {
        "ran_at": now_iso,
        "users_inspected": 0,
        "users_revoked": 0,
        "users_skipped_already_revoked": 0,
        "users_skipped_offer_fallback": 0,
        "errors": 0,
    }

    try:
        # Find all profiles with a past subscription_expires_at
        expired_resp = (
            admin_client
            .table("profiles")
            .select(
                "id, username, subscription_plan, subscription_expires_at, "
                "access_cbse, access_sof_science, access_sof_maths, "
                "access_sof_english, parent_id"
            )
            .lt("subscription_expires_at", now_iso)   # past expiry
            .not_.is_("subscription_expires_at", "null")
            .execute()
        )
    except Exception as exc:
        logger.error("expiry_job.query_failed error=%s", exc)
        result["errors"] += 1
        return result

    profiles = expired_resp.data or []
    result["users_inspected"] = len(profiles)
    logger.info("expiry_job.started users_with_expired_subscription=%d", len(profiles))

    for profile in profiles:
        user_id = profile["id"]
        username = profile.get("username", user_id)

        try:
            # ── Already revoked? ─────────────────────────────────────────────
            has_any_access = bool(
                profile.get("access_cbse")
                or profile.get("access_sof_science")
                or profile.get("access_sof_maths")
                or profile.get("access_sof_english")
            )
            if not has_any_access:
                result["users_skipped_already_revoked"] += 1
                continue

            # ── Check for active offer fallback ──────────────────────────────
            offer_resp = (
                admin_client
                .table("offer_redemptions")
                .select("id, valid_until")
                .eq("user_id", user_id)
                .gte("valid_until", now_iso)
                .limit(1)
                .execute()
            )
            has_active_offer = bool(offer_resp.data)

            # ── Revoke access flags ──────────────────────────────────────────
            old_plan = profile.get("subscription_plan", "free")
            admin_client.table("profiles").update({
                "access_cbse": False,
                "access_sof_science": False,
                "access_sof_maths": False,
                "access_sof_english": False,
                "subscription_expires_at": None,   # clear so it doesn't trigger again
            }).eq("id", user_id).execute()

            result["users_revoked"] += 1

            # ── Timeline event ───────────────────────────────────────────────
            idempotency_key = f"expiry:{user_id}:{profile['subscription_expires_at']}"
            write_timeline_event(
                user_id=user_id,
                event_type=(
                    "OFFER_CODE.fallback_applied" if has_active_offer
                    else "FREE_TIER.fallback_applied"
                ),
                from_plan=old_plan,
                to_plan="FREE_TIER" if not has_active_offer else "OFFER_CODE",
                source="EXPIRY",
                idempotency_key=idempotency_key,
                metadata={
                    "expired_at": profile.get("subscription_expires_at"),
                    "has_active_offer": has_active_offer,
                    "job_ran_at": now_iso,
                },
            )

            # ── Audit event ──────────────────────────────────────────────────
            write_audit_event(
                event_type="subscription.expired",
                target_user_id=user_id,
                entity_type="profile",
                entity_id=user_id,
                metadata={
                    "username": username,
                    "expired_at": profile.get("subscription_expires_at"),
                    "from_plan": old_plan,
                    "has_active_offer": has_active_offer,
                },
            )

            if has_active_offer:
                result["users_skipped_offer_fallback"] += 1

            increment("subscription.expired", username=username)
            increment("subscription.fallback_applied")

            logger.info(
                "expiry_job.revoked user=%s from_plan=%s offer_fallback=%s",
                username,
                old_plan,
                has_active_offer,
            )

        except Exception as exc:
            result["errors"] += 1
            logger.error("expiry_job.user_error user=%s error=%s", user_id, exc)

    # ── Final audit ──────────────────────────────────────────────────────────
    write_audit_event(
        event_type="expiry_job.ran",
        metadata={**result},
    )
    increment("expiry_job.ran")
    increment("expiry_job.users_revoked", value=result["users_revoked"])

    logger.info(
        "expiry_job.completed inspected=%d revoked=%d errors=%d",
        result["users_inspected"],
        result["users_revoked"],
        result["errors"],
    )
    return result


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    summary = run_expiry_job()
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["errors"] == 0 else 1)
