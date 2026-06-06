alter table public.profiles
drop constraint if exists profiles_role_check;

alter table public.profiles
add constraint profiles_role_check
check (role in ('admin', 'parent', 'student', 'teacher', 'sales'));

create table if not exists public.sales_profiles (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  salesperson_type text not null default 'independent',
  region text not null default '',
  phone text not null default '',
  status text not null default 'active',
  default_incentive_percent numeric(5,2) not null default 5,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sales_student_attributions (
  id uuid primary key default gen_random_uuid(),
  sales_profile_id uuid not null references public.profiles(id) on delete cascade,
  student_id uuid not null references public.profiles(id) on delete cascade,
  package_key text not null default 'free',
  package_label text not null default 'Free Trial',
  package_amount integer not null default 0,
  incentive_percent numeric(5,2) not null default 5,
  status text not null default 'pending',
  notes text not null default '',
  onboarded_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (student_id)
);

alter table public.sales_profiles enable row level security;
alter table public.sales_student_attributions enable row level security;

create or replace function public.set_sales_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_sales_profiles_updated_at
  on public.sales_profiles;

create trigger set_sales_profiles_updated_at
before update on public.sales_profiles
for each row
execute function public.set_sales_profiles_updated_at();

create or replace function public.set_sales_student_attributions_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_sales_student_attributions_updated_at
  on public.sales_student_attributions;

create trigger set_sales_student_attributions_updated_at
before update on public.sales_student_attributions
for each row
execute function public.set_sales_student_attributions_updated_at();
