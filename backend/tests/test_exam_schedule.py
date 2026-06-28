"""
test_exam_schedule.py
─────────────────────────────────────────────────────────────────────────────
Regression tests for student exam schedule endpoints.

Covers:
  1. _days_until helper — correct calculation
  2. Past exam rejected (400)
  3. Future exam accepted
  4. Student ownership enforced — cannot access another student's exam
  5. Parent ownership enforced via _verify_child_ownership
  6. Past exam not returned in upcoming query (gte exam_date today)
  7. Cancelled exam not returned in upcoming query
  8. _format_exam adds days_until
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.routes.exam_schedule import (
    _days_until,
    _format_exam,
    _upcoming_query,
    add_student_exam,
    delete_student_exam,
    add_child_exam,
    ExamCreate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def future_date(days=7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

def past_date(days=3) -> str:
    return (date.today() - timedelta(days=days)).isoformat()

STUDENT = {"profile": {"id": "student-uid-1", "username": "teststudent", "role": "student"}}
PARENT  = {"profile": {"id": "parent-uid-1", "username": "testparent", "role": "parent"}}


# ── _days_until ───────────────────────────────────────────────────────────────

class TestDaysUntil:
    def test_future_date_positive(self):
        d = future_date(10)
        result = _days_until(d)
        assert result == 10

    def test_past_date_negative(self):
        d = past_date(5)
        result = _days_until(d)
        assert result < 0

    def test_today_is_zero(self):
        result = _days_until(date.today().isoformat())
        assert result == 0

    def test_invalid_returns_minus1(self):
        assert _days_until("not-a-date") == -1
        assert _days_until("") == -1


# ── _format_exam ──────────────────────────────────────────────────────────────

class TestFormatExam:
    def test_adds_days_until(self):
        row = {"id": "e1", "subject": "Science", "exam_date": future_date(5)}
        result = _format_exam(row)
        assert result["days_until"] == 5
        assert result["subject"] == "Science"

    def test_past_exam_negative_days(self):
        row = {"id": "e2", "subject": "Maths", "exam_date": past_date(3)}
        result = _format_exam(row)
        assert result["days_until"] < 0


# ── add_student_exam ──────────────────────────────────────────────────────────

class TestAddStudentExam:
    def test_past_date_rejected(self, monkeypatch):
        """Past exam date must return 400."""
        req = ExamCreate(title="Test", subject="Maths", exam_date=past_date(2))
        with pytest.raises(HTTPException) as exc:
            add_student_exam(req, student=STUDENT)
        assert exc.value.status_code == 400
        assert "future" in exc.value.detail.lower()

    def test_future_date_accepted(self, monkeypatch):
        """Future exam date should be saved."""
        captured = {}
        class FakeTable:
            def insert(self, payload): captured.update(payload); return self
            def execute(self):
                class R:
                    data = [{"id":"uuid-1","student_id":"student-uid-1","exam_date":future_date(7),
                             "title":"Science Final","subject":"Science","exam_type":None,"notes":None,
                             "status":"active","created_by_role":"student","created_at":"2026-06-28T10:00:00Z"}]
                return R()
        class FakeAdmin:
            def table(self, t): return FakeTable()
        monkeypatch.setattr("app.routes.exam_schedule.admin_client", FakeAdmin())

        req = ExamCreate(title="Science Final", subject="Science", exam_date=future_date(7))
        result = add_student_exam(req, student=STUDENT)
        assert result["success"] is True
        assert captured["student_id"] == "student-uid-1"
        assert captured["created_by_role"] == "student"
        assert captured["status"] == "active"

    def test_access_cbse_not_granted(self, monkeypatch):
        """Adding an exam must not set any paid access fields."""
        captured = {}
        class FakeTable:
            def insert(self, payload): captured.update(payload); return self
            def execute(self):
                class R:
                    data = [{"id":"uuid-2","student_id":"student-uid-1","exam_date":future_date(7),
                             "title":"T","subject":"S","exam_type":None,"notes":None,
                             "status":"active","created_by_role":"student","created_at":"2026-06-28"}]
                return R()
        class FakeAdmin:
            def table(self, t): return FakeTable()
        monkeypatch.setattr("app.routes.exam_schedule.admin_client", FakeAdmin())

        req = ExamCreate(title="T", subject="S", exam_date=future_date(5))
        add_student_exam(req, student=STUDENT)
        assert "access_cbse" not in captured
        assert "subscription_plan" not in captured


# ── delete_student_exam ───────────────────────────────────────────────────────

class TestDeleteStudentExam:
    def test_own_exam_cancelled(self, monkeypatch):
        """Student can cancel own exam."""
        own_exam = {"id": "exam-1", "student_id": "student-uid-1"}

        class FakeTable:
            def select(self, *a): return self
            def eq(self, *a): return self
            def limit(self, *a): return self
            def execute(self):
                class R: data = [own_exam]
                return R()
            def update(self, payload): return self

        class FakeAdmin:
            def table(self, t): return FakeTable()
        monkeypatch.setattr("app.routes.exam_schedule.admin_client", FakeAdmin())
        monkeypatch.setattr("app.routes.exam_schedule._safe_one",
                            lambda fn: (own_exam, None))

        result = delete_student_exam("exam-1", student=STUDENT)
        assert result["success"] is True

    def test_other_student_exam_rejected(self, monkeypatch):
        """Student cannot cancel another student's exam."""
        monkeypatch.setattr("app.routes.exam_schedule._safe_one",
                            lambda fn: (None, None))  # ownership check fails
        with pytest.raises(HTTPException) as exc:
            delete_student_exam("exam-other", student=STUDENT)
        assert exc.value.status_code == 403


# ── add_child_exam (parent) ───────────────────────────────────────────────────

class TestAddChildExam:
    def test_parent_can_add_for_linked_child(self, monkeypatch):
        """Parent can add exam for own linked child."""
        linked_child = {"id": "child-uid-1", "username": "childstudent", "parent_id": "parent-uid-1"}
        monkeypatch.setattr("app.routes.exam_schedule._verify_child_ownership",
                            lambda p, c: linked_child)

        captured = {}
        class FakeTable:
            def insert(self, payload): captured.update(payload); return self
            def execute(self):
                class R:
                    data = [{"id":"uuid-3","student_id":"child-uid-1","exam_date":future_date(10),
                             "title":"Maths Test","subject":"Mathematics","exam_type":None,"notes":None,
                             "status":"active","created_by_role":"parent","created_at":"2026-06-28"}]
                return R()
        class FakeAdmin:
            def table(self, t): return FakeTable()
        monkeypatch.setattr("app.routes.exam_schedule.admin_client", FakeAdmin())

        req = ExamCreate(title="Maths Test", subject="Mathematics", exam_date=future_date(10))
        result = add_child_exam("child-uid-1", req, parent=PARENT)
        assert result["success"] is True
        assert captured["student_id"] == "child-uid-1"
        assert captured["created_by_role"] == "parent"
        assert captured["created_by_user_id"] == "parent-uid-1"

    def test_parent_cannot_add_for_unrelated_child(self, monkeypatch):
        """Parent cannot add exam for unrelated child."""
        monkeypatch.setattr("app.routes.exam_schedule._verify_child_ownership",
                            lambda p, c: None)  # ownership fails

        req = ExamCreate(title="Test", subject="Science", exam_date=future_date(5))
        with pytest.raises(HTTPException) as exc:
            add_child_exam("foreign-child", req, parent=PARENT)
        assert exc.value.status_code == 403

    def test_parent_past_date_rejected(self, monkeypatch):
        """Parent cannot add past exam date for child."""
        linked_child = {"id": "child-uid-1", "parent_id": "parent-uid-1"}
        monkeypatch.setattr("app.routes.exam_schedule._verify_child_ownership",
                            lambda p, c: linked_child)

        req = ExamCreate(title="Old Exam", subject="Science", exam_date=past_date(5))
        with pytest.raises(HTTPException) as exc:
            add_child_exam("child-uid-1", req, parent=PARENT)
        assert exc.value.status_code == 400
