-- DigiX DocAI production-ready starting schema for Supabase/PostgreSQL.
create extension if not exists pgcrypto;

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  original_filename text not null,
  document_type text,
  storage_path text,
  mime_type text not null,
  file_size bigint not null check (file_size >= 0),
  processing_status text not null default 'pending',
  created_at timestamptz not null default now()
);

create table if not exists document_results (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  summary text,
  extracted_json jsonb not null default '{}'::jsonb,
  confidence numeric(5,4),
  model_used text,
  processing_cost numeric(12,6) not null default 0,
  created_at timestamptz not null default now()
);

alter table documents enable row level security;
alter table document_results enable row level security;

create policy "users_read_own_documents"
on documents for select using (auth.uid() = user_id);

create policy "users_insert_own_documents"
on documents for insert with check (auth.uid() = user_id);

create policy "users_delete_own_documents"
on documents for delete using (auth.uid() = user_id);

create policy "users_read_own_results"
on document_results for select
using (exists (
  select 1 from documents d
  where d.id = document_results.document_id and d.user_id = auth.uid()
));
