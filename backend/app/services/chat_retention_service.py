"""
chat_retention_service.py
─────────────────────────────────────────────────────────────────────────────
Platform chat retention cleanup: deletes chat_messages past their per-message
expires_at (set at send-time from the admin-configured retention_days —
see platform_chat.py), along with their Storage attachment file, so chat
storage cost stays flat as usage grows instead of accumulating forever.

Also alerts the team by email when total chat attachment storage is still
over 1 GB after cleanup — i.e. growth is coming from live/recent usage, not
just an unpruned backlog.

Design:
  - Idempotent: running twice is safe — already-deleted rows are simply not
    found on the next run.
  - Hard-deletes expired rows (retention is a real purge, not a soft-delete —
    soft-delete via deleted_at is a separate, user-facing "hide my message"
    feature and is untouched here).
  - Attachment deletion failures don't block the message-row delete — a
    dangling Storage object is a cost/cleanup issue, not a correctness one,
    so we count it and move on rather than leaving old messages around.
  - Never raises — logs and counts errors, returns a summary dict.
  - The storage alert only re-fires after ALERT_COOLDOWN_DAYS so a stuck
    over-threshold state doesn't spam an email every run.

Can be triggered:
  - via admin endpoint: POST /api/admin/operations/run-chat-retention-job
  - via a cron/scheduler (GitHub Actions chat-retention-cleanup.yml)
  - via CLI: python -m app.services.chat_retention_service
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.auth_service import admin_client
from app.services.email_service import send_chat_storage_alert_email

logger = logging.getLogger(__name__)

CHAT_BUCKET = "chat-attachments"
STORAGE_ALERT_THRESHOLD_BYTES = 1 * 1024 ** 3  # 1 GB
ALERT_COOLDOWN_DAYS = 7
_ALERT_STATE_KEY = "chat_storage_alert_state"

_STORAGE_PATH_RE = re.compile(r"/chat-attachments/([^?]+)")


def _extract_storage_path(attachment_url: str) -> str | None:
    """
    Recover the bucket-relative Storage path from a signed attachment URL.

    Signed URLs look like:
      https://<project>.supabase.co/storage/v1/object/sign/chat-attachments/<path>?token=...
    """
    if not attachment_url:
        return None
    match = _STORAGE_PATH_RE.search(attachment_url)
    return match.group(1) if match else None


def _get_last_alert_at() -> datetime | None:
    try:
        row = (
            admin_client.table("admin_settings")
            .select("value")
            .eq("key", _ALERT_STATE_KEY)
            .limit(1)
            .execute()
        )
        if row.data:
            sent_at = (row.data[0].get("value") or {}).get("last_sent_at")
            if sent_at:
                return datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def _set_last_alert_at(when: datetime) -> None:
    try:
        admin_client.table("admin_settings").upsert(
            {"key": _ALERT_STATE_KEY, "value": {"last_sent_at": when.isoformat()}},
            on_conflict="key",
        ).execute()
    except Exception:
        logger.warning("chat_retention.alert_state_save_failed", exc_info=True)


def run_chat_retention_job() -> dict[str, Any]:
    """
    Delete expired chat_messages + their Storage attachments, then alert if
    remaining attachment storage is still over the 1 GB threshold.

    Returns a summary dict with counts of rows inspected/deleted and the
    current total attachment storage in bytes.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    result: dict[str, Any] = {
        "ran_at": now_iso,
        "messages_inspected": 0,
        "messages_deleted": 0,
        "attachments_deleted": 0,
        "attachment_delete_errors": 0,
        "total_attachment_bytes": 0,
        "storage_alert_sent": False,
        "errors": 0,
    }

    try:
        expired_resp = (
            admin_client.table("chat_messages")
            .select("id, attachment_url")
            .not_.is_("expires_at", "null")
            .lt("expires_at", now_iso)
            .execute()
        )
        expired = expired_resp.data or []
        result["messages_inspected"] = len(expired)

        for msg in expired:
            attachment_url = msg.get("attachment_url")
            if attachment_url:
                path = _extract_storage_path(attachment_url)
                if path:
                    try:
                        admin_client.storage.from_(CHAT_BUCKET).remove([path])
                        result["attachments_deleted"] += 1
                    except Exception:
                        result["attachment_delete_errors"] += 1
                        logger.warning("chat_retention.attachment_delete_failed", exc_info=True)

            try:
                admin_client.table("chat_messages").delete().eq("id", msg["id"]).execute()
                result["messages_deleted"] += 1
            except Exception:
                result["errors"] += 1
                logger.error("chat_retention.message_delete_failed", exc_info=True)

        # ── Current total attachment storage (post-cleanup) ────────────────
        usage_resp = (
            admin_client.table("chat_messages")
            .select("attachment_size")
            .not_.is_("attachment_size", "null")
            .execute()
        )
        total_bytes = sum((row.get("attachment_size") or 0) for row in (usage_resp.data or []))
        result["total_attachment_bytes"] = total_bytes

        if total_bytes >= STORAGE_ALERT_THRESHOLD_BYTES:
            last_alert = _get_last_alert_at()
            cooldown_active = last_alert and (now - last_alert) < timedelta(days=ALERT_COOLDOWN_DAYS)
            if not cooldown_active:
                sent = send_chat_storage_alert_email(
                    total_bytes, STORAGE_ALERT_THRESHOLD_BYTES, blocking=True,
                )
                if sent:
                    result["storage_alert_sent"] = True
                    _set_last_alert_at(now)

    except Exception:
        result["errors"] += 1
        logger.error("chat_retention.job_failed", exc_info=True)

    logger.info(
        "chat_retention.completed messages_deleted=%s attachments_deleted=%s "
        "total_attachment_bytes=%s errors=%s",
        result["messages_deleted"], result["attachments_deleted"],
        result["total_attachment_bytes"], result["errors"],
    )
    return result


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    summary = run_chat_retention_job()
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["errors"] == 0 else 1)
