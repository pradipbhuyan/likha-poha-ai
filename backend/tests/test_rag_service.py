from app.services.rag_service import (
    is_admin_upload_user,
    strip_chapter_display_prefix,
)


def test_admin_upload_user_accepts_profile_display_name():
    """
    RAG uploads should accept the admin profile name used by the frontend.

    The login profile can provide "Pradip Admin" while older upload checks only
    allowed "admin" or "pradip".
    """
    assert is_admin_upload_user("Pradip Admin") is True
    assert is_admin_upload_user(" admin ") is True
    assert is_admin_upload_user("student") is False


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
