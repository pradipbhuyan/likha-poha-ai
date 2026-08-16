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
-- AFTERWARDS
-- ============================================================================
-- Once the query above returns the expected row, the username fallback can be
-- deleted from both of these, leaving the flag as the only source of truth:
--
--   backend/app/services/test_account_service.py  -> _LEGACY_TEST_USERNAMES
--   shared/utils/testAccounts.js                  -> LEGACY_TEST_USERNAMES
--   frontend/src/utils/testAccounts.js            -> LEGACY_TEST_USERNAMES
--
-- 'akshita.teststudent' can then also come out of RESERVED_USERNAMES in
-- backend/app/routes/auth.py, since the name would no longer grant anything.
--
-- To revoke access later, no deploy is needed:
--   update public.profiles set is_test_account = false where username = '...';
-- ============================================================================
