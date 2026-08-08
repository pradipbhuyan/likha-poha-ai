"""
Tests for the bank-only Create Lesson Plan and Create Test Paper endpoints.

Both endpoints used to call an LLM live on every request; they now serve
pre-authored content from lesson_plan_bank/ (static files) and
question_bank / subjective_question_bank (Supabase tables), with zero LLM
calls at request time — mirroring Mock Test's zero-LLM MCQ mode.

Lesson-plan tests exercise the real lesson_plan_bank_service against the
real sample file checked in at
backend/app/data/lesson_plan_bank/grade_9/social_science/democracy.json
(no mocking needed — it's a local file, not a live service).

Test-paper tests monkeypatch the bank-lookup functions imported into
app.routes.teacher, since question_bank / subjective_question_bank are
Supabase tables with no local equivalent to exercise directly in tests.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user
import app.routes.teacher as teacher_route

FAKE_USER = SimpleNamespace(id="teacher-1", email="teacher@example.com")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "teacher"})
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── generate_lesson_plan ──────────────────────────────────────────────────────

class TestGenerateLessonPlan:
    def test_bank_hit_returns_the_authored_handout(self, client):
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Lesson Overview" in data["lesson_plan"]
        assert data["grade"] == "Grade 9"
        assert data["chapter"] == "Democracy"

    def test_bank_hit_via_chapter_display_prefix_variant(self, client):
        """A rag_documents-style prefixed chapter string should still resolve
        to the same handout via the fallback matching tiers."""
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Chapter 6: Democracy"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_bank_miss_returns_friendly_message_not_an_error(self, client):
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Nonexistent Chapter XYZ"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200  # not an HTTP error — same convention as Mock Test
        data = resp.json()
        assert data["success"] is False
        assert "still being prepared" in data["message"]

    def test_no_duration_field_in_request_or_response(self, client):
        """duration_minutes was removed — a single handout can't vary by it."""
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert "duration_minutes" not in resp.json()

    def test_non_teacher_role_is_rejected(self, client, monkeypatch):
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "student"})
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 403


# ── generate_test_paper ───────────────────────────────────────────────────────

FAKE_MCQ_BANK_ROW = {
    "id": "q1", "question": "What is the capital of India?",
    "options": {"A": "Mumbai", "B": "New Delhi", "C": "Kolkata", "D": "Chennai"},
    "answer": "B", "explanation": "New Delhi is the capital of India.",
}

FAKE_SUBJECTIVE_BANK_ROW = {
    "id": "s1", "question": "Explain the Rule of Law.",
    "marks": 3, "model_answer": "No one is above the law; everyone gets equal treatment under it.",
}


class TestGenerateTestPaper:
    def test_mcq_and_subjective_bank_hit(self, client, monkeypatch):
        monkeypatch.setattr(
            teacher_route, "get_questions_from_bank_with_fallback",
            lambda **kw: [dict(FAKE_MCQ_BANK_ROW) for _ in range(kw["num_questions"])],
        )
        monkeypatch.setattr(
            teacher_route, "get_subjective_questions_from_bank_with_fallback",
            lambda **kw: [dict(FAKE_SUBJECTIVE_BANK_ROW) for _ in range(kw["num_questions"])],
        )

        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 3, "subjective_count": 2},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["mcq_count"] == 3
        assert data["subjective_count"] == 2
        mcqs = [q for q in data["questions"] if q["type"] == "mcq"]
        assert all(q["source"] == "question_bank" for q in mcqs)
        subjs = [q for q in data["questions"] if q["type"] == "subjective"]
        assert all(q["source"] == "question_bank" for q in subjs)
        assert subjs[0]["answer"] == FAKE_SUBJECTIVE_BANK_ROW["model_answer"]

    def test_mcq_bank_shortfall_returns_friendly_message_not_an_error(self, client, monkeypatch):
        monkeypatch.setattr(teacher_route, "get_questions_from_bank_with_fallback", lambda **kw: [])
        monkeypatch.setattr(teacher_route, "get_bank_capacity_with_fallback", lambda *a: 2)

        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 10, "subjective_count": 0},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200  # not an HTTP error
        data = resp.json()
        assert data["success"] is False
        assert "message" in data

    def test_subjective_bank_shortfall_returns_friendly_message(self, client, monkeypatch):
        monkeypatch.setattr(
            teacher_route, "get_questions_from_bank_with_fallback",
            lambda **kw: [dict(FAKE_MCQ_BANK_ROW) for _ in range(kw["num_questions"])],
        )
        monkeypatch.setattr(teacher_route, "get_subjective_questions_from_bank_with_fallback", lambda **kw: [])
        monkeypatch.setattr(teacher_route, "get_subjective_bank_capacity_with_fallback", lambda *a: 1)

        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 3, "subjective_count": 5},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "message" in data

    def test_zero_questions_requested_is_rejected(self, client):
        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 0, "subjective_count": 0},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400

    def test_non_teacher_role_is_rejected(self, client, monkeypatch):
        monkeypatch.setattr(teacher_route, "_get_profile", lambda uid: {"role": "student"})
        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 3, "subjective_count": 0},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 403
