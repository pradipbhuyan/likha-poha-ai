from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_answer_doubt_api():
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