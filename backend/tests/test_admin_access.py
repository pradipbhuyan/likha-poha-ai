from fastapi.testclient import TestClient

from app.main import app

import app.routes.doubt as doubt_route
import app.routes.lesson as lesson_route
import app.routes.mock_test as mock_test_route

from tests.conftest import fake_student_profile, patch_route_profile


client = TestClient(app)


SUSPENDED_ACCOUNT_MESSAGE = (
    "Your account is suspended. Please contact your parent or administrator."
)


def test_student_without_cbse_access_cannot_generate_lesson(monkeypatch):
    """
    A normal student without CBSE access should not be allowed to generate
    a CBSE lesson.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/lesson.py

    Look for the CBSE access check inside the lesson route access enforcement.
    """
    profile = fake_student_profile(access_cbse=False)

    patch_route_profile(
        monkeypatch,
        lesson_route,
        profile,
    )

    response = client.post(
        "/api/lesson/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "step_title": "What is matter?",
            "teacher_persona": "friendly",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "CBSE access is not enabled for this student."
    )


def test_inactive_student_cannot_generate_lesson(monkeypatch):
    """
    A student whose account is suspended should be blocked from lessons.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/lesson.py

    Look for the account_status check inside the lesson route access enforcement.
    """
    profile = fake_student_profile(account_status="blocked")

    patch_route_profile(
        monkeypatch,
        lesson_route,
        profile,
    )

    response = client.post(
        "/api/lesson/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "step_title": "What is matter?",
            "teacher_persona": "friendly",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == SUSPENDED_ACCOUNT_MESSAGE


def test_student_without_cbse_access_cannot_ask_doubt(monkeypatch):
    """
    A normal student without CBSE access should not be allowed to ask
    CBSE doubts.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/doubt.py

    Look for the CBSE access check inside the doubt route access enforcement.
    """
    profile = fake_student_profile(access_cbse=False)

    patch_route_profile(
        monkeypatch,
        doubt_route,
        profile,
    )

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "question": "What is matter?",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "CBSE access is not enabled."


def test_inactive_student_cannot_ask_doubt(monkeypatch):
    """
    A suspended student should not be allowed to ask doubts.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/doubt.py

    Look for the account_status check inside the doubt route access enforcement.
    """
    profile = fake_student_profile(account_status="blocked")

    patch_route_profile(
        monkeypatch,
        doubt_route,
        profile,
    )

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "question": "What is matter?",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == SUSPENDED_ACCOUNT_MESSAGE


def test_student_without_cbse_access_cannot_generate_mock_test(monkeypatch):
    """
    A normal student without CBSE access should not be allowed to generate
    a CBSE mock test.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/mock_test.py

    Look for the CBSE access check inside the mock-test route access enforcement.
    """
    profile = fake_student_profile(access_cbse=False)

    patch_route_profile(
        monkeypatch,
        mock_test_route,
        profile,
    )

    response = client.post(
        "/api/mock-test/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "mock_type": "CBSE Mock Test",
            "exam_type": "Class Test",
            "question_count": 1,
            "difficulty": "easy",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "CBSE access is not enabled."


def test_inactive_student_cannot_generate_mock_test(monkeypatch):
    """
    A suspended student should not be allowed to generate mock tests.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/mock_test.py

    Look for the account_status check inside the mock-test route access enforcement.
    """
    profile = fake_student_profile(account_status="blocked")

    patch_route_profile(
        monkeypatch,
        mock_test_route,
        profile,
    )

    response = client.post(
        "/api/mock-test/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Matter in Our Surroundings",
            "mock_type": "CBSE Mock Test",
            "exam_type": "Class Test",
            "question_count": 1,
            "difficulty": "easy",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == SUSPENDED_ACCOUNT_MESSAGE


def test_student_without_sof_science_access_cannot_generate_sof_science_mock_test(
    monkeypatch,
):
    """
    A normal student without SOF Science access should not be allowed to
    generate a Science Olympiad mock test.

    If this test fails because the error message changed, update the source in:
        backend/app/routes/mock_test.py

    Look for the SOF Science access check inside the mock-test route access
    enforcement.
    """
    profile = fake_student_profile(access_sof_science=False)

    patch_route_profile(
        monkeypatch,
        mock_test_route,
        profile,
    )

    response = client.post(
        "/api/mock-test/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "SOF",
            "subject": "Science Olympiad",
            "chapter": "General Science",
            "mock_type": "SOF Olympiad Mock Test",
            "exam_type": "Olympiad",
            "question_count": 1,
            "difficulty": "medium",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "SOF Science access is not enabled."