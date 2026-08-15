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
import app.services.auth_service as auth_service
import app.routes.teacher as teacher_route

FAKE_USER = SimpleNamespace(id="teacher-1", email="teacher@example.com")

# subscription_plan="starter" (paid) keeps these functional tests off the
# free-tier daily-quota path, which would otherwise hit the real Supabase
# client via enforce_daily_limit() — quota behavior has its own tests below.
TEACHER_PROFILE = {
    "id": "teacher-1", "role": "teacher", "username": "teacher1",
    "account_status": "active", "subscription_plan": "starter",
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: dict(TEACHER_PROFILE))
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
        assert "No lesson plan has been created yet" in data["message"]

    def test_no_duration_field_in_request_or_response(self, client):
        """duration_minutes was removed — a single handout can't vary by it."""
        resp = client.post(
            "/api/teacher/lesson-plan/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert "duration_minutes" not in resp.json()

    def test_non_teacher_role_is_rejected(self, client, monkeypatch):
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: {"role": "student"})
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
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: {"role": "student"})
        resp = client.post(
            "/api/teacher/test-paper/generate",
            json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                  "mcq_count": 3, "subjective_count": 0},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 403


# ── Server-side gates that used to be missing entirely ──────────────────────
# 1. A self-signed-up teacher stuck in pending_verification could previously
#    call these content routes directly (they only checked role, not
#    account_status), bypassing admin approval.
# 2. The "2/day" free-tier caps advertised on SubscriptionPlansPage.jsx were
#    previously enforced only via a frontend localStorage counter — trivially
#    bypassable via a direct API call. enforce_daily_limit()/log_ai_usage()
#    are now the real, server-side gate.

class TestPendingVerificationBlocked:
    def test_pending_verification_teacher_is_blocked(self, monkeypatch):
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: {
            "role": "teacher", "username": "new-teacher",
            "account_status": "pending_verification", "subscription_plan": "free",
        })
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        with TestClient(app) as c:
            resp = c.post(
                "/api/teacher/test-paper/generate",
                json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                      "mcq_count": 3, "subjective_count": 0},
                headers={"Authorization": "Bearer fake-token"},
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 403

    def test_active_teacher_is_not_blocked(self, monkeypatch):
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: dict(TEACHER_PROFILE))
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        monkeypatch.setattr(teacher_route, "get_questions_from_bank_with_fallback",
                             lambda **kw: [dict(FAKE_MCQ_BANK_ROW) for _ in range(kw["num_questions"])])
        with TestClient(app) as c:
            resp = c.post(
                "/api/teacher/test-paper/generate",
                json={"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                      "mcq_count": 3, "subjective_count": 0},
                headers={"Authorization": "Bearer fake-token"},
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 200


class TestFreeTierDailyLimit:
    def _fake_gate(self, monkeypatch, max_requests=2):
        """In-memory stand-in for the ai_usage_logs-backed daily counter, so
        the test exercises the real enforce/log call sequence without
        touching Supabase."""
        request_log = []

        def fake_enforce(username, feature, max_requests=max_requests):
            allowed = request_log.count((username, feature)) < max_requests
            return {"allowed": allowed, "message": "Daily limit reached.", "usage": {}}

        def fake_log(username, feature, model="", **kw):
            request_log.append((username, feature))

        monkeypatch.setattr(teacher_route, "enforce_daily_limit", fake_enforce)
        monkeypatch.setattr(teacher_route, "log_ai_usage", fake_log)
        return request_log

    def test_free_teacher_is_blocked_after_two_test_papers(self, monkeypatch):
        self._fake_gate(monkeypatch)
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: {
            "role": "teacher", "username": "free-teacher",
            "account_status": "active", "subscription_plan": "free",
        })
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        monkeypatch.setattr(teacher_route, "get_questions_from_bank_with_fallback",
                             lambda **kw: [dict(FAKE_MCQ_BANK_ROW) for _ in range(kw["num_questions"])])
        body = {"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                "mcq_count": 3, "subjective_count": 0}
        with TestClient(app) as c:
            r1 = c.post("/api/teacher/test-paper/generate", json=body, headers={"Authorization": "Bearer fake-token"})
            r2 = c.post("/api/teacher/test-paper/generate", json=body, headers={"Authorization": "Bearer fake-token"})
            r3 = c.post("/api/teacher/test-paper/generate", json=body, headers={"Authorization": "Bearer fake-token"})
        app.dependency_overrides.clear()

        assert r1.status_code == 200 and r1.json()["success"] is True
        assert r2.status_code == 200 and r2.json()["success"] is True
        assert r3.status_code == 429

    def test_paid_teacher_is_never_limited(self, monkeypatch):
        self._fake_gate(monkeypatch)
        monkeypatch.setattr(auth_service, "get_user_profile", lambda uid: dict(TEACHER_PROFILE))
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        monkeypatch.setattr(teacher_route, "get_questions_from_bank_with_fallback",
                             lambda **kw: [dict(FAKE_MCQ_BANK_ROW) for _ in range(kw["num_questions"])])
        body = {"grade": "Grade 9", "subject": "Social Science", "chapter": "Democracy",
                "mcq_count": 3, "subjective_count": 0}
        with TestClient(app) as c:
            responses = [
                c.post("/api/teacher/test-paper/generate", json=body, headers={"Authorization": "Bearer fake-token"})
                for _ in range(3)
            ]
        app.dependency_overrides.clear()
        assert all(r.status_code == 200 and r.json()["success"] is True for r in responses)
