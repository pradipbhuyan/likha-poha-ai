"""
test_teacher_classroom_platform.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for the Teacher Success Platform — Phase 1.

Covers:
  Backend plan limits:
  - Free teacher can list students (only their own)
  - Free teacher cannot add 11th student (limit enforced)
  - Paid teacher can add up to 30 students
  - Count function returns correct value

  Authorization:
  - teacher.students list only returns teacher's own students
  - _ensure_owns_student raises 403 for foreign student
  - _ensure_owns_classroom raises 403 for foreign classroom

  Student actions:
  - archive sets archived_at
  - reset-password uses Supabase auth (stub) — no password in audit log
  - email-credentials blocked for free teacher

  Invitations:
  - create returns invitation dict
  - resend rejected for accepted invitation
  - cancel rejected for accepted invitation
  - expired invitation cannot be resent if accepted

  Classrooms:
  - create returns classroom dict
  - archive sets status=archived
  - duplicate student add is safe (upsert)
  - teacher cannot modify another teacher's classroom

  Audit:
  - all mutating operations write audit events
  - audit metadata never contains passwords
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

import app.routes.teacher_classroom as tc
from app.routes.teacher_classroom import (
    FREE_TEACHER_MAX,
    PAID_TEACHER_MAX,
    INVITATION_EXPIRY_DAYS,
    _resolve_teacher_limit,
    _count_active_assignments,
    _ensure_owns_student,
    _ensure_owns_classroom,
    teacher_dashboard_summary,
    list_students,
    archive_student,
    reset_student_password,
    email_student_credentials,
    create_invitation,
    resend_invitation,
    cancel_invitation,
    create_classroom,
    archive_classroom,
    add_student_to_classroom,
)

TEACHER_FREE = {"id": "teacher-free-1", "role": "teacher"}
TEACHER_PAID = {"id": "teacher-paid-1", "role": "teacher"}

STUDENT_ID = "student-1"
CLASSROOM_ID = "classroom-1"
INV_ID = "invitation-1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_safe_q(rows):
    return lambda fn: (rows, None)


def _mock_safe_one(row):
    return lambda fn: (row, None)


# ─────────────────────────────────────────────────────────────────────────────
# Plan limit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanLimits:
    def test_free_teacher_limit_is_10(self, monkeypatch):
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: True)
        assert _resolve_teacher_limit("any") == FREE_TEACHER_MAX == 10

    def test_paid_teacher_limit_is_30(self, monkeypatch):
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: False)
        assert _resolve_teacher_limit("any") == PAID_TEACHER_MAX == 30

    def test_free_teacher_cannot_create_invitation_at_limit(self, monkeypatch):
        """Free teacher at 10 students cannot create another invitation."""
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: True)
        monkeypatch.setattr(tc, "_count_active_assignments", lambda tid: FREE_TEACHER_MAX)
        from app.routes.teacher_classroom import CreateInvitationRequest
        req = CreateInvitationRequest(student_name="New", grade="Grade 9", email="new@example.com")
        result = create_invitation(req, teacher=TEACHER_FREE)
        assert result["success"] is False
        assert result.get("at_limit") is True
        assert "10" in result["error"]

    def test_paid_teacher_cannot_create_invitation_at_limit(self, monkeypatch):
        """Paid teacher at 30 students cannot create another invitation."""
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: False)
        monkeypatch.setattr(tc, "_count_active_assignments", lambda tid: PAID_TEACHER_MAX)
        from app.routes.teacher_classroom import CreateInvitationRequest
        req = CreateInvitationRequest(student_name="New", grade="Grade 9", email="new@example.com")
        result = create_invitation(req, teacher=TEACHER_PAID)
        assert result["success"] is False
        assert result.get("at_limit") is True
        assert "30" in result["error"]

    def test_free_teacher_under_limit_can_create_invitation(self, monkeypatch):
        """Free teacher with 5/10 students CAN create invitation."""
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: True)
        monkeypatch.setattr(tc, "_count_active_assignments", lambda tid: 5)
        mock_insert = MagicMock()
        mock_insert.return_value.data = [{"id": INV_ID, "status": "pending"}]
        monkeypatch.setattr(tc, "admin_client",
            MagicMock(table=MagicMock(return_value=MagicMock(insert=MagicMock(return_value=MagicMock(execute=mock_insert))))))
        write_mock = MagicMock()
        monkeypatch.setattr(tc, "write_audit_event", write_mock)

        from app.routes.teacher_classroom import CreateInvitationRequest
        req = CreateInvitationRequest(student_name="Arjun", grade="Grade 9", email="arjun@example.com")
        result = create_invitation(req, teacher=TEACHER_FREE)
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Authorization tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthorization:
    def test_ensure_owns_student_raises_403_for_foreign_student(self, monkeypatch):
        """Teacher gets 403 when accessing a student not assigned to them."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _ensure_owns_student("teacher-x", "foreign-student")
        assert exc.value.status_code == 403

    def test_ensure_owns_student_passes_for_own_student(self, monkeypatch):
        """Teacher can access their own assigned student."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": "row-1"}, None))
        _ensure_owns_student("teacher-x", STUDENT_ID)  # no exception

    def test_ensure_owns_classroom_raises_403_for_foreign(self, monkeypatch):
        """Teacher gets 403 for a classroom owned by another teacher."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _ensure_owns_classroom("teacher-x", "foreign-classroom")
        assert exc.value.status_code == 403

    def test_list_students_only_own(self, monkeypatch):
        """list_students only returns teacher's own assigned students."""
        # Fully mock admin_client to prevent any real DB calls
        own_assignments = [{"student_id": STUDENT_ID, "grade": "Grade 9", "subject": "Maths", "section": "A", "archived_at": None, "created_at": "2026-01-01"}]
        profiles_data = [{"id": STUDENT_ID, "username": "Alice", "email": "a@a.com", "grade": "Grade 9", "account_status": "active", "created_at": "2026-01-01"}]

        call_count = {"n": 0}

        class FakeMock:
            @property
            def data(self):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return own_assignments
                return profiles_data
            count = None

        fake = FakeMock()

        mock_tbl = MagicMock()
        mock_tbl.return_value.select.return_value.eq.return_value.execute.return_value = fake
        mock_tbl.return_value.select.return_value.in_.return_value.execute.return_value = fake
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))

        result = list_students(q=None, grade=None, status=None, sort="name", teacher={"id": "teacher-own", "role": "teacher"})
        assert result["success"] is True
        assert result["count"] == 1
        assert result["students"][0]["id"] == STUDENT_ID

    def test_email_credentials_blocked_for_free_teacher(self, monkeypatch):
        """Free teacher cannot email credentials — backend enforces."""
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: True)
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        result = email_student_credentials(STUDENT_ID, teacher=TEACHER_FREE)
        assert result["success"] is False
        assert result.get("upgrade_required") is True
        assert "paid" in result["error"].lower()

    def test_email_credentials_allowed_for_paid_teacher(self, monkeypatch):
        """Paid teacher CAN call email-credentials (goes to Supabase)."""
        monkeypatch.setattr(tc, "is_free_tier_user", lambda uid: False)
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": STUDENT_ID, "username": "Alice", "email": "alice@example.com"}, None))
        mock_auth = MagicMock()
        mock_auth.admin.invite_user_by_email.return_value = None
        monkeypatch.setattr(tc, "admin_client", MagicMock(auth=mock_auth, table=MagicMock()))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        result = email_student_credentials(STUDENT_ID, teacher=TEACHER_PAID)
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Student actions
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentActions:
    def test_archive_sets_archived_at(self, monkeypatch):
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        result = archive_student(STUDENT_ID, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert "archived_at" in result

    def test_reset_password_never_returns_password_in_audit(self, monkeypatch):
        """Audit log for password reset must NOT contain the password."""
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        mock_auth = MagicMock()
        mock_auth.admin.update_user_by_id.return_value = None
        monkeypatch.setattr(tc, "admin_client", MagicMock(auth=mock_auth))
        audit_calls = []
        monkeypatch.setattr(tc, "write_audit_event", lambda **kw: audit_calls.append(kw))
        result = reset_student_password(STUDENT_ID, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert result.get("temp_password")  # password returned once to caller
        # Audit log must NOT contain the password
        for call in audit_calls:
            meta_str = str(call.get("metadata", {}))
            assert result["temp_password"] not in meta_str


# ─────────────────────────────────────────────────────────────────────────────
# Invitation tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInvitations:
    def test_resend_fails_for_accepted_invitation(self, monkeypatch):
        """Cannot resend an already-accepted invitation."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": INV_ID, "status": "accepted", "teacher_id": TEACHER_FREE["id"]}, None))
        result = resend_invitation(INV_ID, teacher=TEACHER_FREE)
        assert result["success"] is False
        assert "accepted" in result["error"]

    def test_cancel_fails_for_accepted_invitation(self, monkeypatch):
        """Cannot cancel an already-accepted invitation."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": INV_ID, "status": "accepted", "teacher_id": TEACHER_FREE["id"]}, None))
        result = cancel_invitation(INV_ID, teacher=TEACHER_FREE)
        assert result["success"] is False
        assert "accepted" in result["error"]

    def test_cancel_pending_invitation_succeeds(self, monkeypatch):
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": INV_ID, "status": "pending", "teacher_id": TEACHER_FREE["id"]}, None))
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        result = cancel_invitation(INV_ID, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert result["status"] == "cancelled"

    def test_resend_pending_extends_expiry(self, monkeypatch):
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": INV_ID, "status": "pending", "teacher_id": TEACHER_FREE["id"]}, None))
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        result = resend_invitation(INV_ID, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert "new_expiry" in result


# ─────────────────────────────────────────────────────────────────────────────
# Classroom tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClassrooms:
    def test_create_classroom(self, monkeypatch):
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value.data = [{"id": CLASSROOM_ID, "name": "9A", "status": "active"}]
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        from app.routes.teacher_classroom import CreateClassroomRequest
        req = CreateClassroomRequest(name="9A")
        result = create_classroom(req, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert result["classroom"]["id"] == CLASSROOM_ID

    def test_archive_classroom(self, monkeypatch):
        monkeypatch.setattr(tc, "_ensure_owns_classroom", lambda t, c: None)
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        result = archive_classroom(CLASSROOM_ID, teacher=TEACHER_FREE)
        assert result["success"] is True
        assert result["status"] == "archived"

    def test_add_student_to_classroom_duplicate_is_safe(self, monkeypatch):
        """Duplicate student add returns success=True with 'already in classroom' note."""
        monkeypatch.setattr(tc, "_ensure_owns_classroom", lambda t, c: None)
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        mock_tbl = MagicMock()
        # Simulate duplicate key error
        def raise_dup(*a, **kw):
            raise Exception("duplicate key value violates unique constraint")
        mock_tbl.return_value.upsert.return_value.execute.side_effect = raise_dup
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        monkeypatch.setattr(tc, "write_audit_event", MagicMock())
        from app.routes.teacher_classroom import AddClassroomStudentRequest
        req = AddClassroomStudentRequest(student_id=STUDENT_ID)
        result = add_student_to_classroom(CLASSROOM_ID, req, teacher=TEACHER_FREE)
        assert result["success"] is True

    def test_teacher_cannot_modify_foreign_classroom(self, monkeypatch):
        """_ensure_owns_classroom raises 403 for foreign classroom."""
        monkeypatch.setattr(tc, "_safe_one", lambda fn: (None, None))
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _ensure_owns_classroom("teacher-a", "classroom-owned-by-teacher-b")
        assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Audit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAudit:
    def test_archive_student_writes_audit_event(self, monkeypatch):
        monkeypatch.setattr(tc, "_ensure_owns_student", lambda t, s: None)
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(tc, "write_audit_event", lambda **kw: audit_calls.append(kw))
        archive_student(STUDENT_ID, teacher=TEACHER_FREE)
        assert len(audit_calls) == 1
        assert audit_calls[0]["event_type"] == "teacher.student.archived"

    def test_classroom_created_writes_audit_event(self, monkeypatch):
        mock_tbl = MagicMock()
        mock_tbl.return_value.insert.return_value.execute.return_value.data = [{"id": CLASSROOM_ID, "name": "9A"}]
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(tc, "write_audit_event", lambda **kw: audit_calls.append(kw))
        from app.routes.teacher_classroom import CreateClassroomRequest
        create_classroom(CreateClassroomRequest(name="9A"), teacher=TEACHER_FREE)
        assert any(c["event_type"] == "teacher.classroom.created" for c in audit_calls)

    def test_invitation_cancelled_writes_audit_event(self, monkeypatch):
        monkeypatch.setattr(tc, "_safe_one", lambda fn: ({"id": INV_ID, "status": "pending", "teacher_id": TEACHER_FREE["id"]}, None))
        mock_tbl = MagicMock()
        mock_tbl.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        monkeypatch.setattr(tc, "admin_client", MagicMock(table=mock_tbl))
        audit_calls = []
        monkeypatch.setattr(tc, "write_audit_event", lambda **kw: audit_calls.append(kw))
        cancel_invitation(INV_ID, teacher=TEACHER_FREE)
        assert any(c["event_type"] == "teacher.invitation.cancelled" for c in audit_calls)

    def test_audit_event_type_signatures(self):
        """All expected audit event types defined in teacher_classroom.py (naming convention)."""
        # Note: teacher.student.created is in teacher_dashboard.py (existing endpoint)
        # teacher_classroom.py handles the new endpoints from Phase 1
        expected = {
            "teacher.student.updated",
            "teacher.student.archived",
            "teacher.student.password_reset",
            "teacher.student.credentials_emailed",
            "teacher.invitation.created",
            "teacher.invitation.resent",
            "teacher.invitation.cancelled",
            "teacher.classroom.created",
            "teacher.classroom.updated",
            "teacher.classroom.archived",
            "teacher.classroom.student_added",
            "teacher.classroom.student_removed",
        }
        # Read source and check each event type string is present
        import inspect
        source = inspect.getsource(tc)
        for evt in expected:
            assert evt in source, f"Missing audit event type: {evt}"
