from fastapi.testclient import TestClient

from app.main import app
import app.routes.mock_test as mock_test_route
from tests.conftest import fake_admin_profile, patch_route_profile

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


# ─────────────────────────────────────────────────────────────────────────────
# Written/Mixed format requires a paid subscription (server-side, not just UI)
# ─────────────────────────────────────────────────────────────────────────────

def _base_payload(**overrides):
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
    payload.update(overrides)
    return payload


def test_written_format_blocked_for_free_tier_user(monkeypatch):
    """A free-tier student calling the API directly must not get Written for free."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)

    called = {"generate": False}

    def fake_generate_cbse_mock_test(**kwargs):
        called["generate"] = True
        return []

    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", fake_generate_cbse_mock_test)

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="written"))

    assert response.status_code == 403
    assert "paid subscription" in response.json()["detail"]
    assert called["generate"] is False  # never reached the question bank


def test_mixed_format_blocked_for_free_tier_user(monkeypatch):
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="mixed"))

    assert response.status_code == 403
    assert "paid subscription" in response.json()["detail"]


def test_mcq_format_allowed_for_free_tier_user(monkeypatch):
    """MCQ stays free for everyone regardless of subscription tier."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="mcq"))

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_written_format_allowed_for_paid_user(monkeypatch):
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: False)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="written"))

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_written_format_allowed_for_admin_regardless_of_tier(monkeypatch):
    """Admins are exempt even if the (irrelevant) tier check would say free."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])
    patch_route_profile(monkeypatch, mock_test_route, fake_admin_profile())

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="written"))

    assert response.status_code == 200
    assert response.json()["success"] is True
