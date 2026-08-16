/**
 * All-access QA test accounts.
 *
 * These accounts exist so the team can see exactly what a student sees —
 * every grade, every subject, no entitlement gates — without provisioning a
 * paid account per scenario.
 *
 * The account is identified by a `profiles.is_test_account` flag, not by its
 * username. Usernames come straight from a user-supplied field at signup with
 * no uniqueness constraint, so a name in shipped code is a grant anyone can
 * claim by registering it. A database flag is provisioned deliberately,
 * revocable without a deploy, and works for more than one QA account.
 *
 * LEGACY FALLBACK: the username set below still grants access so this keeps
 * working before the `is_test_account` column is populated. Delete
 * LEGACY_TEST_USERNAMES (and the `||` clause) once the flag is set on the
 * account — see docs/sql/2026-08-16_add_is_test_account.sql.
 */
const LEGACY_TEST_USERNAMES = new Set(["akshita.teststudent"]);

export function normalizeUsername(value) {
  return String(value || "").trim().toLowerCase();
}

export function isAllAccessTestUser(user) {
  if (user?.isTestAccount === true) return true;
  return LEGACY_TEST_USERNAMES.has(normalizeUsername(user?.username));
}
