alter table public.profiles
add column if not exists grade text not null default 'Grade 9';

update public.profiles
set grade = 'Grade 9'
where role = 'student'
  and (grade is null or trim(grade) = '');
