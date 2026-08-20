-- sql/sairncode_eligibility_schema.sql
-- Real server-synced table for SAIRNcode's Eligibility Verification panel
-- (real-time 270/271 coverage checks, 2026-08-20 BYO-credential expansion).
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_eligibility read/write/delete branch will work.
--
-- WHAT THIS TABLE IS: a HISTORY LOG of eligibility checks the practice has
-- actually run -- not the live call itself (that goes out through
-- api/sc-eligibility.js to the practice's own clearinghouse account and is
-- never cached as authoritative). Each row records what was asked and the
-- summarized real answer that came back, so a coder can see prior checks
-- without re-running (and re-paying for) them.
--
-- DELIBERATELY NOT STORED: the full raw 271 response. It can contain far
-- more PHI than the check itself needs to be useful afterward, and this
-- table inherits the same 64KB ceiling every other sc_* resource has. Only
-- the summarized fields the panel actually renders are persisted.
--
-- Same shape as every other sc_* resource: one row per entry, license_hash-
-- scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('el'+Date.now()).

create table if not exists public.sc_eligibility (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_eligibility_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_eligibility_license on public.sc_eligibility(license_hash);

alter table public.sc_eligibility enable row level security;
drop policy if exists "svc only sc_eligibility" on public.sc_eligibility;
create policy "svc only sc_eligibility" on public.sc_eligibility for all using (false) with check (false);

grant select, insert, update, delete on public.sc_eligibility to service_role;
revoke all on public.sc_eligibility from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_eligibility;
