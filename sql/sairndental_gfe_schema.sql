-- sql/sairndental_gfe_schema.sql
-- SAIRNdental good faith estimates -- No Surprises Act, 45 CFR 149.610
-- Added 2026-09-02. Additive and idempotent; run after
-- sql/sairndental_data_schema.sql. Nothing in that file is duplicated here.
--
-- WHAT THIS STORES. One row per good faith estimate drafted for an uninsured
-- (or self-pay) individual: the patient it names, what started the clock
-- (a scheduling under 149.610(b)(1)(vi)(A)/(B) or a request under (C)), the
-- date of service if there is one, the itemised list with a service code and an
-- expected charge per line as (c)(1)(iv) requires, and whether it has been
-- issued to the patient.
--
-- WHY THE PRACTICE'S NPI/TIN ARE **NOT** HERE. 149.610(c)(1)(v) requires them
-- on every estimate, but they are properties of the practice, not of one
-- estimate, and they already have a home: the dnt_settings row. Copying them
-- onto every estimate row would create a second source that drifts from the
-- first the moment a practice re-registers -- the same duplication this
-- platform has now fixed twice elsewhere. The client reads them from settings
-- and REFUSES to mark an estimate issued while any is missing.
--
-- ACCESS. Registered in api/_resources/sairndental.js and handled by the
-- generic DNT_RESOURCES block in api/sd-data.js, where it is listed as BOTH:
--   * financial (DNT_FINANCIAL_RESOURCES) -- it prices services, so it is
--     limited to the owner and front desk, the roles that issue estimates;
--   * patient-scoped (DNT_PATIENT_SCOPED_RESOURCES, on patient_id) -- it names
--     one patient and carries their date of birth, so practice-wide visibility
--     would undo the scoping dnt_patients exists to enforce.
-- Both gates were chosen deliberately; neither is inherited by accident.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other dnt_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables and the only reachable delete path anywhere
-- is api/sd-data.js's SC_RESOURCES branch. This file is
-- `create table if not exists` and safe to re-run, so granting delete here
-- would silently restore what that sweep removed. Do not add it.
--
-- SIZE CAP: 64KB of jsonb, matching api/sd-data.js's uniform MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.dnt_gfe (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndental',
  gfe_id       text not null,
  data         jsonb not null default '{}'::jsonb,   -- patient_id, patient_name, patient_dob, provider_id, trigger, trigger_date, service_date, primary_procedure_id, primary_description, lines[{procedure_type_id, cdt_code, description, diagnosis_code, expected_charge}], separate_scheduling, status, issued_at, created_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, gfe_id),
  constraint dntgfe_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntgfe_license on public.dnt_gfe(license_hash);

alter table public.dnt_gfe enable row level security;
drop policy if exists "svc only dnt_gfe" on public.dnt_gfe;
create policy "svc only dnt_gfe" on public.dnt_gfe
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.dnt_gfe to service_role;
