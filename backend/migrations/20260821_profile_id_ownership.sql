-- Staged migration from mutable username ownership to profiles.id ownership.
--
-- Safe rollout order:
--   1. Apply this migration.
--   2. Deploy the dual-write/profile_id-read application release.
--   3. Verify the audit queries at the bottom return no unexpected rows.
--
-- Username columns intentionally remain in place as display/audit snapshots.
-- This migration does not rename/delete profiles or broadly purge history.
-- It removes one reviewed, byte-equivalent duplicate progress row under a
-- guarded, idempotent check immediately before creating the unique index.

begin;

do $migration$
declare
  table_name text;
  fk_name text;
begin
  foreach table_name in array array[
    'ai_usage_events',
    'ai_usage_logs',
    'board_paper_attempts',
    'doubt_history',
    'mentor_memory',
    'mock_test_wrong_answers',
    'student_profiles',
    'student_progress',
    'test_history',
    'unanswered_questions',
    'user_feedback',
    'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || table_name) is not null then
      execute format(
        'alter table public.%I add column if not exists profile_id uuid',
        table_name
      );

      -- profiles.username is now unique on lower(trim(username)), so this
      -- backfill is deterministic. Rows with no matching profile remain NULL
      -- for explicit review instead of being assigned speculatively.
      execute format(
        'update public.%I owned
            set profile_id = profile.id
           from public.profiles profile
          where owned.profile_id is null
            and owned.username is not null
            and lower(trim(owned.username)) = lower(trim(profile.username))',
        table_name
      );

      fk_name := table_name || '_profile_id_fkey';
      if not exists (
        select 1
          from pg_constraint
         where conname = fk_name
           and conrelid = ('public.' || table_name)::regclass
      ) then
        execute format(
          'alter table public.%I
             add constraint %I foreign key (profile_id)
             references public.profiles(id) on delete cascade not valid',
          table_name,
          fk_name
        );
      end if;
    end if;
  end loop;
end
$migration$;

-- Compatibility bridge for the many existing writers that still send a
-- username. New/updated rows receive profile_id atomically in Postgres, so a
-- rolling application deployment cannot create a new ownership gap.
create or replace function public.set_profile_id_from_username()
returns trigger
language plpgsql
security definer
set search_path = public
as $function$
begin
  if new.profile_id is null and new.username is not null then
    select profile.id
      into new.profile_id
      from public.profiles profile
     where lower(trim(profile.username)) = lower(trim(new.username));
  end if;
  return new;
end
$function$;

do $triggers$
declare
  table_name text;
  trigger_name text;
begin
  foreach table_name in array array[
    'ai_usage_events', 'ai_usage_logs', 'board_paper_attempts',
    'doubt_history', 'mentor_memory', 'mock_test_wrong_answers',
    'student_profiles', 'student_progress', 'test_history',
    'unanswered_questions', 'user_feedback', 'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || table_name) is not null then
      trigger_name := table_name || '_set_profile_id';
      execute format('drop trigger if exists %I on public.%I', trigger_name, table_name);
      execute format(
        'create trigger %I before insert or update of username, profile_id
           on public.%I for each row
           execute function public.set_profile_id_from_username()',
        trigger_name,
        table_name
      );
    end if;
  end loop;
end
$triggers$;

commit;

-- Index creation is intentionally idempotent. With no live student traffic,
-- ordinary CREATE INDEX is safer to run from migration tools/SQL editors that
-- wrap scripts in a transaction than CREATE INDEX CONCURRENTLY.
create index if not exists ai_usage_events_profile_id_idx
  on public.ai_usage_events (profile_id) where profile_id is not null;
create index if not exists ai_usage_logs_profile_id_idx
  on public.ai_usage_logs (profile_id) where profile_id is not null;
create index if not exists board_paper_attempts_profile_id_idx
  on public.board_paper_attempts (profile_id) where profile_id is not null;
create index if not exists doubt_history_profile_id_idx
  on public.doubt_history (profile_id) where profile_id is not null;
create index if not exists mentor_memory_profile_id_idx
  on public.mentor_memory (profile_id) where profile_id is not null;
create index if not exists mock_test_wrong_answers_profile_id_idx
  on public.mock_test_wrong_answers (profile_id) where profile_id is not null;
create index if not exists student_profiles_profile_id_idx
  on public.student_profiles (profile_id) where profile_id is not null;
create index if not exists student_progress_profile_id_idx
  on public.student_progress (profile_id) where profile_id is not null;
create index if not exists test_history_profile_id_idx
  on public.test_history (profile_id) where profile_id is not null;
create index if not exists unanswered_questions_profile_id_idx
  on public.unanswered_questions (profile_id) where profile_id is not null;
create index if not exists user_feedback_profile_id_idx
  on public.user_feedback (profile_id) where profile_id is not null;
create index if not exists weak_area_alerts_profile_id_idx
  on public.weak_area_alerts (profile_id) where profile_id is not null;

-- Production contained one duplicate ownership key: rows 723 ("likha") and
-- 865 ("Likha"). Their progress/cache payloads were identical and row 865 was
-- newer. This guarded, idempotent remediation records that decision without
-- deleting anything if the rows ever differ from the reviewed state.
do $deduplicate_known_progress$
declare
  reviewed_rows integer;
  payload_versions integer;
begin
  if exists (select 1 from public.student_progress where id = 723) then
    select count(*),
           count(distinct (
             to_jsonb(progress)
             - 'id'
             - 'created_at'
             - 'updated_at'
             - 'username'
           ))
      into reviewed_rows, payload_versions
      from public.student_progress progress
     where id in (723, 865)
       and profile_id = 'b4483af0-a429-4b49-96cd-bb0b4b2d3a74'
       and lower(trim(username)) = 'likha';

    if reviewed_rows <> 2 or payload_versions <> 1 then
      raise exception
        'Known progress rows 723/865 no longer match the reviewed duplicate; nothing deleted';
    end if;

    delete from public.student_progress
     where id = 723
       and profile_id = 'b4483af0-a429-4b49-96cd-bb0b4b2d3a74'
       and username = 'likha';
  end if;
end
$deduplicate_known_progress$;

-- Required before progress upserts can move from username to profile_id.
create unique index if not exists student_progress_owner_chapter_unique
  on public.student_progress (profile_id, grade, mode, subject, chapter);

-- Deployment verification: both protected accounts must retain their IDs and
-- every matching historical row should carry the same profile_id.
select id, email, username, role, is_test_account
  from public.profiles
 where lower(email) in ('admin@tutor.com', 'akshita.teststudent@mail.com')
 order by email;

-- Warnings here identify orphaned historical/system usernames that no longer
-- have a profile. They intentionally remain NULL and are excluded from
-- profile-owned reads; never attach them to a merely similar username.
do $audit$
declare
  table_name text;
  missing_count bigint;
begin
  foreach table_name in array array[
    'ai_usage_events', 'ai_usage_logs', 'board_paper_attempts',
    'doubt_history', 'mentor_memory', 'mock_test_wrong_answers',
    'student_profiles', 'student_progress', 'test_history',
    'unanswered_questions', 'user_feedback', 'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || table_name) is not null then
      execute format(
        'select count(*) from public.%I where username is not null and profile_id is null',
        table_name
      ) into missing_count;
      if missing_count > 0 then
        raise warning '% has % username-owned rows without profile_id', table_name, missing_count;
      end if;
    end if;
  end loop;
end
$audit$;
