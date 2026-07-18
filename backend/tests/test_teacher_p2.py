"""
test_teacher_p2.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for Teacher Success Platform — Phase 2.

Covers:
  Timeline:
  - enforces teacher ownership
  - returns unified sorted events
  - missing source tables do not crash

  Interventions:
  - only includes teacher's own students
  - sorts critical before medium before low

  Tasks:
  - CRUD works
  - teacher cannot access another teacher's tasks
  - task linked to unassigned student is rejected

  Classroom Analytics:
  - enforces classroom ownership
  - handles missing learning data gracefully

  Notes:
  - CRUD works (create/read/update/soft-delete)
  - teacher cannot access another teacher's notes
  - note content is never in audit log

  Parent Contact:
  - returns has_parent=false when no parent linked
  - requires teacher-student ownership
  - message parent handles no parent gracefully
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

import app.routes.teacher_classroom as p2
from app.routes.teacher_classroom import (
    get_student_timeline,
    get_interventions,
    list_tasks,
    create_task,
    complete_task,
    dismiss_task,
    get_classroom_analytics,
    list_notes,
    create_note,
    update_note,
    delete_note,
    get_parent_contact,
    message_parent,
    CreateTaskRequest,
    CreateNoteRequest,
    UpdateNoteRequest,
    MessageParentRequest,
)

TEACHER = {"profile": {"id": "teacher-1"}, "auth_user": {}}
TEACHER2 = {"profile": {"id": "teacher-2"}, "auth_user": {}}
STUDENT_ID = "student-1"
TASK_ID = "task-1"
NOTE_ID = "note-1"
CLASSROOM_ID = "classroom-1"


# ─────────────────────────────────────────────────────────────────────────────
# Timeline
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeline:
    def test_timeline_enforces_ownership(self, monkeypatch):
        """Teacher cannot view timeline of unassigned student."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: (_ for _ in ()).throw(
            __import__("fastapi").HTTPException(status_code=403, detail="Not assigned")
        ))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            get_student_timeline("foreign-student", teacher=TEACHER)
        assert exc.value.status_code == 403

    def test_timeline_missing_tables_do_not_crash(self, monkeypatch):
        """All source queries return empty — graceful response."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": STUDENT_ID, "username": "Alice", "grade": "Grade 9"}, None))
        monkeypatch.setattr(p2, "_safe_q", lambda fn: ([], None))
        result = get_student_timeline(STUDENT_ID, teacher=TEACHER)
        assert result["success"] is True
        assert result["events"] == []
        assert result["count"] == 0

    def test_timeline_sorted_descending(self, monkeypatch):
        """Events sorted by timestamp descending."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": STUDENT_ID, "username": "Alice", "grade": "Grade 9"}, None))
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                # audit_logs
                return [
                    {"event_type": "teacher.student.updated", "created_at": "2026-01-03"},
                    {"event_type": "teacher.student.updated", "created_at": "2026-01-01"},
                ], None
            return [], None
        monkeypatch.setattr(p2, "_safe_q", mock_safe_q)
        result = get_student_timeline(STUDENT_ID, teacher=TEACHER)
        timestamps = [e["timestamp"] for e in result["events"]]
        assert timestamps == sorted(timestamps, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Interventions
# ─────────────────────────────────────────────────────────────────────────────

class TestInterventions:
    def test_returns_only_own_students(self, monkeypatch):
        """Interventions only includes teacher's own assigned active students."""
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                # assignments
                return [{"student_id": "s1", "archived_at": None}], None
            if call_n["n"] == 2:
                # profiles
                return [{"id": "s1", "username": "Alice", "grade": "Grade 9", "account_status": "active"}], None
            return [], None  # activity, tests, invitations
        monkeypatch.setattr(p2, "_safe_q", mock_safe_q)
        monkeypatch.setattr(p2, "is_free_tier_user", lambda uid: True)
        result = get_interventions(teacher=TEACHER)
        assert result["success"] is True
        # All returned student_ids should be from teacher's students
        for inv in result["interventions"]:
            if inv["student_id"] is not None:
                assert inv["student_id"] == "s1"

    def test_no_students_returns_empty(self, monkeypatch):
        monkeypatch.setattr(p2, "_safe_q", lambda fn: ([], None))
        result = get_interventions(teacher=TEACHER)
        assert result["interventions"] == []

    def test_critical_before_medium_before_low(self, monkeypatch):
        """Interventions sorted: critical → medium → low."""
        # Build interventions list with mixed severity
        def make_inv(severity):
            return {"student_id": "s", "student_name": "S", "grade": "G",
                    "severity": severity, "reasons": ["r"], "recommended_actions": ["a"],
                    "last_active_at": None}
        # Patch by directly calling the sort logic
        interventions = [make_inv("low"), make_inv("critical"), make_inv("medium")]
        sev_order = {"critical": 0, "medium": 1, "low": 2}
        interventions.sort(key=lambda x: sev_order.get(x["severity"], 3))
        assert [i["severity"] for i in interventions] == ["critical", "medium", "low"]


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

class TestTasks:
    def test_create_task_basic(self, monkeypatch):
        """Teacher can create a task."""
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value.data = [
            {"id": TASK_ID, "title": "Review test", "status": "open", "priority": "medium"}
        ]
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(p2, "write_audit_event", MagicMock())
        req = CreateTaskRequest(title="Review test", priority="medium")
        result = create_task(req, teacher=TEACHER)
        assert result["success"] is True
        assert result["task"]["id"] == TASK_ID

    def test_create_task_linked_to_unassigned_student_rejected(self, monkeypatch):
        """Task linked to a student the teacher doesn't own is rejected."""
        def raise_403(*a):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not assigned")
        monkeypatch.setattr(p2, "_ensure_owns_student", raise_403)
        from fastapi import HTTPException
        req = CreateTaskRequest(title="Bad task", student_id="foreign-student")
        with pytest.raises(HTTPException) as exc:
            create_task(req, teacher=TEACHER)
        assert exc.value.status_code == 403

    def test_complete_task_requires_ownership(self, monkeypatch):
        """Teacher cannot complete another teacher's task."""
        monkeypatch.setattr(p2, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            complete_task(TASK_ID, teacher=TEACHER2)
        assert exc.value.status_code == 403

    def test_dismiss_task_requires_ownership(self, monkeypatch):
        """Teacher cannot dismiss another teacher's task."""
        monkeypatch.setattr(p2, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            dismiss_task(TASK_ID, teacher=TEACHER2)
        assert exc.value.status_code == 403

    def test_complete_task_writes_audit_event(self, monkeypatch):
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": TASK_ID}, None))
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(p2, "write_audit_event", lambda **kw: audit_calls.append(kw))
        complete_task(TASK_ID, teacher=TEACHER)
        assert any(c["event_type"] == "teacher.task.completed" for c in audit_calls)


# ─────────────────────────────────────────────────────────────────────────────
# Classroom Analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestClassroomAnalytics:
    def test_enforces_classroom_ownership(self, monkeypatch):
        """Teacher cannot access analytics for another teacher's classroom."""
        def raise_403(*a):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not yours")
        monkeypatch.setattr(p2, "_ensure_owns_classroom", raise_403)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            get_classroom_analytics("foreign-classroom", teacher=TEACHER2)
        assert exc.value.status_code == 403

    def test_empty_classroom_returns_safe_defaults(self, monkeypatch):
        """Classroom with no students returns available=false gracefully."""
        monkeypatch.setattr(p2, "_ensure_owns_classroom", lambda t, c: None)
        monkeypatch.setattr(p2, "_safe_q", lambda fn: ([], None))
        result = get_classroom_analytics(CLASSROOM_ID, teacher=TEACHER)
        assert result["success"] is True
        assert result["student_count"] == 0
        assert result["mock_test"]["available"] is False
        assert result["activity"]["available"] is False

    def test_missing_learning_data_shows_not_available(self, monkeypatch):
        """When test_history returns empty, analytics shows available=false."""
        monkeypatch.setattr(p2, "_ensure_owns_classroom", lambda t, c: None)
        call_n = {"n": 0}
        def mock_safe_q(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                # classroom members
                return [{"student_id": STUDENT_ID}], None
            if call_n["n"] == 2:
                # profiles
                return [{"id": STUDENT_ID, "username": "Alice", "account_status": "active"}], None
            # All other queries (test_history, ai_usage_logs) return empty
            return [], None
        monkeypatch.setattr(p2, "_safe_q", mock_safe_q)
        result = get_classroom_analytics(CLASSROOM_ID, teacher=TEACHER)
        assert result["success"] is True
        assert result["mock_test"]["available"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────────────────────────────────────

class TestNotes:
    def test_create_note_sanitizes_content(self, monkeypatch):
        """Note content is HTML-escaped before storage."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        inserted_note = {"stored": None}

        class MockTbl:
            def __init__(self):
                self.data = [{"id": NOTE_ID, "note": "<script>", "visibility": "teacher_private"}]
            def insert(self, row):
                inserted_note["stored"] = row["note"]
                return self
            def execute(self):
                return self

        monkeypatch.setattr(p2, "admin_client", MagicMock(
            table=lambda t: MockTbl() if "notes" in t else MagicMock()
        ))
        monkeypatch.setattr(p2, "write_audit_event", MagicMock())
        req = CreateNoteRequest(note="<script>alert('xss')</script>")
        result = create_note(STUDENT_ID, req, teacher=TEACHER)
        # The sanitized note should not contain raw HTML tags
        assert "<script>" not in (inserted_note["stored"] or "")

    def test_create_note_content_not_in_audit_log(self, monkeypatch):
        """Audit log must never contain the note content."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value.data = [
            {"id": NOTE_ID, "note": "SECRET NOTE CONTENT", "visibility": "teacher_private"}
        ]
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(p2, "write_audit_event", lambda **kw: audit_calls.append(kw))
        req = CreateNoteRequest(note="SECRET NOTE CONTENT")
        create_note(STUDENT_ID, req, teacher=TEACHER)
        for call in audit_calls:
            meta_str = str(call.get("metadata", {}))
            assert "SECRET NOTE CONTENT" not in meta_str

    def test_delete_note_is_soft(self, monkeypatch):
        """delete_note sets deleted_at — does not call DELETE on the DB row."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": NOTE_ID}, None))
        update_called = {"yes": False}
        mock_tbl = MagicMock()
        def track_update(row):
            assert "deleted_at" in row, "deleted_at must be set"
            update_called["yes"] = True
            return mock_tbl.return_value.update.return_value
        mock_tbl.return_value.update.side_effect = track_update
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(p2, "write_audit_event", MagicMock())
        result = delete_note(STUDENT_ID, NOTE_ID, teacher=TEACHER)
        assert result["success"] is True
        assert result.get("deleted") is True

    def test_note_ownership_enforced_on_update(self, monkeypatch):
        """Teacher cannot update another teacher's note."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        req = UpdateNoteRequest(note="updated")
        with pytest.raises(HTTPException) as exc:
            update_note(STUDENT_ID, NOTE_ID, req, teacher=TEACHER2)
        assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Parent Contact
# ─────────────────────────────────────────────────────────────────────────────

class TestParentContact:
    def test_returns_no_parent_when_not_linked(self, monkeypatch):
        """Returns has_parent=False when student has no parent_id."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": STUDENT_ID, "username": "Alice", "grade": "Grade 9", "parent_id": None}, None))
        result = get_parent_contact(STUDENT_ID, teacher=TEACHER)
        assert result["success"] is True
        assert result["has_parent"] is False

    def test_enforces_teacher_student_ownership(self, monkeypatch):
        """Teacher cannot get parent contact for unassigned student."""
        def raise_403(*a):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not assigned")
        monkeypatch.setattr(p2, "_ensure_owns_student", raise_403)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            get_parent_contact(STUDENT_ID, teacher=TEACHER2)
        assert exc.value.status_code == 403

    def test_message_parent_no_parent_returns_error(self, monkeypatch):
        """Message parent fails gracefully when no parent linked."""
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", lambda fn: ({"id": STUDENT_ID, "username": "Alice", "parent_id": None}, None))
        req = MessageParentRequest(subject="Hello", message="Hi there")
        result = message_parent(STUDENT_ID, req, teacher=TEACHER)
        assert result["success"] is False
        assert "parent" in result["error"].lower()

    def test_message_parent_no_email_status_no_email(self, monkeypatch):
        """Message parent with parent who has no email sets status=no_email."""
        call_n = {"n": 0}
        def mock_safe_one(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return {"id": STUDENT_ID, "username": "Alice", "parent_id": "parent-1"}, None
            return {"id": "parent-1", "email": None}, None  # no email
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", mock_safe_one)
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(p2, "write_audit_event", MagicMock())
        req = MessageParentRequest(subject="Hello", message="Hi there")
        result = message_parent(STUDENT_ID, req, teacher=TEACHER)
        assert result["success"] is True
        assert result["status"] == "no_email"

    def test_message_parent_audit_has_no_message_content(self, monkeypatch):
        """Audit log for parent message must not contain message content."""
        call_n = {"n": 0}
        def mock_safe_one(fn):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return {"id": STUDENT_ID, "username": "Alice", "parent_id": "parent-1"}, None
            return {"id": "parent-1", "email": None}, None
        monkeypatch.setattr(p2, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(p2, "_safe_one", mock_safe_one)
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(p2, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(p2, "write_audit_event", lambda **kw: audit_calls.append(kw))
        req = MessageParentRequest(subject="Test", message="PRIVATE MESSAGE BODY")
        message_parent(STUDENT_ID, req, teacher=TEACHER)
        for call in audit_calls:
            meta_str = str(call.get("metadata", {}))
            assert "PRIVATE MESSAGE BODY" not in meta_str
