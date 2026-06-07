from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_evaluate_answer_api():
    """
    Test that the backend can evaluate a student's answer.

    This checks the normal evaluation flow:
    1. The frontend sends a question.
    2. The frontend sends the student's answer.
    3. The frontend also sends ideal_context, which represents the expected answer.
    4. The backend evaluates the student's answer and returns feedback.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - evaluation
      - score
      - passed
    """
    payload = {
        "username": "test_user",
        "question": "What is xylem?",
        "student_answer": (
            "Xylem is a plant tissue that transports water and minerals "
            "from the roots to other parts of the plant. It also gives "
            "support to the plant body."
        ),
        "ideal_context": "Xylem transports water and minerals and gives support.",
    }

    response = client.post("/api/evaluation/evaluate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "evaluation" in data
    assert "score" in data
    assert "passed" in data
    
def test_evaluate_answer_response_has_valid_data_types(monkeypatch):
    """
    Test that the evaluation API returns the expected data types.

    The previous test only checks that important response fields exist.
    This test goes one step deeper and checks that those fields contain
    the kind of values the frontend can safely use.

    Expected result:
    - success should be a boolean.
    - evaluation should be text.
    - score should be a number.
    - passed should be a boolean.
    """
    
    import app.routes.evaluation as evaluation_route

    def fake_evaluate_student_answer(
        grade,
        question,
        student_answer,
        ideal_context,
        username,
        mode="CBSE",
        subject="",
        chapter="",
        step_title="",
        question_type="descriptive",
        expected_keywords=None,
    ):
        return {
            "evaluation": "Good answer.",
            "score": 8,
            "passed": True,
        }

    monkeypatch.setattr(
        evaluation_route,
        "evaluate_student_answer",
        fake_evaluate_student_answer,
    )
    
    payload = {
        "username": "test_user",
        "question": "What is xylem?",
        "student_answer": "Xylem transports water and minerals in plants.",
        "ideal_context": "Xylem transports water and minerals and gives support.",
    }

    response = client.post("/api/evaluation/evaluate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["success"], bool)
    assert isinstance(data["evaluation"], str)
    assert isinstance(data["score"], (int, float))
    assert isinstance(data["passed"], bool)
    
def test_evaluate_answer_score_is_within_expected_range():
    """
    Test that the evaluation score stays within the expected range.

    The frontend may use the score to show progress, pass/fail status,
    colors, badges, or feedback messages. Because of that, the score
    should stay within a predictable range.

    Expected result:
    - The endpoint should return HTTP 200.
    - The score should be greater than or equal to 0.
    - The score should be less than or equal to 100.
    """
    payload = {
        "username": "test_user",
        "question": "What is xylem?",
        "student_answer": "Xylem transports water and minerals in plants.",
        "ideal_context": "Xylem transports water and minerals and gives support.",
    }

    response = client.post("/api/evaluation/evaluate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["score"] >= 0
    assert data["score"] <= 100
    
def test_evaluate_answer_empty_student_answer():
    """
    Test that the evaluation API rejects an empty student answer.

    The student_answer field is important because the backend needs
    actual student input to compare against the ideal answer.

    This test sends an empty student_answer value.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 400 or HTTP 422.
    """
    payload = {
        "username": "test_user",
        "question": "What is xylem?",
        "student_answer": "",
        "ideal_context": "Xylem transports water and minerals and gives support.",
    }

    response = client.post("/api/evaluation/evaluate", json=payload)

    assert response.status_code in [400, 422]
    
def test_generate_practice_questions_api():
    """
    Test that the practice question generation API returns a valid response.

    This checks the flow where the frontend asks the backend to generate
    practice questions from lesson context.

    In this route:
    - ideal_context is used as the lesson text.
    - question is used as the chapter or topic label.

    Expected result:
    - The endpoint should return HTTP 200.
    - The response should contain:
      - success
      - questions
      - message
    """
    payload = {
        "username": "test_user",
        "question": "Xylem",
        "student_answer": "Xylem transports water.",
        "ideal_context": "Xylem transports water and minerals in plants.",
    }

    response = client.post("/api/evaluation/practice-questions", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "success" in data
    assert "questions" in data
    assert "message" in data
