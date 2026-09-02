-- sql/sairnsenior_training_schema.sql
-- SAIRNsenior caregiver training hours -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A6. Additive and idempotent; run after
-- sql/sairnsenior_caregivers_schema.sql. Nothing in that file is duplicated
-- here.
--
-- WHAT THIS STORES. Two tables:
--
--   sen_training_rules    the requirement, as DATA carrying its own citation
--                         and its own scope: jurisdiction, programme, aide
--                         type, in-service vs pre-service, hours, and the
--                         rolling window in months.
--   sen_training_records  what a named caregiver actually completed: hours, the
--                         date, the subject, who delivered it, and what
--                         evidence the agency holds.
--
-- WHY THE RULE IS A ROW AND NOT A CONSTANT IN THE CODE. The hour figures are
-- not universal and picking the wrong one is easy and looks right. Three real
-- rules, each read against primary source during the build, each with a
-- different scope:
--
--   42 CFR 484.80(d)      home health aide at a Medicare-certified agency:
--                         at least 12 hours of in-service training during each
--                         12-month period, supervised by a registered nurse.
--   ORC 5164.913(A)(1)    personal care aide under the Ohio integrated care
--                         delivery system: 30 hours pre-service and 6 hours
--                         in-service every 12 months. (A)(2) also CAPS both --
--                         the department may not require more.
--   OAC 5160-46-12(D)(3)  non-licensed direct care staff at an Ohio home care
--                         waiver agency provider: 12 hours of in-service
--                         training every 12 months. Effective 2025-09-22.
--
-- Six versus twelve is a 2x error on a survey-citable requirement, so the app
-- matches EXACTLY on programme and aide type and reports "no rule on file"
-- when nothing matches, rather than defaulting to whichever figure is nearest.
-- Every other jurisdiction ships empty on purpose: a plausible invented figure
-- for a state nobody read would look authoritative and be wrong.
--
-- A RULE WITHOUT A CITATION IS REFUSED BY THE CLIENT, deliberately. An
-- uncheckable requirement inside a compliance tool is indistinguishable from an
-- invented one, and the whole point of this table is that the next reader can
-- verify it instead of trusting it.
--
-- ACCESS. Registered in api/_resources/sairnsenior.js and served by the same
-- shared bespoke branch in api/sd-data.js as the referral resources, gated on
-- SEN_CLIENT_BROAD_READ_ROLES -- owner, billing, coordinator, scheduler -- for
-- BOTH read and write. Schedulers and coordinators decide who can be sent to a
-- visit and therefore need to see standing; management-only would put it out of
-- reach of the people staffing the schedule, and every-employee would let a
-- caregiver read the whole roster's compliance position.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables; the only reachable delete path anywhere is
-- api/sd-data.js's SC_RESOURCES branch. This file is `create table if not
-- exists` and safe to re-run, so granting delete here would silently restore
-- what that sweep removed. Do not add it.
--
-- SIZE CAP: 64KB of jsonb per row, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.sen_training_rules (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  rule_id      text not null,
  data         jsonb not null default '{}'::jsonb,   -- jurisdiction, program, aide_type, kind (in_service|pre_service), hours, period_months, ceiling, citation, citation_url, effective_from, notes, seeded
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, rule_id),
  constraint sentr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sentr_license on public.sen_training_rules(license_hash);

create table if not exists public.sen_training_records (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  record_id    text not null,
  data         jsonb not null default '{}'::jsonb,   -- caregiver_id, completed_on, hours, kind (in_service|pre_service), title, provider, evidence, created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, record_id),
  constraint sentc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sentc_license on public.sen_training_records(license_hash);

alter table public.sen_training_rules   enable row level security;
alter table public.sen_training_records enable row level security;

drop policy if exists "svc only sen_training_rules"   on public.sen_training_rules;
drop policy if exists "svc only sen_training_records" on public.sen_training_records;

create policy "svc only sen_training_rules" on public.sen_training_rules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sen_training_records" on public.sen_training_records
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_training_rules   to service_role;
grant select, insert, update on public.sen_training_records to service_role;
