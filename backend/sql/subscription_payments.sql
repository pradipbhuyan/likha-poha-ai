create table if not exists public.subscription_payments (
  id uuid primary key default gen_random_uuid(),
  razorpay_order_id text not null unique,
  razorpay_payment_id text,
  parent_id uuid not null,
  child_id uuid not null,
  family_id uuid,
  plan_key text not null,
  amount integer not null default 0,
  amount_paise integer not null default 0,
  currency text not null default 'INR',
  status text not null default 'created',
  provider text not null default 'razorpay',
  metadata jsonb not null default '{}'::jsonb,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.subscription_payments enable row level security;

create index if not exists subscription_payments_parent_id_idx
  on public.subscription_payments(parent_id);

create index if not exists subscription_payments_child_id_idx
  on public.subscription_payments(child_id);

create or replace function public.set_subscription_payments_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_subscription_payments_updated_at
  on public.subscription_payments;

create trigger set_subscription_payments_updated_at
before update on public.subscription_payments
for each row
execute function public.set_subscription_payments_updated_at();
