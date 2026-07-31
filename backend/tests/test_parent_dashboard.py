import pytest
from fastapi import HTTPException

import app.routes.parent_dashboard as parent_dashboard_route


FAKE_PARENT = {
    "profile": {
        "id": "parent_1",
        "email": "parent@example.com",
        "username": "parent_user",
        "role": "parent",
        "family_id": "family_1",
    }
}


def test_get_family_with_mocked_service(monkeypatch):
    """
    Test that the parent family endpoint returns family members.

    This test calls the route function directly and passes a fake authenticated
    parent. It mocks get_family_members so the test does not call Supabase.

    Expected result:
    - success should be True.
    - family_id should match the mocked family.
    - parents and children should come from the mocked service.
    """

    def fake_get_family_members(parent_id):
        return {
            "family_id": "family_1",
            "parents": [
                {
                    "id": parent_id,
                    "username": "parent_user",
                    "role": "parent",
                }
            ],
            "children": [
                {
                    "id": "child_1",
                    "username": "child_user",
                    "role": "student",
                }
            ],
        }

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_family_members",
        fake_get_family_members,
    )

    result = parent_dashboard_route.get_family(parent=FAKE_PARENT)

    assert result["success"] is True
    assert result["family_id"] == "family_1"
    assert len(result["parents"]) == 1
    assert len(result["children"]) == 1


def test_get_parent_children_with_mocked_service(monkeypatch):
    """
    Test that the parent children endpoint returns children for a parent.

    This mocks get_children so the test does not call Supabase.

    Expected result:
    - success should be True.
    - children should contain the mocked child profile.
    """

    def fake_get_children(parent_id):
        return [
            {
                "id": "child_1",
                "username": "child_user",
                "role": "student",
                "parent_id": parent_id,
            }
        ]

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_children",
        fake_get_children,
    )

    result = parent_dashboard_route.get_parent_children(parent=FAKE_PARENT)

    assert result["success"] is True
    assert len(result["children"]) == 1
    assert result["children"][0]["username"] == "child_user"


def test_get_single_child_with_mocked_service(monkeypatch):
    """
    Test that the single-child endpoint returns one child profile.

    This mocks get_child_by_id so the test does not call Supabase.

    Expected result:
    - success should be True.
    - child should match the requested child id.
    """

    def fake_get_child_by_id(parent_id, child_id):
        return {
            "id": child_id,
            "username": "child_user",
            "role": "student",
            "parent_id": parent_id,
        }

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_child_by_id",
        fake_get_child_by_id,
    )

    result = parent_dashboard_route.get_single_child(
        child_id="child_1",
        parent=FAKE_PARENT,
    )

    assert result["success"] is True
    assert result["child"]["id"] == "child_1"
    assert result["child"]["username"] == "child_user"


def test_get_single_child_not_found(monkeypatch):
    """
    Test that the single-child endpoint raises 404 when child is not found.

    Expected result:
    - The route should raise HTTPException.
    - The status code should be 404.
    """

    def fake_get_child_by_id(parent_id, child_id):
        return None

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_child_by_id",
        fake_get_child_by_id,
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.get_single_child(
            child_id="missing_child",
            parent=FAKE_PARENT,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Child not found"
    
class FakeAuthUser:
    """
    Fake auth user returned by create_auth_user.

    The real create_auth_user returns an object with an id.
    The route only needs auth_user.id, so this fake object is enough.
    """

    def __init__(self, user_id):
        self.id = user_id


class FakeInsertResult:
    """
    Fake database insert result.

    The route expects response.data after inserting into profiles.
    """

    def __init__(self, data):
        self.data = data


class FakeProfilesTable:
    """
    Fake admin_client profiles table.

    This captures the inserted payload and returns it as response.data.
    """

    def __init__(self):
        self.inserted_payload = None

    def insert(self, payload):
        self.inserted_payload = payload
        return self

    def execute(self):
        return FakeInsertResult([self.inserted_payload])


class FakeAdminClient:
    """
    Fake admin_client.

    The parent dashboard route calls:
    admin_client.table("profiles").insert(...).execute()

    This fake supports that chain without touching Supabase.
    """

    def __init__(self):
        self.profiles_table = FakeProfilesTable()

    def table(self, table_name):
        assert table_name == "profiles"
        return self.profiles_table


def test_create_student_with_mocked_auth_and_admin_client(monkeypatch):
    """
    Test that a parent can create a student profile.

    This test mocks:
    - get_children so we control the current child count
    - create_auth_user so no real auth user is created
    - admin_client so no real Supabase insert happens

    Expected result:
    - success should be True.
    - child should contain the created student profile.
    - child should belong to the parent's family.
    """

    def fake_get_children(parent_id):
        return []

    def fake_create_auth_user(email, password, email_confirm=True):
        return FakeAuthUser("child_1")

    fake_admin_client = FakeAdminClient()

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_children",
        fake_get_children,
    )
    monkeypatch.setattr(
        parent_dashboard_route,
        "create_auth_user",
        fake_create_auth_user,
    )
    monkeypatch.setattr(
        parent_dashboard_route,
        "admin_client",
        fake_admin_client,
    )

    request = parent_dashboard_route.CreateStudentRequest(
        email="child@example.com",
        password="password123",
        username="child_user",
    )

    result = parent_dashboard_route.create_student(
        data=request,
        parent=FAKE_PARENT,
    )

    assert result["success"] is True
    assert result["child"]["id"] == "child_1"
    assert result["child"]["email"] == "child@example.com"
    assert result["child"]["username"] == "child_user"
    assert result["child"]["role"] == "student"
    assert result["child"]["parent_id"] == "parent_1"
    assert result["child"]["family_id"] == "family_1"


def test_create_student_grade_11_requires_stream(monkeypatch):
    """
    A parent creating a Grade 11/12 child must supply a valid stream.

    Expected result:
    - Missing/invalid stream raises HTTPException 400.
    - Valid stream succeeds and the child profile carries stream + the
      stream's CBSE subjects (mirrors app/routes/auth.py signup behavior).
    """

    def fake_get_children(parent_id):
        return []

    def fake_create_auth_user(email, password, email_confirm=True):
        return FakeAuthUser("child_grade11")

    fake_admin_client = FakeAdminClient()

    monkeypatch.setattr(parent_dashboard_route, "get_children", fake_get_children)
    monkeypatch.setattr(parent_dashboard_route, "create_auth_user", fake_create_auth_user)
    monkeypatch.setattr(parent_dashboard_route, "admin_client", fake_admin_client)

    missing_stream_request = parent_dashboard_route.CreateStudentRequest(
        email="grade11@example.com",
        password="password123",
        username="grade11_child",
        grade="Grade 11",
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.create_student(data=missing_stream_request, parent=FAKE_PARENT)
    assert error.value.status_code == 400
    assert "Stream is required" in error.value.detail

    valid_request = parent_dashboard_route.CreateStudentRequest(
        email="grade11@example.com",
        password="password123",
        username="grade11_child",
        grade="Grade 11",
        stream="PCM",
    )

    result = parent_dashboard_route.create_student(data=valid_request, parent=FAKE_PARENT)

    assert result["success"] is True
    assert result["child"]["grade"] == "Grade 11"
    assert result["child"]["stream"] == "PCM"
    assert result["child"]["cbse_subjects"] == ["Physics", "Chemistry", "Mathematics", "English", "Hindi"]


def test_create_student_rejects_more_than_two_children(monkeypatch):
    """
    Test that a parent cannot create more than two children.

    The route checks the current children before creating a new student.

    Expected result:
    - The route should raise HTTPException.
    - The status code should be 400.
    """

    def fake_get_children(parent_id):
        return [
            {"id": "child_1"},
            {"id": "child_2"},
        ]

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_children",
        fake_get_children,
    )

    request = parent_dashboard_route.CreateStudentRequest(
        email="third-child@example.com",
        password="password123",
        username="third_child",
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.create_student(
            data=request,
            parent=FAKE_PARENT,
        )

    assert error.value.status_code == 400
    # Message changed: now uses canonical subscription resolver for child limit.
    # When resolver fails (no DB in CI), it defaults to FREE_TIER (1 child).
    # The test has 2 children already, which exceeds any plan's limit.
    assert error.value.status_code == 400
    assert "Child limit reached" in error.value.detail or "Maximum" in error.value.detail


def test_create_student_rejects_parent_without_family(monkeypatch):
    """
    Test that a parent without a family_id cannot create a student.

    The child profile must belong to a family, so family_id is required.

    Expected result:
    - The route should raise HTTPException.
    - The status code should be 400.
    """

    def fake_get_children(parent_id):
        return []

    monkeypatch.setattr(
        parent_dashboard_route,
        "get_children",
        fake_get_children,
    )

    parent_without_family = {
        "profile": {
            "id": "parent_no_family",
            "email": "parent@example.com",
            "username": "parent_user",
            "role": "parent",
            "family_id": None,
        }
    }

    request = parent_dashboard_route.CreateStudentRequest(
        email="child@example.com",
        password="password123",
        username="child_user",
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.create_student(
            data=request,
            parent=parent_without_family,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Parent does not belong to a family."


def test_invite_parent_with_mocked_auth_and_admin_client(monkeypatch):
    """
    Test that a parent can invite another parent to the same family.

    This test mocks:
    - invite_parent_by_email so no real Supabase invite is sent
    - admin_client so no real Supabase insert happens

    Expected result:
    - success should be True.
    - parent should contain the invited parent profile.
    - invited parent should belong to the same family.
    """

    def fake_invite_parent_by_email(email, username):
        return FakeAuthUser("parent_2")

    fake_admin_client = FakeAdminClient()

    monkeypatch.setattr(
        parent_dashboard_route,
        "invite_parent_by_email",
        fake_invite_parent_by_email,
    )
    monkeypatch.setattr(
        parent_dashboard_route,
        "admin_client",
        fake_admin_client,
    )

    # InviteParentRequest no longer accepts password — Supabase handles that
    request = parent_dashboard_route.InviteParentRequest(
        email="second-parent@example.com",
        username="second_parent",
    )

    result = parent_dashboard_route.invite_parent(
        data=request,
        parent=FAKE_PARENT,
    )

    assert result["success"] is True
    assert result["parent"]["id"] == "parent_2"
    assert result["parent"]["email"] == "second-parent@example.com"
    assert result["parent"]["username"] == "second_parent"
    assert result["parent"]["role"] == "parent"
    assert result["parent"]["family_id"] == "family_1"
    assert result["parent"]["parent_id"] is None


def test_invite_parent_rejects_parent_without_family():
    """
    Test that a parent without a family_id cannot invite another parent.

    The invited parent must be connected to an existing family.

    Expected result:
    - The route should raise HTTPException.
    - The status code should be 400.
    """

    parent_without_family = {
        "profile": {
            "id": "parent_no_family",
            "email": "parent@example.com",
            "username": "parent_user",
            "role": "parent",
            "family_id": None,
        }
    }

    request = parent_dashboard_route.InviteParentRequest(
        email="second-parent@example.com",
        username="second_parent",
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.invite_parent(
            data=request,
            parent=parent_without_family,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Parent does not belong to a family."


class FakeAuthUserWithId:
    """Fake auth user that includes a user.id attribute."""
    class user:
        id = "new-child-uuid-1"


# ─────────────────────────────────────────────────────────────────────────────
# Child login credential regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestChildLoginCredentials:
    """
    Regression tests for child account creation login flow.
    Root cause fix: create_student now returns login_id and login_email
    so parent can share correct credentials with child.
    """

    def _setup_mocks(self, monkeypatch, insert_data=None):
        """Set up common mocks for create_student tests."""
        monkeypatch.setattr("app.routes.parent_dashboard.get_children", lambda pid: [])

        def fake_resolve(parent_id):
            return {"canonical_plan_key": "FREE_TIER", "plan_name": "Free Tier",
                    "has_full_access": False, "child_limit": 1, "restrictions": []}
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription", fake_resolve)

        fake_auth = FakeAuthUser("new-child-uuid-1")
        monkeypatch.setattr("app.routes.parent_dashboard.create_auth_user",
                            lambda email, password, **kw: fake_auth)

        profiles_table = FakeProfilesTable()
        if insert_data is not None:
            profiles_table.inserted_payload = insert_data
            class FakeResultWithData:
                data = [insert_data]
            profiles_table.execute = lambda: FakeResultWithData()

        fake_admin = FakeAdminClient()
        fake_admin.profiles_table = profiles_table
        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", fake_admin)
        return profiles_table

    def test_create_student_returns_login_id(self, monkeypatch):
        """create_student must return login_id = the child's username."""
        child_data = {"id": "new-child-uuid-1", "username": "Aarav", "email": "Aarav@child.likhapoha.in",
                      "role": "student", "parent_id": "parent_1", "family_id": "family_1"}
        self._setup_mocks(monkeypatch, insert_data=child_data)

        req = create_student_request_factory("Aarav", "password123")
        result = __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
            data=req, parent=FAKE_PARENT
        )
        assert result["success"] is True
        assert result["login_id"] == "Aarav", "login_id must be the child's username"

    def test_create_student_returns_login_email(self, monkeypatch):
        """create_student must return login_email (synthetic or real)."""
        child_data = {"id": "new-child-uuid-1", "username": "Aarav", "email": "Aarav@child.likhapoha.in",
                      "role": "student", "parent_id": "parent_1", "family_id": "family_1"}
        self._setup_mocks(monkeypatch, insert_data=child_data)

        req = create_student_request_factory("Aarav", "password123")
        result = __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
            data=req, parent=FAKE_PARENT
        )
        assert "login_email" in result
        assert "child.likhapoha.in" in result["login_email"]

    def test_synthetic_email_matches_profile_email(self, monkeypatch):
        """Profile email must match the synthetic auth email."""
        import re
        captured_profile = {}

        class CapturingTable:
            def insert(self, payload):
                captured_profile.update(payload)
                return self
            def execute(self):
                class R:
                    data = [captured_profile]
                return R()

        class CapturingAdmin:
            def table(self, t):
                return CapturingTable()

        monkeypatch.setattr("app.routes.parent_dashboard.get_children", lambda pid: [])
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda pid: {"canonical_plan_key":"FREE_TIER","child_limit":1,"plan_name":"Free Tier","restrictions":[]})
        monkeypatch.setattr("app.routes.parent_dashboard.create_auth_user",
                            lambda email, password, **kw: FakeAuthUser("new-child-uuid-1"))
        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", CapturingAdmin())

        req = create_student_request_factory("Aarav Kumar", "pass123")
        result = __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
            data=req, parent=FAKE_PARENT
        )
        # Profile email must contain the sanitized username
        assert "AaravKumar" in captured_profile["email"]
        assert "child.likhapoha.in" in captured_profile["email"]
        # login_email in response must match profile email
        assert result["login_email"] == captured_profile["email"]

    def test_child_access_cbse_is_false_for_free_parent(self, monkeypatch):
        """Child created by free-tier parent must have access_cbse=False."""
        captured = {}

        class CapTable:
            def insert(self, payload):
                captured.update(payload)
                return self
            def execute(self):
                class R:
                    data = [captured]
                return R()

        class CapAdmin:
            def table(self, t): return CapTable()

        monkeypatch.setattr("app.routes.parent_dashboard.get_children", lambda pid: [])
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda pid: {"canonical_plan_key":"FREE_TIER","child_limit":1,"plan_name":"Free Tier","restrictions":[]})
        monkeypatch.setattr("app.routes.parent_dashboard.create_auth_user",
                            lambda email, password, **kw: FakeAuthUser("uuid-1"))
        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", CapAdmin())

        req = create_student_request_factory("TestChild", "pw")
        __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
            data=req, parent=FAKE_PARENT
        )
        assert captured.get("access_cbse") is False, "FREE_TIER child must have access_cbse=False"
        assert captured.get("role") == "student"
        assert captured.get("parent_id") == "parent_1"

    def test_silent_profile_insert_failure_raises_500(self, monkeypatch):
        """If profile insert returns empty data, must raise 500 (not silently succeed)."""
        from fastapi import HTTPException

        class EmptyTable:
            def insert(self, payload): return self
            def execute(self):
                class R:
                    data = []  # silent insert failure
                return R()

        class EmptyAdmin:
            def table(self, t): return EmptyTable()
            class auth:
                class admin:
                    @staticmethod
                    def delete_user(uid): pass

        monkeypatch.setattr("app.routes.parent_dashboard.get_children", lambda pid: [])
        monkeypatch.setattr("app.routes.parent_dashboard.resolve_user_subscription",
                            lambda pid: {"canonical_plan_key":"FREE_TIER","child_limit":1,"plan_name":"Free Tier","restrictions":[]})
        monkeypatch.setattr("app.routes.parent_dashboard.create_auth_user",
                            lambda email, password, **kw: FakeAuthUser("uuid-1"))
        monkeypatch.setattr("app.routes.parent_dashboard.admin_client", EmptyAdmin())

        req = create_student_request_factory("FailChild", "pw")
        with pytest.raises(HTTPException) as exc:
            __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
                data=req, parent=FAKE_PARENT
            )
        assert exc.value.status_code == 500

    def test_login_id_matches_username_for_username_login_flow(self, monkeypatch):
        """
        The login_id returned must be the username the child uses to log in.
        The lookup-email flow: login_id → profiles.username → profiles.email → Supabase auth.
        """
        child_data = {"id": "uuid-1", "username": "RiyaTest", "email": "RiyaTest@child.likhapoha.in",
                      "role": "student", "parent_id": "parent_1", "family_id": "family_1"}
        self._setup_mocks(monkeypatch, insert_data=child_data)

        req = create_student_request_factory("RiyaTest", "mypassword")
        result = __import__("app.routes.parent_dashboard", fromlist=["create_student"]).create_student(
            data=req, parent=FAKE_PARENT
        )
        login_id = result["login_id"]
        login_email = result["login_email"]
        # The lookup-email flow: search profiles where username = login_id → returns login_email
        assert login_id == "RiyaTest"
        assert login_email == "RiyaTest@child.likhapoha.in"
        # Parent can reconstruct: child logs in with username=login_id, password=<what they entered>


def create_student_request_factory(username, password, email=None):
    """Helper to create CreateStudentRequest for tests."""
    import app.routes.parent_dashboard as parent_dashboard_route
    return parent_dashboard_route.CreateStudentRequest(
        username=username,
        password=password,
        email=email,
    )
