"""
Security Test Suite
===================
Tests authentication, authorisation, role-based access control,
and business-logic security rules for the CBSE Tutor platform.
"""

import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app
from app.services.auth_service import get_current_user
from tests.conftest import fake_student_profile, patch_route_profile

import app.routes.lesson as lesson_route
import app.routes.doubt as doubt_route
import app.routes.mock_test as mock_test_route

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(profile: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=profile["id"],
        email=profile["email"],
        username=profile["username"],
        role=profile["role"],
        profile=profile,
    )


def override_as(profile: dict) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_user(profile)


LESSON_PAYLOAD = {
    "username": "test_user",
    "grade": "Grade 9",
    "board": "CBSE",
    "mode": "CBSE",
    "subject": "Science",
    "chapter": "Motion",
    "step_title": "Introduction",
    "teacher_persona": "",
}

DOUBT_PAYLOAD = {
    "username": "test_user",
    "grade": "Grade 9",
    "mode": "CBSE",
    "subject": "Science",
    "chapter": "",
    "question": "What is matter?",
}

MOCK_TEST_PAYLOAD = {
    "username": "test_user",
    "grade": "Grade 9",
    "mode": "CBSE",
    "board": "CBSE",
    "subject": "Science",
    "chapter": "Motion",
    "mock_type": "CBSE Exam Mock Test",
    "difficulty": "Medium",
    "question_count": 5,
    "exam_type": "Class Test",
}


# ---------------------------------------------------------------------------
# 1. Unauthenticated access
# ---------------------------------------------------------------------------

class TestUnauthenticatedAccess:
    """Protected endpoints must return 401/403 when no Bearer token is present."""

    def test_lesson_generate_requires_auth(self):
        app.dependency_overrides.clear()
        r = client.post("/api/lesson/generate", json=LESSON_PAYLOAD)
        assert r.status_code in [401, 403]

    def test_doubt_answer_requires_auth(self):
        app.dependency_overrides.clear()
        r = client.post("/api/doubt/answer", json=DOUBT_PAYLOAD)
        assert r.status_code in [401, 403]

    def test_mock_test_generate_requires_auth(self):
        app.dependency_overrides.clear()
        r = client.post("/api/mock-test/generate", json=MOCK_TEST_PAYLOAD)
        assert r.status_code in [401, 403]

    def test_admin_families_requires_auth(self):
        app.dependency_overrides.clear()
        r = client.get("/api/admin-control/families")
        assert r.status_code in [401, 403]

    def test_parent_dashboard_requires_auth(self):
        app.dependency_overrides.clear()
        r = client.get("/api/parent-dashboard/family")
        assert r.status_code in [401, 403]

    def test_health_check_is_public(self):
        app.dependency_overrides.clear()
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_rag_documents_list_is_public(self, monkeypatch):
        override_as(fake_student_profile())
        monkeypatch.setattr(
            "app.routes.rag.list_rag_documents",
            lambda: [],
            raising=False,
        )
        r = client.get("/api/rag/documents")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 2. Role-based access control
# ---------------------------------------------------------------------------

class TestRoleBasedAccess:
    """Students, parents, and teachers cannot reach admin-only routes."""

    def _patch_for_role(self, monkeypatch, profile: dict):
        """
        Override both get_current_user and auth_service.get_user_profile
        so require_admin reads the non-admin profile without hitting Supabase.
        """
        override_as(profile)
        monkeypatch.setattr(
            "app.services.auth_service.get_user_profile",
            lambda uid: profile,
            raising=False,
        )
        monkeypatch.setattr(
            "app.routes.admin_control.get_user_profile",
            lambda uid: profile,
            raising=False,
        )

    def test_student_cannot_access_admin_families(self, monkeypatch):
        self._patch_for_role(monkeypatch, fake_student_profile())
        r = client.get("/api/admin-control/families")
        assert r.status_code == 403
        assert "Admin access required" in r.json().get("detail", "")

    def test_student_cannot_create_parent_account(self, monkeypatch):
        self._patch_for_role(monkeypatch, fake_student_profile())
        r = client.post("/api/admin-control/parents", json={
            "email": "x@example.com", "username": "X",
        })
        assert r.status_code == 403

    def test_student_cannot_delete_users(self, monkeypatch):
        self._patch_for_role(monkeypatch, fake_student_profile())
        r = client.delete("/api/admin-control/users/any-id")
        assert r.status_code == 403

    def test_student_cannot_update_subscription_plans(self, monkeypatch):
        self._patch_for_role(monkeypatch, fake_student_profile())
        r = client.put("/api/admin-control/subscription-plans", json={"plans": []})
        assert r.status_code == 403

    def test_student_cannot_update_child_access(self, monkeypatch):
        self._patch_for_role(monkeypatch, fake_student_profile())
        r = client.patch("/api/admin-control/access/child-id", json={
            "access_cbse": True,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
        })
        assert r.status_code == 403

    def test_parent_cannot_access_admin_control(self, monkeypatch):
        parent = fake_student_profile(role="parent")
        self._patch_for_role(monkeypatch, parent)
        r = client.get("/api/admin-control/families")
        assert r.status_code == 403

    def test_teacher_cannot_access_admin_control(self, monkeypatch):
        teacher = fake_student_profile(role="teacher")
        self._patch_for_role(monkeypatch, teacher)
        r = client.get("/api/admin-control/families")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 3. Username spoofing prevention
# ---------------------------------------------------------------------------

class TestUsernameSpoofing:
    """Authenticated profile username must override any username in the request body."""

    def test_doubt_ignores_spoofed_username(self, monkeypatch):
        """
        POST /api/doubt/answer must use the authenticated profile username,
        not whatever username an attacker injects in the request body.
        """
        captured = {}

        def fake_answer_doubt(grade, mode, subject, chapter, question,
                               username, model=None, **kwargs):
            captured["username"] = username
            return {
                "answer": "ok", "source_type": "MOCK",
                "sources": [], "mentor_suggestions": [],
            }

        monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

        r = client.post("/api/doubt/answer", json={
            **DOUBT_PAYLOAD,
            "username": "SPOOFED_ADMIN",
        })

        assert r.status_code == 200
        assert captured.get("username") == "test_user", (
            f"Spoofed username was not rejected; got '{captured.get('username')}'"
        )

    def test_lesson_ignores_spoofed_username(self, monkeypatch):
        """
        POST /api/lesson/generate must use the authenticated profile username,
        not the attacker-controlled username in the request body.
        """
        captured = {}

        def fake_generate_step_lesson(**kwargs):
            captured["username"] = kwargs.get("username")
            return {
                "lesson": "ok", "source_type": "MOCK",
                "sources": [], "textbook_visuals": [],
            }

        monkeypatch.setattr(lesson_route, "generate_step_lesson", fake_generate_step_lesson)

        r = client.post("/api/lesson/generate", json={
            **LESSON_PAYLOAD,
            "username": "SPOOFED_ADMIN",
        })

        assert r.status_code == 200
        assert captured.get("username") == "test_user", (
            f"Spoofed username was not rejected; got '{captured.get('username')}'"
        )


# ---------------------------------------------------------------------------
# 4. Suspended / expired account blocking
# ---------------------------------------------------------------------------

class TestSuspendedAccount:
    """Suspended and expired students must be blocked from AI features."""

    def test_suspended_student_cannot_generate_lesson(self, monkeypatch):
        suspended = fake_student_profile(account_status="suspended")
        patch_route_profile(monkeypatch, lesson_route, suspended)
        r = client.post("/api/lesson/generate", json=LESSON_PAYLOAD)
        assert r.status_code == 403
        assert "suspended" in r.json().get("detail", "").lower()

    def test_suspended_student_cannot_ask_doubt(self, monkeypatch):
        suspended = fake_student_profile(account_status="suspended")
        patch_route_profile(monkeypatch, doubt_route, suspended)
        r = client.post("/api/doubt/answer", json=DOUBT_PAYLOAD)
        assert r.status_code == 403
        assert "suspended" in r.json().get("detail", "").lower()

    def test_suspended_student_cannot_take_mock_test(self, monkeypatch):
        suspended = fake_student_profile(account_status="suspended")
        patch_route_profile(monkeypatch, mock_test_route, suspended)
        r = client.post("/api/mock-test/generate", json=MOCK_TEST_PAYLOAD)
        assert r.status_code == 403
        assert "suspended" in r.json().get("detail", "").lower()

    def test_expired_student_cannot_generate_lesson(self, monkeypatch):
        expired = fake_student_profile(account_status="expired")
        patch_route_profile(monkeypatch, lesson_route, expired)
        r = client.post("/api/lesson/generate", json=LESSON_PAYLOAD)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 5. Grade boundary enforcement
# ---------------------------------------------------------------------------

class TestGradeBoundary:
    """Students cannot request content for grades other than their own."""

    def test_grade_9_student_cannot_access_grade_10_lesson(self, monkeypatch):
        """
        A Grade 9 student must be blocked from generating a Grade 10 lesson.
        enforce_profile_grade() in the lesson route enforces this.
        """
        grade_9_student = fake_student_profile(grade="Grade 9")
        patch_route_profile(monkeypatch, lesson_route, grade_9_student)

        r = client.post("/api/lesson/generate", json={
            **LESSON_PAYLOAD,
            "grade": "Grade 10",  # wrong grade
        })
        assert r.status_code == 403

    def test_grade_9_student_cannot_access_grade_10_doubt(self, monkeypatch):
        """A Grade 9 student must be blocked from asking doubts for Grade 10."""
        grade_9_student = fake_student_profile(grade="Grade 9")
        patch_route_profile(monkeypatch, doubt_route, grade_9_student)

        r = client.post("/api/doubt/answer", json={
            **DOUBT_PAYLOAD,
            "grade": "Grade 10",
        })
        assert r.status_code == 403

    def test_grade_9_student_cannot_access_grade_10_mock_test(self, monkeypatch):
        """A Grade 9 student must be blocked from taking a Grade 10 mock test."""
        grade_9_student = fake_student_profile(grade="Grade 9")
        patch_route_profile(monkeypatch, mock_test_route, grade_9_student)

        r = client.post("/api/mock-test/generate", json={
            **MOCK_TEST_PAYLOAD,
            "grade": "Grade 10",
        })
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 6. CBSE access control
# ---------------------------------------------------------------------------

class TestCbseAccessControl:
    """Students without CBSE access must be blocked from CBSE content."""

    def test_student_without_cbse_access_cannot_generate_lesson(self, monkeypatch):
        no_cbse = fake_student_profile(access_cbse=False)
        patch_route_profile(monkeypatch, lesson_route, no_cbse)
        r = client.post("/api/lesson/generate", json=LESSON_PAYLOAD)
        assert r.status_code == 403
        assert "cbse" in r.json().get("detail", "").lower() or \
               "access" in r.json().get("detail", "").lower()

    def test_student_without_cbse_access_cannot_ask_doubt(self, monkeypatch):
        no_cbse = fake_student_profile(access_cbse=False)
        patch_route_profile(monkeypatch, doubt_route, no_cbse)
        r = client.post("/api/doubt/answer", json=DOUBT_PAYLOAD)
        assert r.status_code == 403

    def test_student_without_cbse_access_cannot_take_mock_test(self, monkeypatch):
        no_cbse = fake_student_profile(access_cbse=False)
        patch_route_profile(monkeypatch, mock_test_route, no_cbse)
        r = client.post("/api/mock-test/generate", json=MOCK_TEST_PAYLOAD)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 8. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Required fields must be validated and empty inputs rejected."""

    def test_doubt_empty_question_is_rejected(self):
        """POST /api/doubt/answer with an empty question must return 400 or 422."""
        r = client.post("/api/doubt/answer", json={
            **DOUBT_PAYLOAD,
            "question": "",
        })
        assert r.status_code in [400, 422]

    def test_doubt_missing_username_is_rejected(self):
        """POST /api/doubt/answer with an empty username must return 400 or 422."""
        r = client.post("/api/doubt/answer", json={
            **DOUBT_PAYLOAD,
            "username": "",
        })
        assert r.status_code in [400, 422]

    def test_lesson_empty_step_title_is_rejected(self):
        """POST /api/lesson/generate with an empty step_title must return 400 or 422."""
        r = client.post("/api/lesson/generate", json={
            **LESSON_PAYLOAD,
            "step_title": "",
        })
        assert r.status_code in [400, 422]

    def test_lesson_empty_chapter_is_rejected(self):
        """POST /api/lesson/generate with an empty chapter must return 400 or 422."""
        r = client.post("/api/lesson/generate", json={
            **LESSON_PAYLOAD,
            "chapter": "",
        })
        assert r.status_code in [400, 422]

    def test_doubt_with_unsupported_mode_is_rejected(self):
        """POST /api/doubt/answer with an unrecognized mode must return 403."""
        r = client.post("/api/doubt/answer", json={
            **DOUBT_PAYLOAD,
            "mode": "SOF",
        })
        assert r.status_code == 403
