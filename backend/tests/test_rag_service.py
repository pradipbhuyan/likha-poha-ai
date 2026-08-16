from fastapi.routing import APIRoute

from app.main import app
from app.services.auth_service import require_admin
from app.services.rag_service import strip_chapter_display_prefix


def test_rag_upload_authorization_lives_in_the_route_layer():
    """
    RAG upload authorization is the route's job, via require_admin.

    upload_textbook_text() used to re-check authorization itself against a
    hard-coded username set {"admin", "pradip", "pradip admin"}. That was
    redundant once the routes gained require_admin, and wrong in the
    restrictive direction: any admin whose username was not one of those three
    literals silently got "Only an admin user can upload RAG content" on every
    upload. The check was removed; this test locks in that the route-level
    guard it delegated to is actually present.
    """
    upload_routes = [
        r for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/api/rag/") and "POST" in r.methods
    ]
    assert upload_routes, "expected RAG upload routes to be registered"

    for route in upload_routes:
        guards = set()

        def walk(dependant):
            if dependant.call is not None:
                guards.add(dependant.call)
            for sub in dependant.dependencies:
                walk(sub)

        for sub in route.dependant.dependencies:
            walk(sub)

        assert require_admin in guards, (
            f"POST {route.path} must depend on require_admin — service-layer "
            f"authorization was removed in favour of this guard."
        )


def test_strip_chapter_display_prefix_keeps_rag_filter_metadata_clean():
    """
    Student dropdowns may show book part prefixes, but RAG documents store the
    original chapter label.
    """
    assert strip_chapter_display_prefix(
        "Part 2 - Chapter 4: Exploring Some Geometric Themes"
    ) == "Chapter 4: Exploring Some Geometric Themes"
    assert strip_chapter_display_prefix(
        "Chapter 4: Exploring Some Geometric Themes"
    ) == "Chapter 4: Exploring Some Geometric Themes"
