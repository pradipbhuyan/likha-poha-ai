"""
test_school_outreach_service.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/services/school_outreach_service.py — the Supabase-backed
queries (summary, list, mark-responded), the queue_send() dispatch logic
(row filtering + background-thread wiring), and send_campaign_email()'s
Resend payload (from/to/cc/reply-to).
"""
import json
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
        # 6 sequential count="exact" queries: pending, sent, failed,
        # reminders_sent, responded, sent_today. Regression guard for the
        # real bug this replaced: select("status") + counting rows in
        # Python silently truncated at PostgREST's default 1000-row page
        # size once the table grew past 1000 rows (it undercounted a
        # 28,486-row table as 1000).
        chain_calls = [
            _chain_mock(MagicMock(count=17_000)),  # pending
            _chain_mock(MagicMock(count=11_000)),  # sent
            _chain_mock(MagicMock(count=486)),     # failed
            _chain_mock(MagicMock(count=3)),       # reminders_sent
            _chain_mock(MagicMock(count=2)),       # responded
            _chain_mock(MagicMock(count=1)),       # sent_today
        ]

        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.side_effect = chain_calls
            summary = svc.get_summary()

        assert summary["pending"] == 17_000
        assert summary["sent"] == 11_000
        assert summary["failed"] == 486
        assert summary["total"] == 28_486  # must sum the exact counts, not a truncated row fetch
        assert summary["reminders_sent"] == 3
        assert summary["responded"] == 2
        assert summary["sent_today"] == 1

    def test_handles_zero_state_cleanly(self):
        zero_count = MagicMock(count=0)
        chain_calls = [_chain_mock(zero_count) for _ in range(6)]

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

    def test_state_filter_applies_eq(self):
        resp = MagicMock(data=[{"email": "a@x.com", "state": "Delhi"}], count=1)
        chain = _chain_mock(resp)
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            result = svc.list_principals(state="Delhi")
        chain.eq.assert_any_call("state", "Delhi")
        assert result["total"] == 1

    def test_no_state_filter_does_not_apply_state_eq(self):
        resp = MagicMock(data=[], count=0)
        chain = _chain_mock(resp)
        with patch.object(svc, "admin_client") as mock_client:
            mock_client.table.return_value = chain
            svc.list_principals()
        for call in chain.eq.call_args_list:
            assert call.args[0] != "state"


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

    def test_reminder_send_targets_rows_whose_initial_was_sent(self):
        rows = [
            {"email": "sent1@x.com", "status": "sent", "principal_name": "A", "school_name": "S1"},
        ]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            queued = svc.queue_send(["sent1@x.com"], email_type="reminder")

        assert queued == 1
        mock_thread.assert_called_once()

    def test_reminder_send_skips_rows_never_initially_sent(self):
        # Guard: a follow-up makes no sense for a principal who was never
        # emailed the first pitch, regardless of what got selected in the UI.
        rows = [
            {"email": "never-sent@x.com", "status": "pending", "principal_name": "A", "school_name": "S1"},
        ]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            queued = svc.queue_send(["never-sent@x.com"], email_type="reminder")

        assert queued == 0
        mock_thread.assert_not_called()

    def test_reminder_send_mixed_selection_only_queues_the_sent_rows(self):
        rows = [
            {"email": "sent1@x.com", "status": "sent", "principal_name": "A", "school_name": "S1"},
            {"email": "never-sent@x.com", "status": "pending", "principal_name": "B", "school_name": "S2"},
            {"email": "failed1@x.com", "status": "failed", "principal_name": "C", "school_name": "S3"},
        ]
        with patch.object(svc, "get_by_emails", return_value=rows), \
             patch.object(svc.threading, "Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            queued = svc.queue_send(["sent1@x.com", "never-sent@x.com", "failed1@x.com"], email_type="reminder")

        assert queued == 1
        sent_rows_arg = mock_thread.call_args.kwargs["args"][0]
        assert [r["email"] for r in sent_rows_arg] == ["sent1@x.com"]

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


class TestBatchSubjectLine:
    """
    The initial pitch's subject leads with the AI learning/revision platform
    itself (not the "Principal Command Center" dashboard feature name) — the
    school name personalizes it since that field is reliable across the
    28k-row spreadsheet, unlike the scraped principal_name.
    """

    def test_initial_send_uses_the_ai_platform_subject_with_school_name(self):
        rows = [{"email": "a@x.com", "status": "pending", "principal_name": "A", "school_name": "Kendriya Vidyalaya"}]
        with patch.object(svc, "send_campaign_email") as mock_send, \
             patch.object(svc, "_mark_sent"), \
             patch.object(svc.time, "sleep"):
            mock_send.return_value = svc.SendResult(True, "id-123")
            svc._run_batch(rows, "initial")

        _, kwargs = mock_send.call_args
        assert kwargs["subject"] == "AI-Powered Learning & Revision Platform for Students of Kendriya Vidyalaya"

    def test_initial_send_falls_back_when_school_name_missing(self):
        rows = [{"email": "a@x.com", "status": "pending", "principal_name": "A", "school_name": ""}]
        with patch.object(svc, "send_campaign_email") as mock_send, \
             patch.object(svc, "_mark_sent"), \
             patch.object(svc.time, "sleep"):
            mock_send.return_value = svc.SendResult(True, "id-123")
            svc._run_batch(rows, "initial")

        _, kwargs = mock_send.call_args
        assert kwargs["subject"] == "An AI-Powered Learning & Revision Platform for Your School's Students"


class TestSendCampaignEmailPayload:
    def _sent_payload(self, monkeypatch, **kwargs):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        captured = {}

        def fake_urlopen(req, timeout=15):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            cm = MagicMock()
            cm.__enter__.return_value = MagicMock(status=200, read=lambda: b'{"id": "email-123"}')
            cm.__exit__.return_value = False
            return cm

        with patch.object(svc.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = svc.send_campaign_email(
                to=kwargs.get("to", "principal@example.com"),
                subject=kwargs.get("subject", "Test subject"),
                html=kwargs.get("html", "<p>hi</p>"),
                text=kwargs.get("text", "hi"),
            )
        return result, captured["body"]

    def test_cc_includes_the_reply_to_inbox(self, monkeypatch):
        _result, body = self._sent_payload(monkeypatch)
        assert body["cc"] == [svc.REPLY_TO]

    def test_to_reply_to_and_from_are_still_correct(self, monkeypatch):
        _result, body = self._sent_payload(monkeypatch, to="principal@example.com")
        assert body["to"] == ["principal@example.com"]
        assert body["reply_to"] == svc.REPLY_TO
        assert svc.FROM_ADDRESS in body["from"]

    def test_missing_api_key_fails_without_a_network_call(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        with patch.object(svc.urllib.request, "urlopen") as mock_urlopen:
            result = svc.send_campaign_email(to="a@x.com", subject="s", html="h", text="t")
        assert result.success is False
        mock_urlopen.assert_not_called()


class TestGreetingUsesRoleNotName:
    """
    The greeting addresses "Dear Principal," regardless of the scraped
    principal_name (spreadsheet names are inconsistently formatted/OCR'd
    across 28k rows) — but the school name must still appear, since that
    data is reliable and is the actual personalization hook.
    """

    def test_initial_email_html_and_text(self):
        html = svc.build_principal_email_html("Pushpa Kumari Singh", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        text = svc.build_principal_email_text("Pushpa Kumari Singh", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        for content in (html, text):
            assert "Dear Principal" in content
            assert "Pushpa" not in content
            assert "Atal Adarsh Vidyalaya" in content

    def test_reminder_email_html_and_text(self):
        html = svc.build_reminder_email_html("Pushpa Kumari Singh", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        text = svc.build_reminder_email_text("Pushpa Kumari Singh", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        for content in (html, text):
            assert "Dear Principal" in content
            assert "Pushpa" not in content
            assert "Atal Adarsh Vidyalaya" in content

    def test_missing_or_blank_principal_name_still_works(self):
        html = svc.build_principal_email_html("", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        assert "Dear Principal" in html


class TestFreeOfferAndTrustItems:
    def test_initial_email_mentions_free_student_access(self):
        html = svc.build_principal_email_html("", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        text = svc.build_principal_email_text("", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        for content in (html, text):
            assert "free access to all students" in content

    def test_initial_email_no_longer_mentions_razorpay_or_payments(self):
        html = svc.build_principal_email_html("", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        text = svc.build_principal_email_text("", "Atal Adarsh Vidyalaya", "https://likhapoha.in")
        for content in (html, text):
            assert "Razorpay" not in content
            assert "Safe Payments" not in content
