-- Non-secret delivery diagnostics for teacher-to-parent email.
-- Some environments have not yet applied 20260627_teacher_phase2.sql, so the
-- migration is self-contained and creates the message log when needed.
create table if not exists public.teacher_parent_messages (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references auth.users(id) on delete cascade,
  student_id uuid not null references auth.users(id) on delete cascade,
  parent_id uuid references auth.users(id) on delete set null,
  subject text not null default '',
  message text not null,
  status text not null default 'draft'
    check (status in ('sent', 'draft', 'failed', 'no_email')),
  created_at timestamptz not null default now()
);

alter table public.teacher_parent_messages
  add column if not exists provider text,
  add column if not exists error_code text,
  add column if not exists sent_at timestamptz;

create index if not exists idx_tpm_teacher_id
  on public.teacher_parent_messages (teacher_id);
create index if not exists idx_tpm_student_id
  on public.teacher_parent_messages (student_id);
create index if not exists idx_tpm_parent_id
  on public.teacher_parent_messages (parent_id);
create index if not exists idx_tpm_status
  on public.teacher_parent_messages (status);
create index if not exists idx_tpm_provider_status
  on public.teacher_parent_messages (provider, status, created_at desc);
