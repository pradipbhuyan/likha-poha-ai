-- ============================================================================
-- Add profiles.is_test_account
-- ============================================================================
-- Replaces the hard-coded QA username set in test_account_service.py and
-- shared/utils/testAccounts.js.
--
-- WHY: signup builds the profile with `"username": data.name.strip()` — taken
-- from a user-supplied field, with no uniqueness constraint. A username
-- hard-coded in shipped code is therefore a grant anyone can claim by
-- registering that name. A column is provisioned deliberately, revocable
-- without a deploy, and works for more than one QA account.
--
-- SAFE TO RUN BEFORE OR AFTER THE CODE DEPLOY. The application reads the flag
-- when present and falls back to the legacy username list when the column is
-- absent, so the test account keeps working either way. Running this first is
-- still preferred.
--
-- Run against BOTH Supabase projects if Grade 11/12 uses a separate one.
-- ============================================================================

-- 1. Add the column (idempotent).
alter table public.profiles
  add column if not exists is_test_account boolean not null default false;

comment on column public.profiles.is_test_account is
  'All-access QA account: bypasses learning entitlement gates so the team can '
  'see exactly what a student sees. Grant sparingly; audit periodically.';

-- 2. Grant it to the existing QA account.
update public.profiles
   set is_test_account = true
 where lower(trim(username)) = 'akshita.teststudent';

-- 3. Verify — expect exactly the QA account, role 'student'.
select id, username, role, is_test_account
  from public.profiles
 where is_test_account = true;

-- ============================================================================
-- AFTERWARDS  —  applied 2026-08-16, verify query returned the expected row
-- ============================================================================
-- The username fallback has been removed from all three files; the flag is now
-- the only source of truth:
--
--   backend/app/services/test_account_service.py
--   shared/utils/testAccounts.js
--   frontend/src/utils/testAccounts.js
--
-- CORRECTION to this file's original note: it said 'akshita.teststudent' could
-- then come out of RESERVED_USERNAMES in backend/app/routes/auth.py. That was
-- wrong, and it stays reserved. require_self_by_username() authorizes by
-- comparing the caller's profile username to the one in the request path,
-- while the queries behind it (get_user_progress, get_student_profile,
-- build_study_recommendations) filter on that username STRING. Two accounts
-- sharing a username would each pass the guard for the other's records and
-- read them. Reserving the name is what prevents that for the known-sensitive
-- accounts; see 2026-08-16_check_username_uniqueness.sql for the real fix.
--
-- To revoke test access later, no deploy is needed:
--   update public.profiles set is_test_account = false where id = '...';
--
-- ============================================================================
-- FOLLOW-UP  —  2026-08-17: the column was set but the account had no access
-- ============================================================================
-- Setting the flag is necessary but was not sufficient. GET /api/auth/profile
-- never returned is_test_account, and that endpoint is what the client reads
-- on login, on app load, and on every profile refresh. The client assigns the
-- field as `!!p.is_test_account` with no fallback, so an omitted field did not
-- leave the flag alone — it set it to false on every one of those paths.
--
-- While the username fallback was still in place the client fell back to the
-- name and access worked, which is why this was invisible until the fallback
-- was deleted. The row was correct the whole time; only the transport was not.
--
-- Fixed by returning the flag from /api/auth/profile (and the access_sof_*
-- trio, omitted the same way and zeroed on the client for the same reason),
-- and by reading it in LoginPage.buildLoginUser. The client now merges it with
-- `??` so a genuinely revoked flag (false) still wins while an absent field
-- leaves the held value alone.
--
-- Verify a grant end to end, not just in the table — the query below confirms
-- the row, but only the API response confirms the account can actually use it:
--   curl -s "$API/api/auth/profile" -H "Authorization: Bearer $TOKEN" \
--     | python3 -c 'import json,sys; print(json.load(sys.stdin)["is_test_account"])'
--
-- Regression tests: backend/tests/test_privileged_account_identification.py,
-- class TestFlagReachesTheClient — asserts the response contract rather than
-- the helper, because the helper was never the thing that was wrong.
-- ============================================================================
