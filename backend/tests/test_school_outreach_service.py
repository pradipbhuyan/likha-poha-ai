"""
test_school_outreach_service.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/services/school_outreach_service.py — the Supabase-backed
queries (summary, list, mark-responded) and the queue_send() dispatch logic
(row filtering + background-thread wiring). Sending itself (send_campaign_email)
already went through a live Resend test send in the campaign's development —
these tests focus on the new Supabase-integration surface.
"""
from unittest.mock import MagicMock, patch

import app.services.school_outreach_service as svc


def _chain_mock(execute_return):
    """
    A mock that returns itself from every Supabase query-builder method, so
    any chain (.select().eq().gte()...) resolves to the same object, with
    .execute() always returning the given canned response.
    """
    m = MagicMock()
    for method in ("select", "eq", "is_", "gte", "lte", "or_", "order", "range", "in_", "update"):
        getattr(m, method).return_value = m
    m.not_.is_.return_value = m  # `.not_` is a plain attribute access, not a call
    m.execute.return_value = execute_return
    return m


class TestGetSummary:
    def test_counts_by_status_and_extras(self):
        rows_resp = MagicMock(data=[{"status": "pending"}, {"status": "pending"}, {"status": "sent"}, {"status": "failed"}])
        reminders_resp = MagicMock(count=3)
        responded_resp = MagicMock(count=2)
        sent_today_resp = MagicMock(count=1)

        chain_calls = [
            _chain_mock(rows_resp),
            _chain_mock(reminders_resp),
            _chain_mock(responded_resp),
            _chain_mock(sent_today_resp),
        ]

        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.side_effect = chain_calls
            summary = svc.get_summary()

        assert summary["total"] == 4
        assert summary["pending"] == 2
        assert summary["sent"] == 1
        assert summary["failed"] == 1
        assert summary["reminders_sent"] == 3
        assert summary["responded"] == 2
        assert summary["sent_today"] == 1

    def test_handles_zero_state_cleanly(self):
        empty = MagicMock(data=[])
        zero_count = MagicMock(count=0)
        chain_calls = [_chain_mock(empty), _chain_mock(zero_count), _chain_mock(zero_count), _chain_mock(zero_count)]

        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.side_effect = chain_calls
            summary = svc.get_summary()

        assert summary == {
            "total": 0, "pending": 0, "sent": 0, "failed": 0,
            "sent_today": 0, "reminders_sent": 0, "responded": 0,
        }


class TestListPrincipals:
    def test_returns_rows_and_total(self):
        resp = MagicMock(data=[{"email": "a@x.com"}, {"email": "b@x.com"}], count=2)
        chain = _chain_mock(resp)

        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            result = svc.list_principals(status="pending", limit=50, offset=0)

        assert result["total"] == 2
        assert len(result["rows"]) == 2

    def test_needs_reminder_filter_does_not_raise(self):
        resp = MagicMock(data=[], count=0)
        chain = _chain_mock(resp)
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            result = svc.list_principals(needs_reminder=True)
        assert result == {"rows": [], "total": 0}

    def test_search_query_does_not_raise(self):
        resp = MagicMock(data=[], count=0)
        chain = _chain_mock(resp)
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            result = svc.list_principals(q="atal adarsh")
        assert result == {"rows": [], "total": 0}


class TestMarkResponded:
    def test_updates_matching_rows(self):
        resp = MagicMock(data=[{"email": "a@x.com"}, {"email": "b@x.com"}])
        chain = _chain_mock(resp)
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            updated = svc.mark_responded(["a@x.com", "b@x.com"])
        assert updated == 2

    def test_empty_list_is_a_no_op(self):
        with patch.object(svc, "admin_client") as mock_client:
            updated = svc.mark_responded([])
        assert updated == 0
        mock_client.table.assert_not_called()


class TestQueueSend:
    def test_initial_send_skips_already_sent_rows(self):
        rows = [
            {"email": "pending1@x.com", "status": "pending", "principal_name": "A", "school_name": "S1"},
            {"email": "already-sent@x.com", "status": "sent", "principal_name": "B", "school_name": "S2"},
        ]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            queued = svc.queue_send(["pending1@x.com", "already-sent@x.com"], email_type="initial")

        assert queued == 1  # only the pending row
        mock_thread.assert_called_once()
        _, kwargs = mock_thread.call_args
        assert kwargs["daemon"] is True
        sent_rows_arg = mock_thread.call_args.kwargs["args"][0]
        assert [r["email"] for r in sent_rows_arg] == ["pending1@x.com"]

    def test_reminder_send_does_not_filter_by_status(self):
        rows = [
            {"email": "sent1@x.com", "status": "sent", "principal_name": "A", "school_name": "S1"},
        ]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            queued = svc.queue_send(["sent1@x.com"], email_type="reminder")

        assert queued == 1
        mock_thread.assert_called_once()

    def test_no_matching_rows_starts_no_thread(self):
        with patch.object(svc, "get_by_emails", return_value=[]), \
             patch.object(svc.threading, "Thread") as mock_thread:
            queued = svc.queue_send(["nobody@x.com"], email_type="initial")

        assert queued == 0
        mock_thread.assert_not_called()

    def test_all_already_sent_starts_no_thread_for_initial(self):
        rows = [{"email": "sent1@x.com", "status": "sent", "principal_name": "A", "school_name": "S1"}]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            queued = svc.queue_send(["sent1@x.com"], email_type="initial")

        assert queued == 0
        mock_thread.assert_not_called()
