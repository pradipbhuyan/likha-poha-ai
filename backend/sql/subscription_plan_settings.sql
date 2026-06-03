create table if not exists public.subscription_plan_settings (
  key text primary key,
  label text not null,
  short_label text not null,
  price integer not null default 0,
  billing_label text not null default 'month',
  audience text not null default '',
  badge text not null default '',
  recommended boolean not null default false,
  discount_percent integer not null default 0,
  discount_label text not null default '',
  is_public boolean not null default true,
  display_order integer not null default 999,
  access_cbse boolean not null default true,
  access_sof_science boolean not null default false,
  access_sof_maths boolean not null default false,
  access_sof_english boolean not null default false,
  daily_token_limit integer not null default 0,
  monthly_token_limit integer not null default 0,
  included jsonb not null default '[]'::jsonb,
  not_included jsonb not null default '[]'::jsonb,
  comparison jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.subscription_plan_settings enable row level security;

create or replace function public.set_subscription_plan_settings_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_subscription_plan_settings_updated_at
  on public.subscription_plan_settings;

create trigger set_subscription_plan_settings_updated_at
before update on public.subscription_plan_settings
for each row
execute function public.set_subscription_plan_settings_updated_at();

insert into public.subscription_plan_settings (
  key,
  label,
  short_label,
  price,
  billing_label,
  audience,
  badge,
  recommended,
  discount_percent,
  discount_label,
  is_public,
  display_order,
  access_cbse,
  access_sof_science,
  access_sof_maths,
  access_sof_english,
  daily_token_limit,
  monthly_token_limit,
  included,
  not_included,
  comparison
) values
(
  'free',
  'Free Trial',
  'Free',
  0,
  '14 days',
  'Best for exploring lessons, doubts, and basic progress before choosing a paid plan.',
  'Current starter',
  false,
  0,
  '',
  true,
  1,
  true,
  false,
  false,
  false,
  50000,
  1000000,
  '["1 child profile", "Limited AI lessons and doubt solving", "Basic CBSE practice and progress view"]'::jsonb,
  '["SOF mock tests", "Advanced analytics"]'::jsonb,
  '{"children": "1", "aiUsage": "Limited", "cbse": "Limited", "sof": "Locked", "ragSof": "Locked", "parentDashboard": "Basic"}'::jsonb
),
(
  'starter',
  'Standard',
  'Standard',
  499,
  'month',
  'Best for regular CBSE learning with higher AI limits and parent tracking.',
  '',
  false,
  0,
  '',
  true,
  2,
  true,
  false,
  false,
  false,
  75000,
  1500000,
  '["Everything in Free Trial", "Higher AI lessons, doubts, and explanations", "CBSE mock tests and chapter revision", "Full parent dashboard"]'::jsonb,
  '["SOF RAG mock tests"]'::jsonb,
  '{"children": "1", "aiUsage": "Higher limit", "cbse": "Included", "sof": "Locked", "ragSof": "Locked", "parentDashboard": "Full"}'::jsonb
),
(
  'premium',
  'Premium SOF',
  'Premium',
  999,
  'month',
  'Best for CBSE plus Science, Maths, and English Olympiad preparation.',
  'Recommended',
  true,
  0,
  '',
  true,
  3,
  true,
  true,
  true,
  true,
  100000,
  3000000,
  '["Everything in Standard", "SOF Science, Maths, and English access", "RAG-based SOF mock tests from uploaded workbook content", "Highest AI usage limit", "Advanced analytics and weak-area recommendations"]'::jsonb,
  '[]'::jsonb,
  '{"children": "1", "aiUsage": "Highest limit", "cbse": "Included", "sof": "Included", "ragSof": "Included", "parentDashboard": "Full + analytics"}'::jsonb
),
(
  'family_premium',
  'Family Premium',
  'Family Premium',
  1499,
  'month',
  'Best discounted plan for two children who both need every CBSE and SOF feature.',
  'Best value',
  false,
  0,
  '',
  true,
  4,
  true,
  true,
  true,
  true,
  150000,
  5000000,
  '["Everything in Premium SOF for two children", "Discounted two-child family pricing", "SOF Science, Maths, and English for both children", "Expanded monthly AI usage", "Family progress and usage view"]'::jsonb,
  '[]'::jsonb,
  '{"children": "2", "aiUsage": "Family limit", "cbse": "Included", "sof": "Included", "ragSof": "Included", "parentDashboard": "Full + analytics"}'::jsonb
)
on conflict (key) do nothing;
