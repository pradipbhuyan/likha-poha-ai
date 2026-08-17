"""
test_public_data_exposure.py
═════════════════════════════
Regression tests for the children's-data exposure found by probing the
deployed API on 2026-08-17.

GET /api/analytics/leaderboard had no auth dependency while every other route
in analytics.py did — including require_self_or_admin on the one directly
below it. It was public by accident, and it returned children's first names
alongside their test counts and scores. 19 students were listed in production,
15 with real-looking names.

Two things made it worse than one open endpoint:

  - GET /api/auth/lookup-email/{username} is also public (it has to be; it
    runs before sign-in) and resolves a username to an email address. It had
    no rate limit, so the leaderboard's list of names converted directly into
    a list of children's email addresses.
  - /docs, /redoc and /openapi.json were served publicly, publishing all 407
    endpoints. Finding the unguarded route required no guessing at all.

Run with:
    cd backend && python -m pytest tests/test_public_data_exposure.py -v
"""

from fastapi.routing import APIRoute

from app.config import Settings
from app.main import app
from app.services.auth_service import get_current_user


def _guards_for(path: str, method: str) -> set:
    """Every dependency callable in a route's resolved dependency tree."""
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method.upper() in route.methods:
            found = set()

            def walk(dependant):
                if dependant.call is not None:
                    found.add(dependant.call)
                for sub in dependant.dependencies:
                    walk(sub)

            for sub in route.dependant.dependencies:
                walk(sub)
            return found
    raise AssertionError(f"Route not registered: {method.upper()} {path}")


# ─────────────────────────────────────────────────────────────────────────────
# The leaderboard is not public
# ─────────────────────────────────────────────────────────────────────────────

class TestLeaderboardRequiresAuth:

    def test_leaderboard_requires_authentication(self):
        guards = _guards_for("/api/analytics/leaderboard", "GET")
        assert get_current_user in guards, (
            "GET /api/analytics/leaderboard must require authentication — it "
            "returns children's names alongside their test scores."
        )

    def test_no_analytics_route_is_unauthenticated(self):
        """
        Catches the next one. This route was missed originally because a
        line-based scan attributed the guard from the following route to it.
        """
        unguarded = []
        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue
            if not route.path.startswith("/api/analytics/"):
                continue
            method = sorted(route.methods)[0]
            guards = _guards_for(route.path, method)
            names = {getattr(g, "__name__", "") for g in guards}
            if not any("require_" in n or n == "get_current_user" for n in names):
                unguarded.append(f"{method} {route.path}")

        assert not unguarded, f"Unauthenticated analytics routes: {unguarded}"


# ─────────────────────────────────────────────────────────────────────────────
# Username → email lookup is rate limited
# ─────────────────────────────────────────────────────────────────────────────

class TestEmailLookupIsRateLimited:

    def test_lookup_email_has_a_rate_limiter(self):
        """
        It cannot be authenticated — it runs before sign-in — so the limit is
        the only thing standing between a list of usernames and a list of
        email addresses.
        """
        import inspect

        from app.routes.auth import lookup_email

        sig = inspect.signature(lookup_email)
        assert "_rl" in sig.parameters, (
            "GET /api/auth/lookup-email/{username} must be rate limited — it "
            "is a public username-to-email enumeration primitive."
        )

    def test_limiter_is_tighter_than_login(self):
        """A real user hits this once per sign-in; bulk callers are not real."""
        from app.services.rate_limit_service import EMAIL_LOOKUP_LIMITER, LOGIN_LIMITER

        assert EMAIL_LOOKUP_LIMITER.max_calls <= LOGIN_LIMITER.max_calls


# ─────────────────────────────────────────────────────────────────────────────
# Interactive docs are not published in production
# ─────────────────────────────────────────────────────────────────────────────

class TestApiDocsDisabledInProduction:
    """
    Tests the pure decision function, not a reloaded app.

    An earlier version of this file reloaded app.main under different env vars
    to inspect app.docs_url. That swapped module identity out from under the
    dependency-override keys conftest installs, and broke 29 unrelated tests
    elsewhere in the suite. Settings.docs_urls() exists so this can be checked
    without touching sys.modules.
    """

    def test_disabled_on_render(self, monkeypatch):
        """The exact configuration production runs in: RENDER set, ENVIRONMENT unset."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("RENDER", "true")
        assert Settings.docs_urls() == (None, None, None)

    def test_disabled_with_explicit_production(self, monkeypatch):
        monkeypatch.delenv("RENDER", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert Settings.docs_urls() == (None, None, None)

    def test_available_locally(self, monkeypatch):
        """They are genuinely useful in development and stay on there."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        assert Settings.docs_urls() == ("/docs", "/redoc", "/openapi.json")

    def test_app_is_built_from_that_decision(self):
        """Guards against the constructor drifting away from the helper."""
        import inspect

        import app.main as main_module

        src = inspect.getsource(main_module)
        assert "settings.docs_urls()" in src
        assert "docs_url=_docs_url" in src
        assert "openapi_url=_openapi_url" in src


# ─────────────────────────────────────────────────────────────────────────────
# The chain, stated as one test
# ─────────────────────────────────────────────────────────────────────────────

def test_no_unauthenticated_path_from_anonymous_to_child_pii():
    """
    Anonymous → children's names → their email addresses, in two public
    requests. Breaking any link breaks the chain; this asserts the first one
    is closed and the second is throttled.
    """
    import inspect

    from app.routes.auth import lookup_email

    assert get_current_user in _guards_for("/api/analytics/leaderboard", "GET"), (
        "link 1: the leaderboard must not publish children's names anonymously"
    )
    assert "_rl" in inspect.signature(lookup_email).parameters, (
        "link 2: username-to-email lookup must be throttled"
    )
