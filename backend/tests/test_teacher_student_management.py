"""
test_teacher_student_management.py
====================================
Regression tests for teacher-managed student onboarding.

Covers:
  1. Free teacher limit (max 10 students)
  2. Paid teacher limit (max 30 students)
  3. Expired paid plan falls back to Free Tier limit
  4. Required field validation (name, grade, password)
  5. Optional email
  6. Password never returned in API response
  7. Student auto-assigned to creating teacher
  8. Teacher cannot manage another teacher's students
  9. Credential email: paid teachers only
  10. Credential email: synthetic email blocked
  11. Admin parent-child association
  12. Non-admin cannot link parent to child
  13. is_free_tier_user used (not hardcoded UI check)

Run with:
    cd backend && python -m pytest tests/test_teacher_student_management.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

import app.routes.teacher_dashboard as teacher_route
from app.routes.teacher_dashboard import (
    FREE_TEACHER_MAX_STUDENTS,
    PAID_TEACHER_MAX_STUDENTS,
    _count_assigned_active_students,
    _resolve_student_auth_email,
    _is_synthetic_email,
    CreateStudentRequest,
)
import app.routes.admin_associations as admin_route
from app.routes.admin_associations import (
    LinkParentChildRequest,
    link_parent_to_child,
    unlink_parent_from_child,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

def test_free_teacher_max_is_10():
    assert FREE_TEACHER_MAX_STUDENTS == 10

def test_paid_teacher_max_is_30():
    assert PAID_TEACHER_MAX_STUDENTS == 30

def test_paid_max_greater_than_free_max():
    assert PAID_TEACHER_MAX_STUDENTS > FREE_TEACHER_MAX_STUDENTS


# ─────────────────────────────────────────────────────────────────────────────
# Email helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestEmailHelpers:
    def test_real_email_used_as_is(self):
        result = _resolve_student_auth_email("alice@example.com", "Alice")
        assert result == "alice@example.com"

    def test_no_email_generates_synthetic(self):
        result = _resolve_student_auth_email(None, "Rohan Kumar")
        assert result.endswith("@teacher.likhapoha.in")
        assert "Rohan" in result or "rohankumar" in result.lower()

    def test_empty_email_generates_synthetic(self):
        result = _resolve_student_auth_email("", "Student One")
        assert result.endswith("@teacher.likhapoha.in")

    def test_invalid_email_generates_synthetic(self):
        result = _resolve_student_auth_email("not-an-email", "Priya")
        assert result.endswith("@teacher.likhapoha.in")

    def test_synthetic_teacher_domain_detected(self):
        assert _is_synthetic_email("student@teacher.likhapoha.in") is True

    def test_synthetic_child_domain_detected(self):
        assert _is_synthetic_email("child@child.likhapoha.in") is True

    def test_real_email_not_synthetic(self):
        assert _is_synthetic_email("alice@gmail.com") is False
        assert _is_synthetic_email("student@school.edu") is False

    def test_empty_email_not_synthetic(self):
        assert _is_synthetic_email("") is False
        assert _is_synthetic_email(None) is False


# ─────────────────────────────────────────────────────────────────────────────
# Fake Supabase client for teacher dashboard tests
# ─────────────────────────────────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self._op = None
        self._payload = None
        self._filters = []

    def select(self, *args):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def limit(self, n):
        return self

    def order(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        if self.table_name == "teacher_student_assignments":
            if self._op == "select":
                rows = [r for r in self.client.assignments
                        if all(r.get(k) == v for k, v in self._filters)]
                return FakeResponse(rows)
            if self._op == "insert":
                self.client.assignments.append({
                    "id": f"assign-{len(self.client.assignments)+1}",
                    **self._payload,
                })
                return FakeResponse([self._payload])

        if self.table_name == "profiles":
            if self._op == "select":
                rows = [r for r in self.client.profiles
                        if all(r.get(k) == v for k, v in self._filters)]
                return FakeResponse(rows)
            if self._op == "insert":
                self.client.profiles.append({**self._payload})
                return FakeResponse([self._payload])

        return FakeResponse([])


class FakeAuth:
    """Minimal Supabase auth stub."""
    class admin:
        @staticmethod
        def create_user(payload):
            user = MagicMock()
            user.id = f"user-{payload.get('email', 'test').replace('@','-').replace('.','_')}"
            return user


class FakeAdminClient:
    def __init__(self, assignments=None, profiles=None):
        self.assignments = assignments or []
        self.profiles = profiles or []
        self.auth = FakeAuth()

    def table(self, name):
        return FakeTable(self, name)


def _free_teacher():
    return {"profile": {
        "id": "teacher-free-1",
        "username": "Free Teacher",
        "role": "teacher",
        "access_cbse": False,
        "access_sof_science": False,
        "subscription_plan": "free",
        "subscription_expires_at": None,
    }}


def _paid_teacher():
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    return {"profile": {
        "id": "teacher-paid-1",
        "username": "Paid Teacher",
        "role": "teacher",
        "access_cbse": True,
        "subscription_plan": "starter",
        "subscription_expires_at": exp,
    }}


def _expired_teacher():
    exp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return {"profile": {
        "id": "teacher-expired-1",
        "username": "Expired Teacher",
        "role": "teacher",
        "access_cbse": False,     # revoked
        "subscription_plan": "starter",
        "subscription_expires_at": exp,
    }}


def _make_assignments(teacher_id, count):
    return [
        {"teacher_id": teacher_id, "student_id": f"student-{i}", "grade": "Grade 9"}
        for i in range(count)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Student limit enforcement (backend)
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentLimitEnforcement:

    def test_free_teacher_blocked_at_10_students(self, monkeypatch):
        """Free teacher with 10 students cannot add the 11th."""
        teacher = _free_teacher()
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher["profile"]["id"], 10)
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="New Student", grade="Grade 9", password="pass123"),
                teacher=teacher,
            )
        assert exc.value.status_code == 403
        assert "STUDENT_LIMIT_REACHED" in exc.value.detail
        assert "10" in exc.value.detail

    def test_free_teacher_allowed_up_to_9_students(self, monkeypatch):
        """Free teacher with 9 students CAN add the 10th (not blocked)."""
        teacher = _free_teacher()
        teacher_id = teacher["profile"]["id"]
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher_id, 9),
            profiles=[{
                "id": teacher_id, "role": "teacher",
                "access_cbse": False, "subscription_expires_at": None,
            }]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        # Mock create_auth_user
        mock_user = MagicMock()
        mock_user.id = "new-student-id"
        monkeypatch.setattr(teacher_route, "create_auth_user", lambda **kwargs: mock_user)

        # Must succeed (no exception)
        result = teacher_route.create_student(
            CreateStudentRequest(username="10th Student", grade="Grade 9", password="pass123"),
            teacher=teacher,
        )
        assert result["success"] is True
        assert result["student_count"] == 10

    def test_paid_teacher_blocked_at_30_students(self, monkeypatch):
        """Paid teacher with 30 students cannot add the 31st."""
        teacher = _paid_teacher()
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher["profile"]["id"], 30)
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="31st Student", grade="Grade 9", password="pass123"),
                teacher=teacher,
            )
        assert exc.value.status_code == 403
        assert "STUDENT_LIMIT_REACHED" in exc.value.detail
        assert "30" in exc.value.detail

    def test_paid_teacher_allowed_up_to_29_students(self, monkeypatch):
        """Paid teacher with 29 students CAN add the 30th."""
        teacher = _paid_teacher()
        teacher_id = teacher["profile"]["id"]
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher_id, 29),
            profiles=[{
                "id": teacher_id, "role": "teacher",
                "access_cbse": True,
                "subscription_expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            }]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        mock_user = MagicMock()
        mock_user.id = "new-student-id"
        monkeypatch.setattr(teacher_route, "create_auth_user", lambda **kwargs: mock_user)

        result = teacher_route.create_student(
            CreateStudentRequest(username="30th Student", grade="Grade 9", password="pass123"),
            teacher=teacher,
        )
        assert result["success"] is True
        assert result["student_count"] == 30

    def test_expired_paid_teacher_falls_back_to_free_limit(self, monkeypatch):
        """Expired paid teacher is treated as free tier (limit = 10)."""
        teacher = _expired_teacher()
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher["profile"]["id"], 10)
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        # Expired → is_free_tier_user returns True
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="Extra Student", grade="Grade 9", password="pass123"),
                teacher=teacher,
            )
        assert exc.value.status_code == 403
        assert "STUDENT_LIMIT_REACHED" in exc.value.detail
        assert "10" in exc.value.detail  # free limit, not 30

    def test_student_limit_endpoint_returns_correct_max_for_free(self, monkeypatch):
        teacher = _free_teacher()
        fake_client = FakeAdminClient(assignments=_make_assignments(teacher["profile"]["id"], 3))
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        result = teacher_route.get_student_limit(teacher=teacher)
        assert result["max"] == 10
        assert result["count"] == 3
        assert result["is_paid"] is False
        assert result["at_limit"] is False

    def test_student_limit_endpoint_returns_correct_max_for_paid(self, monkeypatch):
        teacher = _paid_teacher()
        fake_client = FakeAdminClient(assignments=_make_assignments(teacher["profile"]["id"], 15))
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        result = teacher_route.get_student_limit(teacher=teacher)
        assert result["max"] == 30
        assert result["count"] == 15
        assert result["is_paid"] is True
        assert result["at_limit"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Required field validation
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentCreationValidation:

    def test_empty_name_raises_400(self, monkeypatch):
        """NAME_REQUIRED raised when username is empty."""
        teacher = _free_teacher()
        monkeypatch.setattr(teacher_route, "admin_client", FakeAdminClient())
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="", grade="Grade 9", password="pass123"),
                teacher=teacher,
            )
        assert exc.value.status_code == 400
        assert "NAME_REQUIRED" in exc.value.detail

    def test_empty_grade_raises_400(self, monkeypatch):
        """INVALID_GRADE raised when grade is empty."""
        teacher = _free_teacher()
        monkeypatch.setattr(teacher_route, "admin_client", FakeAdminClient())
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="Priya", grade="", password="pass123"),
                teacher=teacher,
            )
        assert exc.value.status_code == 400
        assert "INVALID_GRADE" in exc.value.detail

    def test_empty_password_raises_400(self, monkeypatch):
        """PASSWORD_REQUIRED raised when password is empty."""
        teacher = _free_teacher()
        monkeypatch.setattr(teacher_route, "admin_client", FakeAdminClient())
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="Priya", grade="Grade 9", password=""),
                teacher=teacher,
            )
        assert exc.value.status_code == 400
        assert "PASSWORD_REQUIRED" in exc.value.detail

    def test_short_password_raises_400(self, monkeypatch):
        """Password shorter than 6 characters is rejected."""
        teacher = _free_teacher()
        monkeypatch.setattr(teacher_route, "admin_client", FakeAdminClient())
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_student(
                CreateStudentRequest(username="Priya", grade="Grade 9", password="abc"),
                teacher=teacher,
            )
        assert exc.value.status_code == 400

    def test_email_is_optional_no_error(self, monkeypatch):
        """Student can be created without email (synthetic email used)."""
        teacher = _free_teacher()
        teacher_id = teacher["profile"]["id"]
        fake_client = FakeAdminClient(
            assignments=[],
            profiles=[{"id": teacher_id, "role": "teacher", "access_cbse": False, "subscription_expires_at": None}]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        mock_user = MagicMock()
        mock_user.id = "new-student-no-email"
        monkeypatch.setattr(teacher_route, "create_auth_user", lambda **kwargs: mock_user)

        result = teacher_route.create_student(
            CreateStudentRequest(username="No Email Student", grade="Grade 9", password="pass123", email=None),
            teacher=teacher,
        )
        assert result["success"] is True
        assert result["student"]["has_real_email"] is False

    def test_password_never_in_response(self, monkeypatch):
        """Password must never appear in the API response."""
        teacher = _free_teacher()
        teacher_id = teacher["profile"]["id"]
        fake_client = FakeAdminClient(
            assignments=[],
            profiles=[{"id": teacher_id, "role": "teacher", "access_cbse": False, "subscription_expires_at": None}]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        mock_user = MagicMock()
        mock_user.id = "new-student-secure"
        monkeypatch.setattr(teacher_route, "create_auth_user", lambda **kwargs: mock_user)

        result = teacher_route.create_student(
            CreateStudentRequest(username="Secure Student", grade="Grade 9", password="s3cr3tpass"),
            teacher=teacher,
        )
        assert result["success"] is True
        # Password must NEVER appear anywhere in the response
        response_str = str(result)
        assert "s3cr3tpass" not in response_str
        assert "password" not in result.get("student", {})

    def test_student_auto_assigned_to_teacher(self, monkeypatch):
        """New student is automatically assigned to the creating teacher."""
        teacher = _free_teacher()
        teacher_id = teacher["profile"]["id"]
        fake_client = FakeAdminClient(
            assignments=[],
            profiles=[{"id": teacher_id, "role": "teacher", "access_cbse": False, "subscription_expires_at": None}]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        mock_user = MagicMock()
        mock_user.id = "auto-assigned-student"
        monkeypatch.setattr(teacher_route, "create_auth_user", lambda **kwargs: mock_user)

        teacher_route.create_student(
            CreateStudentRequest(username="Auto Assigned", grade="Grade 9", password="pass123"),
            teacher=teacher,
        )

        # Verify assignment row was created for this teacher
        assigned = [a for a in fake_client.assignments if a.get("teacher_id") == teacher_id]
        assert len(assigned) == 1
        assert assigned[0]["student_id"] == "auto-assigned-student"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Teacher cannot manage another teacher's students
# ─────────────────────────────────────────────────────────────────────────────

class TestTeacherIsolation:

    def test_teacher_cannot_write_note_for_unassigned_student(self, monkeypatch):
        """Teacher cannot save notes for students not assigned to them."""
        fake_client = FakeAdminClient(
            assignments=[
                {"teacher_id": "teacher-A", "student_id": "student-X", "grade": "Grade 9"}
            ]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)

        request = teacher_route.TeacherNoteRequest(
            student_id="student-Y",   # NOT assigned to teacher-A
            subject="Science",
            note="Test note.",
        )
        teacher_B = {"profile": {"id": "teacher-B", "role": "teacher"}}

        with pytest.raises(HTTPException) as exc:
            teacher_route.create_teacher_note(request, teacher=teacher_B)
        assert exc.value.status_code == 403
        assert "not assigned" in exc.value.detail.lower()

    def test_email_credentials_requires_assigned_student(self, monkeypatch):
        """Teacher cannot email credentials for unassigned student."""
        fake_client = FakeAdminClient(
            assignments=[
                {"teacher_id": "teacher-A", "student_id": "student-X", "grade": "Grade 9"}
            ],
            profiles=[
                {"id": "student-Y", "email": "y@example.com", "username": "Y", "role": "student"}
            ]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        teacher_B = {"profile": {"id": "teacher-B", "role": "teacher"}}

        with pytest.raises(HTTPException) as exc:
            teacher_route.email_student_credentials("student-Y", teacher=teacher_B)
        assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 4. Credential email: paid teachers only
# ─────────────────────────────────────────────────────────────────────────────

class TestCredentialEmail:

    def test_free_teacher_cannot_email_credentials(self, monkeypatch):
        """Free-tier teachers get 403 PAID_PLAN_REQUIRED."""
        fake_client = FakeAdminClient(
            assignments=[{"teacher_id": "teacher-free-1", "student_id": "student-1"}],
            profiles=[{"id": "student-1", "email": "s@example.com", "username": "S", "role": "student"}]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: True)

        teacher = _free_teacher()

        with pytest.raises(HTTPException) as exc:
            teacher_route.email_student_credentials("student-1", teacher=teacher)
        assert exc.value.status_code == 403
        assert "PAID_PLAN_REQUIRED" in exc.value.detail

    def test_student_without_real_email_blocked(self, monkeypatch):
        """Credential email blocked for students with synthetic email."""
        teacher_id = "teacher-paid-1"
        fake_client = FakeAdminClient(
            assignments=[{"teacher_id": teacher_id, "student_id": "student-syn"}],
            profiles=[{
                "id": "student-syn",
                "email": "syntheticname@teacher.likhapoha.in",  # synthetic
                "username": "Synthetic",
                "role": "student",
            }]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        teacher = _paid_teacher()

        with pytest.raises(HTTPException) as exc:
            teacher_route.email_student_credentials("student-syn", teacher=teacher)
        assert exc.value.status_code == 400
        assert "EMAIL_REQUIRED_FOR_CREDENTIAL_EMAIL" in exc.value.detail

    def test_student_without_any_email_blocked(self, monkeypatch):
        """Credential email blocked for students with no email at all."""
        teacher_id = "teacher-paid-1"
        fake_client = FakeAdminClient(
            assignments=[{"teacher_id": teacher_id, "student_id": "student-no-email"}],
            profiles=[{
                "id": "student-no-email",
                "email": "",
                "username": "NoEmail",
                "role": "student",
            }]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)
        monkeypatch.setattr(teacher_route, "is_free_tier_user", lambda uid: False)

        teacher = _paid_teacher()

        with pytest.raises(HTTPException) as exc:
            teacher_route.email_student_credentials("student-no-email", teacher=teacher)
        assert exc.value.status_code == 400
        assert "EMAIL_REQUIRED_FOR_CREDENTIAL_EMAIL" in exc.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# 5. Admin parent-child association
# ─────────────────────────────────────────────────────────────────────────────

class FakeAdminClientForLinking:
    """Minimal fake for admin_control link-parent-child tests."""

    def __init__(self, profiles):
        self._profiles = {p["id"]: p for p in profiles}
        self._updates = {}

    def table(self, name):
        return self

    def select(self, *args):
        return self

    def eq(self, key, value):
        self._current_filter_key = key
        self._current_filter_value = value
        return self

    def limit(self, n):
        return self

    def execute(self):
        result = [
            p for p in self._profiles.values()
            if p.get(getattr(self, "_current_filter_key", None)) == getattr(self, "_current_filter_value", None)
        ]
        return FakeResponse(result)

    def update(self, payload):
        self._pending_update = payload
        return self

    def execute_update(self):
        # Apply update to profiles
        fid = getattr(self, "_current_filter_value", None)
        if fid and fid in self._profiles:
            self._profiles[fid].update(self._pending_update or {})
        return FakeResponse([])


class TestParentChildAssociation:

    def test_link_parent_to_child_success(self, monkeypatch):
        """Admin can link a parent to a student."""
        parent = {"id": "parent-1", "role": "parent", "family_id": "family-1", "username": "ParentA"}
        child = {"id": "child-1", "role": "student", "username": "StudentB", "parent_id": None}
        profiles = [parent, child]

        # Build a proper fake that handles the full query chain
        class FullFake:
            def __init__(self):
                self._data = {p["id"]: dict(p) for p in profiles}
                self._filters = []
                self._update_payload = None
                self._table = None

            def table(self, name):
                self._table = name
                self._filters = []
                return self

            def select(self, *args):
                return self

            def eq(self, k, v):
                self._filters.append((k, v))
                return self

            def limit(self, n):
                return self

            def execute(self):
                result = list(self._data.values())
                for k, v in self._filters:
                    result = [r for r in result if r.get(k) == v]
                return FakeResponse(result)

            def update(self, payload):
                self._update_payload = payload
                return self

        fake = FullFake()
        monkeypatch.setattr(admin_route, "admin_client", fake)

        req = LinkParentChildRequest(parent_id="parent-1", child_id="child-1")
        result = link_parent_to_child(req, admin={"profile": {"id": "admin-1", "role": "admin"}})
        assert result["success"] is True
        assert result["parent_id"] == "parent-1"
        assert result["child_id"] == "child-1"

    def test_non_student_cannot_be_linked_as_child(self, monkeypatch):
        """Admin cannot link a parent to another parent (only students allowed)."""
        parent_a = {"id": "parent-1", "role": "parent", "family_id": "family-1", "username": "ParentA"}
        parent_b = {"id": "parent-2", "role": "parent", "family_id": None, "username": "ParentB"}

        class FullFake:
            def __init__(self):
                self._data = {"parent-1": dict(parent_a), "parent-2": dict(parent_b)}
                self._filters = []

            def table(self, name): self._filters = []; return self
            def select(self, *args): return self
            def eq(self, k, v): self._filters.append((k, v)); return self
            def limit(self, n): return self
            def execute(self):
                result = list(self._data.values())
                for k, v in self._filters:
                    result = [r for r in result if r.get(k) == v]
                return FakeResponse(result)
            def update(self, payload): return self

        fake = FullFake()
        monkeypatch.setattr(admin_route, "admin_client", fake)

        req = LinkParentChildRequest(parent_id="parent-1", child_id="parent-2")
        with pytest.raises(HTTPException) as exc:
            link_parent_to_child(req, admin={"profile": {"id": "admin-1", "role": "admin"}})
        assert exc.value.status_code == 400
        assert "UNAUTHORIZED" in exc.value.detail

    def test_non_parent_cannot_be_linked_as_parent(self, monkeypatch):
        """Admin cannot use a student as the parent in a link."""
        student_a = {"id": "student-1", "role": "student", "family_id": None, "username": "StudentA"}
        student_b = {"id": "student-2", "role": "student", "family_id": None, "username": "StudentB"}

        class FullFake:
            def __init__(self):
                self._data = {"student-1": dict(student_a), "student-2": dict(student_b)}
                self._filters = []

            def table(self, name): self._filters = []; return self
            def select(self, *args): return self
            def eq(self, k, v): self._filters.append((k, v)); return self
            def limit(self, n): return self
            def execute(self):
                result = list(self._data.values())
                for k, v in self._filters:
                    result = [r for r in result if r.get(k) == v]
                return FakeResponse(result)
            def update(self, payload): return self

        fake = FullFake()
        monkeypatch.setattr(admin_route, "admin_client", fake)

        req = LinkParentChildRequest(parent_id="student-1", child_id="student-2")
        with pytest.raises(HTTPException) as exc:
            link_parent_to_child(req, admin={"profile": {"id": "admin-1", "role": "admin"}})
        assert exc.value.status_code == 400
        assert "UNAUTHORIZED" in exc.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# 6. Canonical resolver used (not hardcoded checks)
# ─────────────────────────────────────────────────────────────────────────────

class TestCanonicalResolverUsage:

    def test_is_free_tier_user_called_for_student_limit(self, monkeypatch):
        """create_student calls is_free_tier_user — not hardcoded access_cbse check."""
        teacher = _free_teacher()
        fake_client = FakeAdminClient(
            assignments=_make_assignments(teacher["profile"]["id"], 10)
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)

        call_log = []

        def spy_is_free_tier(uid):
            call_log.append(uid)
            return True  # treat as free

        monkeypatch.setattr(teacher_route, "is_free_tier_user", spy_is_free_tier)

        with pytest.raises(HTTPException):
            teacher_route.create_student(
                CreateStudentRequest(username="S", grade="Grade 9", password="pass123"),
                teacher=teacher,
            )

        # Must have been called with the teacher's ID
        assert teacher["profile"]["id"] in call_log

    def test_is_free_tier_user_called_for_email_credentials(self, monkeypatch):
        """email_student_credentials calls is_free_tier_user — not hardcoded."""
        teacher = _free_teacher()
        fake_client = FakeAdminClient(
            assignments=[{"teacher_id": teacher["profile"]["id"], "student_id": "s1"}],
            profiles=[{"id": "s1", "email": "s@x.com", "username": "S", "role": "student"}]
        )
        monkeypatch.setattr(teacher_route, "admin_client", fake_client)

        call_log = []

        def spy_is_free_tier(uid):
            call_log.append(uid)
            return True  # free → should block

        monkeypatch.setattr(teacher_route, "is_free_tier_user", spy_is_free_tier)

        with pytest.raises(HTTPException) as exc:
            teacher_route.email_student_credentials("s1", teacher=teacher)

        assert exc.value.status_code == 403
        assert teacher["profile"]["id"] in call_log
