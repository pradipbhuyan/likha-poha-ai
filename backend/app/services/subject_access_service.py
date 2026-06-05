def normalize_subject(value):
    """Normalize a subject label for access-list comparisons."""
    return " ".join(str(value or "").strip().casefold().split())


def clean_subject_access_list(subjects):
    """Return a deduplicated list of configured subject labels."""
    cleaned = []
    seen = set()

    for subject in subjects or []:
        label = str(subject or "").strip()
        key = normalize_subject(label)

        if not label or key in seen:
            continue

        cleaned.append(label)
        seen.add(key)

    return cleaned


def has_cbse_subject_access(profile, subject):
    """
    Return whether a profile may access one CBSE subject.

    An empty cbse_subjects list preserves the historical behavior: CBSE access
    means all CBSE subjects. A populated list creates a custom low-cost plan.
    """
    allowed_subjects = clean_subject_access_list(
        (profile or {}).get("cbse_subjects") or []
    )

    if not allowed_subjects:
        return True

    subject_key = normalize_subject(subject)

    return any(
        normalize_subject(allowed_subject) == subject_key
        for allowed_subject in allowed_subjects
    )
