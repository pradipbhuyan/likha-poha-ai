-- Harden immutable profile ownership after 20260821_profile_id_ownership.sql.
--
-- Existing rows with profile_id IS NULL are retained as quarantined history.
-- The NOT VALID checks below still reject new orphaned rows. Run the audit
-- function before later validating those checks or making columns NOT NULL.

begin;

create or replace function public.can_access_student_profile(target_profile_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $function$
  select target_profile_id is not null and (
    auth.uid() = target_profile_id
    or exists (
      select 1 from public.profiles actor
       where actor.id = auth.uid() and actor.role = 'admin'
    )
    or exists (
      select 1
        from public.profiles child
        join public.profiles parent on parent.id = auth.uid()
       where child.id = target_profile_id
         and parent.role = 'parent'
         and (
           child.parent_id = parent.id
           or (child.family_id is not null and child.family_id = parent.family_id)
         )
    )
    or exists (
      select 1 from public.teacher_student_assignments assignment
       where assignment.teacher_id = auth.uid()
         and assignment.student_id = target_profile_id
         and coalesce(to_jsonb(assignment)->>'archived_at', '') = ''
    )
  );
$function$;

revoke all on function public.can_access_student_profile(uuid) from public;
grant execute on function public.can_access_student_profile(uuid) to authenticated, service_role;

create or replace function public.is_self_or_admin(target_profile_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $function$
  select target_profile_id is not null and (
    auth.uid() = target_profile_id
    or exists (
      select 1 from public.profiles actor
       where actor.id = auth.uid() and actor.role = 'admin'
    )
  );
$function$;

revoke all on function public.is_self_or_admin(uuid) from public;
grant execute on function public.is_self_or_admin(uuid) to authenticated, service_role;

do $hardening$
declare
  table_name text;
  constraint_name text;
  select_expression text;
begin
  foreach table_name in array array[
    'ai_usage_events', 'ai_usage_logs', 'board_paper_attempts',
    'doubt_history', 'mentor_memory', 'mock_test_wrong_answers',
    'student_profiles', 'student_progress', 'test_history',
    'unanswered_questions', 'user_feedback', 'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || table_name) is null then
      continue;
    end if;

    execute format('alter table public.%I enable row level security', table_name);

    if table_name = 'mock_test_wrong_answers' then
      execute 'drop policy if exists "students_own_wrong_answers" on public.mock_test_wrong_answers';
    end if;

    -- Raw AI metadata, free-form doubts/memory, unanswered questions, and
    -- feedback are private to the account/admin. Parent/teacher access is
    -- limited to structured learning records only.
    select_expression := case
      when table_name in (
        'board_paper_attempts', 'mock_test_wrong_answers', 'student_profiles',
        'student_progress', 'test_history', 'weak_area_alerts'
      ) then 'public.can_access_student_profile(profile_id)'
      else 'public.is_self_or_admin(profile_id)'
    end;

    execute format('drop policy if exists profile_owner_select on public.%I', table_name);
    execute format(
      'create policy profile_owner_select on public.%I for select to authenticated
       using (%s)',
      table_name, select_expression
    );

    execute format('drop policy if exists profile_owner_insert on public.%I', table_name);
    execute format(
      'create policy profile_owner_insert on public.%I for insert to authenticated
       with check (profile_id = auth.uid())',
      table_name
    );

    execute format('drop policy if exists profile_owner_update on public.%I', table_name);
    execute format(
      'create policy profile_owner_update on public.%I for update to authenticated
       using (profile_id = auth.uid()) with check (profile_id = auth.uid())',
      table_name
    );

    execute format('drop policy if exists profile_owner_delete on public.%I', table_name);
    execute format(
      'create policy profile_owner_delete on public.%I for delete to authenticated
       using (profile_id = auth.uid())',
      table_name
    );

    constraint_name := table_name || '_profile_id_fkey';
    if exists (
      select 1 from pg_constraint
       where conname = constraint_name
         and conrelid = ('public.' || table_name)::regclass
         and not convalidated
    ) then
      execute format(
        'alter table public.%I validate constraint %I',
        table_name, constraint_name
      );
    end if;
  end loop;

  -- These tables represent account-owned application state. The trigger from
  -- the previous migration fills profile_id for legacy username-only writers;
  -- if no profile exists, a new orphan is rejected.
  foreach table_name in array array[
    'board_paper_attempts', 'doubt_history', 'mentor_memory',
    'mock_test_wrong_answers', 'student_profiles', 'student_progress',
    'test_history', 'unanswered_questions', 'user_feedback',
    'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || table_name) is null then
      continue;
    end if;
    constraint_name := table_name || '_new_rows_require_profile_id';
    if not exists (
      select 1 from pg_constraint
       where conname = constraint_name
         and conrelid = ('public.' || table_name)::regclass
    ) then
      execute format(
        'alter table public.%I add constraint %I
         check (profile_id is not null) not valid',
        table_name, constraint_name
      );
    end if;
  end loop;
end
$hardening$;

-- Service-role-only operational audit. NULL-owned rows are intentionally not
-- exposed by the RLS policies above and must never be guessed onto an account.
create or replace function public.profile_id_orphan_counts()
returns table(table_name text, orphan_rows bigint)
language plpgsql
security definer
set search_path = public
as $function$
declare
  candidate text;
  row_count bigint;
begin
  foreach candidate in array array[
    'ai_usage_events', 'ai_usage_logs', 'board_paper_attempts',
    'doubt_history', 'mentor_memory', 'mock_test_wrong_answers',
    'student_profiles', 'student_progress', 'test_history',
    'unanswered_questions', 'user_feedback', 'weak_area_alerts'
  ]
  loop
    if to_regclass('public.' || candidate) is not null then
      execute format('select count(*) from public.%I where profile_id is null', candidate)
        into row_count;
      table_name := candidate;
      orphan_rows := row_count;
      return next;
    end if;
  end loop;
end
$function$;

revoke all on function public.profile_id_orphan_counts() from public, anon, authenticated;
grant execute on function public.profile_id_orphan_counts() to service_role;

commit;

-- Run with the service role after deployment:
-- select * from public.profile_id_orphan_counts() order by orphan_rows desc;
