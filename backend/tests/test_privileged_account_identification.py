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
  - QA test account: identified solely by the profiles.is_test_account flag.
    The transitional username fallback was removed once the column was
    populated and verified.

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
# Test account: the database flag is the only source of truth
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

    def test_none_profile_is_safe(self):
        assert is_all_access_test_user(None) is False

    def test_username_alone_no_longer_grants_access(self):
        """
        The transitional fallback is gone.

        profiles.is_test_account was populated on 2026-08-16 and verified, so
        the hard-coded username set was removed. Registering that name must no
        longer grant anything — which was the whole point of the flag.
        """
        assert is_all_access_test_user({"username": "akshita.teststudent"}) is False
        assert is_all_access_test_user({"username": "  Akshita.TestStudent  "}) is False

    def test_the_real_qa_account_still_works(self):
        """The provisioned account keeps its access via the flag."""
        assert is_all_access_test_user(
            {"username": "akshita.teststudent", "is_test_account": True}
        ) is True

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
        [
            "admin", "ADMIN", "PradipAdmin", "pradip-admin",
            "pradip_admin", "Pradip.Admin", "School Administrator",
            "admin2", "pradip", "Pradip", "  PRADIP  ", "akshita",
            "akshita.teststudent",
        ],
    )
    def test_reserved_names_are_rejected(self, name):
        with pytest.raises(Exception) as exc_info:
            auth_route._reject_reserved_username(name)
        assert getattr(exc_info.value, "status_code", None) == 400

    @pytest.mark.parametrize("name", ["Riya Sharma", "pradipa", "akshita2"])
    def test_ordinary_names_are_allowed(self, name):
        auth_route._reject_reserved_username(name)  # must not raise

    def test_every_signup_path_checks(self):
        """Every public account-creating endpoint must call the guard."""
        import inspect
        for fn in (
            auth_route.complete_signup,
            auth_route.signup_free,
            auth_route.teacher_signup,
            auth_route.signup_with_offer_code,
            auth_route.principal_signup,
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
        monkeypatch.setattr(auth_route.settings, "is_production", lambda: True)
        with pytest.raises(Exception) as exc_info:
            self._login()
        assert getattr(exc_info.value, "status_code", None) == 404

    def test_non_production_still_reachable(self, monkeypatch):
        """Local demo access and older tests must keep working."""
        monkeypatch.setattr(auth_route.settings, "is_production", lambda: False)
        result = self._login(password="definitely-wrong")
        # Reachable, and correctly rejects a bad password rather than 404ing.
        assert result.success is False


class TestProductionDetection:
    """
    Security gates must not depend on ENVIRONMENT alone.

    The deployed backend was found serving POST /api/auth/login with HTTP 200
    after that endpoint had supposedly been disabled "in production" — because
    ENVIRONMENT is not set on the host, so it defaulted to "development" and
    every `ENVIRONMENT == "production"` guard was inert. RENDER is injected by
    the platform and cannot be forgotten in a dashboard.
    """

    def _reload_config(self, monkeypatch, environment=None, render=None):
        import importlib
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("RENDER", raising=False)
        if environment is not None:
            monkeypatch.setenv("ENVIRONMENT", environment)
        if render is not None:
            monkeypatch.setenv("RENDER", render)
        import app.config as config_module
        return importlib.reload(config_module).settings

    def test_unset_environment_on_render_is_production(self, monkeypatch):
        """The exact configuration the live deployment was found in."""
        assert self._reload_config(monkeypatch, render="true").is_production() is True

    def test_explicit_production_is_production(self, monkeypatch):
        assert self._reload_config(monkeypatch, environment="production").is_production() is True

    def test_stale_environment_on_render_is_still_production(self, monkeypatch):
        """A leftover ENVIRONMENT value must not re-open a production gate."""
        assert self._reload_config(
            monkeypatch, environment="development", render="true"
        ).is_production() is True

    def test_local_and_ci_are_not_production(self, monkeypatch):
        assert self._reload_config(monkeypatch).is_production() is False
        assert self._reload_config(monkeypatch, environment="development").is_production() is False

    def teardown_method(self):
        """Leave app.config as the rest of the suite expects it."""
        import importlib
        import app.config
        importlib.reload(app.config)


# ─────────────────────────────────────────────────────────────────────────────
# The flag has to survive the trip to the client
# ─────────────────────────────────────────────────────────────────────────────
#
# The helper tests above all pass a profile dict in directly, so they stayed
# green while the account had no access at all. The break was in transport:
# GET /api/auth/profile never returned `is_test_account`, and that endpoint is
# what App.jsx reads on login, on app load, and on every profile refresh. The
# client assigns the field with no fallback, so an omitted field is not
# "unchanged" — it is set to false. Between the flag landing and the username
# fallback being deleted, the fallback masked this; deleting it took all QA
# access away.
#
# These tests assert the response contract rather than the helper, because the
# helper was never the thing that was wrong.

class TestFlagReachesTheClient:

    QA_PROFILE = {
        "id": "70d9e183", "email": "qa@example.test", "username": "akshita.teststudent",
        "role": "student", "grade": "Grade 11", "board": "CBSE",
        "parent_id": None, "family_id": "fam-qa",
        "subscription_plan": "free", "account_status": "active",
        "access_cbse": True, "access_sof_science": False,
        "access_sof_maths": True, "access_sof_english": False,
        "cbse_subjects": ["Physics"], "daily_token_limit": 50000,
        "monthly_token_limit": 1000000, "subscription_expires_at": None,
        "stream": "PCMB", "avatar": "boy3", "is_test_account": True,
    }

    def _get_profile(self, monkeypatch, profile):
        """Call GET /api/auth/profile against a stubbed profiles table."""
        from types import SimpleNamespace
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.auth_service import get_current_user

        class FQ:
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def update(self, *a, **kw): return self
            def single(self): return self
            def execute(self): return SimpleNamespace(data=[profile])

        monkeypatch.setattr(
            auth_route, "admin_client", SimpleNamespace(table=lambda _n: FQ())
        )
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=profile["id"], email=profile["email"]
        )
        try:
            with TestClient(app) as client:
                resp = client.get(
                    "/api/auth/profile",
                    headers={"Authorization": "Bearer fake-token"},
                )
            assert resp.status_code == 200, resp.text
            return resp.json()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_profile_endpoint_returns_the_flag(self, monkeypatch):
        """Omitting it revokes QA access on the client — this is the regression."""
        body = self._get_profile(monkeypatch, self.QA_PROFILE)
        assert "is_test_account" in body, (
            "GET /api/auth/profile dropped is_test_account. App.jsx reads this "
            "field on login and on every app load and assigns it with no "
            "fallback, so omitting it revokes the QA account's access."
        )
        assert body["is_test_account"] is True

    def test_profile_endpoint_reports_a_revoked_flag_as_false(self, monkeypatch):
        body = self._get_profile(
            monkeypatch, {**self.QA_PROFILE, "is_test_account": False}
        )
        assert body["is_test_account"] is False

    def test_profile_endpoint_returns_the_sof_flags(self, monkeypatch):
        """Same omission, same consequence — the client hard-falses these too."""
        body = self._get_profile(monkeypatch, self.QA_PROFILE)
        assert body["access_sof_science"] is False
        assert body["access_sof_maths"] is True
        assert body["access_sof_english"] is False

    def test_me_response_carries_every_entitlement_flag(self):
        """/auth/me feeds the same client fields and must agree with /profile."""
        from types import SimpleNamespace

        body = auth_route._build_me_response(
            SimpleNamespace(id=self.QA_PROFILE["id"], email=self.QA_PROFILE["email"]),
            self.QA_PROFILE,
        )
        for field in (
            "is_test_account",
            "access_cbse",
            "access_sof_science",
            "access_sof_maths",
            "access_sof_english",
        ):
            assert field in body, f"/auth/me dropped {field}"
        assert body["is_test_account"] is True
        assert body["access_sof_maths"] is True

    def test_both_endpoints_agree_on_the_entitlement_fields(self, monkeypatch):
        """
        The client reads entitlements from whichever of the two answered last.
        If they disagree on which fields exist, access flickers by login path.
        """
        from types import SimpleNamespace

        profile_body = self._get_profile(monkeypatch, self.QA_PROFILE)
        me_body = auth_route._build_me_response(
            SimpleNamespace(id=self.QA_PROFILE["id"], email=self.QA_PROFILE["email"]),
            self.QA_PROFILE,
        )
        entitlements = {
            "is_test_account", "access_cbse", "access_sof_science",
            "access_sof_maths", "access_sof_english", "stream", "grade",
            "cbse_subjects", "subscription_plan", "account_status",
        }
        missing_from_profile = entitlements - profile_body.keys()
        missing_from_me = entitlements - me_body.keys()
        assert not missing_from_profile, f"/auth/profile is missing {missing_from_profile}"
        assert not missing_from_me, f"/auth/me is missing {missing_from_me}"
        for field in entitlements:
            assert profile_body[field] == me_body[field], f"{field} disagrees"
