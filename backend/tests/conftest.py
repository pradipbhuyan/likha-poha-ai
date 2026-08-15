import pytest
from types import SimpleNamespace

from app.main import app
from app.services.auth_service import (
    get_current_user,
    require_parent,
    require_self_by_username,
)

import app.routes.doubt as doubt_route
import app.routes.lesson as lesson_route
import app.routes.mock_test as mock_test_route
import app.routes.profile as profile_route
import app.routes.progress as progress_route


TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_PARENT_ID = "22222222-2222-2222-2222-222222222222"


def fake_student_profile(**overrides):
    """
    Build a fake student profile for route tests.

    Tests can override access flags like:
        fake_student_profile(access_cbse=False)
    """
    profile = {
        "id": TEST_USER_ID,
        "user_id": TEST_USER_ID,
        "email": "test@example.com",
        "username": "test_user",
        "role": "student",
        "family_id": "test_family_id",
        "parent_id": "test_parent_id",
        "grade": "Grade 9",
        "mode": "CBSE",
        "account_status": "active",
        "subscription_plan": "free",
        "ai_model_preference": "default",
        "access_cbse": True,
        "cbse_subjects": [],
    }

    profile.update(overrides)
    return profile


def fake_admin_profile(**overrides):
    """
    Build a fake admin profile.

    Admin users should bypass course access checks.
    """
    profile = {
        "id": TEST_USER_ID,
        "user_id": TEST_USER_ID,
        "email": "admin@example.com",
        "username": "admin_user",
        "role": "admin",
        "family_id": None,
        "parent_id": None,
        "grade": None,
        "mode": None,
        "account_status": "active",
        "access_cbse": False,
    }

    profile.update(overrides)
    return profile


def fake_current_user(profile=None):
    """
    Build a fake authenticated user object.

    The real routes expect user.id, so this must be a SimpleNamespace,
    not a plain dictionary.
    """
    if profile is None:
        profile = fake_student_profile()

    return SimpleNamespace(
        id=profile["id"],
        email=profile["email"],
        username=profile["username"],
        role=profile["role"],
        profile=profile,
    )


def fake_parent():
    """
    Build a fake authenticated parent for parent-dashboard tests.
    """
    return {
        "id": TEST_PARENT_ID,
        "email": "parent@example.com",
        "username": "test_parent",
        "role": "parent",
        "profile": {
            "id": TEST_PARENT_ID,
            "email": "parent@example.com",
            "username": "test_parent",
            "role": "parent",
            "family_id": "test_family_id",
            "parent_id": None,
        },
    }


def patch_route_profile(monkeypatch, route_module, profile=None):
    """
    Patch one route module to use a fake profile.

    Use this inside specific tests when you need a different access setup.
    Example:
        patch_route_profile(
            monkeypatch,
            lesson_route,
            fake_student_profile(access_cbse=False),
        )
    """
    if profile is None:
        profile = fake_student_profile()

    user = fake_current_user(profile)

    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        route_module,
        "get_profile_by_user_id",
        lambda user_id: profile,
        raising=False,
    )

    if hasattr(route_module, "enforce_ai_token_limit"):
        monkeypatch.setattr(
            route_module,
            "enforce_ai_token_limit",
            lambda username: None,
            raising=False,
        )


@pytest.fixture(autouse=True)
def override_auth_dependencies(monkeypatch):
    """
    Automatically bypass authentication and profile lookup during tests.

    The real app requires Supabase auth and profile lookup for protected routes.
    Unit/API tests should not depend on real login tokens or real Supabase data.
    """

    fake_profile = fake_student_profile()
    fake_user = fake_current_user(fake_profile)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_parent] = lambda: fake_parent()

    # Routes that take a student username in the path (progress/profile/
    # recommendations) guard with require_self_by_username, which does a real
    # profile lookup. Tests get the same fake student the other guards use.
    app.dependency_overrides[require_self_by_username] = lambda: {
        "auth_user": fake_user,
        "profile": fake_profile,
    }

    # progress/profile derive the username from the session rather than the
    # request body, via a helper called inside the handler (not a dependency),
    # so it needs patching per route module rather than overriding.
    for _route_module in (progress_route, profile_route):
        monkeypatch.setattr(
            _route_module,
            "resolve_session_username",
            lambda _user, _u=fake_profile["username"]: _u,
            raising=False,
        )

    monkeypatch.setattr(
        doubt_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
        raising=False,
    )

    monkeypatch.setattr(
        lesson_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
        raising=False,
    )

    monkeypatch.setattr(
        mock_test_route,
        "get_profile_by_user_id",
        lambda user_id: fake_profile,
        raising=False,
    )

    monkeypatch.setattr(
        lesson_route,
        "enforce_ai_token_limit",
        lambda username: None,
        raising=False,
    )

    monkeypatch.setattr(
        doubt_route,
        "enforce_ai_token_limit",
        lambda username: None,
        raising=False,
    )

    monkeypatch.setattr(
        doubt_route,
        "save_doubt_history",
        lambda **kwargs: {"id": "history-1"},
        raising=False,
    )

    monkeypatch.setattr(
        lesson_route,
        "save_doubt_history",
        lambda **kwargs: {"id": "lesson-history-1"},
        raising=False,
    )

    monkeypatch.setattr(
        doubt_route,
        "list_doubt_history",
        lambda **kwargs: [],
        raising=False,
    )

    monkeypatch.setattr(
        mock_test_route,
        "enforce_ai_token_limit",
        lambda username: None,
        raising=False,
    )

    yield

    app.dependency_overrides.clear()
