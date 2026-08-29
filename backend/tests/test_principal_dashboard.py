"""
test_principal_dashboard.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/routes/principal_dashboard.py — school profile, teacher/student
roster read+link/unlink, dashboard summary, and incentive redemption.

Every route is called directly (mirrors tests/test_teacher_dashboard.py's
style) against a small in-memory FakeAdminClient, so no network/Supabase
dependency is needed.
"""
import pytest
from fastapi import HTTPException

import app.routes.principal_dashboard as principal_dashboard_route


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = []

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, tuple(values)))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def _rows(self):
        if self.table_name == "schools":
            return self.client.schools
        if self.table_name == "profiles":
            return self.client.profiles
        if self.table_name == "teacher_student_assignments":
            return self.client.assignments
        if self.table_name == "school_reward_redemptions":
            return self.client.redemptions
        if self.table_name == "student_profiles":
            return self.client.student_profiles
        return []

    def _matches(self, row):
        for kind, key, value in self.filters:
            if kind == "eq" and row.get(key) != value:
                return False
            if kind == "in" and row.get(key) not in value:
                return False
        return True

    def execute(self):
        rows = self._rows()

        if self.operation == "insert":
            new_row = dict(self.payload)
            new_row.setdefault("id", f"generated-{len(rows) + 1}")
            rows.append(new_row)
            return FakeResponse([new_row])

        if self.operation == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
                    updated.append(row)
            return FakeResponse(updated)

        # select (default)
        return FakeResponse([row for row in rows if self._matches(row)])


class FakeAdminClient:
    def __init__(self):
        self.schools = [
            {
                "id": "school-1",
                "name": "Sunrise Public School",
                "school_code": "SUN-7F3K2",
                "status": "active",
                "udise_code": None,
                "city": "Guwahati",
                "state": "Assam",
                "tier": "bronze",
                "principal_id": "principal-1",
            }
        ]
        self.profiles = [
            {"id": "principal-1", "role": "principal", "username": "Meera Kalita"},
            {
                "id": "teacher-1", "role": "teacher", "username": "Meena Sharma",
                "email": "meena@example.com", "school_id": "school-1",
                "account_status": "active", "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "teacher-2", "role": "teacher", "username": "Unlinked Teacher",
                "email": "unlinked@example.com", "school_id": None,
                "account_status": "active", "created_at": "2026-01-01T00:00:00Z",
            },
            {
                # NOTE: no last_active_date here — that column lives on
                # student_profiles, not profiles (see self.student_profiles
                # below). A prior version of this fixture wrongly seeded it
                # here, which silently masked the real "column does not
                # exist" bug this fixture now guards against.
                "id": "student-1", "role": "student", "username": "Ankita Baruah",
                "email": "ankita@example.com", "school_id": "school-1", "grade": "Grade 10",
                "access_cbse": True, "subscription_plan": "starter",
                "subscription_expires_at": "2099-01-01T00:00:00Z",
                "created_at": "2026-02-01T00:00:00Z",
            },
            {
                "id": "student-2", "role": "student", "username": "Rohit Nath",
                "email": "rohit@example.com", "school_id": "school-1", "grade": "Grade 9",
                "access_cbse": False, "subscription_plan": "free",
                "subscription_expires_at": None,
                "created_at": "2026-02-01T00:00:00Z",
            },
            {
                "id": "student-3", "role": "student", "username": "Unlinked Student",
                "email": "unlinked.student@example.com", "school_id": None, "grade": "Grade 9",
                "access_cbse": False, "subscription_plan": "free",
                "subscription_expires_at": None,
                "created_at": "2026-02-01T00:00:00Z",
            },
        ]
        self.assignments = [
            {"teacher_id": "teacher-1", "student_id": "student-1"},
            {"teacher_id": "teacher-1", "student_id": "student-2"},
        ]
        self.redemptions = []
        # Gamification table — last_active_date's real home, keyed by profile_id.
        self.student_profiles = [
            {"profile_id": "student-1", "last_active_date": "2026-08-27"},
            {"profile_id": "student-2", "last_active_date": "2026-08-26"},
        ]

    def table(self, table_name):
        return FakeTable(self, table_name)


def fake_principal():
    return {"profile": {"id": "principal-1", "role": "principal", "username": "Meera Kalita"}}


@pytest.fixture(autouse=True)
def patch_admin_client(monkeypatch):
    client = FakeAdminClient()
    monkeypatch.setattr(principal_dashboard_route, "admin_client", client)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# School profile
# ─────────────────────────────────────────────────────────────────────────────

def test_get_school_returns_own_school():
    result = principal_dashboard_route.get_school(principal=fake_principal())
    assert result["school"]["name"] == "Sunrise Public School"
    assert result["school"]["school_code"] == "SUN-7F3K2"


def test_get_school_404s_when_no_school_exists(patch_admin_client):
    patch_admin_client.schools.clear()
    with pytest.raises(HTTPException) as exc:
        principal_dashboard_route.get_school(principal=fake_principal())
    assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard summary
# ─────────────────────────────────────────────────────────────────────────────

def test_dashboard_summary_splits_free_and_paid():
    result = principal_dashboard_route.get_dashboard_summary(principal=fake_principal())
    assert result["teacher_count"] == 1          # only teacher-1 is linked to school-1
    assert result["student_count"] == 2           # student-1 + student-2
    assert result["paid_student_count"] == 1      # student-1
    assert result["free_student_count"] == 1      # student-2
    assert result["conversion_rate"] == 50.0
    assert result["tier"] == "bronze"             # 1 paid student, well below silver (100)


# ─────────────────────────────────────────────────────────────────────────────
# Teachers
# ─────────────────────────────────────────────────────────────────────────────

def test_list_teachers_only_shows_linked_teachers():
    result = principal_dashboard_route.list_teachers(principal=fake_principal())
    ids = {t["id"] for t in result["teachers"]}
    assert ids == {"teacher-1"}
    assert result["teachers"][0]["assigned_students"] == 2


def test_link_teacher_by_email_sets_school_id(patch_admin_client):
    data = principal_dashboard_route.LinkAccountRequest(email="unlinked@example.com")
    result = principal_dashboard_route.link_teacher(data, principal=fake_principal())
    assert result["success"] is True

    linked = next(p for p in patch_admin_client.profiles if p["id"] == "teacher-2")
    assert linked["school_id"] == "school-1"


def test_link_teacher_rejects_unknown_email():
    data = principal_dashboard_route.LinkAccountRequest(email="nobody@example.com")
    with pytest.raises(HTTPException) as exc:
        principal_dashboard_route.link_teacher(data, principal=fake_principal())
    assert exc.value.status_code == 404


def test_link_teacher_never_touches_role_or_credentials(patch_admin_client):
    """Linking must only ever set school_id — never role, plan, or password fields."""
    before = dict(next(p for p in patch_admin_client.profiles if p["id"] == "teacher-2"))
    data = principal_dashboard_route.LinkAccountRequest(email="unlinked@example.com")
    principal_dashboard_route.link_teacher(data, principal=fake_principal())
    after = next(p for p in patch_admin_client.profiles if p["id"] == "teacher-2")

    for key in before:
        if key == "school_id":
            continue
        assert after[key] == before[key], f"link_teacher must not modify '{key}'"


def test_unlink_teacher_clears_school_id(patch_admin_client):
    result = principal_dashboard_route.unlink_teacher("teacher-1", principal=fake_principal())
    assert result["success"] is True
    unlinked = next(p for p in patch_admin_client.profiles if p["id"] == "teacher-1")
    assert unlinked["school_id"] is None


def test_unlink_teacher_rejects_teacher_from_other_school(patch_admin_client):
    with pytest.raises(HTTPException) as exc:
        principal_dashboard_route.unlink_teacher("teacher-2", principal=fake_principal())
    assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Students
# ─────────────────────────────────────────────────────────────────────────────

def test_list_students_all():
    result = principal_dashboard_route.list_students(tier="", principal=fake_principal())
    ids = {s["id"] for s in result["students"]}
    assert ids == {"student-1", "student-2"}


def test_list_students_joins_last_active_date_from_student_profiles(patch_admin_client):
    """
    Regression: last_active_date lives on student_profiles, not profiles —
    a prior version selected it straight off profiles and 500'd against a
    real database with "column profiles.last_active_date does not exist".
    """
    result = principal_dashboard_route.list_students(tier="", principal=fake_principal())
    by_id = {s["id"]: s["last_active_date"] for s in result["students"]}
    assert by_id["student-1"] == "2026-08-27"
    assert by_id["student-2"] == "2026-08-26"

    # A student with no student_profiles row must not crash — just None.
    patch_admin_client.profiles.append({
        "id": "student-4", "role": "student", "username": "No Gamification Row",
        "email": "nogami@example.com", "school_id": "school-1", "grade": "Grade 9",
        "access_cbse": False, "subscription_plan": "free", "subscription_expires_at": None,
        "created_at": "2026-02-01T00:00:00Z",
    })
    result = principal_dashboard_route.list_students(tier="", principal=fake_principal())
    by_id = {s["id"]: s["last_active_date"] for s in result["students"]}
    assert by_id["student-4"] is None


def test_list_students_filters_paid_only():
    result = principal_dashboard_route.list_students(tier="paid", principal=fake_principal())
    assert [s["id"] for s in result["students"]] == ["student-1"]
    assert result["students"][0]["tier"] == "paid"


def test_list_students_filters_free_only():
    result = principal_dashboard_route.list_students(tier="free", principal=fake_principal())
    assert [s["id"] for s in result["students"]] == ["student-2"]
    assert result["students"][0]["tier"] == "free"


def test_link_student_never_touches_plan_or_role(patch_admin_client):
    before = dict(next(p for p in patch_admin_client.profiles if p["id"] == "student-3"))
    data = principal_dashboard_route.LinkAccountRequest(email="unlinked.student@example.com")
    principal_dashboard_route.link_student(data, principal=fake_principal())
    after = next(p for p in patch_admin_client.profiles if p["id"] == "student-3")

    for key in before:
        if key == "school_id":
            continue
        assert after[key] == before[key], f"link_student must not modify '{key}'"
    assert after["school_id"] == "school-1"


def test_unlink_student_rejects_student_from_other_school(patch_admin_client):
    with pytest.raises(HTTPException) as exc:
        principal_dashboard_route.unlink_student("student-3", principal=fake_principal())
    assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Incentives
# ─────────────────────────────────────────────────────────────────────────────

def test_incentives_reports_current_tier_and_progress():
    result = principal_dashboard_route.get_incentives(principal=fake_principal())
    assert result["paid_student_count"] == 1
    assert result["tier"] == "bronze"
    assert result["next_tier"]["tier"] == "silver"
    assert result["redemption_history"] == []


def test_redeem_reward_rejects_locked_reward():
    """1 paid student → bronze tier; a gold-tier reward must be rejected."""
    data = principal_dashboard_route.RedeemRewardRequest(reward_key="gold_workbooks")
    with pytest.raises(HTTPException) as exc:
        principal_dashboard_route.redeem_reward(data, principal=fake_principal())
    assert exc.value.status_code == 403


def test_redeem_reward_succeeds_for_unlocked_reward(patch_admin_client):
    data = principal_dashboard_route.RedeemRewardRequest(reward_key="bronze_support")
    result = principal_dashboard_route.redeem_reward(data, principal=fake_principal())
    assert result["success"] is True
    assert len(patch_admin_client.redemptions) == 1
    assert patch_admin_client.redemptions[0]["reward_key"] == "bronze_support"
    assert patch_admin_client.redemptions[0]["status"] == "requested"


def test_redeem_reward_never_touches_an_individual_account(patch_admin_client):
    """A redemption must only ever write to school_reward_redemptions."""
    profiles_before = [dict(p) for p in patch_admin_client.profiles]
    data = principal_dashboard_route.RedeemRewardRequest(reward_key="bronze_support")
    principal_dashboard_route.redeem_reward(data, principal=fake_principal())
    assert patch_admin_client.profiles == profiles_before
