-- School outreach campaign — Supabase-backed send-state tracking, replacing
-- the local SQLite file (scripts/school_outreach/campaign_state.db) so the
-- admin console can read/filter/select principals and trigger sends.
--
-- Purely additive — a new table, no existing schema touched.

create table if not exists public.school_outreach_principals (
  id                uuid          primary key default gen_random_uuid(),
  email             text          not null unique,
  principal_name    text          not null default '',
  school_name       text          not null default '',
  district          text          not null default '',
  state             text          not null default '',
  aff_no            text          not null default '',
  status            text          not null default 'pending'
                    check (status in ('pending', 'sent', 'failed')),
  resend_id         text          not null default '',
  error             text          not null default '',
  attempts          integer       not null default 0,
  sent_at           timestamptz,
  reminder_sent_at  timestamptz,
  responded         boolean       not null default false,
  responded_at      timestamptz,
  created_at        timestamptz   not null default now(),
  updated_at        timestamptz   not null default now()
);

create index if not exists idx_outreach_principals_status
  on public.school_outreach_principals (status);

create index if not exists idx_outreach_principals_sent_at
  on public.school_outreach_principals (sent_at);

alter table public.school_outreach_principals enable row level security;

create policy "service_role_all_outreach_principals"
  on public.school_outreach_principals for all
  to service_role using (true) with check (true);

create or replace function public.set_outreach_principals_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_outreach_principals_updated_at
  on public.school_outreach_principals;

create trigger set_outreach_principals_updated_at
before update on public.school_outreach_principals
for each row
execute function public.set_outreach_principals_updated_at();

NOTIFY pgrst, 'reload schema';
