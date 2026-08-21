import pytest
from fastapi import HTTPException

import app.routes.admin_control as admin_control_route
import app.routes.teacher_dashboard as teacher_dashboard_route


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = []

    def select(self, value):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def in_(self, key, values):
        self.filters.append((key, tuple(values)))
        return self

    def order(self, column, desc=False):
        return self

    def execute(self):
        if self.table_name == "teacher_student_assignments":
            rows = self._filtered(self.client.assignments)
            return FakeResponse(rows)

        if self.table_name == "profiles":
            rows = self._filtered(self.client.profiles)
            return FakeResponse(rows)

        if self.table_name == "ai_usage_logs":
            rows = self._filtered(self.client.usage_logs)
            return FakeResponse(rows)

        if self.table_name == "student_progress":
            rows = self._filtered(self.client.progress_rows)
            return FakeResponse(rows)

        if self.table_name == "teacher_notes":
            if self.operation == "insert":
                row = {
                    "id": "note-created-1",
                    **self.payload,
                }
                self.client.notes.append(row)
                return FakeResponse([row])

            rows = self._filtered(self.client.notes)
            return FakeResponse(rows)

        return FakeResponse([])

    def _filtered(self, rows):
        filtered = rows

        for key, value in self.filters:
            if isinstance(value, tuple):
                filtered = [
                    row for row in filtered
                    if row.get(key) in value
                ]
            else:
                filtered = [
                    row for row in filtered
                    if row.get(key) == value
                ]

        return filtered


class FakeAdminClient:
    def __init__(self):
        self.assignments = [
            {
                "id": "assignment-1",
                "teacher_id": "teacher-1",
                "student_id": "student-1",
                "grade": "Grade 9",
                "subject": "Science",
                "section": "9A",
            }
        ]
        self.profiles = [
            {
                "id": "student-1",
                "username": "Akshita",
                "email": "akshita@example.com",
                "role": "student",
                "grade": "Grade 9",
            },
            {
                "id": "student-2",
                "username": "Rohan",
                "email": "rohan@example.com",
                "role": "student",
                "grade": "Grade 9",
            },
        ]
        self.usage_logs = [
            {
                "profile_id": "student-1",
                "username": "Akshita",
                "feature": "lesson",
                "total_tokens": 100,
                "estimated_cost": 0.01,
                "created_at": "2026-06-04T10:00:00+00:00",
            },
            {
                "profile_id": "student-2",
                "username": "Rohan",
                "feature": "lesson",
                "total_tokens": 999,
                "estimated_cost": 0.09,
                "created_at": "2026-06-04T10:00:00+00:00",
            },
        ]
        self.progress_rows = [
            {
                "profile_id": "student-1",
                "username": "Akshita",
                "subject": "Science",
                "chapter": "Motion",
                "current_step_index": 2,
                "completed": True,
                "updated_at": "2026-06-04T11:00:00+00:00",
            }
        ]
        self.notes = []

    def table(self, table_name):
        return FakeTable(self, table_name)


def fake_teacher():
    """Return the dependency payload used by teacher dashboard routes."""
    return {
        "profile": {
            "id": "teacher-1",
            "email": "teacher@example.com",
            "username": "Science Teacher",
            "role": "teacher",
        }
    }


def test_teacher_summary_is_scoped_to_assigned_students(monkeypatch):
    """
    Teacher dashboard should show only assigned students and their activity.

    Source under test:
        backend/app/routes/teacher_dashboard.py
        get_teacher_summary()
    """
    fake_client = FakeAdminClient()
    monkeypatch.setattr(teacher_dashboard_route, "admin_client", fake_client)
    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    result = teacher_dashboard_route.get_teacher_summary(
        teacher=fake_teacher(),
    )

    assert result["success"] is True
    assert result["summary"]["assigned_students"] == 1
    assert result["students"][0]["profile"]["username"] == "Akshita"
    assert result["students"][0]["activity"]["tokens_total"] == 100
    assert result["students"][0]["progress_summary"]["completed_chapters"] == 1


def test_teacher_note_requires_assigned_student(monkeypatch):
    """
    Teachers should not be able to write notes for unassigned students.

    Source under test:
        backend/app/routes/teacher_dashboard.py
        create_teacher_note()
    """
    fake_client = FakeAdminClient()
    monkeypatch.setattr(teacher_dashboard_route, "admin_client", fake_client)

    request = teacher_dashboard_route.TeacherNoteRequest(
        student_id="student-2",
        subject="Science",
        chapter="Motion",
        note="Needs revision.",
    )

    with pytest.raises(HTTPException) as error:
        teacher_dashboard_route.create_teacher_note(
            request,
            teacher=fake_teacher(),
        )

    assert error.value.status_code == 403
    assert error.value.detail == "Student is not assigned to this teacher."
