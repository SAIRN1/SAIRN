-- sql/sairncode_dme_schema.sql
-- Real server-synced table for SAIRNcode's DME/DMEPOS records
-- (gap-closure pass 2 item 6, 2026-08-22). Run this once in the Supabase
-- SQL editor before api/sd-data.js's sc_dme read/write/delete branch works.
--
-- WHY THIS ONE GENUINELY NEEDS STORAGE, decided by verification rather than
-- carried over from an earlier item: two of the item's gates cannot function
-- without history.
--
--   1. SAME-OR-SIMILAR EQUIPMENT. Delivering equipment the beneficiary
--      already has is a named duplicate-payment denial trigger, and the only
--      way to check it is against a record of what this supplier previously
--      delivered. A stateless calculator cannot answer "does this patient
--      already have one" -- and the gate deliberately fails closed on an
--      unchecked history, so it needs somewhere real to look.
--
--   2. PRIOR AUTHORIZATION EXEMPTION STATUS. Under CMS-1828-F a supplier
--      that hit a 90% provisional affirmation rate on at least ten initial
--      PA requests between 1 June and 30 November 2025 is exempt for one
--      annual cycle, the first running 1 June 2026 to 31 May 2027. That is
--      per-supplier, per-cycle state with a real expiry -- not something a
--      coder should be re-deriving from memory on every claim.
--
-- WHAT IS DELIBERATELY *NOT* STORED HERE: the Required Prior Authorization
-- List itself. It holds 74 HCPCS codes and only the seven added 13 April
-- 2026 were confirmed against a primary source during this build, so the app
-- carries those seven as a disclosed partial reference and returns an honest
-- "not in this app's verified list -- that is not a clearance" for anything
-- else. Shipping a hand-assembled 74 nobody verified would be the same
-- fabrication class the 2026-08-18 audit removed from every other panel.
--
-- Same shape as every other sc_* resource: one row per entry, license_hash-
-- scoped, a jsonb data column. entry_id is the client's own locally-generated
-- id ('dm'+Date.now()).

create table if not exists public.sc_dme (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_dme_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_dme_license on public.sc_dme(license_hash);

alter table public.sc_dme enable row level security;
drop policy if exists "svc only sc_dme" on public.sc_dme;
create policy "svc only sc_dme" on public.sc_dme for all using (false) with check (false);

grant select, insert, update, delete on public.sc_dme to service_role;
revoke all on public.sc_dme from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_dme;
