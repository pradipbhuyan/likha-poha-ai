from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import fake_student_profile, patch_route_profile

import app.routes.doubt as doubt_route
import app.routes.lesson as lesson_route
import app.routes.mock_test as mock_test_route


client = TestClient(app)


GRADE_FIXTURES = [
    ("Grade 1", "EVS", "Uploaded Book Content"),
    ("Grade 2", "Maths", "Uploaded Book Content"),
    ("Grade 3", "English", "Uploaded Book Content"),
    ("Grade 4", "Science", "Uploaded Book Content"),
    ("Grade 5", "Social Science", "Uploaded Book Content"),
    ("Grade 6", "Science", "Uploaded Book Content"),
    ("Grade 7", "Maths", "Uploaded Book Content"),
    ("Grade 8", "English", "Uploaded Book Content"),
    ("Grade 9", "Science", "Cell: The Building Block of Life"),
    ("Grade 10", "Science", "Uploaded Book Content"),
]


def patch_all_grade_routes(monkeypatch, grade):
    """Patch auth/profile dependencies for all protected learning routes."""
    profile = fake_student_profile(grade=grade)

    for route_module in [lesson_route, doubt_route, mock_test_route]:
        patch_route_profile(monkeypatch, route_module, profile)


def test_students_from_grade_1_to_grade_10_can_generate_lessons(monkeypatch):
    """
    Every onboarded grade should be able to execute the lesson-generation path
    for content tagged to that same grade.
    """
    captured_grades = []

    def fake_generate_step_lesson(
        grade,
        subject,
        chapter,
        mode,
        step_title,
        teacher_persona="",
        username="unknown",
    ):
        captured_grades.append(grade)
        return {
            "lesson": f"{grade} lesson for {chapter}",
            "source_type": "MOCK",
            "sources": [],
        }

    monkeypatch.setattr(
        lesson_route,
        "generate_step_lesson",
        fake_generate_step_lesson,
    )

    for grade, subject, chapter in GRADE_FIXTURES:
        patch_all_grade_routes(monkeypatch, grade)

        response = client.post(
            "/api/lesson/generate",
            json={
                "username": "test_user",
                "grade": grade,
                "mode": "CBSE",
                "subject": subject,
                "chapter": chapter,
                "step_title": "Concept introduction",
                "teacher_persona": "Friendly Teacher",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["source_type"] == "MOCK"

    assert captured_grades == [grade for grade, _, _ in GRADE_FIXTURES]


def test_students_from_grade_1_to_grade_10_can_use_lesson_follow_up(monkeypatch):
    """Every onboarded grade should be able to ask a follow-up for its lesson."""
    captured_grades = []

    def fake_answer_lesson_follow_up(
        grade,
        mode,
        subject,
        chapter,
        step_title,
        lesson,
        question,
        username="unknown",
        **kwargs,
    ):
        captured_grades.append(grade)
        return {
            "answer": f"{grade} follow-up answer",
            "source_type": "MOCK",
            "sources": [],
        }

    monkeypatch.setattr(
        lesson_route,
        "answer_lesson_follow_up",
        fake_answer_lesson_follow_up,
    )

    for grade, subject, chapter in GRADE_FIXTURES:
        patch_all_grade_routes(monkeypatch, grade)

        response = client.post(
            "/api/lesson/follow-up",
            json={
                "username": "test_user",
                "grade": grade,
                "mode": "CBSE",
                "subject": subject,
                "chapter": chapter,
                "step_title": "Concept introduction",
                "lesson": "This is a lesson.",
                "question": "Can you explain this again?",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["source_type"] == "MOCK"

    assert captured_grades == [grade for grade, _, _ in GRADE_FIXTURES]


def test_students_from_grade_1_to_grade_10_can_ask_doubts(monkeypatch):
    """Every onboarded grade should be able to ask CBSE doubts for its grade."""
    captured_grades = []

    def fake_answer_doubt(grade, mode, subject, chapter, question, username, model=None, **kwargs):
        captured_grades.append(grade)
        return {
            "answer": f"{grade} doubt answer",
            "source_type": "MOCK",
            "sources": [],
            "mentor_suggestions": [],
        }

    monkeypatch.setattr(doubt_route, "answer_doubt", fake_answer_doubt)
    # Force a DKB miss so every grade actually reaches answer_doubt -- a
    # generic "Please explain this concept." question can now hit a real
    # DKB entry in at least one grade/subject after this session's
    # coverage-building work, which would short-circuit the route before
    # the mocked answer_doubt this test asserts against.
    monkeypatch.setattr(doubt_route, "search_doubt_kb", lambda **kwargs: None)

    for grade, subject, chapter in GRADE_FIXTURES:
        patch_all_grade_routes(monkeypatch, grade)

        response = client.post(
            "/api/doubt/answer",
            json={
                "username": "test_user",
                "grade": grade,
                "mode": "CBSE",
                "subject": subject,
                "chapter": chapter,
                "question": "Please explain this concept.",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["source_type"] == "MOCK"

    assert captured_grades == [grade for grade, _, _ in GRADE_FIXTURES]


def test_students_from_grade_1_to_grade_10_can_generate_mock_tests(monkeypatch):
    """Every onboarded grade should be able to generate a CBSE mock test."""
    captured_grades = []

    def fake_generate_cbse_mock_test(
        grade,
        subject,
        chapter,
        exam_type,
        num_questions,
        difficulty,
    ):
        captured_grades.append(grade)
        return [
            {
                "id": 1,
                "section": subject,
                "question": f"{grade} question",
                "options": {
                    "A": "Option A",
                    "B": "Option B",
                    "C": "Option C",
                    "D": "Option D",
                },
                "answer": "A",
                "explanation": "Mock explanation.",
                "marks": 1,
            }
        ]

    monkeypatch.setattr(
        mock_test_route,
        "generate_cbse_mock_test",
        fake_generate_cbse_mock_test,
    )

    for grade, subject, chapter in GRADE_FIXTURES:
        patch_all_grade_routes(monkeypatch, grade)

        response = client.post(
            "/api/mock-test/generate",
            json={
                "username": "test_user",
                "grade": grade,
                "mode": "CBSE",
                "subject": subject,
                "chapter": chapter,
                "mock_type": "CBSE Mock Test",
                "exam_type": "Class Test",
                "question_count": 1,
                "difficulty": "easy",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["questions"][0]["question"] == f"{grade} question"

    assert captured_grades == [grade for grade, _, _ in GRADE_FIXTURES]


def test_student_cannot_request_learning_content_for_another_grade(monkeypatch):
    """Backend grade enforcement should block manual cross-grade API requests."""
    patch_all_grade_routes(monkeypatch, "Grade 5")

    response = client.post(
        "/api/lesson/generate",
        json={
            "username": "test_user",
            "grade": "Grade 9",
            "mode": "CBSE",
            "subject": "Science",
            "chapter": "Cell: The Building Block of Life",
            "step_title": "Concept introduction",
            "teacher_persona": "Friendly Teacher",
        },
    )

    assert response.status_code == 403
    assert "Grade 5" in response.json()["detail"]
