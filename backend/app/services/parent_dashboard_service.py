from app.services.auth_service import admin_client


def get_family_profile(user_id: str):
    response = (
        admin_client
        .table("profiles")
        .select("id, email, username, role, parent_id, family_id")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data


def get_family_members(user_id: str):
    profile = get_family_profile(user_id)

    if not profile or not profile.get("family_id"):
        return {
            "family_id": None,
            "parents": [],
            "children": [],
        }

    family_id = profile["family_id"]

    response = (
        admin_client
        .table("profiles")
        .select("id, email, username, role, parent_id, family_id")
        .eq("family_id", family_id)
        .execute()
    )

    members = response.data or []

    return {
        "family_id": family_id,
        "parents": [m for m in members if m.get("role") == "parent"],
        "children": [m for m in members if m.get("role") == "student"],
    }


def get_children(parent_user_id: str):
    return get_family_members(parent_user_id)["children"]


def get_parents(parent_user_id: str):
    return get_family_members(parent_user_id)["parents"]


def get_child_by_id(parent_user_id: str, child_id: str):
    family = get_family_members(parent_user_id)
    family_id = family.get("family_id")

    if not family_id:
        return None

    response = (
        admin_client
        .table("profiles")
        .select("id, email, username, role, parent_id, family_id")
        .eq("id", child_id)
        .eq("family_id", family_id)
        .eq("role", "student")
        .single()
        .execute()
    )

    return response.data