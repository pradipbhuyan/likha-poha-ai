from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_evaluate_answer_api():
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