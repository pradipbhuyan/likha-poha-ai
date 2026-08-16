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
-- ============================================================================
