create table if not exists public.doubt_history (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  username text not null,
  grade text not null default 'Grade 9',
  mode text not null default 'CBSE',
  subject text not null default '',
  chapter text not null default '',
  question text not null,
  prompt_question text not null default '',
  answer text not null,
  source_type text not null default 'LLM',
  sources jsonb not null default '[]'::jsonb,
  mentor_suggestions jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.doubt_history enable row level security;

create index if not exists doubt_history_profile_created_idx
  on public.doubt_history (profile_id, created_at desc);

create index if not exists doubt_history_username_created_idx
  on public.doubt_history (username, created_at desc);
