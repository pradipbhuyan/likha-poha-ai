from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_quiz_api():
    """
    Test that the quiz generation API returns a valid response.

    This checks the normal quiz flow:
    1. The frontend sends grade, subject, chapter, mode, difficulty, and question count.
    2. The backend generates quiz questions.
    3. The response includes quiz questions and a status message.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - questions
      - message
    """
    payload = {
        "grade": "Grade 9",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "mode": "CBSE",
        "difficulty": "easy",
        "question_count": 3,
    }

    response = client.post("/api/quiz/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "questions" in data
    assert "message" in data