"""
All-access QA test accounts.

These accounts exist so the team can see exactly what a student sees — every
grade, every subject, no entitlement gates — without provisioning a paid
account per scenario.

The account is identified by a `profiles.is_test_account` flag, not by its
username. Usernames come straight from a user-supplied field at signup
(auth.py builds the profile with `"username": data.name.strip()`) with no
uniqueness constraint, so a username hard-coded here is a grant anyone can
claim by registering that name. A database flag is provisioned deliberately,
revocable without a deploy, and supports more than one QA account.

LEGACY FALLBACK: the username set below still grants access so this keeps
working before the `is_test_account` column is populated. Delete
_LEGACY_TEST_USERNAMES (and the fallback branch) once the flag is set on the
account — see docs/sql/2026-08-16_add_is_test_account.sql.
"""

_LEGACY_TEST_USERNAMES = {"akshita.teststudent"}


def normalize_username(value: str | None) -> str:
    """Normalize usernames used for narrowly scoped test-account behavior."""
    return str(value or "").strip().casefold()


def is_all_access_test_user(profile: dict | None) -> bool:
    """Return true for test accounts that should bypass learning access gates."""
    if (profile or {}).get("is_test_account") is True:
        return True

    return normalize_username((profile or {}).get("username")) in _LEGACY_TEST_USERNAMES
