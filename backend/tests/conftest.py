import pytest
from types import SimpleNamespace

from app.main import app
from app.services.auth_service import get_current_user, require_parent

import app.routes.doubt as doubt_route
import app.routes.lesson as lesson_route
import app.routes.mock_test as mock_test_route




@pytest.fixture(autouse=True)
def override_auth_dependencies(monkeypatch):
    """
    Automatically bypass authentication and profile lookup during tests.

    The real app requires Supabase auth and profile lookup for protected routes.
    Unit/API tests should not depend on real login tokens or real Supabase data.
    """

    fake_profile = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "email": "test@example.com",
        "username": "test_user",
        "role": "student",
        "family_id": "test_family_id",
        "parent_id": "test_parent_id",
        "grade": "Grade 9",
        "mode": "CBSE",
        "account_status": "active",
        "access_cbse": True,
        "access_sof_science": True,
        "access_sof_maths": True,
        "access_sof_english": True,
    }

    fake_user = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        email="test@example.com",
        username="test_user",
        role="student",
        profile=fake_profile,
    )

    fake_parent = {
        "id": "22222222-2222-2222-2222-222222222222",
        "email": "parent@example.com",
        "username": "test_parent",
        "role": "parent",
        "profile": {
            "id": "22222222-2222-2222-2222-222222222222",
            "email": "parent@example.com",
            "username": "test_parent",
            "role": "parent",
            "family_id": "test_family_id",
            "parent_id": None,
        },
    }

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_parent] = lambda: fake_parent

    monkeypatch.setattr(
        doubt_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
    )

    monkeypatch.setattr(
        lesson_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
    )

    monkeypatch.setattr(
        mock_test_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
    )
    
    monkeypatch.setattr(
        lesson_route,
        "enforce_ai_token_limit",
        lambda username: None,
    )

    monkeypatch.setattr(
        doubt_route,
        "enforce_ai_token_limit",
        lambda username: None,
    )

    monkeypatch.setattr(
        mock_test_route,
        "enforce_ai_token_limit",
        lambda username: None,
    )

    yield

    app.dependency_overrides.clear()