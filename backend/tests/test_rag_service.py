from app.services.rag_service import is_admin_upload_user


def test_admin_upload_user_accepts_profile_display_name():
    """
    RAG uploads should accept the admin profile name used by the frontend.

    The login profile can provide "Pradip Admin" while older upload checks only
    allowed "admin" or "pradip".
    """
    assert is_admin_upload_user("Pradip Admin") is True
    assert is_admin_upload_user(" admin ") is True
    assert is_admin_upload_user("student") is False
