from fastapi.testclient import TestClient

from app.main import app
import app.routes.mock_test as mock_test_route

client = TestClient(app)


def test_generate_cbse_mock_test_api_with_mocked_service(monkeypatch):
    """
    Test that the mock test API can generate a CBSE-style mock test.

    This test mocks generate_cbse_mock_test so it does not call any AI service
    or external dependency. It only checks that the route sends the right kind
    of response back to the frontend.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - questions should contain the mocked CBSE question.
    - message should confirm successful generation.
    """

    def fake_generate_cbse_mock_test(
        grade,
        subject,
        chapter,
        exam_type,
        num_questions,
        difficulty,
    ):
        return [
            {
                "id": 1,
                "section": "Science",
                "question": "What is matter?",
                "options": {
                    "A": "Mass",
                    "B": "Space",
                    "C": "Both mass and space",
                    "D": "None",
                },
                "answer": "C",
                "explanation": "Matter has mass and occupies space.",
                "marks": 1,
            }
        ]

    monkeypatch.setattr(
        mock_test_route,
        "generate_cbse_mock_test",
        fake_generate_cbse_mock_test,
    )

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "mock_type": "CBSE Mock Test",
        "exam_type": "Class Test",
        "question_count": 1,
        "difficulty": "easy",
    }

    response = client.post("/api/mock-test/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "What is matter?"
    assert data["questions"][0]["answer"] == "C"
    assert data["message"] == "Mock test generated successfully"


def test_generate_olympiad_mock_test_api_with_mocked_service(monkeypatch):
    """
    Test that the mock test API can generate an Olympiad-style mock test.

    This checks the special branch where mock_type is exactly:
    "SOF Olympiad Mock Test"

    In that case, the route should call generate_olympiad_mock_test instead
    of generate_cbse_mock_test.

    Expected result:
    - The endpoint should return HTTP 200.
    - success should be True.
    - questions should contain the mocked Olympiad question.
    """

    def fake_generate_olympiad_mock_test(
        olympiad,
        num_questions,
        difficulty,
        **kwargs,
    ):
        return [
            {
                "id": 1,
                "section": "Science",
                "question": "Which planet is known as the Red Planet?",
                "options": {
                    "A": "Earth",
                    "B": "Mars",
                    "C": "Venus",
                    "D": "Jupiter",
                },
                "answer": "B",
                "explanation": "Mars is called the Red Planet.",
                "marks": 1,
            }
        ]

    monkeypatch.setattr(
        mock_test_route,
        "generate_olympiad_mock_test",
        fake_generate_olympiad_mock_test,
    )

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "SOF",
        "subject": "Science Olympiad",
        "chapter": "General Science",
        "mock_type": "SOF Olympiad Mock Test",
        "exam_type": "Olympiad",
        "question_count": 1,
        "difficulty": "medium",
    }

    response = client.post("/api/mock-test/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert len(data["questions"]) == 1
    assert data["questions"][0]["answer"] == "B"


def test_generate_mock_test_response_has_valid_data_types(monkeypatch):
    """
    Test that the mock test API response has the expected data types.

    The frontend needs predictable response types so it can render the mock
    test screen safely.

    Expected result:
    - success should be a boolean.
    - questions should be a list.
    - message should be text.
    """

    def fake_generate_cbse_mock_test(
        grade,
        subject,
        chapter,
        exam_type,
        num_questions,
        difficulty,
    ):
        return []

    monkeypatch.setattr(
        mock_test_route,
        "generate_cbse_mock_test",
        fake_generate_cbse_mock_test,
    )

    payload = {
        "username": "test_user",
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Atoms and Molecules",
        "mock_type": "CBSE Mock Test",
        "exam_type": "Class Test",
        "question_count": 3,
        "difficulty": "easy",
    }

    response = client.post("/api/mock-test/generate", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["success"], bool)
    assert isinstance(data["questions"], list)
    assert isinstance(data["message"], str)
