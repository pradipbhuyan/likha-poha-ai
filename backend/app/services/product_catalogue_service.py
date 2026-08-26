"""
product_catalogue_service.py
─────────────────────────────────────────────────────────────────────────────
Live-loads the product catalogue (grade/coaching-program visibility) from the
admin_settings DB row, falling back to the hardcoded defaults in
app.data.product_catalogue when no row exists yet.

This is the single place any code — admin routes or student-facing
enforcement (e.g. signup grade validation) — must go through to know what's
actually visible right now. Reading app.data.product_catalogue's
DEFAULT_PRODUCT_CATALOGUE directly ignores whatever an admin has toggled via
the Product Catalogue admin page, since the DB row (when present) overrides
those hardcoded defaults.
"""
from __future__ import annotations

import copy

from app.data.product_catalogue import (
    DEFAULT_PRODUCT_CATALOGUE,
    get_visible_coaching_programs,
    get_visible_grades,
)

_CATALOGUE_KEY = "product_catalogue"


def _merge_with_defaults(stored: dict) -> dict:
    """
    Merge a DB-stored catalogue onto the current hardcoded defaults, section
    by section and key by key: a key the stored row already has keeps its
    stored value (an admin's real toggle); a key the stored row DOESN'T have
    keeps the current default rather than vanishing; a key the stored row
    has that ISN'T in the current defaults is dropped as orphaned.

    Why this exists (found live 2026-08-26, not hypothetical): a real
    `admin_settings` row already existed with `coaching_programs` keyed
    "JEE"/"NEET"/"CUET" (all visible:false, no entry at all for
    "sat"/"ielts"/"toefl_ibt") — saved before this section was renamed to
    "jee_main"/"neet_ug"/"cuet_ug" and expanded to six exams. Without this
    merge, that one stale row would have (a) made every exam read as hidden
    the moment TD-14's /status fix shipped, and (b) shown the admin a
    catalogue page with 3 dead keys that don't match anything real anymore,
    where toggling any of them would silently do nothing — the exact bug
    TD-14 was about, just re-introduced one level up via stale data instead
    of missing code. The next admin save naturally writes the merged,
    current-schema catalogue back, self-correcting the DB row for good.
    """
    merged = copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE)
    for section, defaults in merged.items():
        stored_section = stored.get(section, {})
        for key in defaults:
            if key in stored_section:
                defaults[key] = stored_section[key]
    return merged


def load_product_catalogue() -> dict:
    """Return the live catalogue from admin_settings, merged onto the
    hardcoded defaults (see _merge_with_defaults) — or just the defaults
    when no row exists yet."""
    try:
        from app.services.auth_service import admin_client  # noqa: PLC0415
        resp = (
            admin_client
            .table("admin_settings")
            .select("value")
            .eq("key", _CATALOGUE_KEY)
            .limit(1)
            .execute()
        )
        if resp.data:
            return _merge_with_defaults(resp.data[0]["value"])
    except Exception:
        pass
    return copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE)


def save_product_catalogue(catalogue: dict) -> None:
    """Upsert the catalogue into admin_settings."""
    from app.services.auth_service import admin_client  # noqa: PLC0415
    admin_client.table("admin_settings").upsert(
        {"key": _CATALOGUE_KEY, "value": catalogue},
        on_conflict="key",
    ).execute()


def get_live_visible_grades() -> set[str]:
    """
    Return the set of grades currently visible to students, honoring
    whatever an admin has toggled via the Product Catalogue admin page.

    Callers that accept a student-supplied grade (signup, profile edits)
    must validate against this — not the static ALL_GRADES_INCLUDING_HIDDEN
    list — or the admin's "hide this grade" switch has no real effect.
    """
    return set(get_visible_grades(load_product_catalogue()))


def get_live_visible_coaching_programs() -> set[str]:
    """
    Return the set of Exam Prep Center exam keys currently visible to
    students (jee_main / neet_ug / cuet_ug / sat / ielts / toefl_ibt),
    honoring whatever an admin has toggled via the Product Catalogue admin
    page's Coaching Programs section.

    Added 2026-08-26 (TECH_DEBT.md TD-14) — mirrors get_live_visible_grades().
    Before this, the "visible" toggle on this admin page was cosmetic: it
    saved to the DB but nothing ever read it back, so it silently did
    nothing. exam_prep.py's GET /status must call this instead of
    hardcoding every exam as active.
    """
    return set(get_visible_coaching_programs(load_product_catalogue()))
