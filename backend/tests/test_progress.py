from fastapi.testclient import TestClient

from app.main import app

import app.routes.progress as progress_route

client = TestClient(app)

def setup_fake_progress_store(monkeypatch):
    fake_store = {}

    def fake_save_chapter_progress(data):
        key = (
            data.get("username"),
            data.get("grade"),
            data.get("mode"),
            data.get("subject"),
            data.get("chapter"),
        )

        existing = fake_store.get(key, {})

        step_index = int(data.get("current_step_index", 0))
        last_lesson = data.get("last_lesson", "")

        step_lessons = existing.get("step_lessons", {})

        if last_lesson:
            step_lessons[str(step_index)] = last_lesson

        progress = {
            "username": data.get("username"),
            "grade": data.get("grade"),
            "mode": data.get("mode"),
            "subject": data.get("subject"),
            "chapter": data.get("chapter"),
            "current_step_index": step_index,
            "completed": data.get("completed", False),
            "last_lesson": last_lesson or existing.get("last_lesson", ""),
            "step_lessons": step_lessons,
            "updated_at": None,
        }

        fake_store[key] = progress
        return progress

    def fake_get_chapter_progress(
        username,
        grade,
        mode,
        subject,
        chapter,
    ):
        key = (
            username,
            grade,
            mode,
            subject,
            chapter,
        )

        return fake_store.get(
            key,
            {
                "username": username,
                "grade": grade,
                "mode": mode,
                "subject": subject,
                "chapter": chapter,
                "current_step_index": 0,
                "completed": False,
                "last_lesson": "",
                "step_lessons": {},
                "updated_at": None,
            },
        )

    monkeypatch.setattr(
        progress_route,
        "save_chapter_progress",
        fake_save_chapter_progress,
    )

    monkeypatch.setattr(
        progress_route,
        "get_chapter_progress",
        fake_get_chapter_progress,
    )

    return fake_store


def test_save_and_get_chapter_progress(monkeypatch):
    """
    Test that chapter progress can be saved and then retrieved.

    This checks the normal student flow:
    1. A student starts or continues a chapter.
    2. The frontend saves the student's current progress.
    3. The frontend later asks the backend for that same chapter progress.

    Expected result:
    - Saving progress should return HTTP 200.
    - Getting progress should return HTTP 200.
    - The response should contain a "progress" object.
    """
    setup_fake_progress_store(monkeypatch)
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


def test_update_existing_chapter_progress(monkeypatch):
    """
    Test that existing chapter progress can be updated.

    This checks what happens when a student comes back to the same chapter
    and moves further ahead in the lesson.

    The test first saves progress at step 1, then saves progress again for
    the same user, grade, subject, and chapter at step 4.

    Expected result:
    - Both save requests should return HTTP 200.
    - The latest saved progress should replace or update the older progress.
    - The retrieved progress should show:
      - current_step_index as 4
      - completed as True
      - last_lesson as "Updated lesson."
    """
    
    setup_fake_progress_store(monkeypatch)
    initial_payload = {
        "username": "test_user_update",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Update Test Chapter",
        "current_step_index": 1,
        "completed": False,
        "last_lesson": "Initial lesson.",
    }

    updated_payload = {
        "username": "test_user_update",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Update Test Chapter",
        "current_step_index": 4,
        "completed": True,
        "last_lesson": "Updated lesson.",
    }

    first_response = client.post("/api/progress/save", json=initial_payload)
    assert first_response.status_code == 200

    second_response = client.post("/api/progress/save", json=updated_payload)
    assert second_response.status_code == 200

    get_response = client.post(
        "/api/progress/chapter",
        json={
            "username": "test_user_update",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Update Test Chapter",
        },
    )

    assert get_response.status_code == 200

    data = get_response.json()

    assert "progress" in data
    assert data["progress"] is not None

    progress = data["progress"]

    assert progress["current_step_index"] == 4
    assert progress["completed"] is True
    assert progress["last_lesson"] == "Updated lesson."


def test_save_progress_missing_username():
    """
    Test that saving progress without a username is rejected.

    The username is required because progress must belong to a specific
    student. Without it, the backend would not know which student record
    to save or update.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 400 or HTTP 422.
      - 400 means bad request.
      - 422 means validation error.
    """
    payload = {
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Test Chapter",
        "current_step_index": 1,
        "completed": False,
        "last_lesson": "This is a test lesson.",
    }

    response = client.post("/api/progress/save", json=payload)

    assert response.status_code in [400, 422]


def test_save_progress_invalid_step_index():
    """
    Test that saving progress with an invalid step index is rejected.

    The current_step_index field should be a number because it represents
    the student's current position in the lesson flow.

    This test sends the text value "wrong" instead of a number.

    Expected result:
    - The backend should reject the request.
    - The response should be HTTP 400 or HTTP 422.
    """
    payload = {
        "username": "test_user_invalid",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Test Chapter",
        "current_step_index": "wrong",
        "completed": False,
        "last_lesson": "This is a test lesson.",
    }

    response = client.post("/api/progress/save", json=payload)

    assert response.status_code in [400, 422]


def test_different_chapters_have_separate_progress(monkeypatch):
    """
    Test that progress for different chapters is stored separately.

    This checks an important real-world student flow:
    the same student may study multiple chapters in the same subject.

    The test saves progress for two chapters:
    - Atoms and Molecules
    - Gravitation

    Expected result:
    - Both chapters should save successfully.
    - Retrieving each chapter should return its own progress.
    - The progress for one chapter should not overwrite the other chapter.
    """
    
    setup_fake_progress_store(monkeypatch)
    chapter_one_payload = {
        "username": "test_user_multi",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Atoms and Molecules",
        "current_step_index": 2,
        "completed": False,
        "last_lesson": "Atoms lesson.",
    }

    chapter_two_payload = {
        "username": "test_user_multi",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Gravitation",
        "current_step_index": 5,
        "completed": True,
        "last_lesson": "Gravity lesson.",
    }

    response_one = client.post("/api/progress/save", json=chapter_one_payload)
    response_two = client.post("/api/progress/save", json=chapter_two_payload)

    assert response_one.status_code == 200
    assert response_two.status_code == 200

    get_chapter_one = client.post(
        "/api/progress/chapter",
        json={
            "username": "test_user_multi",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Atoms and Molecules",
        },
    )

    get_chapter_two = client.post(
        "/api/progress/chapter",
        json={
            "username": "test_user_multi",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Gravitation",
        },
    )

    assert get_chapter_one.status_code == 200
    assert get_chapter_two.status_code == 200

    progress_one = get_chapter_one.json()["progress"]
    progress_two = get_chapter_two.json()["progress"]

    assert progress_one["chapter"] == "Atoms and Molecules"
    assert progress_one["current_step_index"] == 2
    assert progress_one["completed"] is False

    assert progress_two["chapter"] == "Gravitation"
    assert progress_two["current_step_index"] == 5
    assert progress_two["completed"] is True