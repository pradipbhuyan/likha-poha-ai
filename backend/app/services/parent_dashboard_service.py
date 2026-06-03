from app.services.auth_service import admin_client


def get_family_profile(user_id: str):
    """Load one parent/student profile with subscription and access fields."""
    response = (
        admin_client
        .table("profiles")
        .select(
            "id, email, username, role, parent_id, family_id, "
            "subscription_plan, account_status, access_cbse, "
            "access_sof_science, access_sof_maths, access_sof_english, "
            "daily_token_limit, monthly_token_limit"
        )
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data


def get_family_members(user_id: str):
    """Return all parent and child profiles in the user's family."""
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
        .select(
            "id, email, username, role, parent_id, family_id, "
            "subscription_plan, account_status, access_cbse, "
            "access_sof_science, access_sof_maths, access_sof_english, "
            "daily_token_limit, monthly_token_limit"
        )
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
    """Return child profiles visible to the given parent user."""
    return get_family_members(parent_user_id)["children"]


def get_parents(parent_user_id: str):
    """Return parent profiles in the given parent's family."""
    return get_family_members(parent_user_id)["parents"]


def get_child_by_id(parent_user_id: str, child_id: str):
    """Return a child only if it belongs to the given parent's family."""
    family = get_family_members(parent_user_id)
    family_id = family.get("family_id")

    if not family_id:
        return None

    response = (
        admin_client
        .table("profiles")
        .select(
            "id, email, username, role, parent_id, family_id, "
            "subscription_plan, account_status, access_cbse, "
            "access_sof_science, access_sof_maths, access_sof_english, "
            "daily_token_limit, monthly_token_limit"
        )
        .eq("id", child_id)
        .eq("family_id", family_id)
        .eq("role", "student")
        .single()
        .execute()
    )

    return response.data
