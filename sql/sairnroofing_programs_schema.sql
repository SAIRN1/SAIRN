-- sql/sairnroofing_programs_schema.sql
-- SAIRNroofing Phase 4d -- manufacturer certification programmes, COMPANY level.
--
--   rf_company_programs -- one row per programme the company tracks. MUTABLE:
--                          requirements get corrected, standing changes, a
--                          renewal date moves. Nothing here asserts a past
--                          fact, so unlike rf_claim_agreements and
--                          rf_certifications this is an upsert.
--
-- ── ONE TABLE, NOT TWO, AND THAT IS A DECISION ───────────────────────────
-- Phase 3a and Phase 5 both used a rules table plus a records table, and the
-- reflex here was to copy that: rf_program_rules + rf_company_credentials. It
-- is the wrong shape at this cardinality. A roofer tracks about THREE
-- programmes. The requirements and the company's standing in a programme are
-- read together, written together, and there is exactly one standing per
-- programme -- so splitting them would buy a join and cost a class of bug where
-- the two rows disagree about which programme they describe.
--
-- The 3a/5 split earned itself: many rules across many states, many records
-- across many employees, and genuinely different lifecycles. Recorded here so
-- the difference is a judgement someone made, not drift.
--
-- ── NOTHING IS SEEDED, DELIBERATELY ──────────────────────────────────────
-- There is no sql/sairnroofing_programs_seed_*.json in this repo and there
-- should not be one until somebody reads a real programme agreement. GAF's,
-- Owens Corning's and CertainTeed's actual terms sit behind contractor
-- portals; what is publicly reachable is contractor marketing pages. Michael's
-- decision 2026-08-25, matching the Phase 5 notice-text call: ship the
-- mechanism, let the contractor enter their own thresholds citing their own
-- agreement. api/_lib/roofing-programs.js refuses to evaluate a requirement
-- that names no source, so an unsourced threshold cannot become a verdict.
--
-- ── NOT A COMPLIANCE TABLE ───────────────────────────────────────────────
-- These are voluntary commercial programmes, not state mandates. The scope doc
-- is explicit that the app must not present them as regulatory, and the engine
-- attaches that disclosure to every result. This table is the opposite posture
-- from rf_cert_rules (state licensing, where the law decides) -- do not merge
-- them or reuse one for the other.
--
-- ── GRANTS: THE SOUND IDIOM ──────────────────────────────────────────────
-- REVOKE ALL from service_role FIRST, then grant. A bare GRANT is additive and
-- cannot remove what postgres's default ACL already conferred (TRUNCATE/
-- REFERENCES/TRIGGER). See sql/append_only_grant_audit.sql. Mutable table, so
-- UPDATE is granted; DELETE is NOT -- there is no delete path in the code, and
-- retiring a programme is status 'not_enrolled', not a row removal.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_company_programs (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnroofing',
  program_id    text not null,                      -- client-generated (RFPRG-<slug>)
  manufacturer  text not null,                      -- 'GAF', 'Owens Corning', ...
  program_name  text not null,                      -- 'Master Elite', ...
  status        text not null default 'not_enrolled',
  obtained_on   date,
  expires_on    date,
  -- Explicit, for the same reason rf_certifications.has_expiry is explicit: a
  -- programme with no renewal date is a different fact from one whose renewal
  -- date was never entered, and a null expires_on cannot tell them apart.
  has_expiry    boolean not null default true,
  -- requirements: [{ req_id, label, kind, source (REQUIRED by the engine),
  --   threshold, unit,
  --   computed kinds -> credential, denominator, roles[]
  --   attested kinds -> attested_value, attested_on, attested_by }]
  requirements  jsonb not null default '[]'::jsonb,
  data          jsonb not null default '{}'::jsonb,  -- notes, portal contact
  updated_by    text,                                -- server-stamped
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, program_id),
  constraint rfprg_status_check check (status in
    ('not_enrolled','in_progress','held','lapsed')),
  constraint rfprg_reqs_is_array check (jsonb_typeof(requirements) = 'array'),
  -- A held programme with no renewal date and no explicit "never expires" is
  -- the ambiguity has_expiry exists to prevent; refuse it at the row rather
  -- than letting the engine report 'unknown' forever.
  constraint rfprg_expiry_coherent check (
    status <> 'held' or has_expiry = false or expires_on is not null
  ),
  constraint rfprg_data_size check (octet_length(data::text) <= 65536),
  constraint rfprg_reqs_size check (octet_length(requirements::text) <= 65536)
);

create index if not exists idx_rfprg_license on public.rf_company_programs(license_hash);

alter table public.rf_company_programs enable row level security;

drop policy if exists "svc only rf_company_programs" on public.rf_company_programs;
create policy "svc only rf_company_programs" on public.rf_company_programs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.rf_company_programs from service_role;
grant select, insert, update on public.rf_company_programs to service_role;
revoke all on public.rf_company_programs from anon, authenticated;

-- Verify after running:
--   select count(*) from rf_company_programs;   -- expect 0
--
-- Confirm the grants (expect INSERT,SELECT,UPDATE; no DELETE, no TRUNCATE):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'rf_company_programs';
--
-- Confirm the coherence constraint actually bites (expect an ERROR, not a row):
--   insert into public.rf_company_programs
--     (license_hash, program_id, manufacturer, program_name, status)
--   values ('test', 'RFPRG-CHECK', 'M', 'N', 'held');
