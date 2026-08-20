-- sql/sairncode_anesthesia_base_units_schema.sql
-- Real server-synced table for SAIRNcode's ASA Base Units Reference
-- (2026-08-20, pre-SAIRNcare gap pass). Run this once in the Supabase SQL
-- editor before api/sd-data.js's sc_anesthesia_base_units read/write/
-- delete branch will work.
--
-- WHY THIS TABLE STARTS EMPTY, DELIBERATELY, WITH NO SEEDED BASE-UNIT
-- VALUES: same discipline as sql/sairncode_scrubrules_schema.sql. The
-- existing Anesthesia Time Units Calculator's time-unit MATH is real and
-- correct (minutes/15 + base units, the standard ASA convention) -- what
-- it never had was a real Relative Value Guide base-unit reference behind
-- the "Base Units" number, which was pure free-text entry. This session
-- has no live, authoritative ASA RVG data source to verify specific
-- CPT-to-base-unit values against. Hardcoding even one plausible-sounding
-- but unverified base-unit value into a billing tool would be a real
-- fabrication risk -- a coder/admin adds values they've personally
-- verified, required Source field included so every entry is traceable.
--
-- Same shape as every other sc_* resource: one row per entry, license_
-- hash-scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('abu'+Date.now()).

create table if not exists public.sc_anesthesia_base_units (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_anesthesia_base_units_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_anesthesia_base_units_license on public.sc_anesthesia_base_units(license_hash);

alter table public.sc_anesthesia_base_units enable row level security;
drop policy if exists "svc only sc_anesthesia_base_units" on public.sc_anesthesia_base_units;
create policy "svc only sc_anesthesia_base_units" on public.sc_anesthesia_base_units for all using (false) with check (false);

grant select, insert, update, delete on public.sc_anesthesia_base_units to service_role;
revoke all on public.sc_anesthesia_base_units from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_anesthesia_base_units;
