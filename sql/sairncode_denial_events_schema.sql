-- sql/sairncode_denial_events_schema.sql
-- Real server-synced table for SAIRNcode's Denial Pattern Log (denial
-- pattern tracking, part of the 2026-08-20 post-audit expansion, item 3).
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_denial_events read/write/delete branch will work.
--
-- WHY THIS TABLE EXISTS SEPARATELY FROM sc_denial:
-- sc_denial (sql/sairncode_data_schema.sql) is an aggregate table -- one
-- row per denial CODE with a manually-entered count, and no payer field.
-- It cannot answer "which payer denies which codes most" or any other
-- real pattern question, because it was never designed to record
-- individual occurrences. This table is the real fix: one row per actual
-- denial EVENT (code, payer, reason, amount, date), which SAIRNcode's
-- Denial Pattern Log panel writes to directly and its pattern-breakdown
-- view (top payers, top reasons) computes live from, never a placeholder
-- or invented trend.
--
-- Same shape as every other sc_* resource: one row per entry, license_
-- hash-scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('dne'+Date.now()).

create table if not exists public.sc_denial_events (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_denial_events_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_denial_events_license on public.sc_denial_events(license_hash);

alter table public.sc_denial_events enable row level security;
drop policy if exists "svc only sc_denial_events" on public.sc_denial_events;
create policy "svc only sc_denial_events" on public.sc_denial_events for all using (false) with check (false);

grant select, insert, update, delete on public.sc_denial_events to service_role;
revoke all on public.sc_denial_events from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_denial_events;
