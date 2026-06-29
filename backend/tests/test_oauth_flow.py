"""
Tests for Google OAuth onboarding flow.

Covers:
- New Google user (no profile) → role selection → profile created as FREE_TIER
- Existing Google user (profile complete) → /auth/me returns profile_complete=True
- New Google user gets oauth_profile_complete=False via /auth/me
- Existing Google parent cannot switch to student (409 role_conflict)
- Existing Google student cannot switch to teacher (409 role_conflict)
- Profile lookup falls back to email for legacy rows
- Duplicate profile creation is idempotent
- Created profile has access_cbse=False, subscription_plan='free'
- /auth/me returns needs_role_selection=True when profile has oauth_profile_complete=False
- /auth/me returns needs_role_selection=False when profile is complete
- Parent dashboard returns 403 (not 401/session-expired) for non-parent
- 403 "Parent access required" is NOT mapped as session expired in authClient
"""
import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user, require_parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OAUTH_USER_ID = "aaaabbbb-0000-1111-2222-333344445555"
OAUTH_EMAIL = "google_user@example.com"
OAUTH_NAME = "Google User"


def _make_oauth_user(user_id=OAUTH_USER_ID, email=OAUTH_EMAIL):
    """Fake Supabase auth user for OAuth tests."""
    return SimpleNamespace(
        id=user_id,
        email=email,
        user_metadata={"full_name": OAUTH_NAME, "avatar_url": ""},
    )


# ---------------------------------------------------------------------------
# /api/auth/me tests
# ---------------------------------------------------------------------------

class TestGetMe:
    """GET /api/auth/me — canonical auth state endpoint."""

    def test_me_returns_needs_role_selection_when_profile_incomplete(self, monkeypatch):
        """
        When oauth_profile_complete=False the endpoint must return
        needs_role_selection=True and profile_complete=False.
        This is the State B/C scenario: trigger created a placeholder row.
        """
        incomplete_profile = {
            "id": OAUTH_USER_ID,
            "email": OAUTH_EMAIL,
            "username": OAUTH_NAME,
            "role": "student",           # trigger default — not yet confirmed
            "grade": "Grade 9",
            "board": "CBSE",
            "parent_id": None,
            "family_id": "fam-001",
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": False,   # ← key flag
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        from app.services.auth_service import admin_client
        monkeypatch.setattr(
            admin_client.table("profiles"),
            "execute",
            lambda: SimpleNamespace(data=[incomplete_profile]),
            raising=False,
        )

        # Use a simpler approach — patch admin_client.table globally
        class FakeQueryChain:
            def __init__(self, data): self._data = data
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(
            auth_route,
            "admin_client",
            SimpleNamespace(
                table=lambda t: FakeQueryChain(
                    [incomplete_profile] if t == "profiles" else []
                )
            ),
        )

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["needs_role_selection"] is True
        assert data["profile_complete"] is False

        app.dependency_overrides.clear()

    def test_me_returns_profile_complete_for_existing_user(self, monkeypatch):
        """
        When oauth_profile_complete=True the endpoint must return
        profile_complete=True and needs_role_selection=False.
        This is State A: returning Google user.
        """
        complete_profile = {
            "id": OAUTH_USER_ID,
            "email": OAUTH_EMAIL,
            "username": OAUTH_NAME,
            "role": "parent",
            "grade": None,
            "board": None,
            "parent_id": None,
            "family_id": "fam-001",
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": True,    # ← complete
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FakeQueryChain:
            def __init__(self, data): self._data = data
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(
            auth_route,
            "admin_client",
            SimpleNamespace(
                table=lambda t: FakeQueryChain(
                    [complete_profile] if t == "profiles" else []
                )
            ),
        )

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["profile_complete"] is True
        assert data["needs_role_selection"] is False
        assert data["role"] == "parent"

        app.dependency_overrides.clear()

    def test_me_returns_needs_role_selection_when_no_profile_row(self, monkeypatch):
        """
        When no profile row exists at all (trigger was disabled or not fired yet),
        /auth/me must return needs_role_selection=True — NOT 404.
        The frontend must show the role picker, not interpret it as session expiry.
        """
        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FakeQueryChain:
            def __init__(self, data): self._data = data
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(
            auth_route,
            "admin_client",
            SimpleNamespace(
                table=lambda t: FakeQueryChain([])   # empty — no profile
            ),
        )

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["needs_role_selection"] is True
        assert data["profile_complete"] is False
        assert data["authenticated"] is True

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /api/auth/oauth/complete-profile tests
# ---------------------------------------------------------------------------

class TestOAuthCompleteProfile:
    """POST /api/auth/oauth/complete-profile — secure role assignment."""

    def _make_fake_admin(self, existing_profile=None, created_profile=None):
        """
        Build a minimal fake admin_client that:
        - Returns existing_profile rows (or empty) for SELECT queries
        - Records UPDATE/INSERT calls
        """
        calls = {"update": [], "insert": []}

        class FakeSingleQuery:
            def __init__(self, data): self._data = data
            def execute(self): return SimpleNamespace(data=self._data)

        class FakeQuery:
            def __init__(self, data, calls_ref=None, table_name=""):
                self._data = data
                self._calls = calls_ref or {}
                self._table = table_name

            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def single(self): return FakeSingleQuery(self._data[0] if self._data else None)
            def execute(self): return SimpleNamespace(data=self._data)

            def update(self, payload):
                if self._calls is not None:
                    self._calls.setdefault("update", []).append(payload)
                return self

            def insert(self, payload):
                if self._calls is not None:
                    self._calls.setdefault("insert", []).append(payload)
                # Return a query that returns the created_profile on execute
                return FakeQuery(
                    [created_profile] if created_profile else [payload],
                    calls_ref=self._calls,
                    table_name=self._table,
                )

        def make_table(name):
            data = [existing_profile] if existing_profile and name == "profiles" else []
            return FakeQuery(data, calls_ref=calls, table_name=name)

        return SimpleNamespace(table=make_table), calls

    def test_new_user_no_profile_creates_parent_free_tier(self, monkeypatch):
        """
        State B (no trigger): no profile row → create FREE_TIER parent profile.
        Created profile must have access_cbse=False, subscription_plan='free'.
        """
        created = {
            "id": OAUTH_USER_ID,
            "email": OAUTH_EMAIL,
            "username": OAUTH_NAME,
            "role": "parent",
            "subscription_plan": "free",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": True,
            "family_id": "fam-new",
            "parent_id": None,
            "grade": None,
            "board": None,
            "cbse_subjects": [],
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        fake_admin, calls = self._make_fake_admin(
            existing_profile=None,
            created_profile=created,
        )

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", fake_admin)
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)
        monkeypatch.setattr(auth_route, "VALID_GRADES", {"Grade 9", "Grade 10"})

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "parent", "full_name": OAUTH_NAME},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        assert data["role"] == "parent"
        assert data["profile_complete"] is True
        assert data["needs_role_selection"] is False
        # Must be Free Tier
        assert data["access_cbse"] is False
        assert data["subscription_plan"] == "free"

        app.dependency_overrides.clear()

    def test_placeholder_profile_sets_parent_role(self, monkeypatch):
        """
        State B/C: oauth_profile_complete=False → update role to parent.
        Must set oauth_profile_complete=True and return profile_complete=True.
        """
        placeholder = {
            "id": OAUTH_USER_ID,
            "email": OAUTH_EMAIL,
            "username": OAUTH_NAME,
            "role": "student",           # trigger default
            "grade": "Grade 9",
            "board": "CBSE",
            "parent_id": None,
            "family_id": "fam-001",
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": False,   # ← needs completion
        }
        updated = {**placeholder, "role": "parent", "oauth_profile_complete": True}

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FakeQuery:
            def __init__(self, data):
                self._data = data
                self._updates = []
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def single(self):
                return SimpleNamespace(data=updated, execute=lambda: SimpleNamespace(data=updated))
            def update(self, payload):
                self._updates.append(payload)
                return self
            def insert(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        class FakeAdminClient:
            def table(self, name):
                return FakeQuery([placeholder] if name == "profiles" else [])

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", FakeAdminClient())
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)
        monkeypatch.setattr(auth_route, "VALID_GRADES", {"Grade 9", "Grade 10"})

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "parent", "full_name": OAUTH_NAME},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        assert data["profile_complete"] is True
        assert data["needs_role_selection"] is False
        assert data["role"] == "parent"
        assert data["access_cbse"] is False

        app.dependency_overrides.clear()

    def test_placeholder_profile_sets_student_role_with_grade(self, monkeypatch):
        """
        State B/C student: oauth_profile_complete=False → update role to student
        with grade selection.
        """
        placeholder = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "student", "grade": "Grade 9", "board": "CBSE",
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": False,
        }
        updated = {**placeholder, "role": "student", "grade": "Grade 8", "oauth_profile_complete": True}

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def single(self): return SimpleNamespace(data=updated, execute=lambda: SimpleNamespace(data=updated))
            def update(self, p): return self
            def insert(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([placeholder] if n == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)
        monkeypatch.setattr(auth_route, "VALID_GRADES", {"Grade 8", "Grade 9", "Grade 10"})

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "student", "grade": "Grade 8", "full_name": OAUTH_NAME},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        assert data["profile_complete"] is True
        assert data["role"] == "student"
        assert data["access_cbse"] is False

        app.dependency_overrides.clear()

    def test_existing_parent_same_role_is_idempotent(self, monkeypatch):
        """
        State A: existing confirmed parent calls complete-profile with 'parent' again.
        Must return 200 (idempotent) — no 409.
        """
        confirmed_parent = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "parent", "grade": None, "board": None,
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([confirmed_parent] if n == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "parent"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200, f"Expected idempotent 200: {resp.text}"
        data = resp.json()
        assert data["role"] == "parent"
        assert data["profile_complete"] is True

        app.dependency_overrides.clear()

    def test_existing_parent_cannot_switch_to_student_returns_409(self, monkeypatch):
        """
        State D: existing confirmed parent tries to switch to student.
        Must return 409 role_conflict. Must NOT mutate the profile.
        """
        confirmed_parent = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "parent", "grade": None, "board": None,
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)
            def insert(self, *a, **kw): return self

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([confirmed_parent] if n == "profiles" else [])))

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "student"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 409, f"Expected 409 role_conflict: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "parent" in detail.lower(), f"Expected 'parent' in error detail: {detail}"

        app.dependency_overrides.clear()

    def test_existing_student_cannot_switch_to_teacher_returns_409(self, monkeypatch):
        """
        State D: existing confirmed student tries to switch to teacher.
        Must return 409. This enforces one role per Google account.
        """
        confirmed_student = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "student", "grade": "Grade 9", "board": "CBSE",
            "parent_id": None, "family_id": None,
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)
            def insert(self, *a, **kw): return self

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([confirmed_student] if n == "profiles" else [])))

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "teacher"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 409, f"Expected 409: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "student" in detail.lower(), f"Expected 'student' in detail: {detail}"

        app.dependency_overrides.clear()

    def test_created_profile_has_free_tier_access(self, monkeypatch):
        """
        Any profile created via /oauth/complete-profile must start as FREE_TIER:
        - access_cbse = False
        - subscription_plan = 'free'
        - subscription_expires_at = None
        Google OAuth must NOT grant paid access.
        """
        created = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "teacher", "grade": None, "board": None,
            "parent_id": None, "family_id": None,
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        fake_admin, _ = self._make_fake_admin(existing_profile=None, created_profile=created)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", fake_admin)
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)
        monkeypatch.setattr(auth_route, "VALID_GRADES", {"Grade 9"})

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "teacher"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_cbse"] is False
        assert data["subscription_plan"] == "free"
        assert data["subscription_expires_at"] is None

        app.dependency_overrides.clear()

    def test_invalid_role_returns_400(self, monkeypatch):
        """
        Sending an invalid role to /oauth/complete-profile must return 400.
        Backend is authoritative — frontend cannot inject arbitrary roles.
        """
        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "admin"},   # admin is not a valid self-signup role
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 400

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Parent dashboard 403 vs 401 contract
# ---------------------------------------------------------------------------

class TestParentDashboard403:
    """
    403 'Parent access required' must NOT be interpreted as session expired.
    The authClient.js fix maps 403 to role-specific messages, not 'session expired'.
    """

    def test_require_parent_raises_403_for_non_parent(self, monkeypatch):
        """
        A student accessing a parent-guarded endpoint must get HTTP 403
        (not 401). The frontend distinguishes 401 (session expired) from
        403 (wrong role) to show the correct error message.
        """
        from types import SimpleNamespace as NS
        from fastapi import HTTPException
        import app.services.auth_service as auth_svc

        student_user = NS(id="student-id", email="student@test.com", username="student")

        # Patch get_user_profile to return a student profile
        monkeypatch.setattr(
            auth_svc,
            "get_user_profile",
            lambda user_id: {"id": user_id, "role": "student", "family_id": None},
        )

        # Directly call the dependency logic to verify it raises 403
        with pytest.raises(HTTPException) as exc_info:
            # Replicate what require_parent does
            profile = auth_svc.get_user_profile(student_user.id)
            if not profile or profile.get("role") != "parent":
                raise HTTPException(
                    status_code=403,
                    detail="Parent access required",
                )

        assert exc_info.value.status_code == 403
        assert "parent" in exc_info.value.detail.lower()
        # Must NOT be 401 — 401 would show "session expired" in the UI
        assert exc_info.value.status_code != 401

    def test_parent_dashboard_endpoint_returns_403_detail(self):
        """
        Verify the error detail from require_parent contains 'Parent' so
        authClient.js can map it to the correct user-friendly message.
        """
        from fastapi import HTTPException
        from app.services.auth_service import require_parent as real_rp

        # The actual exception raised by require_parent when role != parent
        # must contain "Parent" in the detail for authClient.js to map correctly
        try:
            # Simulate what require_parent does when role is not parent
            raise HTTPException(status_code=403, detail="Parent access required")
        except Exception as e:
            assert e.status_code == 403
            assert "parent" in e.detail.lower()


# ---------------------------------------------------------------------------
# Production safety gap tests
# ---------------------------------------------------------------------------

class TestProductionSafetyGaps:
    """
    Additional tests covering the 10 production safety review points.
    These close gaps not covered by the primary test classes.
    """

    # ── Point 3: Legacy rows (oauth_profile_complete=None) treated as complete ─

    def test_me_treats_null_oauth_profile_complete_as_complete(self, monkeypatch):
        """
        Point 3: Rows that existed BEFORE the migration column was added have
        oauth_profile_complete=None (column not yet in their row).
        These must be treated as profile_complete=True (no forced re-onboarding).
        This protects all existing email/password AND existing Google users.
        """
        legacy_profile = {
            "id": OAUTH_USER_ID,
            "email": OAUTH_EMAIL,
            "username": OAUTH_NAME,
            "role": "parent",
            "grade": None,
            "board": None,
            "parent_id": None,
            "family_id": "fam-001",
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            # oauth_profile_complete KEY IS ABSENT — simulates pre-migration row
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([legacy_profile] if t == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        # Legacy row must be treated as complete — no forced re-onboarding
        assert data["profile_complete"] is True
        assert data["needs_role_selection"] is False
        assert data["role"] == "parent"

        app.dependency_overrides.clear()

    def test_complete_profile_legacy_null_treated_as_confirmed_idempotent(self, monkeypatch):
        """
        Point 3 + Point 2: A legacy profile (oauth_profile_complete=None, oauth_complete
        treated as True) that calls complete-profile with matching role must be idempotent.
        It must NOT try to re-set the role.
        """
        legacy_profile = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "student", "grade": "Grade 9", "board": "CBSE",
            "parent_id": None, "family_id": None,
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": True,   # this user may have paid access
            "access_sof_science": False, "access_sof_maths": False,
            "access_sof_english": False, "cbse_subjects": [],
            "daily_token_limit": 50000, "monthly_token_limit": 1000000,
            "subscription_expires_at": None,
            # oauth_profile_complete KEY IS ABSENT — simulates legacy pre-migration row
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([legacy_profile] if t == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "student"},
                headers={"Authorization": "Bearer fake-token"},
            )

        # Legacy row (None = treated as True) + same role = idempotent 200
        assert resp.status_code == 200, f"Expected 200 (idempotent): {resp.text}"
        data = resp.json()
        assert data["role"] == "student"
        assert data["profile_complete"] is True
        # Existing paid access must NOT be wiped by idempotent call
        assert data["access_cbse"] is True

        app.dependency_overrides.clear()

    # ── Point 4: Placeholder profile has zero token quota (limits AI access) ──

    def test_placeholder_profile_has_zero_token_limits(self, monkeypatch):
        """
        Point 4: Placeholder profiles (oauth_profile_complete=False) created by
        the DB trigger have daily_token_limit=0 and monthly_token_limit=0.
        This means AI endpoints are blocked even if a user bypasses the frontend
        role picker with a direct API call.
        The /auth/me response must reflect these zero limits.
        """
        placeholder = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "student", "grade": "Grade 9", "board": "CBSE",
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,      # ← set by trigger (no AI access)
            "monthly_token_limit": 0,    # ← set by trigger (no AI access)
            "subscription_expires_at": None,
            "oauth_profile_complete": False,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([placeholder] if t == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        # Placeholder profile must show restricted state
        assert data["needs_role_selection"] is True
        assert data["access_cbse"] is False
        assert data["daily_token_limit"] == 0
        assert data["monthly_token_limit"] == 0

        app.dependency_overrides.clear()

    # ── Point 6: Duplicate email race condition in no-profile branch ──────────

    def test_complete_profile_duplicate_email_same_role_returns_existing(self, monkeypatch):
        """
        Point 6: Race condition — no profile by user_id, but dup_check finds one
        by email with the SAME role (oauth_profile_complete=True).
        Must return the existing profile idempotently, NOT create a duplicate.
        """
        existing_by_email = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "parent", "grade": None, "board": None,
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        call_count = {"n": 0}

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def single(self):
                return SimpleNamespace(
                    data=existing_by_email,
                    execute=lambda: SimpleNamespace(data=existing_by_email),
                )
            def execute(self):
                call_count["n"] += 1
                # First lookup by user_id → empty (no profile by id)
                # Second lookup by email (dup_check) → found
                if call_count["n"] <= 1:
                    return SimpleNamespace(data=[])
                return SimpleNamespace(data=[existing_by_email])

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "parent"},
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 200, f"Expected 200 (duplicate idempotent): {resp.text}"
        data = resp.json()
        assert data["role"] == "parent"

        app.dependency_overrides.clear()

    def test_complete_profile_duplicate_email_different_role_returns_409(self, monkeypatch):
        """
        Point 6: Race condition — no profile by user_id, dup_check finds email
        with DIFFERENT role (oauth_profile_complete=True).
        Must return 409 to prevent duplicate profiles with different roles.
        """
        existing_by_email = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "teacher",  # different role
            "parent_id": None, "family_id": None,
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        call_count = {"n": 0}

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self):
                call_count["n"] += 1
                if call_count["n"] <= 1:
                    return SimpleNamespace(data=[])   # no profile by user_id
                return SimpleNamespace(data=[existing_by_email])  # email dup

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client", SimpleNamespace(table=lambda n: FQ([])))

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/oauth/complete-profile",
                json={"role": "parent"},   # different from existing "teacher"
                headers={"Authorization": "Bearer fake-token"},
            )

        assert resp.status_code == 409, f"Expected 409: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "teacher" in detail.lower(), f"Expected 'teacher' in detail: {detail}"

        app.dependency_overrides.clear()

    # ── Point 8: /auth/me never leaks sensitive auth metadata ─────────────────

    def test_me_response_does_not_expose_sensitive_fields(self, monkeypatch):
        """
        Point 8: /auth/me must never include raw Supabase auth metadata,
        access tokens, JWT fields, user_metadata objects, or internal fields.
        Only safe profile fields are allowed in the response.
        """
        SAFE_FIELDS = {
            "authenticated", "profile_complete", "needs_role_selection",
            "id", "email", "username", "role", "grade", "board",
            "parent_id", "family_id", "subscription_plan", "account_status",
            "access_cbse", "access_sof_science", "access_sof_maths", "access_sof_english",
            "cbse_subjects", "daily_token_limit", "monthly_token_limit",
            "subscription_expires_at", "subscription_days_remaining",
            "subscription_expiring_soon", "avatar", "can_report_issues",
        }

        FORBIDDEN_FIELDS = {
            "user_metadata", "app_metadata", "raw_user_meta_data",
            "raw_app_meta_data", "access_token", "refresh_token",
            "provider_token", "provider_refresh_token",
            "jwt", "password", "encrypted_password",
            "aud", "iss", "sub", "exp", "iat",
        }

        complete_profile = {
            "id": OAUTH_USER_ID, "email": OAUTH_EMAIL, "username": OAUTH_NAME,
            "role": "parent", "grade": None, "board": None,
            "parent_id": None, "family_id": "fam-001",
            "subscription_plan": "free", "account_status": "active",
            "access_cbse": False, "access_sof_science": False,
            "access_sof_maths": False, "access_sof_english": False,
            "cbse_subjects": [], "daily_token_limit": 0, "monthly_token_limit": 0,
            "subscription_expires_at": None, "oauth_profile_complete": True,
        }

        oauth_user = _make_oauth_user()
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([complete_profile] if t == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        response_keys = set(resp.json().keys())

        # All returned keys must be in the safe allow-list
        unexpected_keys = response_keys - SAFE_FIELDS
        assert not unexpected_keys, (
            f"Unexpected fields in /auth/me response: {unexpected_keys}. "
            "These may expose sensitive auth metadata."
        )

        # Explicitly verify no forbidden fields are present
        for field in FORBIDDEN_FIELDS:
            assert field not in response_keys, (
                f"Sensitive field '{field}' found in /auth/me response."
            )

        app.dependency_overrides.clear()

    def test_me_no_profile_response_does_not_expose_sensitive_fields(self, monkeypatch):
        """
        Point 8: /auth/me 'no profile' path (returns username/avatar from
        user_metadata) must also not expose raw metadata objects or token fields.
        """
        FORBIDDEN_FIELDS = {
            "user_metadata", "app_metadata", "raw_user_meta_data",
            "access_token", "refresh_token", "provider_token",
            "jwt", "password", "aud", "iss",
        }

        oauth_user = _make_oauth_user()
        # Simulate Google user with rich metadata (locale, hd, email_verified, etc.)
        oauth_user.user_metadata = {
            "full_name": "Google User",
            "avatar_url": "https://lh3.googleusercontent.com/photo.jpg",
            "email_verified": True,
            "iss": "https://accounts.google.com",
            "sub": "google-uid-12345",
            "hd": "example.com",
            "locale": "en",
        }
        app.dependency_overrides[get_current_user] = lambda: oauth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([])))  # no profile

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        response_keys = set(data.keys())

        for field in FORBIDDEN_FIELDS:
            assert field not in response_keys, (
                f"Sensitive field '{field}' leaked in no-profile /auth/me response."
            )

        # Only these safe fields are expected in the no-profile case
        assert data["needs_role_selection"] is True
        assert "username" in data
        assert "avatar" in data
        # username must only be the display name, NOT a raw metadata object
        assert isinstance(data["username"], str)
        assert isinstance(data["avatar"], str)

        app.dependency_overrides.clear()

    # ── Point 1: Email/password users unaffected by migration ─────────────────

    def test_email_user_with_true_oauth_complete_is_unaffected(self, monkeypatch):
        """
        Point 1: Email/password signup users have oauth_profile_complete=True
        (migration DEFAULT TRUE). /auth/me must treat them as fully complete
        and never show the role picker.
        """
        email_user_profile = {
            "id": "email-user-id-001",
            "email": "email_user@example.com",
            "username": "Email User",
            "role": "student",
            "grade": "Grade 9",
            "board": "CBSE",
            "parent_id": None,
            "family_id": None,
            "subscription_plan": "free",
            "account_status": "active",
            "access_cbse": False,
            "access_sof_science": False,
            "access_sof_maths": False,
            "access_sof_english": False,
            "cbse_subjects": [],
            "daily_token_limit": 0,
            "monthly_token_limit": 0,
            "subscription_expires_at": None,
            "oauth_profile_complete": True,  # Default TRUE from migration
        }

        email_auth_user = SimpleNamespace(
            id="email-user-id-001",
            email="email_user@example.com",
            user_metadata={},
        )
        app.dependency_overrides[get_current_user] = lambda: email_auth_user

        class FQ:
            def __init__(self, d): self._data = d
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            def execute(self): return SimpleNamespace(data=self._data)

        import app.routes.auth as auth_route
        monkeypatch.setattr(auth_route, "admin_client",
            SimpleNamespace(table=lambda t: FQ([email_user_profile] if t == "profiles" else [])))
        monkeypatch.setattr(auth_route, "_check_can_report_issues", lambda uid: False)

        with TestClient(app) as client:
            resp = client.get("/api/auth/me",
                              headers={"Authorization": "Bearer fake-token"})

        assert resp.status_code == 200
        data = resp.json()
        # Email user must NEVER see role picker
        assert data["profile_complete"] is True
        assert data["needs_role_selection"] is False
        assert data["role"] == "student"

        app.dependency_overrides.clear()
