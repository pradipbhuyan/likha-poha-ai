-- Principal portal: schools table + profiles.school_id + reward redemptions.
-- Run in Supabase Dashboard → SQL Editor.
--
-- Purely additive — no existing column is renamed or dropped, no existing
-- row's behavior changes. profiles.school_id defaults to NULL for every
-- existing teacher/student/parent/admin row, so nothing already in
-- production is affected until a principal explicitly links an account.
--
-- SCHEMA-DRIFT NOTE: the only two migrations that touch profiles_role_check
-- in this repo (add_teacher_dashboard.sql, add_sales_incentive.sql) list
-- ('admin','parent','student','teacher') and (...,'sales') respectively —
-- but app/services/auth_service.py's require_student() also accepts a
-- role='child' profile (admin-created children), which isn't in either
-- tracked list. That means the live constraint has likely drifted from what's
-- committed here. Before running this file, check your actual Supabase
-- constraint (\d+ profiles in psql, or the table editor's constraints tab)
-- and adjust the `check (role in (...))` list below if it differs — this
-- file's list is a best-effort reconstruction (existing roles + 'child' +
-- the new 'principal'), not a confirmed copy of production.

alter table public.profiles
drop constraint if exists profiles_role_check;

alter table public.profiles
add constraint profiles_role_check
check (role in ('admin', 'parent', 'student', 'child', 'teacher', 'sales', 'principal'));

-- ── Schools ──────────────────────────────────────────────────────────────
create table if not exists public.schools (
  id                uuid          primary key default gen_random_uuid(),
  name              text          not null,
  udise_code        text,                       -- India's official school ID; optional
  address           text          not null default '',
  city              text          not null default '',
  state             text          not null default '',
  board             text          not null default 'CBSE',
  school_code       text          not null unique,   -- short join code, e.g. "SPS-7F3K2"
  principal_id      uuid          not null references public.profiles(id) on delete cascade,
  -- pending_verification until an admin confirms the school is real — same
  -- gate teacher-signup already uses, for the same reason: don't let anyone
  -- claim a school and start accumulating incentive-tier credit against it.
  status            text          not null default 'pending_verification'
                    check (status in ('pending_verification', 'active', 'rejected')),
  tier              text          not null default 'bronze'
                    check (tier in ('bronze', 'silver', 'gold', 'platinum')),
  created_at        timestamptz   not null default now(),
  updated_at        timestamptz   not null default now()
);

create unique index if not exists idx_schools_udise_code
  on public.schools (udise_code)
  where udise_code is not null;

create index if not exists idx_schools_principal
  on public.schools (principal_id);

-- ── profiles.school_id — additive, nullable, zero effect on existing rows ──
alter table public.profiles
  add column if not exists school_id uuid references public.schools(id) on delete set null;

create index if not exists idx_profiles_school_id
  on public.profiles (school_id)
  where school_id is not null;

-- ── Reward redemptions (principal-initiated, admin-fulfilled) ─────────────
create table if not exists public.school_reward_redemptions (
  id                  uuid          primary key default gen_random_uuid(),
  school_id           uuid          not null references public.schools(id) on delete cascade,
  principal_id        uuid          not null references public.profiles(id) on delete cascade,
  reward_key          text          not null,
  reward_label        text          not null default '',
  tier_at_redemption  text          not null default '',
  status              text          not null default 'requested'
                      check (status in ('requested', 'fulfilled', 'declined')),
  notes               text          not null default '',
  created_at          timestamptz   not null default now(),
  updated_at          timestamptz   not null default now()
);

create index if not exists idx_school_reward_redemptions_school
  on public.school_reward_redemptions (school_id, status);

-- ── RLS ────────────────────────────────────────────────────────────────────
-- Every principal/admin route in the backend queries through admin_client
-- (the service-role key, which bypasses RLS). These tables are never queried
-- directly from the frontend, so RLS here is a defense-in-depth backstop,
-- matching the pattern already used for sales_lead_claims.
alter table public.schools enable row level security;
alter table public.school_reward_redemptions enable row level security;

create policy "service_role_all_schools"
  on public.schools for all
  to service_role using (true) with check (true);

create policy "service_role_all_school_reward_redemptions"
  on public.school_reward_redemptions for all
  to service_role using (true) with check (true);

-- ── updated_at triggers ────────────────────────────────────────────────────
create or replace function public.set_schools_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_schools_updated_at on public.schools;

create trigger set_schools_updated_at
before update on public.schools
for each row
execute function public.set_schools_updated_at();

create or replace function public.set_school_reward_redemptions_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_school_reward_redemptions_updated_at on public.school_reward_redemptions;

create trigger set_school_reward_redemptions_updated_at
before update on public.school_reward_redemptions
for each row
execute function public.set_school_reward_redemptions_updated_at();

-- PostgREST caches the schema; Supabase usually reloads it automatically on
-- DDL, but if requests 404/PGRST204 on school_id or the new tables afterward:
NOTIFY pgrst, 'reload schema';
