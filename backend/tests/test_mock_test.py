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


def _allow_daily_limit(monkeypatch):
    """
    Free-tier requests now go through the real enforce_daily_limit(), which
    queries ai_usage_logs over the network. Tests that aren't specifically
    exercising the daily-cap behavior must stub it — otherwise they depend on
    real, accumulating DB state (how many mock tests this test username has
    already logged today), which makes them flaky/order-dependent instead of
    hermetic.
    """
    monkeypatch.setattr(
        mock_test_route, "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": True, "message": "Allowed", "usage": {}},
    )
    monkeypatch.setattr(mock_test_route, "log_ai_usage", lambda **kwargs: None)


def test_written_format_blocked_for_free_tier_user(monkeypatch):
    """A free-tier student calling the API directly must not get Written for free."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    _allow_daily_limit(monkeypatch)

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
    _allow_daily_limit(monkeypatch)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])

    response = client.post("/api/mock-test/generate", json=_base_payload(question_format="mixed"))

    assert response.status_code == 403
    assert "paid subscription" in response.json()["detail"]


def test_mcq_format_allowed_for_free_tier_user(monkeypatch):
    """MCQ stays free for everyone regardless of subscription tier."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    _allow_daily_limit(monkeypatch)
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


# ─────────────────────────────────────────────────────────────────────────────
# REGRESSION: free-tier daily mock-test cap (previously documented but never
# enforced server-side — FREE_MOCK_TEST_DAILY_LIMIT was read only for the
# parent dashboard's display text; nothing counted or blocked against it).
# ─────────────────────────────────────────────────────────────────────────────

def test_free_tier_blocked_once_daily_mock_test_limit_reached(monkeypatch):
    """A free-tier student who already used today's cap gets 429, not a test."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    generate_called = {"value": False}
    monkeypatch.setattr(
        mock_test_route, "generate_cbse_mock_test",
        lambda **kwargs: generate_called.__setitem__("value", True) or [],
    )
    monkeypatch.setattr(
        mock_test_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {
            "allowed": False,
            "message": "Daily limit reached",
            "usage": {"requests": max_requests},
        },
    )

    response = client.post("/api/mock-test/generate", json=_base_payload())

    assert response.status_code == 429
    assert response.json()["detail"] == mock_test_route.FREE_MOCK_TEST_LIMIT_MESSAGE
    assert generate_called["value"] is False  # never reached the question bank


def test_free_tier_allowed_under_daily_mock_test_limit(monkeypatch):
    """A free-tier student still under today's cap can generate normally."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])
    monkeypatch.setattr(
        mock_test_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {
            "allowed": True, "message": "Allowed", "usage": {"requests": 2},
        },
    )
    monkeypatch.setattr(mock_test_route, "log_ai_usage", lambda **kwargs: None)

    response = client.post("/api/mock-test/generate", json=_base_payload())

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_free_tier_generation_logs_usage_against_the_daily_cap(monkeypatch):
    """A successful free-tier generation must be counted, or the cap above is a no-op."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: True)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])
    monkeypatch.setattr(
        mock_test_route,
        "enforce_daily_limit",
        lambda username, feature, max_requests: {"allowed": True, "message": "Allowed", "usage": {}},
    )
    logged = {}
    monkeypatch.setattr(
        mock_test_route,
        "log_ai_usage",
        lambda **kwargs: logged.update(kwargs),
    )

    response = client.post("/api/mock-test/generate", json=_base_payload())

    assert response.status_code == 200
    assert logged.get("feature") == mock_test_route.MOCK_TEST_FREE_TIER_FEATURE


def test_paid_user_never_hits_the_daily_mock_test_limit(monkeypatch):
    """Paid users must not be metered by the free-tier cap at all."""
    monkeypatch.setattr(mock_test_route, "is_free_tier_user", lambda user_id: False)
    monkeypatch.setattr(mock_test_route, "generate_cbse_mock_test", lambda **kwargs: [])

    def fail_if_called(username, feature, max_requests):
        raise AssertionError("enforce_daily_limit must not be called for a paid user")

    monkeypatch.setattr(mock_test_route, "enforce_daily_limit", fail_if_called)

    response = client.post("/api/mock-test/generate", json=_base_payload())

    assert response.status_code == 200
    assert response.json()["success"] is True
