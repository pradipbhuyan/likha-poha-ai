from fastapi.testclient import TestClient

from app.main import app
from app.services.openai_service import GPT5_MINI_TEXT_MODEL
import app.routes.doubt as doubt_route

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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None):
        return {
            "answer": "Matter is anything that has mass and occupies space.",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [
                "Try giving two examples of matter.",
            ],
        }

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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None):
        return {
            "answer": "Matter has mass and occupies space.",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None):
        captured["mode"] = mode
        captured["username"] = username
        return {
            "answer": "SOF answer",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    payload = {
        "username": "spoofed_user",
        "grade": "Grade 9",
        "mode": "SOF",
        "subject": "Science Olympiad",
        "chapter": "",
        "question": "What is motion?",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 200
    assert captured["username"] == "test_user"
    assert captured["mode"] == "SOF"


def test_answer_doubt_saves_full_history(monkeypatch):
    """A normal Ask Doubt request should persist the full answer for review."""
    captured_history = {}

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None):
        return {
            "answer": "Osmosis is movement of water across a membrane.",
            "source_type": "RAG",
            "sources": [{"document": {"title": "Cell chapter"}}],
            "mentor_suggestions": ["Give a practice question"],
        }

    def fake_save_doubt_history(**kwargs):
        captured_history.update(kwargs)
        return {"id": "history-42"}

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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None):
        return {
            "answer": "Short follow-up answer.",
            "source_type": "LLM",
            "sources": [],
            "mentor_suggestions": [],
        }

    def fake_save_doubt_history(**kwargs):
        captured["called"] = True
        return {"id": "history-should-not-exist"}

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


def test_admin_selected_gpt5_mini_is_used_for_doubt(monkeypatch):
    """Admin model override should win over the default/family plan routing."""
    from tests.conftest import fake_student_profile, patch_route_profile

    captured = {}
    profile = fake_student_profile(ai_model_preference="gpt-5-mini")
    patch_route_profile(monkeypatch, doubt_route, profile)

    def fake_answer_doubt(
        grade,
        mode,
        subject,
        chapter,
        question,
        username,
        model=None,
    ):
        captured["model"] = model
        return {
            "answer": "Step-wise answer",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Motion",
            "question": "What is motion?",
        },
    )

    assert response.status_code == 200
    assert captured["model"] == GPT5_MINI_TEXT_MODEL


def test_answer_doubt_rejects_sof_subject_without_access(monkeypatch):
    from tests.conftest import fake_student_profile, patch_route_profile

    profile = fake_student_profile(
        access_sof_science=True,
        access_sof_maths=False,
        access_sof_english=False,
    )
    patch_route_profile(monkeypatch, doubt_route, profile)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "SOF",
        "subject": "Maths Olympiad",
        "chapter": "",
        "question": "Solve this olympiad problem.",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 403
    assert "SOF Maths access is not enabled" in response.json()["detail"]


def test_answer_doubt_requires_sof_subject():
    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "SOF",
        "subject": "",
        "chapter": "",
        "question": "Explain this olympiad question.",
    }

    response = client.post("/api/doubt/answer", json=payload)

    assert response.status_code == 400
    assert "Please select Science, Maths, or English Olympiad" in response.json()["detail"]


def test_extract_doubt_image_returns_ocr_text(monkeypatch):
    monkeypatch.setattr(
        doubt_route,
        "extract_text_from_image_bytes",
        lambda image_bytes: "Question 1: What is matter?",
    )

    response = client.post(
        "/api/doubt/extract-image",
        files={"file": ("question.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["text"] == "Question 1: What is matter?"


def test_extract_doubt_image_rejects_non_image_file():
    response = client.post(
        "/api/doubt/extract-image",
        files={"file": ("question.txt", b"not-image", "text/plain")},
    )

    assert response.status_code == 400
    assert "Please upload a JPG" in response.json()["detail"]
