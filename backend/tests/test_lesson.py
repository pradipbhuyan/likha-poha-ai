from fastapi.testclient import TestClient

from app.main import app

import app.routes.lesson as lesson_route

client = TestClient(app)


def mock_lesson_generation(monkeypatch):
    """
    Mock lesson generation so tests do not call the real AI service.
    """

    def fake_generate_lesson_content(*args, **kwargs):
        return {
            "success": True,
            "lesson": "This is a generated lesson about matter.",
            "source_type": "MOCK",
            "sources": [],
            "message": "Lesson generated successfully.",
        }

    possible_lesson_function_names = [
        "generate_lesson_content",
        "generate_lesson_with_rag",
        "generate_lesson_with_sources",
        "generate_lesson_for_step",
        "generate_lesson_from_rag",
        "generate_lesson_text",
    ]

    for function_name in possible_lesson_function_names:
        monkeypatch.setattr(
            lesson_route,
            function_name,
            fake_generate_lesson_content,
            raising=False,
        )


def mock_lesson_follow_up(monkeypatch):
    """
    Mock lesson follow-up so tests do not call the real AI service.
    """

    def fake_answer_lesson_follow_up(*args, **kwargs):
        return {
            "success": True,
            "answer": "Particles are tiny units that make up matter.",
            "source_type": "MOCK",
            "sources": [],
            "message": "Follow-up answered successfully.",
        }

    possible_follow_up_function_names = [
        "answer_lesson_follow_up",
        "ask_lesson_follow_up",
        "answer_follow_up_question",
        "generate_lesson_follow_up",
        "answer_lesson_question",
    ]

    for function_name in possible_follow_up_function_names:
        monkeypatch.setattr(
            lesson_route,
            function_name,
            fake_answer_lesson_follow_up,
            raising=False,
        )


def test_generate_lesson_api(monkeypatch):
    """
    Test that the lesson generation API returns a valid response.
    """

    mock_lesson_generation(monkeypatch)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "What is matter?",
        "teacher_persona": "friendly",
    }

    response = client.post("/api/lesson/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "lesson" in data
    assert "source_type" in data
    assert "sources" in data
    assert "message" in data


def test_generate_lesson_response_has_valid_data_types(monkeypatch):
    """
    Test that the lesson generation API returns values with expected data types.
    """

    mock_lesson_generation(monkeypatch)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "What is matter?",
        "teacher_persona": "friendly",
    }

    response = client.post("/api/lesson/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["success"], bool)
    assert isinstance(data["lesson"], (str, type(None)))
    assert isinstance(data["source_type"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["message"], str)


def test_generate_lesson_empty_step_title():
    """
    Test that the lesson generation API rejects an empty step title.
    """

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "",
        "teacher_persona": "friendly",
    }

    response = client.post("/api/lesson/generate", json=payload)

    assert response.status_code in [400, 422]


def test_lesson_follow_up_api(monkeypatch):
    """
    Test that the lesson follow-up API returns a valid response.
    """

    mock_lesson_follow_up(monkeypatch)

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "What is matter?",
        "lesson": "Matter is anything that has mass and occupies space.",
        "question": "Can you explain particles in matter?",
    }

    response = client.post("/api/lesson/follow-up", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "answer" in data
    assert "source_type" in data
    assert "sources" in data
    assert "message" in data


def test_lesson_follow_up_empty_question():
    """
    Test that the lesson follow-up API rejects an empty question.
    """

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "What is matter?",
        "lesson": "Matter is anything that has mass and occupies space.",
        "question": "",
    }

    response = client.post("/api/lesson/follow-up", json=payload)

    assert response.status_code in [400, 422]