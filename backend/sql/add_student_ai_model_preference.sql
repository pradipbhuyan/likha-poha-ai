alter table public.profiles
add column if not exists ai_model_preference text not null default 'default';

update public.profiles
set ai_model_preference = 'default'
where ai_model_preference is null
  or trim(ai_model_preference) = '';

alter table public.profiles
drop constraint if exists profiles_ai_model_preference_check;

alter table public.profiles
add constraint profiles_ai_model_preference_check
check (ai_model_preference in ('default', 'gpt-5', 'gpt-5-mini'));
