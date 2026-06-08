create table if not exists public.onboarding_guide_settings (
  key text primary key default 'default',
  enabled boolean not null default true,
  active_theme text not null default 'quest',
  rotation_enabled boolean not null default false,
  rotation_days integer not null default 14,
  student_theme text not null default 'quest',
  parent_theme text not null default 'clean',
  teacher_theme text not null default 'forest',
  show_once_per_theme boolean not null default true,
  auto_open boolean not null default true,
  message text not null default 'A friendly first-time guide helps new users understand the main pages without feeling lost.',
  updated_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.onboarding_guide_settings enable row level security;

drop policy if exists "onboarding guide settings are readable"
  on public.onboarding_guide_settings;

create policy "onboarding guide settings are readable"
on public.onboarding_guide_settings
for select
using (true);

create or replace function public.set_onboarding_guide_settings_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_onboarding_guide_settings_updated_at
  on public.onboarding_guide_settings;

create trigger set_onboarding_guide_settings_updated_at
before update on public.onboarding_guide_settings
for each row
execute function public.set_onboarding_guide_settings_updated_at();

insert into public.onboarding_guide_settings (
  key,
  enabled,
  active_theme,
  rotation_enabled,
  rotation_days,
  student_theme,
  parent_theme,
  teacher_theme,
  show_once_per_theme,
  auto_open,
  message
) values (
  'default',
  true,
  'quest',
  false,
  14,
  'quest',
  'clean',
  'forest',
  true,
  true,
  'A friendly first-time guide helps new users understand the main pages without feeling lost.'
)
on conflict (key) do nothing;
