-- ============================================================================
-- Resolve the four duplicate-username groups found 2026-08-16
-- ============================================================================
-- Detection (2026-08-16_check_username_uniqueness.sql step 1) returned:
--
--   shibanichild   2 students  ShibaniChild@mail.com | Shibanichild@child.likhapoha.in
--   vijay          2 students  vijay.sim.student@example.test | marketing.student@likhapoha.in
--   manish         2 parents   manish.sim.parent@example.test | marketing.parent@likhapoha.in
--   shibani        1 parent
--                  1 student   Shibani@mail.com | shibani.barooah1@gmail.com
--
-- THE TRAP: do not simply rename one profile.
--
-- student_progress, student_profiles and test_history are keyed by the
-- username STRING and carry no user id — progress_service writes
-- {"username": ..., "grade": ..., "subject": ...} with nothing tying the row
-- to a profile id. Renaming a profile therefore leaves its records behind
-- under the old name, where they become visible to whichever account keeps
-- it. That is worse than the duplicate.
--
-- The safe order is: find out who actually has data, THEN rename only an
-- account that has none.
-- ============================================================================

-- ============================================================================
-- RESOLVED 2026-08-16: all four groups confirmed as test accounts by the
-- platform owner and scheduled for deletion rather than renaming. See
-- 2026-08-16_delete_duplicate_test_accounts.sql, which supersedes the rename
-- path below. The queries here remain useful as a diagnostic if duplicates
-- reappear.
-- ============================================================================

-- ── 1. Which of the four names actually have records? ───────────────────────
-- Names with zero rows everywhere are free to rename either side.
with dupes(name) as (
  values ('shibanichild'), ('vijay'), ('manish'), ('shibani')
)
select d.name,
       (select count(*) from public.student_progress p
         where lower(trim(p.username)) = d.name)  as progress_rows,
       (select count(*) from public.test_history t
         where lower(trim(t.username)) = d.name)  as test_rows,
       (select count(*) from public.student_profiles s
         where lower(trim(s.username)) = d.name)  as gamified_rows,
       (select count(*) from public.weak_area_alerts w
         where lower(trim(w.username)) = d.name)  as weak_area_rows
  from dupes d
 order by d.name;

-- ── 2. For any name with rows, when were they written? ──────────────────────
-- Both accounts active over the same period means the history is already
-- comingled and cannot be split by query — there is no column to split on.
-- One account active and the other dormant usually means the dormant one is
-- safe to rename.
-- select username, min(updated_at) as first_seen, max(updated_at) as last_seen,
--        count(*) as rows
--   from public.student_progress
--  where lower(trim(username)) = 'shibani'
--  group by username;

-- ── 3. Rename the account that has NO records ───────────────────────────────
-- Only after step 1 shows it is safe. Pick the profile id from the detection
-- query. Suffix keeps the name recognisable in support conversations.
-- update public.profiles
--    set username = username || '.2'
--  where id = '<profile-id-with-no-records>';

-- ── 4. Re-run detection, then apply the constraint ──────────────────────────
-- See 2026-08-16_check_username_uniqueness.sql steps 1 and 3.

-- ============================================================================
-- READING THE FOUR CASES
-- ============================================================================
-- vijay, manish — both sides look synthetic (*.sim.* simulation accounts and
--   marketing.* demo accounts). If neither is a real customer, renaming or
--   deleting one side is low-risk regardless of what step 1 returns. Check
--   whether the simulation tooling recreates them, or the duplicate returns.
--
-- shibanichild — the @child.likhapoha.in address is a system-generated child
--   account, so this is most likely the same child created twice rather than
--   two different people. Confirm with the parent before touching either.
--
-- shibani — a parent and a student sharing one username, and the only group
--   spanning two roles. This is the one with real exposure: the parent
--   account passes require_self_by_username() for '/api/profile/shibani' and
--   '/api/progress/user/shibani' and reads the student's records. If both
--   accounts belong to the same person that is harmless in practice; if not,
--   it is a live cross-account read. Establish which before anything else.
--
-- ============================================================================
-- THE REAL FIX, LONGER TERM
-- ============================================================================
-- Key these tables on the profile id rather than the username, and treat
-- username as display text. That removes this whole class of problem: renames
-- become safe, duplicates stop being a data-leak vector, and
-- require_self_by_username() can compare ids instead of strings. It is a
-- backfill (add user_id, populate by username join, switch the queries, drop
-- the username filter) and should be planned rather than rushed — the join
-- itself is ambiguous for exactly the rows this file is about, so resolve
-- the four duplicates first.
-- ============================================================================
