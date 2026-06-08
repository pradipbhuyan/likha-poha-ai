create table if not exists public.rag_visual_assets (
  id uuid primary key default gen_random_uuid(),
  document_id bigint references public.rag_documents(id) on delete cascade,
  board text not null default 'CBSE',
  grade text not null default '',
  subject text not null default '',
  chapter text not null default '',
  title text not null default '',
  page_number integer not null,
  asset_url text not null,
  storage_path text not null,
  caption text not null default '',
  nearby_text text not null default '',
  status text not null default 'needs_review',
  uploaded_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.rag_visual_assets enable row level security;

drop policy if exists "rag visual assets are readable"
  on public.rag_visual_assets;

create policy "rag visual assets are readable"
on public.rag_visual_assets
for select
using (true);

create or replace function public.set_rag_visual_assets_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_rag_visual_assets_updated_at
  on public.rag_visual_assets;

create trigger set_rag_visual_assets_updated_at
before update on public.rag_visual_assets
for each row
execute function public.set_rag_visual_assets_updated_at();

create index if not exists rag_visual_assets_document_page_idx
  on public.rag_visual_assets (document_id, page_number);

create index if not exists rag_visual_assets_lookup_idx
  on public.rag_visual_assets (board, grade, subject, chapter, status);

