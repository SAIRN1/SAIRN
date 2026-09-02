-- sql/sairndental_credentials_schema.sql
-- SAIRNdental licensing / credentialing (2026-08-24).
--
--   dnt_cred_rules    -- VERSIONED licensing requirements as data, with a
--                        required authority citation. Seeded from
--                        sql/sairndental_credentials_seed_ohio.json.
--   dnt_credentials   -- APPEND-ONLY credential records per provider.
--
-- SHAPE IS DELIBERATELY THE SAME as sairncare_compliance_schema.sql
-- (alf_compliance_rules + alf_staff_credentials). Reused rather than
-- reinvented: the two features answer different questions but have the
-- identical "versioned regulation as data with a real citation, plus an
-- append-only record of who holds what" problem.
--
-- ── WHY APPEND-ONLY ──────────────────────────────────────────────────────
-- A credential row asserts that a real, named clinician held a real licence or
-- registration on a real date. That is the exact class of record that must not
-- be quietly edited later: if a licence number was mistyped, the correction is
-- a NEW row that supersedes, never an overwrite of the original. The API grants
-- service_role select+insert only -- no update, no delete -- so the endpoint
-- physically cannot rewrite history even by mistake.
--
-- The reader resolves "current" by taking the LATEST row per
-- (provider_id, record_type, subject) -- see latestByKey() in
-- api/_lib/dental-credentials.js. A superseded row stays on disk and stops
-- firing alerts.
--
-- ── NO DERIVED EXPIRY DATES, AND THAT IS LOAD-BEARING ────────────────────
-- ORC 4715.24(A), read verbatim 2026-08-24: "A license expires on the date
-- that is two years from the date of issuance and may be registered for
-- additional two-year periods." That is a PER-LICENSEE ANNIVERSARY. Two widely
-- published secondary claims ("December 31 of odd-numbered years" / "of
-- even-numbered years") contradict each other AND the statute.
--
-- So expires_on lives in each row's own data, entered from the practice's own
-- licence document. Nothing in this feature computes an expiry from a state.
--
-- ── ROLE GATE: PROMISED HERE, THEN CLOSED 2026-08-29 ─────────────────────
-- This header used to say there was no per-employee role gate and explain why:
-- "SAIRNdental has NO employee auth -- there is no api/dnt-auth.js, and every
-- existing dnt_* resource is gated by the practice's license key alone ... If
-- per-employee auth is added to SAIRNdental later, this is a resource that
-- should be re-gated at that time. Recorded here so the gap is known, not
-- discovered."
--
-- Employee auth was added (api/dnt-auth.js). The re-gating this note asked for
-- did not happen, and the note stopped being true without changing, so the gap
-- went back to being undiscovered until a platform-wide sweep on 2026-08-29
-- compared this write path against rf_cert_rules and alf_compliance_rules --
-- the same reference-rule shape in two other apps, both owner/management-only.
-- Until then any signed-in employee, including a provider or front desk, could
-- rewrite a state credentialing requirement.
--
-- NOW: dnt_cred_rules WRITE is owner-only, enforced in api/sd-data.js against
-- api/dnt-auth.js's MANAGEMENT_ROLES ({ owner: true }); `verified_by` records
-- that owner's employee_id instead of the literal 'license'. READ is unchanged
-- and deliberately stays open to any signed-in employee -- a provider needs to
-- see what their state requires of them, and published law is not sensitive.
-- The lesson worth keeping is about the note, not the gate: a comment that
-- describes a CONDITION ("there is no employee auth") silently becomes a false
-- claim the day the condition changes, and nothing checks comments.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.dnt_cred_rules (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  app_id           text not null default 'sairndental',
  rule_id          text not null,
  state            text not null,                  -- 'OH', or 'US' for federal
  requirement_type text not null,                  -- continuing_education | license_term | certification | dea_term | dea_training
  role             text,                           -- dentist | hygienist | null = applies to both
  effective_from   date not null,
  effective_to     date,
  status           text not null default 'active',
  data             jsonb not null default '{}'::jsonb,   -- carries data.authority (citation/url/quote/read_on)
  verified_by      text,   -- server-stamped from the session. SEE NOTE BELOW.
  -- WHAT THIS ACTUALLY RECORDS, corrected 2026-08-29: the employee_id of
  -- whoever was SIGNED IN when the row was written. Not who verified the
  -- content. The two coincide only by accident -- the Ohio HSSA contingency
  -- rules were written by a disposable verification account and carry its id.
  -- THE REAL PROVENANCE IS data.authority (citation, url, quote, read_on),
  -- which is required and is what a customer would have to defend.
  -- Kept as `verified_by` rather than renamed to `loaded_by`: the rename is
  -- correct and is deferred, because it is a migration across six live tables
  -- plus every write path plus two tools that subtract this field BY NAME
  -- (api/reference-fingerprint.js, sql/platform_reference_rules_divergence_
  -- 2026-08-28.sql). See SAIRN-BACKLOG.md.
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (license_hash, rule_id),
  constraint dntcr_type_check check (requirement_type in
    ('continuing_education','license_term','certification','dea_term','dea_training')),
  constraint dntcr_status_check check (status in ('active','superseded')),
  constraint dntcr_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_dntcr_license on public.dnt_cred_rules(license_hash);
create index if not exists idx_dntcr_state on public.dnt_cred_rules(license_hash, state);

create table if not exists public.dnt_credentials (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairndental',
  entry_id      text not null,                     -- client-generated (DCRED-<timestamp>)
  provider_id   text not null,                     -- references dnt_providers.provider_id
  -- state_license    -- a state dental/hygiene licence: state, number, expires_on
  -- dea_registration -- DEA number, schedules, expires_on, plus the one-time
  --                     MATE attestation flag (NOT an expiring thing itself)
  -- ce_cycle         -- one CE period: cycle_start, cycle_end, hours_logged
  -- certification    -- BLS/CPR and similar: issuer, expires_on
  -- payer_enrollment -- 2026-09-02, competitive-gap audit B1. NOT licensure:
  --                     a licence says the dentist may practise, an enrolment
  --                     says a particular payer will pay them. Carries payer,
  --                     provider_number, network_status, effective_on, term_on
  --                     and revalidation_due_on. Every one of those dates is
  --                     the one on the payer's own letter -- nothing is
  --                     derived from a payer name, the same rule the licence
  --                     half already states about ORC 4715.24(A).
  record_type   text not null,
  data          jsonb not null default '{}'::jsonb,
  recorded_at   timestamptz not null default now(),  -- server-stamped; supersession order
  created_at    timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint dntcd_type_check check (record_type in
    ('state_license','dea_registration','ce_cycle','certification','payer_enrollment')),
  constraint dntcd_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_dntcd_license on public.dnt_credentials(license_hash);
create index if not exists idx_dntcd_provider on public.dnt_credentials(license_hash, provider_id);

alter table public.dnt_cred_rules enable row level security;
alter table public.dnt_credentials enable row level security;

drop policy if exists "svc only dnt_cred_rules" on public.dnt_cred_rules;
create policy "svc only dnt_cred_rules" on public.dnt_cred_rules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only dnt_credentials" on public.dnt_credentials;
create policy "svc only dnt_credentials" on public.dnt_credentials
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- Rules may be superseded in place (status flips, effective_to gets set), so
-- they get update. Credential records get INSERT ONLY -- see "why append-only"
-- above. The absence of update/delete here is the enforcement, not a comment.
grant select, insert, update on public.dnt_cred_rules to service_role;
grant select, insert on public.dnt_credentials to service_role;
revoke all on public.dnt_cred_rules from anon, authenticated;
revoke all on public.dnt_credentials from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from dnt_cred_rules;
--   select count(*) from dnt_credentials;
--
-- Confirm the append-only grant actually took (expect NO 'UPDATE' or 'DELETE'
-- row for dnt_credentials):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'dnt_credentials';

-- ---------------------------------------------------------------------------
-- MIGRATION 2026-09-02 -- payer_enrollment (competitive-gap audit B1)
--
-- REQUIRED ON ANY DATABASE THAT ALREADY RAN THIS FILE. `create table if not
-- exists` above does NOT alter an existing table, so the CHECK constraint on
-- an already-provisioned practice still enumerates only the original four
-- record types. Until this runs, every payer-enrolment write is rejected by
-- Postgres with a check-constraint violation -- api/sd-data.js catches that
-- specific case and returns RECORD_TYPE_NOT_MIGRATED naming this block,
-- rather than a generic error the app would render as 'saved on this device
-- only'. That message would read as a connectivity problem, and it is not:
-- the write will never succeed until this is run.
--
-- Idempotent and safe to re-run. Drops the old constraint by name and adds
-- it back with the fifth type; a fresh database gets the same constraint from
-- the create above and this simply replaces it with an identical one.
alter table public.dnt_credentials drop constraint if exists dntcd_type_check;
alter table public.dnt_credentials add constraint dntcd_type_check check (record_type in
  ('state_license','dea_registration','ce_cycle','certification','payer_enrollment'));

-- Confirm it took (expect the five-value list, including payer_enrollment):
--   select pg_get_constraintdef(oid) from pg_constraint
--    where conname = 'dntcd_type_check';
