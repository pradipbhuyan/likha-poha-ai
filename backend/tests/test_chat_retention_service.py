"""
test_chat_retention_service.py
═════════════════════════
Regression tests for the platform chat retention cleanup job.

Covers:
  - Expired messages are deleted along with their Storage attachment
  - Attachment delete failures don't block the message-row delete
  - Storage path is correctly recovered from a signed attachment URL
  - Storage alert fires when total attachment bytes >= 1 GB
  - Storage alert respects the cooldown window (no spam every run)
  - Job never raises — always returns a summary dict

Run with:
    cd backend && python -m pytest tests/test_chat_retention_service.py -v
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import app.services.chat_retention_service as crs
from app.services.chat_retention_service import (
    run_chat_retention_job,
    _extract_storage_path,
    STORAGE_ALERT_THRESHOLD_BYTES,
)


class TestExtractStoragePath:
    def test_extracts_path_from_signed_url(self):
        url = "https://xxxx.supabase.co/storage/v1/object/sign/chat-attachments/room1/user1_123_file.png?token=abc"
        assert _extract_storage_path(url) == "room1/user1_123_file.png"

    def test_returns_none_for_empty_url(self):
        assert _extract_storage_path(None) is None
        assert _extract_storage_path("") is None

    def test_returns_none_for_unrelated_url(self):
        assert _extract_storage_path("https://example.com/foo.png") is None


class TestRunChatRetentionJob:
    def test_deletes_expired_messages_and_attachments(self, monkeypatch):
        expired = [
            {"id": "m1", "attachment_url": "https://x.supabase.co/storage/v1/object/sign/chat-attachments/r1/a.png?token=t"},
            {"id": "m2", "attachment_url": None},
        ]
        mock_client = MagicMock()
        # expired-messages query
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = expired
        # usage query (post-cleanup total)
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = []
        monkeypatch.setattr(crs, "admin_client", mock_client)
        monkeypatch.setattr(crs, "_get_last_alert_at", lambda: None)

        result = run_chat_retention_job()

        assert result["messages_inspected"] == 2
        assert result["messages_deleted"] == 2
        assert result["attachments_deleted"] == 1
        assert result["errors"] == 0
        # storage.from_(...).remove([...]) called once for the message with an attachment
        mock_client.storage.from_.return_value.remove.assert_called_once_with(["r1/a.png"])

    def test_attachment_delete_failure_does_not_block_message_delete(self, monkeypatch):
        expired = [{"id": "m1", "attachment_url": "https://x.supabase.co/storage/v1/object/sign/chat-attachments/r1/a.png?token=t"}]
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = expired
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = []
        mock_client.storage.from_.return_value.remove.side_effect = Exception("storage down")
        monkeypatch.setattr(crs, "admin_client", mock_client)
        monkeypatch.setattr(crs, "_get_last_alert_at", lambda: None)

        result = run_chat_retention_job()

        assert result["attachment_delete_errors"] == 1
        assert result["messages_deleted"] == 1  # row delete still happened
        assert result["errors"] == 0

    def test_no_expired_messages_is_a_noop(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = [{"attachment_size": 100}]
        monkeypatch.setattr(crs, "admin_client", mock_client)

        result = run_chat_retention_job()

        assert result["messages_deleted"] == 0
        assert result["total_attachment_bytes"] == 100
        assert result["storage_alert_sent"] is False

    def test_sends_alert_when_over_threshold(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = [
            {"attachment_size": STORAGE_ALERT_THRESHOLD_BYTES + 1}
        ]
        monkeypatch.setattr(crs, "admin_client", mock_client)
        monkeypatch.setattr(crs, "_get_last_alert_at", lambda: None)
        set_alert_calls = []
        monkeypatch.setattr(crs, "_set_last_alert_at", lambda when: set_alert_calls.append(when))
        monkeypatch.setattr(crs, "send_chat_storage_alert_email", lambda *a, **kw: True)

        result = run_chat_retention_job()

        assert result["storage_alert_sent"] is True
        assert len(set_alert_calls) == 1

    def test_does_not_alert_under_threshold(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = [
            {"attachment_size": STORAGE_ALERT_THRESHOLD_BYTES - 1}
        ]
        monkeypatch.setattr(crs, "admin_client", mock_client)
        email_calls = []
        monkeypatch.setattr(crs, "send_chat_storage_alert_email", lambda *a, **kw: email_calls.append(a) or True)

        result = run_chat_retention_job()

        assert result["storage_alert_sent"] is False
        assert len(email_calls) == 0

    def test_alert_respects_cooldown(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.not_.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_client.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = [
            {"attachment_size": STORAGE_ALERT_THRESHOLD_BYTES + 1}
        ]
        monkeypatch.setattr(crs, "admin_client", mock_client)
        recent_alert = datetime.now(timezone.utc) - timedelta(days=1)  # within 7-day cooldown
        monkeypatch.setattr(crs, "_get_last_alert_at", lambda: recent_alert)
        email_calls = []
        monkeypatch.setattr(crs, "send_chat_storage_alert_email", lambda *a, **kw: email_calls.append(a) or True)

        result = run_chat_retention_job()

        assert result["storage_alert_sent"] is False
        assert len(email_calls) == 0

    def test_never_raises_on_unexpected_error(self, monkeypatch):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("db down")
        monkeypatch.setattr(crs, "admin_client", mock_client)

        result = run_chat_retention_job()

        assert result["errors"] == 1
        assert "ran_at" in result
