from fastapi.testclient import TestClient

from app.main import app
import app.routes.doubt as doubt_route
from tests.conftest import fake_student_profile, patch_route_profile

client = TestClient(app)


def test_answer_doubt_api(monkeypatch):
    """
    Test that the doubt-answering API returns a valid response.

    This test mocks answer_doubt so it does not call the real AI service,
    Supabase, or any external dependency.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - answer
      - source_type
      - mentor_suggestions
    """

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        return {
            "answer": "Matter is anything that has mass and occupies space.",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [
                "Try giving two examples of matter.",
            ],
        }

    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "",
        "chapter": "",
        "question": "What is matter?",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "answer" in data
    assert "source_type" in data
    assert "mentor_suggestions" in data

    assert data["success"] is True
    assert data["answer"] == "Matter is anything that has mass and occupies space."
    assert data["source_type"] == "MOCK"


def test_answer_doubt_response_has_valid_data_types(monkeypatch):
    """
    Test that the doubt-answering API returns values with expected data types.

    The frontend depends on these response fields to display the tutor answer
    and mentor suggestions properly.

    Expected result:
    - success should be a boolean.
    - answer should be text.
    - source_type should be text.
    - mentor_suggestions should be a list.
    """

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        return {
            "answer": "Matter has mass and occupies space.",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "question": "What is matter?",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["success"], bool)
    assert isinstance(data["answer"], str)
    assert isinstance(data["source_type"], str)
    assert isinstance(data["mentor_suggestions"], list)


def test_answer_doubt_empty_question():
    """
    Test that the doubt-answering API rejects an empty question.

    The question field is required because the tutor needs an actual student
    doubt to answer.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 400 or HTTP 422.
    """
    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "question": "",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code in [400, 422]


def test_answer_doubt_uses_authenticated_profile_username(monkeypatch):
    captured = {}

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        captured["mode"] = mode
        captured["username"] = username
        return {
            "answer": "CBSE answer",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    payload = {
        "username": "spoofed_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "",
        "question": "What is motion?",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 200
    assert captured["username"] == "test_user"
    assert captured["mode"] == "CBSE"


def test_answer_doubt_saves_full_history(monkeypatch):
    """A normal Ask Doubt request should persist the full answer for review."""
    captured_history = {}

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        return {
            "answer": "Osmosis is movement of water across a membrane.",
            "source_type": "RAG",
            "sources": [{"document": {"title": "Cell chapter"}}],
            "mentor_suggestions": ["Give a practice question"],
        }

    def fake_save_doubt_history(**kwargs):
        captured_history.update(kwargs)
        return {"id": "history-42"}

    # DKB returns None → falls through to LLM path (which is what this test exercises)
    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)
    monkeypatch.setattr(doubt_route, "save_doubt_history", fake_save_doubt_history)

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Cell",
            "question": "Preferred answer style: Explain simply",
            "display_question": "What is osmosis?",
        },
    )

    assert response.status_code == 200
    assert response.json()["history_id"] == "history-42"
    assert captured_history["username"] == "test_user"
    assert captured_history["question"] == "What is osmosis?"
    assert captured_history["answer"] == "Osmosis is movement of water across a membrane."
    assert captured_history["source_type"] == "RAG"


def test_answer_doubt_can_skip_history_for_followups(monkeypatch):
    """Follow-up helper calls should not clutter the student's doubt history."""
    captured = {"called": False}

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        return {
            "answer": "Short follow-up answer.",
            "source_type": "LLM",
            "sources": [],
            "mentor_suggestions": [],
        }

    def fake_save_doubt_history(**kwargs):
        captured["called"] = True
        return {"id": "history-should-not-exist"}

    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)
    monkeypatch.setattr(doubt_route, "save_doubt_history", fake_save_doubt_history)

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Cell",
            "question": "Mentor follow-up mode.",
            "save_to_history": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["history_id"] is None
    assert captured["called"] is False


def test_answer_doubt_uses_platform_rag_for_founder_questions(monkeypatch):
    """Questions about the app should not use the general tutor LLM path."""
    captured = {"answer_doubt_called": False}

    def fake_answer_doubt(*args, **kwargs):
        captured["answer_doubt_called"] = True
        raise AssertionError("Platform questions must not call the general LLM path.")

    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "",
            "question": "Who founded Likha Poha AI?",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert captured["answer_doubt_called"] is False
    assert data["source_type"] == "PLATFORM_RAG"
    assert "parent-engineer" in data["answer"] or "Bangalore" in data["answer"]
    assert "Indian families" in data["answer"] or "NCERT" in data["answer"]


def test_get_doubt_history_returns_authenticated_student_rows(monkeypatch):
    """History endpoint should return only rows loaded for the signed-in profile."""
    captured = {}

    def fake_list_doubt_history(**kwargs):
        captured.update(kwargs)
        return [
            {
                "id": "history-1",
                "question": "What is osmosis?",
                "answer": "Water movement.",
            }
        ]

    monkeypatch.setattr(doubt_route, "list_doubt_history", fake_list_doubt_history)

    response = client.get("/api/doubt/history?limit=5")

    assert response.status_code == 200
    assert response.json()["history"][0]["question"] == "What is osmosis?"
    assert captured["profile_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured["limit"] == 5



def test_answer_doubt_rejects_unsupported_mode():
    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "SOF",
        "subject": "",
        "chapter": "",
        "question": "Explain this question.",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 403
    assert "Invalid learning mode" in response.json()["detail"]


def _mock_doubt_answer(monkeypatch):
    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)
    monkeypatch.setattr(
        doubt_route,
        "answer_doubt",
        lambda **kwargs: {
            "answer": "Matter is anything with mass and volume.",
            "source_type": "TEXTBOOK_EXCERPT",
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
        },
    )


def test_free_tier_user_blocked_after_daily_limit(monkeypatch):
    """The 6th doubt of the day for a free-tier user must return 429, not an answer."""
    _mock_doubt_answer(monkeypatch)
    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(
        doubt_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": False, "message": "capped"},
    )

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 429
    assert "5" in response.json()["detail"]


def test_free_tier_user_within_limit_gets_answer_and_logs_usage(monkeypatch):
    """A free-tier user under the cap should be answered normally and counted."""
    _mock_doubt_answer(monkeypatch)
    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(
        doubt_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": True, "message": "ok"},
    )

    logged = {}
    monkeypatch.setattr(
        doubt_route,
        "log_ai_usage",
        lambda **kwargs: logged.update(kwargs),
    )

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert logged.get("feature") == "doubt_answer_free_tier"


def test_free_tier_user_blocked_by_daily_limit_even_on_a_dkb_hit(monkeypatch):
    """The daily cap must be checked BEFORE the DKB lookup, so a free-tier
    user who has used all 5 doubts today is blocked even for a question the
    DKB already has a cached answer for — every doubt counts, hit or miss."""
    monkeypatch.setattr(
        doubt_route,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    def _boom_answer_doubt(**kwargs):
        raise AssertionError("answer_doubt must not be reached when the daily cap is exhausted")
    monkeypatch.setattr(doubt_route, "answer_doubt", _boom_answer_doubt)

    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(
        doubt_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": False, "message": "capped"},
    )

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 429


def test_free_tier_dkb_hit_counts_against_the_daily_quota(monkeypatch):
    """A DKB hit must log usage for a free-tier user, same as a miss —
    hits are no longer free/unlimited against the daily cap."""
    monkeypatch.setattr(
        doubt_route,
        "search_doubt_kb",
        lambda **kwargs: {"answer": "Cached answer", "question": "q", "source_type": "DOUBT_KB", "id": "1", "similarity": 0.9},
    )

    def _boom_answer_doubt(**kwargs):
        raise AssertionError("answer_doubt must not be reached on a DKB hit")
    monkeypatch.setattr(doubt_route, "answer_doubt", _boom_answer_doubt)

    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(
        doubt_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": True, "message": "ok"},
    )

    logged = {}
    monkeypatch.setattr(doubt_route, "log_ai_usage", lambda **kwargs: logged.update(kwargs))

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 200
    assert response.json()["source_type"] == "DOUBT_KB"
    assert logged.get("feature") == "doubt_answer_free_tier"


def test_paid_user_never_capped(monkeypatch):
    """A paid user must never hit the daily-limit gate, no matter the usage."""
    _mock_doubt_answer(monkeypatch)
    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: False)

    def _boom(*args, **kwargs):
        raise AssertionError("enforce_daily_limit must not be called for a paid user")

    monkeypatch.setattr(doubt_route, "enforce_daily_limit", _boom)
    monkeypatch.setattr(doubt_route, "log_ai_usage", _boom)

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 200
    assert response.json()["success"] is True


# ── Exemplar Research paywall for teachers ───────────────────────────────────
# ExemplarResearchPage.jsx reuses this endpoint (chapter="Exemplar: <chapter>").
# SubscriptionPlansPage.jsx advertises Exemplar Research as paid-teacher-only;
# previously nothing in this route enforced that for teachers, so a free-tier
# teacher calling the API directly got full, unrestricted access.

def test_free_tier_teacher_is_blocked_from_exemplar_research(monkeypatch):
    _mock_doubt_answer(monkeypatch)
    profile = fake_student_profile(role="teacher", subscription_plan="free")
    patch_route_profile(monkeypatch, doubt_route, profile)

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Exemplar: Matter",
        "question": "Explain Exemplar problem on matter.",
    })

    assert response.status_code == 403
    assert response.json()["detail"]["feature"] == "EXEMPLAR_RESEARCH"


def test_paid_teacher_can_use_exemplar_research(monkeypatch):
    _mock_doubt_answer(monkeypatch)
    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: False)
    profile = fake_student_profile(role="teacher", subscription_plan="starter")
    patch_route_profile(monkeypatch, doubt_route, profile)

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Exemplar: Matter",
        "question": "Explain Exemplar problem on matter.",
    })

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_free_tier_teacher_is_not_blocked_from_non_exemplar_doubts(monkeypatch):
    """The Exemplar gate must only apply to Exemplar-prefixed chapters — a free
    teacher's regular Ask Doubt use is untouched (still subject to the normal
    5/day DKB-only cap, not a hard block)."""
    _mock_doubt_answer(monkeypatch)
    monkeypatch.setattr(doubt_route, "is_free_tier_user", lambda user_id: False)
    profile = fake_student_profile(role="teacher", subscription_plan="free")
    patch_route_profile(monkeypatch, doubt_route, profile)

    response = client.post("/api/doubt/answer", json={
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter",
        "question": "What is matter?",
    })

    assert response.status_code == 200
    assert response.json()["success"] is True
