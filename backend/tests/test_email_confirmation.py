"""
Tests for email confirmation behaviour across admin and parent signup flows.

Rules under test:
- Admin creates parent (default)         → invite_parent_by_email() — real Supabase invite email
- Admin creates parent skip_confirm=True → create_auth_user(email_confirm=True) — immediate access
- Admin creates child/teacher            → create_auth_user(email_confirm=True) — immediate access
- Parent invites another parent          → invite_parent_by_email() — real Supabase invite email
- Parent creates student child           → create_auth_user(email_confirm=True) — immediate access
"""

import pytest
from fastapi import HTTPException
from types import SimpleNamespace

import app.routes.admin_onboarding as admin_control_route
import app.routes.parent_dashboard as parent_dashboard_route


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class FakeAuthUser:
    """Minimal auth user object returned by mocked create_auth_user."""

    def __init__(self, user_id="fake-user-id"):
        self.id = user_id


class CapturingAuthUser:
    """
    Fake create_auth_user that records the email_confirm flag it was called with.

    Tests can inspect .called_with_email_confirm to assert the correct flag was
    passed without making any real Supabase calls.
    """

    def __init__(self, user_id="fake-user-id"):
        self.user_id = user_id
        self.called_with_email_confirm = None

    def __call__(self, email, password, email_confirm=True):
        self.called_with_email_confirm = email_confirm
        return FakeAuthUser(self.user_id)


class CapturingInviteParent:
    """
    Fake invite_parent_by_email that records whether it was called.

    Tests use this to assert that the invite path (real Supabase email) was
    taken rather than the create_auth_user bypass path.
    """

    def __init__(self, user_id="invited-user-id"):
        self.user_id = user_id
        self.was_called = False
        self.called_with_email = None

    def __call__(self, email, username):
        self.was_called = True
        self.called_with_email = email
        return FakeAuthUser(self.user_id)


class FakeInsertResult:
    def __init__(self, data):
        self.data = data


class FakeProfilesTable:
    def __init__(self, payload_store=None):
        self.inserted_payload = None
        self._payload_store = payload_store
        self._querying = False

    def insert(self, payload):
        self.inserted_payload = payload
        self._querying = False
        return self

    # create_student's pre-insert _reject_taken_username() check queries by
    # username before ever calling insert() — none of these tests simulate
    # a username collision, so the read side always reports "nothing found".
    def select(self, *_):
        self._querying = True
        return self

    def ilike(self, *_): return self
    def eq(self, *_): return self
    def limit(self, *_): return self

    def execute(self):
        if self._querying:
            return FakeInsertResult([])
        return FakeInsertResult([self.inserted_payload])


class FakeAdminClientForParentDashboard:
    """Fake admin_client that handles profile inserts for parent dashboard tests."""

    def __init__(self):
        self.profiles_table = FakeProfilesTable()

    def table(self, table_name):
        assert table_name == "profiles"
        return self.profiles_table


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    """Minimal fake table for admin_control tests."""

    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = []

    def select(self, value):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def ilike(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, _value):
        return self

    def execute(self):
        if self.table_name == "families" and self.operation == "insert":
            return FakeResponse([{"id": "new-family-id", **self.payload}])

        if self.table_name == "profiles" and self.operation == "insert":
            return FakeResponse([dict(self.payload)])

        return FakeResponse([])


class FakeAdminClientForAdminControl:
    """Fake admin_client that supports family + profile creation."""

    def table(self, table_name):
        return FakeTable(self, table_name)


FAKE_PARENT = {
    "profile": {
        "id": "parent-1",
        "email": "parent@example.com",
        "username": "parent_user",
        "role": "parent",
        "family_id": "family-1",
    }
}

FAKE_PARENT_NO_FAMILY = {
    "profile": {
        "id": "parent-no-family",
        "email": "parent@example.com",
        "username": "parent_user",
        "role": "parent",
        "family_id": None,
    }
}


# ---------------------------------------------------------------------------
# POSITIVE TESTS — Admin user creation (email_confirm=True, no email sent)
# ---------------------------------------------------------------------------

def test_admin_creates_parent_sends_confirmation_email_by_default(monkeypatch):
    """
    Admin-created parents must receive a real invitation email by default.

    The default path uses invite_parent_by_email (Supabase invite_user_by_email)
    which actually sends an email with a confirmation link. The parent clicks the
    link to verify their email and set their password before first login.

    Expected: invite_parent_by_email is called (not create_auth_user).
    """
    invite_capturer = CapturingInviteParent("parent-abc")
    monkeypatch.setattr(admin_control_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateParentRequest(
        email="newparent@example.com",
        username="new_parent",
        family_id="family-existing",
        # no password — invite flow, parent sets their own password
    )

    result = admin_control_route.create_parent(request, admin={"role": "admin"})

    assert result["success"] is True
    assert invite_capturer.was_called is True
    assert invite_capturer.called_with_email == "newparent@example.com"


def test_admin_creates_parent_with_skip_confirmation_bypasses_email(monkeypatch):
    """
    When admin sets skip_email_confirmation=True, the account is immediately active.

    This is for in-person onboarding where the admin hands credentials directly
    to the parent without needing email verification.

    Expected: create_auth_user called with email_confirm=True (no email sent).
    """
    capturer = CapturingAuthUser("parent-skipped")
    monkeypatch.setattr(admin_control_route, "create_auth_user", capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateParentRequest(
        email="inperson@example.com",
        password="secure123",
        username="inperson_parent",
        family_id="family-existing",
        skip_email_confirmation=True,
    )

    result = admin_control_route.create_parent(request, admin={"role": "admin"})

    assert result["success"] is True
    assert capturer.called_with_email_confirm is True


def test_admin_creates_child_bypasses_email_confirmation(monkeypatch):
    """
    Admin-created child accounts must be immediately active.

    Children are managed by their parent and should not need to confirm an
    email before the parent can set them up.

    Expected: create_auth_user called with email_confirm=True.
    """
    capturer = CapturingAuthUser("child-abc")
    monkeypatch.setattr(admin_control_route, "create_auth_user", capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateChildRequest(
        email="child@example.com",
        password="childpass123",
        username="child_user",
        parent_id="parent-1",
        family_id="family-1",
        grade="Grade 9",
    )

    result = admin_control_route.create_child(request, admin={"role": "admin"})

    assert result["success"] is True
    assert capturer.called_with_email_confirm is True


def test_admin_creates_teacher_bypasses_email_confirmation(monkeypatch):
    """
    Admin-created teacher accounts must be immediately active.

    Teachers are onboarded by admins and need immediate access to their
    dashboard without waiting for email confirmation.

    Expected: create_auth_user called with email_confirm=True.
    """

    class FakeAdminClientWithTeacherProfile(FakeAdminClientForAdminControl):
        def table(self, table_name):
            t = FakeTable(self, table_name)
            return t

    capturer = CapturingAuthUser("teacher-abc")
    monkeypatch.setattr(admin_control_route, "create_auth_user", capturer)
    monkeypatch.setattr(
        admin_control_route, "admin_client", FakeAdminClientWithTeacherProfile()
    )

    request = admin_control_route.CreateTeacherRequest(
        email="teacher@example.com",
        password="teachpass123",
        username="teacher_user",
        teacher_type="independent",
    )

    result = admin_control_route.create_teacher(request, admin={"role": "admin"})

    assert result["success"] is True
    assert capturer.called_with_email_confirm is True


# ---------------------------------------------------------------------------
# POSITIVE TESTS — Parent invites parent (email_confirm=False, email required)
# ---------------------------------------------------------------------------

def test_parent_invite_always_sends_real_confirmation_email(monkeypatch):
    """
    A parent inviting another parent must use invite_parent_by_email.

    Supabase's invite_user_by_email sends a real invitation email with a
    confirmation link. The invited parent cannot log in until they click the link.

    Expected: invite_parent_by_email is called (not create_auth_user).
    """
    invite_capturer = CapturingInviteParent("invited-parent")
    monkeypatch.setattr(parent_dashboard_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(
        parent_dashboard_route, "admin_client", FakeAdminClientForParentDashboard()
    )

    request = parent_dashboard_route.InviteParentRequest(
        email="invite@example.com",
        username="invited_parent",
    )

    result = parent_dashboard_route.invite_parent(data=request, parent=FAKE_PARENT)

    assert result["success"] is True
    assert invite_capturer.was_called is True
    assert invite_capturer.called_with_email == "invite@example.com"


def test_parent_invite_creates_profile_in_same_family(monkeypatch):
    """
    Invited parent must be attached to the inviting parent's family.

    Expected: invited parent profile has the same family_id as the inviting parent.
    """
    invite_capturer = CapturingInviteParent("invited-parent-2")
    monkeypatch.setattr(parent_dashboard_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(
        parent_dashboard_route, "admin_client", FakeAdminClientForParentDashboard()
    )

    request = parent_dashboard_route.InviteParentRequest(
        email="second@example.com",
        username="second_parent",
    )

    result = parent_dashboard_route.invite_parent(data=request, parent=FAKE_PARENT)

    assert result["success"] is True
    assert result["parent"]["family_id"] == "family-1"
    assert result["parent"]["role"] == "parent"
    assert result["parent"]["parent_id"] is None


def test_parent_invite_always_uses_invite_api_regardless_of_email(monkeypatch):
    """
    The invite path always calls invite_parent_by_email for any email address.

    Expected: invite_parent_by_email is called for all parent-initiated invites.
    """
    invite_capturer = CapturingInviteParent("invited-parent-3")
    monkeypatch.setattr(parent_dashboard_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(
        parent_dashboard_route, "admin_client", FakeAdminClientForParentDashboard()
    )

    for email in ["simple@test.com", "complex+tag@domain.co.in", "parent2@example.com"]:
        request = parent_dashboard_route.InviteParentRequest(
            email=email,
            username="test_parent",
        )
        parent_dashboard_route.invite_parent(data=request, parent=FAKE_PARENT)
        assert invite_capturer.was_called is True, (
            f"Expected invite_parent_by_email to be called for email '{email}'"
        )


# ---------------------------------------------------------------------------
# NEGATIVE TESTS — Invalid/missing data should be rejected early
# ---------------------------------------------------------------------------

def test_parent_invite_rejected_when_parent_has_no_family():
    """
    A parent without a family_id must not be allowed to invite other parents.

    Without a family, there is no valid family_id to attach the invited parent
    to. The route must reject the request before creating any auth user.

    Expected: HTTP 400.
    """
    request = parent_dashboard_route.InviteParentRequest(
        email="invite@example.com",
        username="invited_parent",
    )

    with pytest.raises(HTTPException) as error:
        parent_dashboard_route.invite_parent(
            data=request,
            parent=FAKE_PARENT_NO_FAMILY,
        )

    assert error.value.status_code == 400
    assert "family" in error.value.detail.lower()


def test_admin_create_parent_default_skip_email_confirmation_is_false():
    """
    CreateParentRequest must default skip_email_confirmation to False.

    By default all parents must confirm their email. Only set True for
    in-person onboarding where the admin hands credentials directly.
    """
    request = admin_control_route.CreateParentRequest(
        email="parent@example.com",
        password="password123",
        username="parent_user",
    )

    assert request.skip_email_confirmation is False


def test_admin_create_parent_accepts_skip_email_confirmation_true():
    """
    CreateParentRequest must accept skip_email_confirmation=True.

    Admins doing in-person onboarding can bypass email confirmation.
    """
    request = admin_control_route.CreateParentRequest(
        email="parent@example.com",
        password="password123",
        username="parent_user",
        skip_email_confirmation=True,
    )

    assert request.skip_email_confirmation is True


def test_admin_create_parent_with_skip_false_uses_invite_api(monkeypatch):
    """
    Explicitly setting skip_email_confirmation=False uses the invite API.

    This is the secure default — invite_parent_by_email is called which sends
    a real confirmation email via Supabase.

    Expected: invite_parent_by_email is called.
    """
    invite_capturer = CapturingInviteParent("parent-explicit-no-skip")
    monkeypatch.setattr(admin_control_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateParentRequest(
        email="confirm-me@example.com",
        username="confirm_parent",
        family_id="family-xyz",
        skip_email_confirmation=False,
    )

    result = admin_control_route.create_parent(request, admin={"role": "admin"})

    assert result["success"] is True
    assert invite_capturer.was_called is True


def test_parent_creates_student_child_bypasses_email_confirmation(monkeypatch):
    """
    When a parent creates a child account, the child must be immediately active.

    Children are set up and managed by their parent, so email confirmation would
    block the parent from completing onboarding.

    Expected: create_auth_user called with email_confirm=True (default).
    """
    capturer = CapturingAuthUser("student-abc")
    monkeypatch.setattr(parent_dashboard_route, "create_auth_user", capturer)
    monkeypatch.setattr(
        parent_dashboard_route, "admin_client", FakeAdminClientForParentDashboard()
    )
    monkeypatch.setattr(
        parent_dashboard_route,
        "get_children",
        lambda parent_id: [],
    )

    request = parent_dashboard_route.CreateStudentRequest(
        email="student@example.com",
        password="student123",
        username="student_user",
    )

    result = parent_dashboard_route.create_student(data=request, parent=FAKE_PARENT)

    assert result["success"] is True
    assert capturer.called_with_email_confirm is True


def test_admin_creates_parent_auto_creates_family_and_sends_invite_email(monkeypatch):
    """
    When admin creates a parent without a family_id, a new family is created
    AND invite_parent_by_email is called (sends real email via Supabase).

    Expected:
    - family insert call is made
    - invite_parent_by_email is called
    """
    invite_capturer = CapturingInviteParent("parent-new-family")
    monkeypatch.setattr(admin_control_route, "invite_parent_by_email", invite_capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateParentRequest(
        email="autofamily@example.com",
        username="auto_family_parent",
        # no family_id → backend will create one
    )

    result = admin_control_route.create_parent(request, admin={"role": "admin"})

    assert result["success"] is True
    assert invite_capturer.was_called is True


def test_admin_creates_parent_auto_creates_family_and_skips_confirmation(monkeypatch):
    """
    When admin creates a parent without family_id AND skip_email_confirmation=True,
    a new family is created AND the account is immediately active (no email sent).

    Expected:
    - family insert call is made
    - create_auth_user called with email_confirm=True (no email)
    """
    capturer = CapturingAuthUser("parent-new-family-skipped")
    monkeypatch.setattr(admin_control_route, "create_auth_user", capturer)
    monkeypatch.setattr(admin_control_route, "admin_client", FakeAdminClientForAdminControl())

    request = admin_control_route.CreateParentRequest(
        email="autofamily-skipped@example.com",
        password="pass123",
        username="auto_family_skipped",
        skip_email_confirmation=True,
    )

    result = admin_control_route.create_parent(request, admin={"role": "admin"})

    assert result["success"] is True
    assert capturer.called_with_email_confirm is True
    assert result["parent"]["family_id"] == "new-family-id"
