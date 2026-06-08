from app.services.auth_service import admin_client


DEFAULT_ONBOARDING_GUIDE_SETTINGS = {
    "enabled": True,
    "active_theme": "quest",
    "rotation_enabled": False,
    "rotation_days": 14,
    "student_theme": "quest",
    "parent_theme": "clean",
    "teacher_theme": "forest",
    "show_once_per_theme": True,
    "auto_open": True,
    "message": (
        "A friendly first-time guide helps new users understand the main pages "
        "without feeling lost."
    ),
}

ALLOWED_THEMES = {"clean", "quest", "space", "forest"}


def _clean_theme(value, fallback):
    """Return a known guide theme id, falling back when settings are stale."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in ALLOWED_THEMES else fallback


def normalize_onboarding_guide_settings(row=None):
    """Merge a Supabase settings row with defaults for frontend-safe output."""
    settings = dict(DEFAULT_ONBOARDING_GUIDE_SETTINGS)

    if row:
        for key in settings:
            if key in row and row[key] is not None:
                settings[key] = row[key]

    settings["active_theme"] = _clean_theme(settings["active_theme"], "quest")
    settings["student_theme"] = _clean_theme(
        settings["student_theme"],
        settings["active_theme"],
    )
    settings["parent_theme"] = _clean_theme(
        settings["parent_theme"],
        settings["active_theme"],
    )
    settings["teacher_theme"] = _clean_theme(
        settings["teacher_theme"],
        settings["active_theme"],
    )
    settings["rotation_days"] = max(7, min(60, int(settings["rotation_days"] or 14)))
    settings["message"] = str(settings["message"] or "").strip()

    return settings


def get_onboarding_guide_settings():
    """Load onboarding guide settings, falling back to defaults if table is absent."""
    try:
        response = (
            admin_client
            .table("onboarding_guide_settings")
            .select("*")
            .eq("key", "default")
            .limit(1)
            .execute()
        )
        row = response.data[0] if response.data else None

        return {
            "settings": normalize_onboarding_guide_settings(row),
            "persisted": bool(row),
            "source": "database" if row else "defaults",
        }
    except Exception as exc:
        return {
            "settings": normalize_onboarding_guide_settings(),
            "persisted": False,
            "source": "defaults",
            "load_error": str(exc),
        }


def save_onboarding_guide_settings(payload, updated_by=None):
    """Persist admin-edited guide settings to Supabase."""
    settings = normalize_onboarding_guide_settings(payload)
    row = {
        "key": "default",
        **settings,
        "updated_by": updated_by,
    }

    response = (
        admin_client
        .table("onboarding_guide_settings")
        .upsert(row, on_conflict="key")
        .execute()
    )
    saved_row = response.data[0] if response.data else row

    return {
        "settings": normalize_onboarding_guide_settings(saved_row),
        "persisted": True,
        "source": "database",
    }
