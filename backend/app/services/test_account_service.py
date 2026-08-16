"""
All-access QA test accounts.

These accounts exist so the team can see exactly what a student sees — every
grade, every subject, no entitlement gates — without provisioning a paid
account per scenario.

Identified solely by the `profiles.is_test_account` flag. It was previously a
username hard-coded here, which is a grant anyone could claim: auth.py builds
the profile with `"username": data.name.strip()`, taken from a user-supplied
field with no uniqueness constraint. The flag is provisioned deliberately,
revocable without a deploy, and works for any number of QA accounts.

To grant or revoke, no code change is needed:
    update public.profiles set is_test_account = <true|false> where id = '...';
"""


def is_all_access_test_user(profile: dict | None) -> bool:
    """Return true for test accounts that should bypass learning access gates."""
    return (profile or {}).get("is_test_account") is True
