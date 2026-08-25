-- sql/sairnroofing_claims_schema.sql
-- SAIRNroofing Phase 3b -- insurance claim record + photo evidence.
--
--   rf_claims        -- MUTABLE claim record, keyed by claim_id. A claim
--                       evolves over its real 45-90 day lifecycle (money fields
--                       fill in as cheques arrive, status advances), so unlike
--                       rf_certifications this is an upsert, not append-only.
--   rf_claim_photos  -- APPEND-ONLY evidence photos, tagged by phase/elevation/
--                       damage. Append-only ON PURPOSE and for a different
--                       reason than the certifications: a tear-off photo is the
--                       evidentiary basis for a hidden-damage supplement, and
--                       evidence that can be edited after the fact is not
--                       evidence. A correction is a new photo, never a rewrite.
--
-- ── GRANTS: THE SOUND IDIOM ──────────────────────────────────────────────
-- REVOKE ALL from service_role FIRST, then grant. `grant select, insert` alone
-- is not sufficient -- postgres's default ACL confers TRUNCATE/REFERENCES/
-- TRIGGER/MAINTAIN on every new table, and GRANT cannot subtract. See
-- sql/append_only_grant_audit.sql. rf_claims gets update (it is mutable);
-- rf_claim_photos does not.
--
-- ── THE MONEY RULE IS ENFORCED IN api/_lib/roofing-claims.js, NOT HERE ───
-- The seven money fields live as separate keys inside data, never one
-- collapsed amount -- see that module's header for why (conflating them is how
-- the recoverable-depreciation release gets lost). A jsonb blob cannot express
-- "these must stay separate" as a column constraint, so the guarantee is in the
-- normalizer that writes them, backed by tests. This comment records that the
-- absence of money COLUMNS here is deliberate, not an oversight.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_claims (
  id                   uuid primary key default gen_random_uuid(),
  license_hash         text not null,
  app_id               text not null default 'sairnroofing',
  claim_id             text not null,                 -- client-generated (RFCLM-<timestamp>)
  job_id               text not null,                 -- references rf_jobs.job_id
  assigned_employee_id text,                           -- estimator/foreman handling it; null = management-only
  status               text not null default 'loss_reported',
  data                 jsonb not null default '{}'::jsonb,  -- carrier, claim_number, adjuster,
                                                              -- peril, policy_type, the 7 money fields,
                                                              -- waiting_on_carrier flag, insurer_denial_at
  -- CORRECTED 2026-08-25: this line previously ended "...waiting_on_carrier
  -- flag, contingency sig", anticipating the signed contingency agreement
  -- living in this blob. That was wrong and Phase 5 does not do it. The
  -- signature moved to its own APPEND-ONLY table in
  -- sql/sairnroofing_agreements_schema.sql, for three reasons this same file
  -- already argues elsewhere: rf_claims is a mutable upsert and an executed
  -- agreement is evidence ("evidence that can be edited after the fact is not
  -- evidence" -- see rf_claim_photos above); rfclm_data_size caps this column
  -- at 64KB and a captured signature is an image; and a rescission needs a
  -- second, later record, which one mutable field cannot express.
  -- What DOES belong here is insurer_denial_at -- the date of the carrier's
  -- written denial. It is claim history, not agreement evidence, and Colorado's
  -- rescission clock (C.R.S. 6-22-104) starts from it.
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (license_hash, claim_id),
  constraint rfclm_status_check check (status in
    ('loss_reported','adjuster_assigned','adjuster_meeting','scope_written',
     'contingency_signed','install_complete','depreciation_released')),
  constraint rfclm_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfclm_license on public.rf_claims(license_hash);
create index if not exists idx_rfclm_job on public.rf_claims(license_hash, job_id);
create index if not exists idx_rfclm_assignee on public.rf_claims(license_hash, assigned_employee_id);

create table if not exists public.rf_claim_photos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  photo_id     text not null,                         -- client-generated (RFCPH-<timestamp>)
  claim_id     text not null,                         -- references rf_claims.claim_id
  captured_by  text not null,                         -- server-stamped from the session
  data         jsonb not null default '{}'::jsonb,    -- photo_base64, phase, elevation, damage_type, note
  created_at   timestamptz not null default now(),
  unique (license_hash, photo_id),
  -- 1.5MB, matching rf_photos -- base64 photo payloads, not the 64KB app-data ceiling.
  constraint rfcph_data_size check (octet_length(data::text) <= 1572864)
);

create index if not exists idx_rfcph_license_claim on public.rf_claim_photos(license_hash, claim_id);

alter table public.rf_claims enable row level security;
alter table public.rf_claim_photos enable row level security;

drop policy if exists "svc only rf_claims" on public.rf_claims;
create policy "svc only rf_claims" on public.rf_claims
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only rf_claim_photos" on public.rf_claim_photos;
create policy "svc only rf_claim_photos" on public.rf_claim_photos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- rf_claims is mutable, so it keeps UPDATE. rf_claim_photos is append-only
-- evidence and does NOT.
revoke all on public.rf_claims from service_role;
grant select, insert, update on public.rf_claims to service_role;
revoke all on public.rf_claim_photos from service_role;
grant select, insert on public.rf_claim_photos to service_role;
revoke all on public.rf_claims from anon, authenticated;
revoke all on public.rf_claim_photos from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from rf_claims;
--   select count(*) from rf_claim_photos;
--
-- Confirm the grants (expect rf_claims = INSERT,SELECT,UPDATE ;
-- rf_claim_photos = INSERT,SELECT ; no TRUNCATE on either):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_claims','rf_claim_photos')
--    group by table_name;
