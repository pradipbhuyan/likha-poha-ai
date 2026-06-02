from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.routes.admin_control as admin_control_route


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeAuthAdmin:
    def __init__(self, client):
        self.client = client
        self.deleted_users = []

    def delete_user(self, user_id):
        self.deleted_users.append(user_id)


class FakeAuth:
    def __init__(self, client):
        self.admin = FakeAuthAdmin(client)


class FakeTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = []
        self.order_args = None

    def select(self, value):
        self.operation = "select"
        self.select_value = value
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, column, desc=False):
        self.order_args = {
            "column": column,
            "desc": desc,
        }
        return self

    def execute(self):
        self.client.calls.append(
            {
                "table": self.table_name,
                "operation": self.operation,
                "payload": self.payload,
                "filters": self.filters,
                "order": self.order_args,
            }
        )

        if self.table_name == "ai_usage_logs":
            return FakeResponse(self.client.usage_logs)

        if self.table_name == "families" and self.operation == "insert":
            family = {
                "id": self.client.created_family_id,
                **self.payload,
            }
            return FakeResponse([family])

        if self.table_name == "profiles" and self.operation == "select":
            return FakeResponse(self.client.profile_rows)

        if self.table_name == "profiles" and self.operation == "insert":
            inserted = dict(self.payload)
            return FakeResponse([inserted])

        if self.table_name == "profiles" and self.operation == "update":
            updated = {
                "id": self._filter_value("id"),
                "role": self._filter_value("role"),
                **self.payload,
            }
            return FakeResponse([updated])

        if self.table_name == "profiles" and self.operation == "delete":
            return FakeResponse([])

        return FakeResponse([])

    def _filter_value(self, key):
        for filter_key, filter_value in self.filters:
            if filter_key == key:
                return filter_value
        return None


class FakeAdminClient:
    def __init__(self):
        self.calls = []
        self.profile_rows = []
        self.usage_logs = []
        self.created_family_id = "family-created-123"
        self.auth = FakeAuth(self)

    def table(self, table_name):
        return FakeTable(self, table_name)


def make_fake_auth_user(user_id):
    return SimpleNamespace(id=user_id)


def test_build_student_activity_summarizes_usage_logs(monkeypatch):
    """
    Admin dashboard student activity should summarize AI usage logs.

    Source under test:
        backend/app/routes/admin_control.py
        build_student_activity()
    """
    fake_client = FakeAdminClient()

    now = datetime.now(timezone.utc).isoformat()

    fake_client.usage_logs = [
        {
            "username": "Akshita",
            "feature": "lesson",
            "total_tokens": 100,
            "estimated_cost": 0.01,
            "created_at": now,
        },
        {
            "username": "Akshita",
            "feature": "doubt",
            "total_tokens": 50,
            "estimated_cost": 0.02,
            "created_at": now,
        },
        {
            "username": "Akshita",
            "feature": "mock_test",
            "total_tokens": 25,
            "estimated_cost": 0.03,
            "created_at": "2020-01-01T00:00:00+00:00",
        },
    ]

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    activity = admin_control_route.build_student_activity("Akshita")

    assert activity["username"] == "Akshita"
    assert activity["lessons_generated"] == 1
    assert activity["doubts_asked"] == 1
    assert activity["mock_tests_generated"] == 1
    assert activity["requests_total"] == 3
    assert activity["tokens_total"] == 175
    assert activity["cost_total"] == pytest.approx(0.06)
    assert activity["last_activity"] == now


def test_get_all_families_groups_parents_children_and_admins(monkeypatch):
    """
    Admin should be able to see families grouped by family_id.

    Source under test:
        backend/app/routes/admin_control.py
        get_all_families()
    """
    fake_client = FakeAdminClient()

    fake_client.profile_rows = [
        {
            "id": "parent-1",
            "username": "Parent",
            "role": "parent",
            "family_id": "family-1",
        },
        {
            "id": "child-1",
            "username": "Akshita",
            "role": "student",
            "family_id": "family-1",
        },
        {
            "id": "admin-1",
            "username": "Admin",
            "role": "admin",
            "family_id": "family-1",
        },
    ]

    fake_client.usage_logs = [
        {
            "username": "Akshita",
            "feature": "lesson",
            "total_tokens": 100,
            "estimated_cost": 0.01,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    result = admin_control_route.get_all_families(admin={"role": "admin"})

    assert result["success"] is True
    assert len(result["families"]) == 1

    family = result["families"][0]

    assert family["family_id"] == "family-1"
    assert len(family["parents"]) == 1
    assert len(family["children"]) == 1
    assert len(family["admins"]) == 1
    assert family["children"][0]["activity"]["tokens_total"] == 100


def test_create_parent_creates_family_when_family_id_is_missing(monkeypatch):
    """
    If admin creates a parent without family_id, backend should create
    a new family first.

    Source under test:
        backend/app/routes/admin_control.py
        create_parent()
    """
    fake_client = FakeAdminClient()

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)
    monkeypatch.setattr(
        admin_control_route,
        "create_auth_user",
        lambda email, password: make_fake_auth_user("parent-user-123"),
    )

    request = admin_control_route.CreateParentRequest(
        email="parent@example.com",
        password="password123",
        username="Parent User",
    )

    result = admin_control_route.create_parent(
        request,
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["parent"]["id"] == "parent-user-123"
    assert result["parent"]["role"] == "parent"
    assert result["parent"]["family_id"] == "family-created-123"

    family_insert_calls = [
        call
        for call in fake_client.calls
        if call["table"] == "families" and call["operation"] == "insert"
    ]

    assert len(family_insert_calls) == 1


def test_create_parent_uses_existing_family_id(monkeypatch):
    """
    If admin provides family_id, backend should not create a new family.

    Source under test:
        backend/app/routes/admin_control.py
        create_parent()
    """
    fake_client = FakeAdminClient()

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)
    monkeypatch.setattr(
        admin_control_route,
        "create_auth_user",
        lambda email, password: make_fake_auth_user("parent-user-456"),
    )

    request = admin_control_route.CreateParentRequest(
        email="parent2@example.com",
        password="password123",
        username="Second Parent",
        family_id="existing-family-1",
    )

    result = admin_control_route.create_parent(
        request,
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["parent"]["family_id"] == "existing-family-1"

    family_insert_calls = [
        call
        for call in fake_client.calls
        if call["table"] == "families" and call["operation"] == "insert"
    ]

    assert family_insert_calls == []


def test_create_child_creates_student_profile(monkeypatch):
    """
    Admin should be able to create a child/student profile.

    Source under test:
        backend/app/routes/admin_control.py
        create_child()
    """
    fake_client = FakeAdminClient()

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)
    monkeypatch.setattr(
        admin_control_route,
        "create_auth_user",
        lambda email, password: make_fake_auth_user("child-user-123"),
    )

    request = admin_control_route.CreateChildRequest(
        email="child@example.com",
        password="password123",
        username="Child User",
        parent_id="parent-1",
        family_id="family-1",
    )

    result = admin_control_route.create_child(
        request,
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["child"]["id"] == "child-user-123"
    assert result["child"]["role"] == "student"
    assert result["child"]["parent_id"] == "parent-1"
    assert result["child"]["family_id"] == "family-1"
    assert result["child"]["access_cbse"] is True
    assert result["child"]["daily_token_limit"] == 50000
    assert result["child"]["monthly_token_limit"] == 1000000


def test_update_child_access_updates_subscription_and_access_flags(monkeypatch):
    """
    Admin should be able to update student subscription and access flags.

    Source under test:
        backend/app/routes/admin_control.py
        update_child_access()
    """
    fake_client = FakeAdminClient()

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    request = admin_control_route.UpdateAccessRequest(
        access_cbse=True,
        access_sof_science=True,
        access_sof_maths=False,
        access_sof_english=True,
        subscription_plan="premium",
        account_status="active",
    )

    result = admin_control_route.update_child_access(
        "child-1",
        request,
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["profile"]["id"] == "child-1"
    assert result["profile"]["role"] == "student"
    assert result["profile"]["access_cbse"] is True
    assert result["profile"]["access_sof_science"] is True
    assert result["profile"]["access_sof_maths"] is False
    assert result["profile"]["access_sof_english"] is True
    assert result["profile"]["subscription_plan"] == "premium"

    update_call = [
        call
        for call in fake_client.calls
        if call["table"] == "profiles" and call["operation"] == "update"
    ][0]

    assert ("id", "child-1") in update_call["filters"]
    assert ("role", "student") in update_call["filters"]


def test_update_child_limits_updates_daily_and_monthly_limits(monkeypatch):
    """
    Admin should be able to update AI token limits for a student.

    Source under test:
        backend/app/routes/admin_control.py
        update_child_limits()
    """
    fake_client = FakeAdminClient()

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    request = admin_control_route.UpdateLimitsRequest(
        daily_token_limit=25000,
        monthly_token_limit=500000,
    )

    result = admin_control_route.update_child_limits(
        "child-1",
        request,
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["profile"]["id"] == "child-1"
    assert result["profile"]["daily_token_limit"] == 25000
    assert result["profile"]["monthly_token_limit"] == 500000

    update_call = [
        call
        for call in fake_client.calls
        if call["table"] == "profiles" and call["operation"] == "update"
    ][0]

    assert ("id", "child-1") in update_call["filters"]
    assert ("role", "student") in update_call["filters"]


def test_delete_user_removes_profile_and_auth_user(monkeypatch):
    """
    Admin should be able to delete a user profile and auth user.

    Source under test:
        backend/app/routes/admin_control.py
        delete_user()
    """
    fake_client = FakeAdminClient()
    fake_client.profile_rows = [
        {
            "id": "user-1",
            "username": "Student",
            "role": "student",
        }
    ]

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    result = admin_control_route.delete_user(
        "user-1",
        admin={"role": "admin"},
    )

    assert result["success"] is True
    assert result["message"] == "User deleted successfully."
    assert "user-1" in fake_client.auth.admin.deleted_users

    delete_calls = [
        call
        for call in fake_client.calls
        if call["table"] == "profiles" and call["operation"] == "delete"
    ]

    assert len(delete_calls) == 1
    assert ("id", "user-1") in delete_calls[0]["filters"]


def test_delete_user_returns_404_when_profile_not_found(monkeypatch):
    """
    Deleting an unknown user should return a clear 404 error.

    Source under test:
        backend/app/routes/admin_control.py
        delete_user()
    """
    fake_client = FakeAdminClient()
    fake_client.profile_rows = []

    monkeypatch.setattr(admin_control_route, "admin_client", fake_client)

    with pytest.raises(HTTPException) as error:
        admin_control_route.delete_user(
            "missing-user",
            admin={"role": "admin"},
        )

    assert error.value.status_code == 404
    assert error.value.detail == "User not found."