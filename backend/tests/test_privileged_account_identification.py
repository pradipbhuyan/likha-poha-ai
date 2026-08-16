"""
test_privileged_account_identification.py
══════════════════════════════════════════
Regression tests for go-live findings 06 and 07 — elevated access keyed on
usernames rather than on roles or provisioned flags.

Signup builds the profile with `"username": data.name.strip()`, taken from a
user-supplied field with no uniqueness constraint. Any username hard-coded in
shipped code is therefore a grant that anyone can claim by registering that
name. Two mechanisms were affected:

  - Admin: Sidebar.jsx, SalesCollateralPage.jsx and AnalyticsPage.jsx granted
    admin UI to `username === "pradip"`, and rag_service re-checked RAG upload
    authorization against {"admin", "pradip", "pradip admin"}. All admin
    authority now comes from the profile role, which is what the 90 admin
    endpoints already enforced.
  - QA test account: identified by a profiles.is_test_account flag, with the
    legacy username retained as a transitional fallback until the column is
    populated.

The legacy /api/auth/login path is also disabled in production here — a second
authentication path outside Supabase's session and lockout policy.

Run with:
    cd backend && python -m pytest tests/test_privileged_account_identification.py -v
"""

import pytest

from app.routes import auth as auth_route
from app.services import rag_service
from app.services.test_account_service import is_all_access_test_user


# ─────────────────────────────────────────────────────────────────────────────
# Test account: flag first, username only as a transitional fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestAllAccessTestAccount:

    def test_flag_grants_access(self):
        assert is_all_access_test_user({"username": "anyone", "is_test_account": True}) is True

    def test_flag_works_for_any_username(self):
        """A second QA account must not need a code change."""
        assert is_all_access_test_user(
            {"username": "qa.second.account", "is_test_account": True}
        ) is True

    def test_ordinary_account_is_not_a_test_account(self):
        assert is_all_access_test_user({"username": "real_student"}) is False
        assert is_all_access_test_user({"username": "real_student", "is_test_account": False}) is False

    def test_missing_flag_does_not_grant(self):
        """A profile loaded before the migration simply has no flag."""
        assert is_all_access_test_user({"username": "real_student"}) is False

    def test_none_profile_is_safe(self):
        assert is_all_access_test_user(None) is False

    def test_legacy_username_still_works_pre_migration(self):
        """
        The existing QA account must keep working before is_test_account is
        populated — deploys are automatic on push, so code can land first.
        """
        assert is_all_access_test_user({"username": "akshita.teststudent"}) is True
        assert is_all_access_test_user({"username": "  Akshita.TestStudent  "}) is True

    def test_flag_takes_priority_over_absent_username(self):
        assert is_all_access_test_user({"is_test_account": True}) is True


# ─────────────────────────────────────────────────────────────────────────────
# No username-keyed admin authority
# ─────────────────────────────────────────────────────────────────────────────

class TestNoUsernameKeyedAdmin:

    def test_rag_service_has_no_admin_username_set(self):
        """rag_service must not re-check authorization against literal names."""
        assert not hasattr(rag_service, "ADMIN_USERS")
        assert not hasattr(rag_service, "is_admin_upload_user")

    def test_upload_does_not_gate_on_username(self):
        """
        Assert against the function body, not its docstring — the docstring
        deliberately quotes the removed rejection message to explain why it
        went, and a naive substring check matches that explanation.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(rag_service.upload_textbook_text).lstrip())
        fn = tree.body[0]
        body = fn.body[1:] if ast.get_docstring(fn) else fn.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "is_admin_upload_user" not in code
        assert "Only an admin user can upload" not in code


# ─────────────────────────────────────────────────────────────────────────────
# Reserved usernames
# ─────────────────────────────────────────────────────────────────────────────

class TestReservedUsernames:

    @pytest.mark.parametrize(
        "name",
        ["admin", "pradip", "Pradip", "  PRADIP  ", "akshita", "akshita.teststudent"],
    )
    def test_reserved_names_are_rejected(self, name):
        with pytest.raises(Exception) as exc_info:
            auth_route._reject_reserved_username(name)
        assert getattr(exc_info.value, "status_code", None) == 400

    @pytest.mark.parametrize("name", ["Riya Sharma", "pradipa", "admin2", "akshita2"])
    def test_ordinary_names_are_allowed(self, name):
        auth_route._reject_reserved_username(name)  # must not raise

    def test_every_signup_path_checks(self):
        """All three account-creating endpoints must call the guard."""
        import inspect
        for fn in (
            auth_route.complete_signup,
            auth_route.signup_free,
            auth_route.signup_with_offer_code,
        ):
            src = inspect.getsource(fn)
            assert "_reject_reserved_username" in src, (
                f"{fn.__name__} must reject reserved usernames — otherwise a "
                f"name that grants elevated behaviour is claimable at signup."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Legacy login is not reachable in production
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacyLoginDisabledInProduction:

    def _login(self, username="admin", password="x"):
        from app.models.schemas import LoginRequest
        return auth_route.login(LoginRequest(username=username, password=password))

    def test_production_returns_404(self, monkeypatch):
        monkeypatch.setattr(auth_route.settings, "ENVIRONMENT", "production")
        with pytest.raises(Exception) as exc_info:
            self._login()
        assert getattr(exc_info.value, "status_code", None) == 404

    def test_non_production_still_reachable(self, monkeypatch):
        """Local demo access and older tests must keep working."""
        monkeypatch.setattr(auth_route.settings, "ENVIRONMENT", "development")
        result = self._login(password="definitely-wrong")
        # Reachable, and correctly rejects a bad password rather than 404ing.
        assert result.success is False
