-- Teacher invitations: capture the chosen academic stream for Grade 11/12
-- invites so the student's profile gets the right stream + subjects the
-- moment they accept — matching the rule already enforced for parent-added
-- children (parent_dashboard.py) and self-signup (auth.py).
--
-- Run this in the Supabase SQL editor (Postgrest has no DDL).

ALTER TABLE teacher_invitations
    ADD COLUMN IF NOT EXISTS stream TEXT;
