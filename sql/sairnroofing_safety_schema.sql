-- sql/sairnroofing_safety_schema.sql
-- SAIRNroofing gap B4 -- fall-protection equipment and job hazard assessments.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHAT THIS IS, AND WHAT IT IS NOT ═══════════════════════════════════════
-- The 2026-08-26 competitive-gap audit's Tier-B item B4, verified rather than
-- trusted before building: sairnroofing.html has five hits for "osha", all in
-- the certifications panel, and ZERO for fall protection, anchor, JHA, toolbox,
-- incident or near miss. api/ and sql/ have none of those at all.
--
-- TWO APPS ALREADY LOG INCIDENTS AND THIS DELIBERATELY DOES NOT DUPLICATE
-- THEM. SAIRNbuild has a Safety & Incidents panel with an osha_reportable flag
-- and bld_toolbox_talks; StoneDesk has an incident type list (near_miss,
-- first_aid, recordable, lost_time, property, exposure, equipment). Both are
-- client-side and both are INCIDENT LOGGING -- what happened after the fact.
-- These two tables are the other half: equipment that EXPIRES, and a hazard
-- assessment the crew on the roof today has or has not signed. An incident log
-- is a record; this is a clock and a cross-check.
--
-- ══ NO INSPECTION INTERVAL IS SEEDED AND THERE IS NO DEFAULT ═══════════════
-- The single most dangerous thing this file could do is state an interval as
-- though it were regulation. Intervals come from the standard, the
-- manufacturer's instructions and the competent person's judgement; they differ
-- by equipment type and by employer programme; and a wrong one printed as
-- authoritative is a contractor telling an OSHA inspector a number this
-- application invented. So inspection_interval_days is NULLABLE with NO
-- default, it carries an interval_source, and api/_lib/roofing-safety.js
-- refuses to compute a due date without both.
--
-- NOTHING HERE PRODUCES A COMPLIANCE VERDICT. The engine's board carries its
-- own disclaimer in the response so a UI cannot present it as one by omission.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- tools/sairn_sql_preflight.py can only compare CHECK constraints where both
-- sides state a numeric bound. See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. Fall-protection equipment, and its inspection clock.
-- ---------------------------------------------------------------------------
-- `status` is separate from the inspection state on purpose. "Overdue for
-- inspection" and "taken out of service" need OPPOSITE actions -- chase it
-- versus do not touch it -- and collapsing them is how a failed harness ends
-- up on a list somebody works through and ticks off.
create table if not exists public.rf_safety_equipment (
  id                        uuid primary key default gen_random_uuid(),
  license_hash              text not null,
  equipment_id              text not null,        -- client-generated
  kind                      text not null,        -- harness, anchor, lanyard, SRL, ladder: the contractor's own vocabulary
  identifier                text,                 -- serial or asset tag
  job_id                    text,                 -- where it currently is, if assigned
  in_service_on             date,
  last_inspected_on         date,
  last_inspected_by         text,
  -- NULLABLE, NO DEFAULT. See the header: a default here would be this file
  -- inventing a figure a contractor repeats to an inspector.
  inspection_interval_days  integer,
  interval_source           text,                 -- the engine requires it before running the clock
  status                    text not null default 'in_service',
  notes                     text,
  data                      jsonb not null default '{}'::jsonb,
  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  updated_by                text,
  unique (license_hash, equipment_id),
  constraint rfeq_status_check check (status in ('in_service','removed_from_service','failed_inspection','retired')),
  constraint rfeq_interval_sane check (inspection_interval_days is null or (inspection_interval_days > 0 and inspection_interval_days <= 3650)),
  constraint rfeq_source_size check (interval_source is null or octet_length(interval_source) <= 2048),
  constraint rfeq_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfeq_license on public.rf_safety_equipment(license_hash);
-- The query this table exists to answer quickly: what is out of date.
create index if not exists idx_rfeq_due on public.rf_safety_equipment(license_hash, status, last_inspected_on);

-- ---------------------------------------------------------------------------
-- 2. Job hazard assessments, and who signed them.
-- ---------------------------------------------------------------------------
-- `acknowledged_by` is a jsonb ARRAY of employee ids rather than a join table,
-- matching how rf_schedule already stores its crew. The engine compares it
-- against the crew scheduled for that job on that date -- supplied by the
-- caller from rf_schedule, never inferred -- and names who is on the roof
-- without having signed. That comparison is the whole point: a JHA in a folder
-- tells you nothing.
create table if not exists public.rf_job_hazard_assessments (
  id                uuid primary key default gen_random_uuid(),
  license_hash      text not null,
  jha_id            text not null,                -- client-generated
  job_id            text not null,
  assessed_on       date,
  competent_person  text,
  hazards           jsonb not null default '[]'::jsonb,
  controls          jsonb not null default '[]'::jsonb,
  acknowledged_by   jsonb not null default '[]'::jsonb,
  notes             text,
  data              jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  updated_by        text,
  unique (license_hash, jha_id),
  constraint rfjha_hazards_is_array check (jsonb_typeof(hazards) = 'array'),
  constraint rfjha_controls_is_array check (jsonb_typeof(controls) = 'array'),
  constraint rfjha_ack_is_array check (jsonb_typeof(acknowledged_by) = 'array'),
  constraint rfjha_hazards_size check (octet_length(hazards::text) <= 65536),
  constraint rfjha_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfjha_license on public.rf_job_hazard_assessments(license_hash);
create index if not exists idx_rfjha_job on public.rf_job_hazard_assessments(license_hash, job_id, assessed_on);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
-- Service-role only, matching every other rf_ table. SELECT/INSERT/UPDATE and
-- NO DELETE, and here that matters more than usual: a safety record is exactly
-- what an inspector or an attorney asks for, and a feature that can erase one
-- is a feature that will be asked why it did.
alter table public.rf_safety_equipment enable row level security;
drop policy if exists "svc only rf_safety_equipment" on public.rf_safety_equipment;
create policy "svc only rf_safety_equipment" on public.rf_safety_equipment
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_safety_equipment from service_role;
grant select, insert, update on public.rf_safety_equipment to service_role;
revoke all on public.rf_safety_equipment from anon, authenticated;

alter table public.rf_job_hazard_assessments enable row level security;
drop policy if exists "svc only rf_job_hazard_assessments" on public.rf_job_hazard_assessments;
create policy "svc only rf_job_hazard_assessments" on public.rf_job_hazard_assessments
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_job_hazard_assessments from service_role;
grant select, insert, update on public.rf_job_hazard_assessments to service_role;
revoke all on public.rf_job_hazard_assessments from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_safety_equipment;         -- expect 0
--   select count(*) from rf_job_hazard_assessments;   -- expect 0
--
-- Grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_safety_equipment','rf_job_hazard_assessments')
--    group by table_name;
--
-- Confirm the array constraint bites (expect an ERROR, not a row):
--   insert into public.rf_job_hazard_assessments (license_hash, jha_id, job_id, hazards)
--   values ('test', 'RFJHA-CHECK', 'J', '"not-an-array"'::jsonb);
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables.
