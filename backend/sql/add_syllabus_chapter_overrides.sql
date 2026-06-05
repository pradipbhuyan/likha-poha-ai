create table if not exists public.syllabus_chapter_overrides (
  id uuid primary key default gen_random_uuid(),
  grade text not null,
  mode text not null,
  subject text not null,
  chapters jsonb not null default '[]'::jsonb,
  updated_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (grade, mode, subject)
);

alter table public.syllabus_chapter_overrides enable row level security;

drop policy if exists "syllabus overrides are readable" on public.syllabus_chapter_overrides;

create policy "syllabus overrides are readable"
on public.syllabus_chapter_overrides
for select
using (true);

create or replace function public.set_syllabus_chapter_overrides_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_syllabus_chapter_overrides_updated_at
  on public.syllabus_chapter_overrides;

create trigger set_syllabus_chapter_overrides_updated_at
before update on public.syllabus_chapter_overrides
for each row
execute function public.set_syllabus_chapter_overrides_updated_at();

create table if not exists public.syllabus_subject_overrides (
  id uuid primary key default gen_random_uuid(),
  grade text not null,
  mode text not null,
  subjects jsonb not null default '[]'::jsonb,
  updated_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (grade, mode)
);

alter table public.syllabus_subject_overrides enable row level security;

drop policy if exists "syllabus subject overrides are readable" on public.syllabus_subject_overrides;

create policy "syllabus subject overrides are readable"
on public.syllabus_subject_overrides
for select
using (true);

create or replace function public.set_syllabus_subject_overrides_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_syllabus_subject_overrides_updated_at
  on public.syllabus_subject_overrides;

create trigger set_syllabus_subject_overrides_updated_at
before update on public.syllabus_subject_overrides
for each row
execute function public.set_syllabus_subject_overrides_updated_at();
