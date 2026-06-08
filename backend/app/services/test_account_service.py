ALL_ACCESS_TEST_USERNAMES = {"akshita.teststudent"}


def normalize_username(value: str | None) -> str:
    """Normalize usernames used for narrowly scoped test-account behavior."""
    return str(value or "").strip().casefold()


def is_all_access_test_user(profile: dict | None) -> bool:
    """Return true for test accounts that should bypass learning access gates."""
    return normalize_username((profile or {}).get("username")) in ALL_ACCESS_TEST_USERNAMES
