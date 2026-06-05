alter table public.profiles
add column if not exists cbse_subjects jsonb not null default '[]'::jsonb;

update public.profiles
set cbse_subjects = '[]'::jsonb
where cbse_subjects is null;
