-- M11 Phase 2B: School OS account-link ownership-proof artifacts.
--
-- This is backend security infrastructure. It stores SHA-256 verifiers only:
-- never raw School OS state, raw completion code, user PII, or credentials.
-- Phase 2C must invoke the proof endpoint only after explicit LP user consent.

begin;

create table if not exists public.school_os_account_link_completion_artifacts (
  id                  uuid        primary key default gen_random_uuid(),
  lp_user_id          uuid        not null references public.profiles(id) on delete restrict,
  state_verifier      text        not null
                                  check (state_verifier ~ '^[0-9a-f]{64}$'),
  completion_verifier text        not null
                                  check (completion_verifier ~ '^[0-9a-f]{64}$'),
  status              text        not null default 'ISSUED'
                                  check (status in ('ISSUED', 'CONSUMED')),
  created_at          timestamptz not null default now(),
  expires_at          timestamptz not null,
  consumed_at         timestamptz,
  constraint school_os_account_link_completion_artifacts_state_verifier_key
    unique (state_verifier),
  constraint school_os_account_link_completion_artifacts_completion_verifier_key
    unique (completion_verifier),
  constraint school_os_account_link_completion_artifacts_ttl_check
    check (expires_at > created_at and expires_at <= created_at + interval '60 seconds'),
  constraint school_os_account_link_completion_artifacts_consumption_check
    check (
      (status = 'ISSUED' and consumed_at is null)
      or (status = 'CONSUMED' and consumed_at is not null)
    )
);

comment on table public.school_os_account_link_completion_artifacts is
  'M11 Phase 2B digest-only, single-use School OS account-link completion artifacts.';

create index if not exists school_os_account_link_completion_artifacts_expiry_idx
  on public.school_os_account_link_completion_artifacts (expires_at);

alter table public.school_os_account_link_completion_artifacts enable row level security;
alter table public.school_os_account_link_completion_artifacts force row level security;

create policy "service_role_all_school_os_account_link_completion_artifacts"
  on public.school_os_account_link_completion_artifacts
  for all
  to service_role
  using (true)
  with check (true);

-- This one statement is the sole consumption mechanism. It cannot return a
-- subject twice, because its WHERE clause requires the row to still be ISSUED.
-- It has no auth/browser context and is callable only by the backend service
-- role; request authentication is performed by the Python endpoint first.
create or replace function public.consume_school_os_account_link_completion_artifact(
  p_completion_verifier text,
  p_state_verifier text
)
returns table (lp_user_id uuid)
language sql
security definer
set search_path = ''
as $function$
  update public.school_os_account_link_completion_artifacts
     set status = 'CONSUMED',
         consumed_at = now()
   where completion_verifier = p_completion_verifier
     and state_verifier = p_state_verifier
     and status = 'ISSUED'
     and expires_at > now()
 returning school_os_account_link_completion_artifacts.lp_user_id;
$function$;

revoke all on table public.school_os_account_link_completion_artifacts
  from public, anon, authenticated;

revoke all on function public.consume_school_os_account_link_completion_artifact(text, text)
  from public, anon, authenticated;
grant execute on function public.consume_school_os_account_link_completion_artifact(text, text)
  to service_role;

commit;

notify pgrst, 'reload schema';
