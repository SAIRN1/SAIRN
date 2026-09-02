-- sql/sairndental_treatment_plans_schema.sql
-- SAIRNdental treatment plans -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A9. Additive and idempotent; run after
-- sql/sairndental_data_schema.sql. Nothing in that file is duplicated here.
--
-- WHAT THIS IS, AND WHAT IT IS NOT. A treatment plan is PROPOSED work: a
-- patient, a title, a status, and a list of items each carrying a procedure
-- type, a phase, a fee, an optional tooth/area and an optional planned date.
-- The audit drew the distinction that matters -- it is DISTINCT FROM CHARGING A
-- COMPLETED PROCEDURE. dnt_charges records work already done and money already
-- owed; this records work proposed and not yet accepted. Neither replaces the
-- other and a row here moves no money.
--
-- IT IS NOT A GOOD FAITH ESTIMATE, and that is the confusion this feature has
-- to avoid creating. A plan estimate and a GFE look identical on paper -- CDT
-- codes with expected charges -- and they are legally different objects. A GFE
-- under 45 CFR 149.610 carries required content and a deadline; a plan estimate
-- carries neither. The app says so on the panel and on the printed plan, and
-- points at dnt_gfe, which does it properly. Do not merge the two tables: the
-- moment a plan could be mistaken for a GFE, a practice can believe it has met
-- a federal obligation it has not.
--
-- NO TOTALS ARE STORED. Fee, insurance estimate and patient portion are
-- computed at render time from the items, the patient's payer and this
-- practice's dnt_coverage_rules. A stored total drifts from the coverage rules
-- it came from the moment one is edited, and would then have to be believed
-- rather than checked. Where NO coverage rule exists for a payer and procedure,
-- the app reports "no coverage rule" rather than a $0 estimate -- a zero
-- produced by an absent rule is a fabricated figure that the patient-portion
-- column would silently inherit.
--
-- NOR IS "STARTED" STORED. Whether an accepted plan has been started is derived
-- from real appointments for its planned procedures, so a plan cannot report
-- progress the schedule does not show.
--
-- ACCESS. Registered in api/_resources/sairndental.js and handled by the
-- generic DNT_RESOURCES block in api/sd-data.js, where it is listed as BOTH:
--   * financial (DNT_FINANCIAL_RESOURCES) -- it prices what the patient is
--     being asked to accept, same footing as dnt_charges and dnt_gfe;
--   * patient-scoped (DNT_PATIENT_SCOPED_RESOURCES on patient_id) -- it names
--     one patient and describes their proposed care.
-- Both were chosen deliberately; neither is inherited by accident.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other dnt_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables; the only reachable delete path anywhere is
-- api/sd-data.js's SC_RESOURCES branch. This file is `create table if not
-- exists` and safe to re-run, so granting delete here would silently restore
-- what that sweep removed. Do not add it.
--
-- SIZE CAP: 64KB of jsonb, matching api/sd-data.js's uniform MAX_PAYLOAD_BYTES.
-- A plan's items live in the blob, so this is a real ceiling rather than a
-- formality -- at roughly 200 bytes per item it allows a few hundred items on
-- one plan, far beyond any real case, but a client that looped and appended
-- would hit it rather than growing without bound.

create extension if not exists pgcrypto;

create table if not exists public.dnt_txplans (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndental',
  txplan_id    text not null,
  data         jsonb not null default '{}'::jsonb,   -- patient_id, provider_id, title, status (proposed|presented|accepted|declined), decided_on, note, items[{procedure_type_id, phase, fee, tooth, planned_on}], created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, txplan_id),
  constraint dnttp_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dnttp_license on public.dnt_txplans(license_hash);

alter table public.dnt_txplans enable row level security;
drop policy if exists "svc only dnt_txplans" on public.dnt_txplans;
create policy "svc only dnt_txplans" on public.dnt_txplans
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.dnt_txplans to service_role;
