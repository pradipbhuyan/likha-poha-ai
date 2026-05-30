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