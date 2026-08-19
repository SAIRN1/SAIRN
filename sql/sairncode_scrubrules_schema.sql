-- sql/sairncode_scrubrules_schema.sql
-- Real server-synced table for SAIRNcode's Scrub Rules Reference (rule-
-- based claim scrubbing, part of the 2026-08-19 post-audit expansion).
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_scrubrules read/write/delete branch will work.
--
-- WHY THIS TABLE STARTS EMPTY, DELIBERATELY, WITH NO SEEDED RULES:
-- Michael asked for deterministic NCCI/CCI PTP edit checks, Excludes1/
-- Excludes2 diagnosis-pairing checks, and modifier rules. This session has
-- no live, authoritative CMS NCCI/AMA data source to verify specific code-
-- pair rules against right now -- exactly the same "no live CPT/ICD-10/
-- HCPCS database" limitation SAIRNcode's own AI system prompt already
-- discloses, and the same root cause as the real AAPC-exam 65% score this
-- whole audit pass started from. Hardcoding even one plausible-sounding
-- but unverified rule into a medical-billing compliance tool would be a
-- real, dangerous fabrication -- exactly the class of bug this session's
-- fabrication sweep spent most of its time removing from every other
-- panel in this file. So: a real, honest, EMPTY starter table a coder or
-- compliance admin populates with rules THEY have verified against a real
-- current source (the UI's Add Rule form has a required "source" field for
-- exactly this reason), same "honest empty state, never seed fake data"
-- discipline every sc_* table in this file already follows.
--
-- Same shape as every other sc_* resource: one row per entry, license_
-- hash-scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('sr'+Date.now()).

create table if not exists public.sc_scrubrules (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_scrubrules_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_scrubrules_license on public.sc_scrubrules(license_hash);

alter table public.sc_scrubrules enable row level security;
drop policy if exists "svc only sc_scrubrules" on public.sc_scrubrules;
create policy "svc only sc_scrubrules" on public.sc_scrubrules for all using (false) with check (false);

grant select, insert, update, delete on public.sc_scrubrules to service_role;
revoke all on public.sc_scrubrules from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_scrubrules;
