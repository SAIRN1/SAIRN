-- sql/sairncode_claims_schema.sql
-- Real server-synced table for SAIRNcode's Claims Management panel.
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_claims read/write/delete branch will work.
--
-- WHY THIS EXISTS: a full audit (2026-08-19) ahead of Michael's real
-- medical-coder review found Claims Management was the one SAIRNcode panel
-- still 100% static -- 8 hardcoded fake patient rows (CLM-2601..2608) and
-- hardcoded "Seed data"-labeled KPIs, with zero way to ever add a real
-- claim. Every sibling panel (Revenue, Denial, HCC, DRG, etc.) already got
-- real per-practice CRUD in the 2026-08-18 fabrication audit
-- (sql/sairncode_data_schema.sql) -- this is that same 16th resource,
-- added after the fact. Identical shape to all 15 tables in that file:
-- one row per entry, license_hash-scoped, a jsonb data column.
--
-- entry_id is the client's own locally-generated id ('cl'+Date.now()),
-- same convention as every other sc_* table.

create table if not exists public.sc_claims (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_claims_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_claims_license on public.sc_claims(license_hash);

alter table public.sc_claims enable row level security;
drop policy if exists "svc only sc_claims" on public.sc_claims;
create policy "svc only sc_claims" on public.sc_claims for all using (false) with check (false);

grant select, insert, update, delete on public.sc_claims to service_role;
revoke all on public.sc_claims from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_claims;
