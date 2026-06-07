create table if not exists public.sales_collaterals (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  audience text not null default 'parents',
  channel text not null default 'whatsapp',
  format text not null default 'image',
  description text not null default '',
  caption text not null default '',
  asset_url text not null default '',
  thumbnail_url text not null default '',
  status text not null default 'active',
  display_order integer not null default 999,
  uploaded_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.sales_collaterals enable row level security;

drop policy if exists "sales collaterals are readable"
  on public.sales_collaterals;

create policy "sales collaterals are readable"
on public.sales_collaterals
for select
using (true);

create or replace function public.set_sales_collaterals_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_sales_collaterals_updated_at
  on public.sales_collaterals;

create trigger set_sales_collaterals_updated_at
before update on public.sales_collaterals
for each row
execute function public.set_sales_collaterals_updated_at();

create index if not exists sales_collaterals_status_order_idx
  on public.sales_collaterals (status, display_order, created_at desc);

create index if not exists sales_collaterals_channel_idx
  on public.sales_collaterals (channel, audience);
