-- sql/sairnroofing_certifications_schema.sql
-- SAIRNroofing Phase 3a -- per-employee certifications + licensing rules.
--
--   rf_cert_rules      -- VERSIONED licensing/safety requirements as data, each
--                         carrying a required authority citation. Seeded from
--                         sql/sairnroofing_certifications_seed_ohio.json.
--   rf_certifications  -- APPEND-ONLY per-employee credential records.
--
-- Same shape as sairndental_credentials_schema.sql and
-- sairncare_compliance_schema.sql. Reused rather than reinvented.
--
-- ── GRANTS: THE SOUND IDIOM, NOT THE ONE THAT LEFT NINE TABLES OPEN ──────
-- REVOKE ALL from service_role FIRST, then grant exactly what is needed.
-- `grant select, insert` alone is NOT sufficient: postgres's default ACL for
-- relations in schema public grants service_role TRUNCATE/REFERENCES/TRIGGER/
-- MAINTAIN on every table it creates, and GRANT is additive -- it cannot remove
-- what the role already holds. Confirmed live 2026-08-24 via pg_default_acl
-- after TRUNCATE was found on dnt_credentials; nine tables platform-wide were
-- affected. See sql/append_only_grant_audit.sql.
--
-- This file is written the sound way from the start so it does not become the
-- tenth. It stays correct even if the default-ACL fix in that file's Section 4
-- has not been applied yet.
--
-- ── WHY APPEND-ONLY ──────────────────────────────────────────────────────
-- A certification row asserts that a named worker held a real card on a real
-- date. A correction is a NEW row that supersedes, never an overwrite. The
-- reader takes the latest per (employee_id, record_type, subject) --
-- latestByKey() in api/_lib/roofing-credentials.js.
--
-- ── has_expiry IS A REAL COLUMN-LEVEL CONCERN, NOT A UI DETAIL ───────────
-- OSHA 10/30 Outreach cards carry NO federal expiration. Storing that as a
-- null expires_on would be indistinguishable from "we never entered the date",
-- so data.has_expiry is explicit and the engine reports 'current' for a
-- lifetime card versus 'unknown' for a genuinely missing renewal date. The
-- CHECK below refuses the ambiguous combination outright.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_cert_rules (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  app_id           text not null default 'sairnroofing',
  rule_id          text not null,
  state            text not null,                 -- 'OH', or 'US' for federal
  requirement_type text not null,                 -- state_licensing | safety_standard | training_card
  role             text,
  effective_from   date not null,
  effective_to     date,
  status           text not null default 'active',
  data             jsonb not null default '{}'::jsonb,  -- carries data.authority
  verified_by      text,   -- SEE NOTE BELOW -- this is who was signed in, not who verified
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
  constraint rfcr_type_check check (requirement_type in
    ('state_licensing','safety_standard','training_card')),
  constraint rfcr_status_check check (status in ('active','superseded')),
  constraint rfcr_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfcr_license on public.rf_cert_rules(license_hash);
create index if not exists idx_rfcr_state on public.rf_cert_rules(license_hash, state);

create table if not exists public.rf_certifications (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  entry_id     text not null,                     -- client-generated (RFCERT-<timestamp>)
  employee_id  text not null,                     -- references sairnroofing_employee_auth.employee_id
  -- osha_card       -- OSHA 10/30 Outreach card (no federal expiry)
  -- safety_training -- fall protection, ladder, competent person
  -- installer_cert  -- manufacturer per-installer cert (e.g. Tesla Certified)
  -- local_license   -- municipal/county registration where one is required
  record_type  text not null,
  data         jsonb not null default '{}'::jsonb,
  recorded_at  timestamptz not null default now(),  -- supersession order
  created_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint rfcd_type_check check (record_type in
    ('osha_card','safety_training','installer_cert','local_license')),
  -- Refuses the ambiguous state: a record must either declare it has no expiry
  -- or carry one. Nothing may be silently undated.
  constraint rfcd_expiry_check check (
    (data->>'has_expiry') = 'false' or (data ? 'expires_on')
  ),
  constraint rfcd_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfcd_license on public.rf_certifications(license_hash);
create index if not exists idx_rfcd_employee on public.rf_certifications(license_hash, employee_id);

alter table public.rf_cert_rules enable row level security;
alter table public.rf_certifications enable row level security;

drop policy if exists "svc only rf_cert_rules" on public.rf_cert_rules;
create policy "svc only rf_cert_rules" on public.rf_cert_rules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only rf_certifications" on public.rf_certifications;
create policy "svc only rf_certifications" on public.rf_certifications
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- Revoke FIRST (clears the default-ACL baseline), then grant exactly what each
-- table needs. Rules may be superseded in place, so they keep update;
-- certifications are append-only and do not.
revoke all on public.rf_cert_rules from service_role;
grant select, insert, update on public.rf_cert_rules to service_role;
revoke all on public.rf_certifications from service_role;
grant select, insert on public.rf_certifications to service_role;
revoke all on public.rf_cert_rules from anon, authenticated;
revoke all on public.rf_certifications from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from rf_cert_rules;
--   select count(*) from rf_certifications;
--
-- Confirm the grants took. Expect exactly INSERT, SELECT for rf_certifications
-- and INSERT, SELECT, UPDATE for rf_cert_rules -- no TRUNCATE on either:
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_cert_rules','rf_certifications')
--    group by table_name;
