"""
test_school_join.py
─────────────────────────────────────────────────────────────────────────────
Tests for the opt-in, self-serve school join/leave endpoints added to
app/routes/profile.py (POST /profile/join-school, POST /profile/leave-school).

These are deliberately NOT part of signup/login/OAuth-completion — a signed
-in user links their own account to a school on their own schedule, from
account settings. The tests assert exactly that boundary: only school_id
ever changes.
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.routes.profile as profile_route


def fake_user(user_id="student-1"):
    return SimpleNamespace(id=user_id)


class FakeTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []
        self.operation = None
        self.payload = None

    def select(self, *_a, **_k):
        self.operation = "select"
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, *_a, **_k):
        return self

    def _rows(self):
        return self.client.schools if self.table_name == "schools" else self.client.profiles

    def _matches(self, row):
        return all(row.get(k) == v for k, v in self.filters)

    def execute(self):
        rows = self._rows()
        if self.operation == "update":
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
            return SimpleNamespace(data=[r for r in rows if self._matches(r)])
        return SimpleNamespace(data=[r for r in rows if self._matches(r)])


class FakeClient:
    def __init__(self, schools, profiles):
        self.schools = schools
        self.profiles = profiles

    def table(self, name):
        return FakeTable(self, name)


@pytest.fixture
def seed():
    schools = [
        {"id": "school-1", "name": "Sunrise Public School", "school_code": "SUN-7F3K2", "status": "active"},
        {"id": "school-2", "name": "Rejected Academy", "school_code": "REJ-00000", "status": "rejected"},
    ]
    profiles = [
        {"id": "student-1", "role": "student", "school_id": None, "subscription_plan": "starter", "grade": "Grade 9"},
    ]
    return schools, profiles


def test_join_school_sets_school_id(seed):
    schools, profiles = seed
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        result = profile_route.join_school(
            profile_route.JoinSchoolRequest(school_code="sun-7f3k2"),
            user=fake_user(),
        )
    assert result["success"] is True
    assert result["school"]["name"] == "Sunrise Public School"
    assert profiles[0]["school_id"] == "school-1"


def test_join_school_never_touches_plan_or_role(seed):
    schools, profiles = seed
    before = dict(profiles[0])
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        profile_route.join_school(
            profile_route.JoinSchoolRequest(school_code="SUN-7F3K2"),
            user=fake_user(),
        )
    after = profiles[0]
    for key in before:
        if key == "school_id":
            continue
        assert after[key] == before[key], f"join_school must not modify '{key}'"


def test_join_school_rejects_unknown_code(seed):
    schools, profiles = seed
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        result = profile_route.join_school(
            profile_route.JoinSchoolRequest(school_code="NOPE-00000"),
            user=fake_user(),
        )
    assert result["success"] is False
    assert profiles[0]["school_id"] is None


def test_join_school_rejects_rejected_school(seed):
    schools, profiles = seed
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        result = profile_route.join_school(
            profile_route.JoinSchoolRequest(school_code="REJ-00000"),
            user=fake_user(),
        )
    assert result["success"] is False
    assert profiles[0]["school_id"] is None


def test_join_school_requires_a_code(seed):
    schools, profiles = seed
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        result = profile_route.join_school(
            profile_route.JoinSchoolRequest(school_code="   "),
            user=fake_user(),
        )
    assert result["success"] is False


def test_leave_school_clears_school_id(seed):
    schools, profiles = seed
    profiles[0]["school_id"] = "school-1"
    with patch("app.routes.profile._sb", FakeClient(schools, profiles)):
        result = profile_route.leave_school(user=fake_user())
    assert result["success"] is True
    assert profiles[0]["school_id"] is None
