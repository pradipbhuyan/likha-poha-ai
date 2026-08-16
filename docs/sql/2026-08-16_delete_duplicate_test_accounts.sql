-- ============================================================================
-- Delete the duplicate test accounts  —  PREVIEW FIRST, DELETE LAST
-- ============================================================================
-- Confirmed as test accounts by the platform owner, 2026-08-16.
--
--   shibanichild  982c90b7-137a-430b-b9c2-4bc6dc1dab64  student  ShibaniChild@mail.com
--   shibanichild  d8264f39-ac8a-4a7c-961b-fb755502dcae  student  Shibanichild@child.likhapoha.in
--   vijay         d4db478b-f4b5-4d88-bc2b-00bbe09a33ae  student  vijay.sim.student@example.test
--   vijay         5b7d1e35-26e7-4827-99cf-8a871019e6b2  student  marketing.student@likhapoha.in
--   manish        e4aa657a-7619-456c-becd-a28793c3f6b7  parent   manish.sim.parent@example.test
--   manish        5a2743d1-4454-44ba-a8a2-8196fbe415ee  parent   marketing.parent@likhapoha.in
--   shibani       cd56fa27-9700-43ed-9a34-ec0528ca619c  parent   Shibani@mail.com
--   shibani       93ce54e5-1f1f-4b5e-8edc-5b851afa2597  student  shibani.barooah1@gmail.com
--
-- CHECK THIS ONE BEFORE RUNNING: shibani.barooah1@gmail.com is the only
-- address here that reads like a real person's primary mailbox rather than a
-- synthetic one (@example.test, @likhapoha.in, @child.likhapoha.in, and the
-- throwaway @mail.com pair). If it belongs to someone real, drop that id from
-- section 4 and keep the account — the duplicate is resolved either way once
-- the parent 'shibani' account goes.
--
-- ── WHY THIS IS NOT ONE DELETE STATEMENT ────────────────────────────────────
--
-- Seven tables store user data keyed by the username STRING with no foreign
-- key to profiles, so deleting a profile row leaves them behind entirely:
--
--     student_progress, test_history, weak_area_alerts, student_profiles,
--     mock_test_wrong_answers, ai_usage_logs, board_paper_attempts
--
-- Worse, those orphans stay attached to the *name*. Leaving them means the
-- next account that registers one of these usernames inherits the test data
-- and its history. Clean the username-keyed rows first, the profile second,
-- and the Supabase auth user last.
--
-- Deleting a profiles row also does NOT delete the auth.users row behind it.
-- Section 6 covers that.
-- ============================================================================

-- ============================================================================
-- 1. PREVIEW — what exists today. Run this and keep the output.
-- ============================================================================
with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
select t.username,
       (select count(*) from public.student_progress        x where lower(trim(x.username)) = t.username) as progress,
       (select count(*) from public.test_history            x where lower(trim(x.username)) = t.username) as tests,
       (select count(*) from public.weak_area_alerts        x where lower(trim(x.username)) = t.username) as weak_areas,
       (select count(*) from public.student_profiles        x where lower(trim(x.username)) = t.username) as gamified,
       (select count(*) from public.mock_test_wrong_answers x where lower(trim(x.username)) = t.username) as wrong_answers,
       (select count(*) from public.ai_usage_logs           x where lower(trim(x.username)) = t.username) as ai_logs,
       (select count(*) from public.board_paper_attempts    x where lower(trim(x.username)) = t.username) as board_attempts
  from targets t
 order by t.username;

-- ============================================================================
-- 2. SAFETY CHECK — do the two 'manish' parent accounts have children?
-- ============================================================================
-- Deleting a parent orphans any child profile pointing at it. If this returns
-- rows, decide what happens to those children BEFORE deleting the parents.
select p.id            as child_id,
       p.username      as child_username,
       p.email         as child_email,
       p.parent_id,
       p.family_id
  from public.profiles p
 where p.parent_id in (
         'e4aa657a-7619-456c-becd-a28793c3f6b7',
         '5a2743d1-4454-44ba-a8a2-8196fbe415ee',
         'cd56fa27-9700-43ed-9a34-ec0528ca619c'   -- shibani (parent)
       );

-- Same question for families these accounts belong to.
select id, username, email, role, family_id
  from public.profiles
 where family_id in (
         select family_id from public.profiles
          where id in (
            'e4aa657a-7619-456c-becd-a28793c3f6b7',
            '5a2743d1-4454-44ba-a8a2-8196fbe415ee',
            'cd56fa27-9700-43ed-9a34-ec0528ca619c'
          ) and family_id is not null
       )
 order by family_id, role;

-- ============================================================================
-- 3. BACKUP — snapshot the profile rows before deleting anything.
-- ============================================================================
-- Cheap insurance. The nightly db-backup workflow covers the database as a
-- whole, but this keeps the eight rows to hand without a restore.
create table if not exists public.profiles_deleted_20260816 as
select * from public.profiles
 where id in (
   '982c90b7-137a-430b-b9c2-4bc6dc1dab64',
   'd8264f39-ac8a-4a7c-961b-fb755502dcae',
   'd4db478b-f4b5-4d88-bc2b-00bbe09a33ae',
   '5b7d1e35-26e7-4827-99cf-8a871019e6b2',
   'e4aa657a-7619-456c-becd-a28793c3f6b7',
   '5a2743d1-4454-44ba-a8a2-8196fbe415ee',
   'cd56fa27-9700-43ed-9a34-ec0528ca619c',
   '93ce54e5-1f1f-4b5e-8edc-5b851afa2597'
 );

select count(*) as backed_up from public.profiles_deleted_20260816;  -- expect 8

-- ============================================================================
-- 4. DELETE — username-keyed data first
-- ============================================================================
-- Run as one transaction so a failure part-way leaves nothing half-removed.
-- Remove 'shibani' from the list below if that gmail account turns out to be
-- a real person — but note the username-keyed tables cannot distinguish the
-- parent's rows from the student's, so keeping the student means keeping the
-- name's data wholesale.

begin;

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.student_progress
 where lower(trim(username)) in (select username from targets);

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.test_history
 where lower(trim(username)) in (select username from targets);

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.weak_area_alerts
 where lower(trim(username)) in (select username from targets);

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.student_profiles
 where lower(trim(username)) in (select username from targets);

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.mock_test_wrong_answers
 where lower(trim(username)) in (select username from targets);

with targets(username) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
delete from public.board_paper_attempts
 where lower(trim(username)) in (select username from targets);

-- ai_usage_logs is cost/telemetry history rather than user content. Deleting
-- it rewrites past spend reporting, so it is left in place by default.
-- Uncomment only if you want these accounts out of the usage figures too.
-- with targets(username) as (
--   values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
-- )
-- delete from public.ai_usage_logs
--  where lower(trim(username)) in (select username from targets);

commit;

-- ============================================================================
-- 5. DELETE — the profile rows
-- ============================================================================
-- Only after section 2 confirmed no children are orphaned.
delete from public.profiles
 where id in (
   '982c90b7-137a-430b-b9c2-4bc6dc1dab64',
   'd8264f39-ac8a-4a7c-961b-fb755502dcae',
   'd4db478b-f4b5-4d88-bc2b-00bbe09a33ae',
   '5b7d1e35-26e7-4827-99cf-8a871019e6b2',
   'e4aa657a-7619-456c-becd-a28793c3f6b7',
   '5a2743d1-4454-44ba-a8a2-8196fbe415ee',
   'cd56fa27-9700-43ed-9a34-ec0528ca619c',
   '93ce54e5-1f1f-4b5e-8edc-5b851afa2597'
 );

-- ============================================================================
-- 6. DELETE — the Supabase auth users
-- ============================================================================
-- Deleting from public.profiles leaves auth.users intact, and those accounts
-- can still sign in — they just land without a profile. Remove them from the
-- Supabase dashboard (Authentication > Users, search each email) or via the
-- admin API. Do this last: it is the least reversible step.

-- ============================================================================
-- 7. VERIFY
-- ============================================================================
-- Duplicate detection should now return nothing.
select lower(trim(username)) as normalized_username, count(*) as accounts
  from public.profiles
 where username is not null and trim(username) <> ''
 group by lower(trim(username))
having count(*) > 1;

-- Then apply the uniqueness constraint from
-- 2026-08-16_check_username_uniqueness.sql step 3, and drop the backup table
-- once you are satisfied:
--   drop table public.profiles_deleted_20260816;
-- ============================================================================
