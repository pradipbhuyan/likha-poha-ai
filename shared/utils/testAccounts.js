/**
 * All-access QA test accounts.
 *
 * These accounts exist so the team can see exactly what a student sees —
 * every grade, every subject, no entitlement gates — without provisioning a
 * paid account per scenario.
 *
 * Identified solely by the `profiles.is_test_account` flag. It was previously
 * a username hard-coded here, which is a grant anyone could claim: signup
 * takes the username straight from a user-supplied field with no uniqueness
 * constraint. The flag is provisioned deliberately, revocable without a
 * deploy, and works for any number of QA accounts.
 *
 * To grant or revoke, no code change is needed:
 *   update public.profiles set is_test_account = <true|false> where id = '...';
 */
export function isAllAccessTestUser(user) {
  return user?.isTestAccount === true;
}
