-- Enforce uniqueness on profiles.username
-- Run this in Supabase SQL Editor
--
-- get_child_analytics, get_parent_dashboard_summary (parent_dashboard.py),
-- get_user_progress, and build_study_recommendations all filter
-- test_history/student_progress/weak_area_alerts/ai_usage_logs by the
-- `username` STRING, not by profile id. Two profiles sharing a username
-- therefore each see the other's mock test scores and progress. This
-- collided for real on 2026-08-20 (two "likha" profiles — see
-- docs/sql/2026-08-16_check_username_uniqueness.sql for the original
-- investigation).
--
-- Application-level checks now exist in backend/app/routes/auth.py
-- (_reject_taken_username, called from complete_signup, signup_free,
-- signup_with_offer_code) and parent_dashboard.py (create_student), but
-- those are best-effort — this index is the real backstop.
--
-- IMPORTANT: run docs/sql/2026-08-16_check_username_uniqueness.sql step 1
-- first. If it returns any rows, resolve those duplicates (rename the
-- account that should lose the name) before running this — the index
-- creation will fail while duplicates exist.

create unique index concurrently if not exists profiles_username_unique_ci
    on public.profiles (lower(trim(username)))
 where username is not null and trim(username) <> '';
