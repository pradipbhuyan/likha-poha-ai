create table if not exists public.performance_test_runs (
  id uuid primary key default gen_random_uuid(),
  test_type text not null,
  status text not null default 'queued',
  concurrency integer not null default 1,
  duration_seconds integer not null default 30,
  started_by uuid references public.profiles(id) on delete set null,
  started_at timestamptz,
  finished_at timestamptz,
  summary jsonb not null default '{}'::jsonb,
  results jsonb not null default '[]'::jsonb,
  classification text not null default 'Queued',
  error_message text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.performance_test_runs enable row level security;

create or replace function public.set_performance_test_runs_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_performance_test_runs_updated_at
  on public.performance_test_runs;

create trigger set_performance_test_runs_updated_at
before update on public.performance_test_runs
for each row
execute function public.set_performance_test_runs_updated_at();

create index if not exists performance_test_runs_created_at_idx
  on public.performance_test_runs (created_at desc);

create index if not exists performance_test_runs_status_created_idx
  on public.performance_test_runs (status, created_at desc);

create index if not exists performance_test_runs_classification_created_idx
  on public.performance_test_runs (classification, created_at desc);
