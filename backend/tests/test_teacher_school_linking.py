"""
test_teacher_school_linking.py
─────────────────────────────────────────────────────────────────────────────
Regression coverage for the one existing endpoint this feature modifies:
teacher_dashboard.create_student() now silently inherits the creating
teacher's school_id, if any.

The critical guarantee under test: this must be safe to deploy BEFORE the
20260828_principal_school_support.sql migration runs. If the `school_id`
column doesn't exist yet, _get_teacher_school_link() must swallow the error
and create_student's insert payload must come out byte-for-byte identical
to how it looked before this feature existed — no 500, no missing student.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import app.routes.teacher_dashboard as teacher_dashboard_route
from app.routes.teacher_dashboard import CreateStudentRequest


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    """Supports the exact chain shapes create_student and _get_teacher_school_link use."""

    def __init__(self, client, table_name, school_id_column_exists):
        self.client = client
        self.table_name = table_name
        self.school_id_column_exists = school_id_column_exists
        self._op = None
        self._payload = None
        self._filters = []

    def select(self, columns):
        if (
            self.table_name == "profiles"
            and "school_id" in columns
            and not self.school_id_column_exists
        ):
            raise Exception(
                "Could not find the 'school_id' column of 'profiles' in the schema cache"
            )
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def ilike(self, key, value):
        self._filters.append((key, value))
        return self

    def limit(self, _n):
        return self

    def order(self, *_a, **_k):
        return self

    def _row_matches(self, row):
        return all(row.get(k) == v for k, v in self._filters)

    def execute(self):
        if self.table_name == "teacher_student_assignments":
            if self._op == "insert":
                self.client.assignments.append({"id": "assign-new", **self._payload})
                return FakeResponse([self._payload])
            return FakeResponse([r for r in self.client.assignments if self._row_matches(r)])

        if self.table_name == "profiles":
            if self._op == "insert":
                self.client.profiles.append({**self._payload})
                return FakeResponse([self._payload])
            return FakeResponse([r for r in self.client.profiles if self._row_matches(r)])

        return FakeResponse([])


class FakeAuth:
    class admin:
        @staticmethod
        def create_user(payload):
            user = MagicMock()
            user.id = f"user-{payload.get('email', 'test')}"
            return user


class FakeAdminClient:
    def __init__(self, profiles, school_id_column_exists):
        self.profiles = profiles
        self.assignments = []
        self.auth = FakeAuth()
        self.school_id_column_exists = school_id_column_exists

    def table(self, name):
        return FakeTable(self, name, self.school_id_column_exists)


def _paid_teacher(teacher_id="teacher-1"):
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    return {"profile": {
        "id": teacher_id,
        "username": "Meena Sharma",
        "role": "teacher",
        "access_cbse": True,
        "subscription_plan": "starter",
        "subscription_expires_at": exp,
    }}


def _create(monkeypatch, teacher_profile_row, school_id_column_exists):
    client = FakeAdminClient(profiles=[teacher_profile_row], school_id_column_exists=school_id_column_exists)
    monkeypatch.setattr(teacher_dashboard_route, "admin_client", client)
    monkeypatch.setattr(teacher_dashboard_route, "is_free_tier_user", lambda uid: False)

    mock_user = MagicMock()
    mock_user.id = "new-student-auth-id"
    monkeypatch.setattr(teacher_dashboard_route, "create_auth_user", lambda **kwargs: mock_user)

    result = teacher_dashboard_route.create_student(
        CreateStudentRequest(username="New Student", grade="Grade 9", password="temp1234"),
        teacher=_paid_teacher(teacher_profile_row["id"]),
    )
    inserted_student = client.profiles[-1]
    return result, inserted_student


class TestSchoolLinkingIsSafeBeforeMigration:

    def test_column_missing_omits_school_id_entirely(self, monkeypatch):
        """
        No 'school_id' column yet (migration not run) → the insert payload
        must have NO school_id key at all — identical to pre-feature behavior.
        """
        teacher_row = {"id": "teacher-1", "role": "teacher"}  # no school_id column
        result, inserted_student = _create(monkeypatch, teacher_row, school_id_column_exists=False)

        assert result["success"] is True
        assert "school_id" not in inserted_student

    def test_column_missing_does_not_raise(self, monkeypatch):
        """The whole point of the guard: a missing column must never 500 create-student."""
        teacher_row = {"id": "teacher-1", "role": "teacher"}
        try:
            _create(monkeypatch, teacher_row, school_id_column_exists=False)
        except HTTPException:
            pytest.fail("create_student must not raise when the school_id column is missing")


class TestSchoolLinkingWorksAfterMigration:

    def test_student_inherits_linked_teacher_school_id(self, monkeypatch):
        teacher_row = {"id": "teacher-1", "role": "teacher", "school_id": "school-1"}
        _result, inserted_student = _create(monkeypatch, teacher_row, school_id_column_exists=True)
        assert inserted_student["school_id"] == "school-1"

    def test_unlinked_teacher_creates_unlinked_student(self, monkeypatch):
        """Column exists, but this teacher has no school — student.school_id is None, not omitted."""
        teacher_row = {"id": "teacher-1", "role": "teacher", "school_id": None}
        _result, inserted_student = _create(monkeypatch, teacher_row, school_id_column_exists=True)
        assert inserted_student["school_id"] is None
