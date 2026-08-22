-- sql/sairncare_compliance_schema.sql
-- SAIRNcare Phase 2: compliance-rules engine + staff credentialing. Two tables.
--
--   alf_compliance_rules  -- VERSIONED jurisdiction requirements as data.
--   alf_staff_credentials -- append-only credential/training records per staff member.
--
-- SHAPE IS DELIBERATELY THE SAME AS alf_payer_rules (Phase 1): rule_id, state,
-- a type discriminator, effective_from/effective_to, status, jsonb data, a
-- server-stamped verified_by, and a required authority citation. Reused rather
-- than reinvented -- the two engines answer different questions but have the
-- identical "versioned regulation as data with a real citation" problem.
--
-- WHY VERSIONED, restated for this phase: every figure in here is a live
-- administrative-code number that changes on its own schedule and differs by
-- jurisdiction with no dominant pattern to default to. Verified 2026-08-22
-- against the actual current code, and that pass corrected the working summary
-- in FOUR of four states -- see sairncare_compliance_seed.json for each.
--
-- NO "CORE MODEL + EXCEPTIONS" SHORTCUT, and this is a design constraint the
-- research forced rather than a preference: no two of these four states share a
-- licensure model, a staffing-ratio METHOD, or a training-hour structure.
--   OH  -- ratio expressed as a PERCENTAGE UPLIFT over the provider's own (or a
--          benchmark) basic-service ratio, with a fixed 1:10 fallback.
--   IN  -- no per-resident ratio at all; THRESHOLD rules keyed to census bands.
--   MI  -- flat per-resident ratios that differ by licence class AND by shift.
--   PA  -- not a headcount ratio at all; SERVICE-HOURS PER RESIDENT PER DAY.
-- A single numeric "ratio" column would have to be null or lie for three of the
-- four, so staffing rules are stored as a typed method + method-specific fields.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_compliance_rules (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  app_id           text not null default 'sairncare',
  rule_id          text not null,
  state            text not null,                  -- 2-letter USPS, uppercase
  -- What kind of requirement this row expresses. Kept as a small closed set so
  -- the engine can dispatch on it; extending it is a deliberate schema change.
  requirement_type text not null,                  -- staffing | training | licensure
  -- Which licence/certification class within the state this row applies to
  -- (e.g. 'rcf_memory_care', 'afc_small', 'alr', 'pch'). Null = applies to every
  -- class in that state. This exists because MI and PA both regulate two
  -- genuinely different facility classes with different numbers.
  facility_class   text,
  effective_from   date not null,
  effective_to     date,
  status           text not null default 'active', -- active | never_in_force
  data             jsonb not null default '{}'::jsonb,
  verified_by      text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (license_hash, rule_id),
  constraint alfcp_type_check check (requirement_type in ('staffing','training','licensure')),
  constraint alfcp_status_check check (status in ('active','never_in_force')),
  constraint alfcp_state_len check (char_length(state) = 2),
  constraint alfcp_date_order check (effective_to is null or effective_to >= effective_from),
  constraint alfcp_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfcp_license on public.alf_compliance_rules(license_hash);
create index if not exists idx_alfcp_lookup on public.alf_compliance_rules(license_hash, state, requirement_type);

-- Staff credentialing / certifications-licences (platform product rule 9).
-- Built HERE rather than as its own phase because it is the same underlying data
-- as training-hour tracking: a completed dementia in-service and a current CPR
-- card are both "a dated, expiring thing this staff member holds," and splitting
-- them into two stores would guarantee they drift.
--
-- APPEND-ONLY. A credential record asserts that a real person completed real
-- training on a real date -- the exact class of record that must not be quietly
-- edited later. A correction is a NEW row that supersedes, never an overwrite.
create table if not exists public.alf_staff_credentials (
  id              uuid primary key default gen_random_uuid(),
  license_hash    text not null,
  app_id          text not null default 'sairncare',
  entry_id        text not null,                  -- client-generated (CRED-<timestamp>)
  staff_id        text not null,                   -- references alf_staff.staff_id
  -- 'training_hours' rows carry hours + category and feed the compliance engine.
  -- 'credential' rows carry an expiring licence/certification (CPR, first aid,
  -- nursing licence, background check) and feed the expiry view.
  record_type     text not null,
  data            jsonb not null default '{}'::jsonb,
  recorded_by     text,                            -- server-stamped from the real session
  created_at      timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfsc_type_check check (record_type in ('training_hours','credential')),
  constraint alfsc_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfsc_license on public.alf_staff_credentials(license_hash);
create index if not exists idx_alfsc_staff on public.alf_staff_credentials(license_hash, staff_id);

grant select, insert, update on public.alf_compliance_rules to service_role;
grant select, insert on public.alf_staff_credentials to service_role;
revoke all on public.alf_compliance_rules from anon, authenticated;
revoke all on public.alf_staff_credentials from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_compliance_rules;
--   select count(*) from alf_staff_credentials;
