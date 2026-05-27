from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_save_and_get_chapter_progress():
    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Test Chapter",
        "current_step_index": 1,
        "completed": False,
        "last_lesson": "This is a test lesson.",
    }

    save_response = client.post("/api/progress/save", json=payload)

    assert save_response.status_code == 200

    get_response = client.post(
        "/api/progress/chapter",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Test Chapter",
        },
    )

    assert get_response.status_code == 200

    data = get_response.json()

    assert "progress" in data