from app.services.subject_access_service import (
    clean_subject_access_list,
    has_cbse_subject_access,
)


def test_empty_cbse_subject_list_allows_all_subjects():
    """Existing plans should keep all CBSE subjects when no custom list exists."""
    profile = {
        "cbse_subjects": [],
    }

    assert has_cbse_subject_access(profile, "Science") is True
    assert has_cbse_subject_access(profile, "English") is True


def test_custom_cbse_subject_list_limits_subjects_case_insensitively():
    """Custom subject lists allow only matching CBSE subjects."""
    profile = {
        "cbse_subjects": ["Science", "Maths"],
    }

    assert has_cbse_subject_access(profile, "science") is True
    assert has_cbse_subject_access(profile, "Maths") is True
    assert has_cbse_subject_access(profile, "English") is False


def test_clean_subject_access_list_deduplicates_labels():
    """Admin-submitted subject lists should stay clean before persistence."""
    assert clean_subject_access_list([" Science ", "science", "", "Maths"]) == [
        "Science",
        "Maths",
    ]
