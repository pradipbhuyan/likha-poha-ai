create table if not exists public.rag_upload_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  status text not null default 'queued',
  phase text not null default 'queued',
  filename text not null default '',
  file_size bigint not null default 0,
  page_count integer not null default 0,
  processed_pages integer not null default 0,
  total_chapters integer not null default 0,
  processed_chapters integer not null default 0,
  total_chunks integer not null default 0,
  processed_chunks integer not null default 0,
  percent integer not null default 0,
  message text not null default '',
  error_message text not null default '',
  result jsonb not null default '{}'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.rag_upload_jobs enable row level security;

drop policy if exists "rag upload jobs are readable" on public.rag_upload_jobs;

create policy "rag upload jobs are readable"
on public.rag_upload_jobs
for select
using (true);

create or replace function public.set_rag_upload_jobs_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_rag_upload_jobs_updated_at
  on public.rag_upload_jobs;

create trigger set_rag_upload_jobs_updated_at
before update on public.rag_upload_jobs
for each row
execute function public.set_rag_upload_jobs_updated_at();

create index if not exists rag_upload_jobs_created_at_idx
  on public.rag_upload_jobs (created_at desc);

create index if not exists rag_upload_jobs_status_idx
  on public.rag_upload_jobs (status, created_at desc);
