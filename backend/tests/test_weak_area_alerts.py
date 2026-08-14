from fastapi.testclient import TestClient

from app.main import app
import app.routes.weak_area_alerts as weak_area_alerts_route
from tests.conftest import TEST_USER_ID, fake_current_user, fake_student_profile
from app.services.auth_service import get_current_user

client = TestClient(app)


class _ChainMock:
    """Records the insert payload, then returns it as the insert response."""
    def __init__(self):
        self.inserted = None

    def table(self, name):
        return self

    def insert(self, payload):
        self.inserted = payload
        return self

    def execute(self):
        return type("Resp", (), {"data": [self.inserted]})()


def _payload(**overrides):
    body = {
        "grade": "Grade 9",
        "mode": "CBSE",
        "subject": "Science",
        "chapter": "Matter in Our Surroundings",
        "step_title": "Quick check",
        "step_index": 2,
        "attempts": 3,
        "best_score": 40,
    }
    body.update(overrides)
    return body


def test_username_is_derived_from_authenticated_profile_not_request_body(monkeypatch):
    """
    Regression test: this endpoint used to trust a client-supplied `username`
    field with no auth at all, letting anyone spoof alerts for any account.
    The request no longer even has a username field — it must come from the
    authenticated user's own profile.
    """
    profile = fake_student_profile(username="real_logged_in_student")
    monkeypatch.setattr(weak_area_alerts_route, "get_user_profile", lambda user_id: profile)
    chain = _ChainMock()
    monkeypatch.setattr(weak_area_alerts_route, "supabase", chain)

    response = client.post("/api/weak-area-alerts/save", json=_payload())

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert chain.inserted["username"] == "real_logged_in_student"


def test_client_supplied_username_field_is_ignored(monkeypatch):
    """Even if a caller sends a username in the body, it can't override the real one."""
    profile = fake_student_profile(username="real_logged_in_student")
    monkeypatch.setattr(weak_area_alerts_route, "get_user_profile", lambda user_id: profile)
    chain = _ChainMock()
    monkeypatch.setattr(weak_area_alerts_route, "supabase", chain)

    response = client.post(
        "/api/weak-area-alerts/save",
        json=_payload(username="someone_elses_account"),
    )

    assert response.status_code == 200
    assert chain.inserted["username"] == "real_logged_in_student"
    assert chain.inserted["username"] != "someone_elses_account"


def test_missing_profile_is_rejected(monkeypatch):
    monkeypatch.setattr(weak_area_alerts_route, "get_user_profile", lambda user_id: None)
    chain = _ChainMock()
    monkeypatch.setattr(weak_area_alerts_route, "supabase", chain)

    response = client.post("/api/weak-area-alerts/save", json=_payload())

    assert response.status_code == 403
    assert chain.inserted is None  # never reached the insert


def test_requires_authentication():
    """With no fake-auth override at all, an unauthenticated caller must be rejected."""
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post("/api/weak-area-alerts/save", json=_payload())
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_user] = lambda: fake_current_user()
