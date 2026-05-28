from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_lesson_api():
    """
    Test that the lesson generation API returns a valid response.

    This checks the normal lesson flow:
    1. The frontend sends student, subject, chapter, and lesson step details.
    2. The backend generates lesson content.
    3. The response includes the generated lesson and source information.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - lesson
      - source_type
      - sources
      - message
    """
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
    
def test_generate_lesson_response_has_valid_data_types():
    """
    Test that the lesson generation API returns values with expected data types.

    The frontend depends on these fields to display lesson content,
    source information, and status messages.

    Expected result:
    - success should be a boolean.
    - lesson should be text or None.
    - source_type should be text.
    - sources should be a list.
    - message should be text.
    """
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

    The step_title tells the backend what part of the lesson to generate.
    Without it, the tutor does not know what concept to teach.

    This test sends an empty step_title.

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
        "step_title": "",
        "teacher_persona": "friendly",
    }

    response = client.post("/api/lesson/generate", json=payload)

    assert response.status_code in [400, 422]
    
def test_lesson_follow_up_api():
    """
    Test that the lesson follow-up API returns a valid response.

    This checks the flow where a student asks a question after receiving
    a lesson explanation.

    Example:
    - The tutor teaches "What is matter?"
    - The student asks a follow-up question like "Can you explain particles?"
    - The backend returns an answer.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - answer
      - source_type
      - sources
      - message
    """
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

    The follow-up question is required because the tutor needs to know
    what the student is asking about.

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
        "step_title": "What is matter?",
        "lesson": "Matter is anything that has mass and occupies space.",
        "question": "",
    }

    response = client.post("/api/lesson/follow-up", json=payload)

    assert response.status_code in [400, 422]