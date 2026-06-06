create table if not exists public.subscription_contact_settings (
  key text primary key default 'default',
  email text not null default 'lilhapohaai@gmail.com',
  phone text not null default '',
  whatsapp text not null default '',
  availability text not null default 'We usually respond within one business day.',
  message text not null default 'Need help choosing a plan or activating access? Contact us and we will guide you.',
  updated_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.subscription_contact_settings enable row level security;

drop policy if exists "subscription contact settings are readable"
  on public.subscription_contact_settings;

create policy "subscription contact settings are readable"
on public.subscription_contact_settings
for select
using (true);

create or replace function public.set_subscription_contact_settings_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_subscription_contact_settings_updated_at
  on public.subscription_contact_settings;

create trigger set_subscription_contact_settings_updated_at
before update on public.subscription_contact_settings
for each row
execute function public.set_subscription_contact_settings_updated_at();

insert into public.subscription_contact_settings (
  key,
  email,
  phone,
  whatsapp,
  availability,
  message
) values (
  'default',
  'lilhapohaai@gmail.com',
  '',
  '',
  'We usually respond within one business day.',
  'Need help choosing a plan or activating access? Contact us and we will guide you.'
)
on conflict (key) do nothing;
