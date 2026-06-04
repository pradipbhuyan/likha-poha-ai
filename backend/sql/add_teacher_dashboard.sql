alter table public.profiles
drop constraint if exists profiles_role_check;

alter table public.profiles
add constraint profiles_role_check
check (role in ('admin', 'parent', 'student', 'teacher'));

create table if not exists public.teacher_profiles (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  teacher_type text not null default 'independent',
  school_name text not null default '',
  subjects jsonb not null default '[]'::jsonb,
  grades jsonb not null default '[]'::jsonb,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.teacher_student_assignments (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  student_id uuid not null references public.profiles(id) on delete cascade,
  grade text not null default 'Grade 9',
  subject text not null default '',
  section text not null default '',
  created_at timestamptz not null default now(),
  unique (teacher_id, student_id, subject)
);

create table if not exists public.teacher_notes (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  student_id uuid not null references public.profiles(id) on delete cascade,
  subject text not null default '',
  chapter text not null default '',
  note text not null,
  created_at timestamptz not null default now()
);

alter table public.teacher_profiles enable row level security;
alter table public.teacher_student_assignments enable row level security;
alter table public.teacher_notes enable row level security;

create or replace function public.set_teacher_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_teacher_profiles_updated_at
  on public.teacher_profiles;

create trigger set_teacher_profiles_updated_at
before update on public.teacher_profiles
for each row
execute function public.set_teacher_profiles_updated_at();
