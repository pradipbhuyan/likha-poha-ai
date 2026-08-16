-- ============================================================================
-- profiles.username uniqueness — INVESTIGATE FIRST, then decide
-- ============================================================================
-- WHY THIS MATTERS
--
-- require_self_by_username() in backend/app/services/auth_service.py authorizes
-- by comparing the caller's profile username to the username in the request
-- path:
--
--     if profile.get("username") != username and role not in ("admin", "teacher"):
--         raise HTTPException(403, ...)
--
-- The queries it guards then filter on that username STRING, not on the user
-- id:
--
--     get_user_progress(username)          -> student_progress.eq("username", ...)
--     get_student_profile(username)        -> student_profiles.eq("username", ...)
--     build_study_recommendations(...)     -> test_history.eq("username", ...)
--
-- So if two profiles share a username, each passes the guard for the other's
-- records and reads them. Signup does not prevent this: auth.py builds the
-- profile with `"username": data.name.strip()` from a user-supplied field, and
-- there is no uniqueness constraint on the column.
--
-- RESERVED_USERNAMES currently blocks this for the known-sensitive names only.
-- A uniqueness constraint is the real fix.
--
-- DO NOT blindly add the constraint — it will fail if duplicates already
-- exist, and the resolution is a product decision (which account keeps the
-- name). Work through the steps below in order.
-- ============================================================================

-- 1. Do duplicates exist today? Run this first.
--    Empty result = safe to add the constraint in step 3.
select lower(trim(username)) as normalized_username,
       count(*)              as accounts,
       array_agg(id)         as profile_ids,
       array_agg(role)       as roles,
       array_agg(email)      as emails
  from public.profiles
 where username is not null
   and trim(username) <> ''
 group by lower(trim(username))
having count(*) > 1
 order by count(*) desc;

-- 2. If step 1 returned rows, check whether the duplicates actually hold data.
--    Substitute a normalized_username from step 1.
-- select 'progress' as source, username, count(*)
--   from public.student_progress where lower(trim(username)) = '<name>' group by username
-- union all
-- select 'test_history', username, count(*)
--   from public.test_history where lower(trim(username)) = '<name>' group by username
-- union all
-- select 'student_profiles', username, count(*)
--   from public.student_profiles where lower(trim(username)) = '<name>' group by username;
--
--    Rows here mean the duplicate accounts are already sharing records, and
--    renaming one will not separate the history that has accumulated. Decide
--    per case which account keeps the name and which is renamed.

-- 3. Only once step 1 returns empty: enforce it going forward.
--    Case-insensitive, ignoring surrounding whitespace, which is how the
--    application compares usernames.
-- create unique index concurrently if not exists profiles_username_unique_ci
--     on public.profiles (lower(trim(username)))
--  where username is not null and trim(username) <> '';

-- ============================================================================
-- AFTER THE CONSTRAINT EXISTS
-- ============================================================================
-- Signup should catch the collision and return a friendly error rather than
-- surfacing a database exception — add a pre-insert check in the three signup
-- paths in backend/app/routes/auth.py (complete_signup, signup_free,
-- signup_with_offer_code), next to the existing _reject_reserved_username call.
--
-- RESERVED_USERNAMES still has a job after that: it stops the seeded demo and
-- QA account names being taken at all, which uniqueness alone would not do
-- (first claimant wins).
-- ============================================================================
