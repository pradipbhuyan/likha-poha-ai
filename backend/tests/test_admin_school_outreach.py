"""
test_admin_school_outreach.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/routes/admin_school_outreach.py. The service layer's Supabase
queries are already covered in test_school_outreach_service.py — these tests
mock the service module itself and focus on the route's request validation
and response shape.
"""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import app.routes.admin_school_outreach as route


def fake_admin():
    return {"profile": {"id": "admin-1", "role": "admin"}}


class TestGetSummary:
    def test_returns_service_summary(self):
        with patch.object(route.svc, "get_summary", return_value={"total": 5, "pending": 3}):
            result = route.get_summary(admin=fake_admin())
        assert result == {"success": True, "summary": {"total": 5, "pending": 3}}


class TestListPrincipals:
    def test_passes_filters_through(self):
        with patch.object(route.svc, "list_principals", return_value={"rows": [{"email": "a@x.com"}], "total": 1}) as mock_list:
            result = route.list_principals(
                status="pending", needs_reminder=False, q="atal", state="", limit=50, offset=0, admin=fake_admin()
            )

        mock_list.assert_called_once_with(status="pending", needs_reminder=False, q="atal", state="", limit=50, offset=0)
        assert result["success"] is True
        assert result["total"] == 1
        assert result["principals"] == [{"email": "a@x.com"}]

    def test_passes_state_filter_through(self):
        with patch.object(route.svc, "list_principals", return_value={"rows": [], "total": 0}) as mock_list:
            route.list_principals(
                status="", needs_reminder=False, q="", state="Delhi", limit=50, offset=0, admin=fake_admin()
            )

        mock_list.assert_called_once_with(status="", needs_reminder=False, q="", state="Delhi", limit=50, offset=0)


class TestListStates:
    def test_returns_the_fixed_state_list(self):
        result = route.list_states(admin=fake_admin())
        assert result["success"] is True
        assert "Delhi" in result["states"]
        assert result["states"] == route.svc.OUTREACH_STATES


class TestSendToSelected:
    def test_rejects_invalid_type(self):
        data = route.SendRequest(emails=["a@x.com"], type="weekly")
        with pytest.raises(HTTPException) as exc:
            route.send_to_selected(data, admin=fake_admin())
        assert exc.value.status_code == 400

    def test_rejects_empty_emails(self):
        data = route.SendRequest(emails=[], type="initial")
        with pytest.raises(HTTPException) as exc:
            route.send_to_selected(data, admin=fake_admin())
        assert exc.value.status_code == 400

    def test_queues_initial_send(self):
        data = route.SendRequest(emails=["a@x.com", "b@x.com"], type="initial")
        with patch.object(route.svc, "queue_send", return_value=2) as mock_queue:
            result = route.send_to_selected(data, admin=fake_admin())

        mock_queue.assert_called_once_with(["a@x.com", "b@x.com"], email_type="initial")
        assert result["success"] is True
        assert result["queued"] == 2

    def test_queues_reminder_send(self):
        data = route.SendRequest(emails=["a@x.com"], type="reminder")
        with patch.object(route.svc, "queue_send", return_value=1) as mock_queue:
            result = route.send_to_selected(data, admin=fake_admin())

        mock_queue.assert_called_once_with(["a@x.com"], email_type="reminder")
        assert result["queued"] == 1


class TestMarkResponded:
    def test_rejects_empty_emails(self):
        data = route.MarkRespondedRequest(emails=[])
        with pytest.raises(HTTPException) as exc:
            route.mark_responded(data, admin=fake_admin())
        assert exc.value.status_code == 400

    def test_marks_and_returns_count(self):
        data = route.MarkRespondedRequest(emails=["a@x.com", "b@x.com"])
        with patch.object(route.svc, "mark_responded", return_value=2) as mock_mark:
            result = route.mark_responded(data, admin=fake_admin())

        mock_mark.assert_called_once_with(["a@x.com", "b@x.com"])
        assert result == {"success": True, "updated": 2}
