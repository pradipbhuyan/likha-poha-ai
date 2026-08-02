"""
test_student_feature_access_denial.py
─────────────────────────────────────────────────────────────────────────────
Regression tests that a student without CBSE/paid access is correctly denied
lesson generation, doubt-answering, and mock-test features (not admin-panel
access — despite this file's former name, test_admin_access.py, it has never
tested any admin route).
"""
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


def test_student_without_cbse_subject_access_cannot_generate_lesson(monkeypatch):
    """
    A custom CBSE plan should block lesson generation for subjects outside the
    student's configured subject list.
    """
    profile = fake_student_profile(cbse_subjects=["Science", "Maths"])

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
            "subject": "English",
            "chapter": "Nouns",
            "step_title": "What are nouns?",
            "teacher_persona": "friendly",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "CBSE English access is not enabled for this student."
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


def test_student_without_cbse_access_can_still_ask_doubt(monkeypatch):
    """
    Ask Doubt never calls an LLM for any tier, so it no longer gates by
    subject/topic access — a student without CBSE access must still get a
    normal (retrieval-only) answer, not a 403. The only free-tier control
    is the shared 5/day cap, tested elsewhere.
    """
    profile = fake_student_profile(access_cbse=False)

    patch_route_profile(
        monkeypatch,
        doubt_route,
        profile,
    )
    monkeypatch.setattr(
        doubt_route,
        "answer_doubt",
        lambda **kwargs: {
            "answer": "Matter is anything with mass and volume.",
            "source_type": "TEXTBOOK_EXCERPT",
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
        },
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

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_student_without_cbse_subject_access_can_still_ask_doubt(monkeypatch):
    """
    Ask Doubt no longer gates by a student's configured subject list — the
    only free-tier control is the shared 5/day cap. A custom CBSE plan must
    not block a doubt for a subject outside the student's subject list.
    """
    profile = fake_student_profile(cbse_subjects=["Science", "Maths"])

    patch_route_profile(
        monkeypatch,
        doubt_route,
        profile,
    )
    monkeypatch.setattr(
        doubt_route,
        "answer_doubt",
        lambda **kwargs: {
            "answer": "A noun is a naming word.",
            "source_type": "TEXTBOOK_EXCERPT",
            "sources": [],
            "textbook_visuals": [],
            "mentor_suggestions": [],
        },
    )

    response = client.post(
        "/api/doubt/answer",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "English",
            "chapter": "Nouns",
            "question": "What is a noun?",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


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


def test_student_without_cbse_subject_access_cannot_generate_mock_test(monkeypatch):
    """
    A custom CBSE plan should block mock tests for subjects outside the
    student's configured subject list.
    """
    profile = fake_student_profile(cbse_subjects=["Science", "Maths"])

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
            "subject": "English",
            "chapter": "Nouns",
            "mock_type": "CBSE Mock Test",
            "exam_type": "Class Test",
            "question_count": 1,
            "difficulty": "easy",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "CBSE English access is not enabled."


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
