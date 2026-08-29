"""
test_admin_schools.py
─────────────────────────────────────────────────────────────────────────────
Tests for app/routes/admin_schools.py — admin verify/reject of a
principal-created school. Mirrors the pending-teacher approval tests in
spirit (same pattern as admin_support.py's verify-teacher).
"""
import pytest
from unittest.mock import MagicMock, patch

import app.routes.admin_schools as admin_schools_route


def fake_admin():
    return {"profile": {"id": "admin-1", "role": "admin"}}


def _table_router(schools_by_id, profiles_by_id):
    def router(name):
        table = MagicMock()
        if name == "schools":
            def select_chain(*_a, **_k):
                chain = MagicMock()

                def eq(key, value):
                    if key == "status":
                        matches = [s for s in schools_by_id.values() if s.get("status") == value]
                        response = MagicMock(data=matches)
                    elif key == "id":
                        row = schools_by_id.get(value)
                        response = MagicMock(data=[row] if row else [])
                    else:
                        return chain
                    # Route under test may chain either .limit().execute() or
                    # .order().execute() — stub both so it doesn't matter which.
                    chain.limit.return_value.execute.return_value = response
                    chain.order.return_value.execute.return_value = response
                    return chain
                chain.eq.side_effect = eq
                return chain
            table.select.side_effect = select_chain

            def update(payload):
                chain = MagicMock()

                def eq(_key, value):
                    if value in schools_by_id:
                        schools_by_id[value].update(payload)
                    return MagicMock(execute=MagicMock(return_value=MagicMock(data=[])))
                chain.eq.side_effect = eq
                return chain
            table.update.side_effect = update
            return table

        if name == "profiles":
            def update(payload):
                chain = MagicMock()

                def eq(_key, value):
                    if value in profiles_by_id:
                        profiles_by_id[value].update(payload)
                    return MagicMock(execute=MagicMock(return_value=MagicMock(data=[])))
                chain.eq.side_effect = eq
                return chain
            table.update.side_effect = update

            def select_chain(*_a, **_k):
                chain = MagicMock()

                def in_(_key, values):
                    matches = [profiles_by_id[v] for v in values if v in profiles_by_id]
                    chain.execute.return_value = MagicMock(data=matches)
                    return chain
                chain.in_.side_effect = in_
                return chain
            table.select.side_effect = select_chain
            return table

        if name == "platform_audit_logs":
            table.insert.return_value.execute.return_value = MagicMock(data=[])
            return table

        return MagicMock()
    return router


@pytest.fixture
def seed():
    schools = {
        "school-1": {
            "id": "school-1", "name": "Sunrise Public School",
            "status": "pending_verification", "principal_id": "principal-1",
        }
    }
    profiles = {
        "principal-1": {
            "id": "principal-1", "role": "principal", "account_status": "pending_verification",
            "username": "Meera Kalita", "email": "meera@example.com",
        },
    }
    return schools, profiles


def test_list_pending_schools_returns_only_pending(seed):
    schools, profiles = seed
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router(schools, profiles)
        result = admin_schools_route.list_pending_schools(admin=fake_admin())
        assert len(result["schools"]) == 1
        assert result["schools"][0]["id"] == "school-1"


def test_list_pending_schools_attaches_principal_identity(seed):
    """An admin approving a school needs to see who the principal is, not just the school."""
    schools, profiles = seed
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router(schools, profiles)
        result = admin_schools_route.list_pending_schools(admin=fake_admin())
    assert result["schools"][0]["principal_username"] == "Meera Kalita"
    assert result["schools"][0]["principal_email"] == "meera@example.com"


def test_verify_school_activates_school_and_principal(seed):
    schools, profiles = seed
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router(schools, profiles)
        with patch("app.routes.admin_schools.write_audit_event"):
            result = admin_schools_route.verify_school("school-1", admin=fake_admin())

    assert result["success"] is True
    assert schools["school-1"]["status"] == "active"
    assert profiles["principal-1"]["account_status"] == "active"


def test_verify_school_rejects_already_active_school(seed):
    schools, profiles = seed
    schools["school-1"]["status"] = "active"
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router(schools, profiles)
        result = admin_schools_route.verify_school("school-1", admin=fake_admin())

    assert result["success"] is False
    assert schools["school-1"]["status"] == "active"  # unchanged


def test_reject_school_sets_status_rejected(seed):
    schools, profiles = seed
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router(schools, profiles)
        with patch("app.routes.admin_schools.write_audit_event"):
            result = admin_schools_route.reject_school("school-1", admin=fake_admin())

    assert result["success"] is True
    assert schools["school-1"]["status"] == "rejected"
    # Rejecting must never touch the principal's own account state.
    assert profiles["principal-1"]["account_status"] == "pending_verification"


def test_verify_unknown_school_returns_error():
    with patch("app.routes.admin_schools.admin_client") as mock_client:
        mock_client.table.side_effect = _table_router({}, {})
        result = admin_schools_route.verify_school("does-not-exist", admin=fake_admin())
    assert result["success"] is False
