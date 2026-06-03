from fastapi.testclient import TestClient

from app.main import app
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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username):
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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username):
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

    def fake_answer_doubt(grade, mode, subject, chapter, question, username):
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
