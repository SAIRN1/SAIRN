-- sql/sairnvet_data_schema.sql
-- SAIRNvet application data -- the clinical record reaches a server.
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run. Until it runs, every write
-- answers 503 NOT_PROVISIONED naming this file and every read answers
-- provisioned:false, so the app degrades honestly instead of claiming a
-- backup it does not have.
--
-- WHY THIS FILE EXISTS, MEASURED. tools/local_only_collection_check.py on
-- 2026-09-09 reported sairnvet.html as 42 of 42 collections with NO route to
-- a server -- the worst ratio on the platform, and the app with the most
-- regulated content on it. svData() existed the whole time and named exactly
-- one resource, `shared_knowledge`, an AI context sink. Patients, clients,
-- SOAP notes, lab results, imaging, invoicing, the COMPLIANCE register and
-- the CONTROLLED-SUBSTANCE log lived in one browser and nowhere else.
-- api/_resources/sairnvet.js recorded the empty registry as the honest answer
-- at the time -- "a registry that lists resources no code requests is a claim
-- about the platform that nothing backs" -- and that stays true: the code now
-- requests them, so the names go here.
--
-- FORTY-ONE TABLES, ONE EXCLUDED, and the exclusion is written down in
-- api/_resources/sairnvet.js rather than left as an absence.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name (strip
-- sv_, singularise), the rule sairnbuild's and sairnlaw's schemas document.
--
-- ONE ID COLUMN IS NOT A MINTED ID AND THAT IS DELIBERATE. sv_controlled's
-- records carry NO `id` field -- the app finds a drug with
-- `list.find(d => d.drug === drugName)`, so the DRUG NAME is the record's
-- identity and always has been. controlled_id holds that name. The
-- alternative was minting ids into a live controlled-substance register,
-- which is a data migration on a regulated record to satisfy a naming
-- convention. The client's sync hook carries a per-resource id-field map for
-- exactly this one case.
--
-- SECURITY MODEL, STATED PLAINLY BECAUSE OF WHAT IS IN HERE. These tables are
-- gated on the LICENCE KEY ONLY. SAIRNvet has no per-employee authentication
-- at all -- its `role` is a self-selected dropdown at login, never
-- server-verified, which the app's own AI dispatcher header already says is
-- why it carries no role gate. So a licence-only gate is not a weakening: it
-- is the whole authentication this app has, and the open-work row for
-- SAIRNvet's missing auth subsystem is where that gets fixed, for every
-- resource at once. sv_controlled is a DEA-relevant register and
-- sv_audit_log is its audit trail; both are in scope of that row, and this
-- file does not pretend otherwise.
--
-- RLS enabled with no anon policy -- api/sd-data.js is the only door in.
-- 64KB per row's data jsonb, matching sd-data.js's uniform MAX_PAYLOAD_BYTES.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE, and do NOT add one when fixing a
-- missing grant. The platform's only reachable delete path is sd-data.js's
-- SC_RESOURCES branch; corrections here are upserts and cancellation is a
-- status field. `revoke all` precedes each grant because a bare grant is
-- additive and cannot remove what the default ACL already handed over.

create extension if not exists pgcrypto;

-- Controlled-substance dose audit trail -- who logged what, when, and every refusal. Capped at 500 entries client-side.
create table if not exists public.sv_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  audit_log_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, audit_log_id),
  constraint sv_audit_log_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_audit_log enable row level security;
drop policy if exists "svc only sv_audit_log" on public.sv_audit_log;
create policy "svc only sv_audit_log" on public.sv_audit_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_audit_log from service_role;
grant select, insert, update on public.sv_audit_log to service_role;

-- Billing transactions.
create table if not exists public.sv_billing (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  billing_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, billing_id),
  constraint sv_billing_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_billing enable row level security;
drop policy if exists "svc only sv_billing" on public.sv_billing;
create policy "svc only sv_billing" on public.sv_billing
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_billing from service_role;
grant select, insert, update on public.sv_billing to service_role;

-- Boarding stays.
create table if not exists public.sv_boarding (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  boarding_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, boarding_id),
  constraint sv_boarding_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_boarding enable row level security;
drop policy if exists "svc only sv_boarding" on public.sv_boarding;
create policy "svc only sv_boarding" on public.sv_boarding
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_boarding from service_role;
grant select, insert, update on public.sv_boarding to service_role;

-- Owners/clients.
create table if not exists public.sv_clients (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  client_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint sv_clients_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_clients enable row level security;
drop policy if exists "svc only sv_clients" on public.sv_clients;
create policy "svc only sv_clients" on public.sv_clients
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_clients from service_role;
grant select, insert, update on public.sv_clients to service_role;

-- Coggins (EIA) test records -- a regulated equine test with a certificate.
create table if not exists public.sv_coggins (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  coggins_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, coggins_id),
  constraint sv_coggins_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_coggins enable row level security;
drop policy if exists "svc only sv_coggins" on public.sv_coggins;
create policy "svc only sv_coggins" on public.sv_coggins
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_coggins from service_role;
grant select, insert, update on public.sv_coggins to service_role;

-- Client communications log.
create table if not exists public.sv_comms (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  comm_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, comm_id),
  constraint sv_comms_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_comms enable row level security;
drop policy if exists "svc only sv_comms" on public.sv_comms;
create policy "svc only sv_comms" on public.sv_comms
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_comms from service_role;
grant select, insert, update on public.sv_comms to service_role;

-- Practice compliance items.
create table if not exists public.sv_compliance (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  compliance_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, compliance_id),
  constraint sv_compliance_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_compliance enable row level security;
drop policy if exists "svc only sv_compliance" on public.sv_compliance;
create policy "svc only sv_compliance" on public.sv_compliance
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_compliance from service_role;
grant select, insert, update on public.sv_compliance to service_role;

-- Conservation-programme records.
create table if not exists public.sv_conservation (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  conservation_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, conservation_id),
  constraint sv_conservation_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_conservation enable row level security;
drop policy if exists "svc only sv_conservation" on public.sv_conservation;
create policy "svc only sv_conservation" on public.sv_conservation
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_conservation from service_role;
grant select, insert, update on public.sv_conservation to service_role;

-- CONTROLLED-SUBSTANCE REGISTER. controlled_id holds the DRUG NAME, not a minted id -- see the id-column note in the header.
create table if not exists public.sv_controlled (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  controlled_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, controlled_id),
  constraint sv_controlled_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_controlled enable row level security;
drop policy if exists "svc only sv_controlled" on public.sv_controlled;
create policy "svc only sv_controlled" on public.sv_controlled
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_controlled from service_role;
grant select, insert, update on public.sv_controlled to service_role;

-- Small-animal dental records.
create table if not exists public.sv_dental (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  dental_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, dental_id),
  constraint sv_dental_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_dental enable row level security;
drop policy if exists "svc only sv_dental" on public.sv_dental;
create policy "svc only sv_dental" on public.sv_dental
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_dental from service_role;
grant select, insert, update on public.sv_dental to service_role;

-- Document metadata.
create table if not exists public.sv_documents (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  document_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, document_id),
  constraint sv_documents_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_documents enable row level security;
drop policy if exists "svc only sv_documents" on public.sv_documents;
create policy "svc only sv_documents" on public.sv_documents
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_documents from service_role;
grant select, insert, update on public.sv_documents to service_role;

-- Equine dental records.
create table if not exists public.sv_equinedental (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  equinedental_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, equinedental_id),
  constraint sv_equinedental_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_equinedental enable row level security;
drop policy if exists "svc only sv_equinedental" on public.sv_equinedental;
create policy "svc only sv_equinedental" on public.sv_equinedental
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_equinedental from service_role;
grant select, insert, update on public.sv_equinedental to service_role;

-- Exam rooms and their current state.
create table if not exists public.sv_examrooms (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  examroom_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, examroom_id),
  constraint sv_examrooms_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_examrooms enable row level security;
drop policy if exists "svc only sv_examrooms" on public.sv_examrooms;
create policy "svc only sv_examrooms" on public.sv_examrooms
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_examrooms from service_role;
grant select, insert, update on public.sv_examrooms to service_role;

-- Farm calls.
create table if not exists public.sv_farmcalls (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  farmcall_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, farmcall_id),
  constraint sv_farmcalls_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_farmcalls enable row level security;
drop policy if exists "svc only sv_farmcalls" on public.sv_farmcalls;
create policy "svc only sv_farmcalls" on public.sv_farmcalls
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_farmcalls from service_role;
grant select, insert, update on public.sv_farmcalls to service_role;

-- Financial records.
create table if not exists public.sv_financials (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  financial_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, financial_id),
  constraint sv_financials_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_financials enable row level security;
drop policy if exists "svc only sv_financials" on public.sv_financials;
create policy "svc only sv_financials" on public.sv_financials
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_financials from service_role;
grant select, insert, update on public.sv_financials to service_role;

-- Herd health records.
create table if not exists public.sv_herdhealth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  herdhealth_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, herdhealth_id),
  constraint sv_herdhealth_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_herdhealth enable row level security;
drop policy if exists "svc only sv_herdhealth" on public.sv_herdhealth;
create policy "svc only sv_herdhealth" on public.sv_herdhealth
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_herdhealth from service_role;
grant select, insert, update on public.sv_herdhealth to service_role;

-- Imaging studies (metadata, no image bytes).
create table if not exists public.sv_imaging (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  imaging_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, imaging_id),
  constraint sv_imaging_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_imaging enable row level security;
drop policy if exists "svc only sv_imaging" on public.sv_imaging;
create policy "svc only sv_imaging" on public.sv_imaging
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_imaging from service_role;
grant select, insert, update on public.sv_imaging to service_role;

-- Invoices.
create table if not exists public.sv_invoicing (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  invoicing_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, invoicing_id),
  constraint sv_invoicing_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_invoicing enable row level security;
drop policy if exists "svc only sv_invoicing" on public.sv_invoicing;
create policy "svc only sv_invoicing" on public.sv_invoicing
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_invoicing from service_role;
grant select, insert, update on public.sv_invoicing to service_role;

-- Laboratory results.
create table if not exists public.sv_labresults (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  labresult_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, labresult_id),
  constraint sv_labresults_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_labresults enable row level security;
drop policy if exists "svc only sv_labresults" on public.sv_labresults;
create policy "svc only sv_labresults" on public.sv_labresults
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_labresults from service_role;
grant select, insert, update on public.sv_labresults to service_role;

-- Lameness exams.
create table if not exists public.sv_lameness (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  lameness_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, lameness_id),
  constraint sv_lameness_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_lameness enable row level security;
drop policy if exists "svc only sv_lameness" on public.sv_lameness;
create policy "svc only sv_lameness" on public.sv_lameness
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_lameness from service_role;
grant select, insert, update on public.sv_lameness to service_role;

-- Mobile-vet stops.
create table if not exists public.sv_mobilevet (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  mobilevet_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, mobilevet_id),
  constraint sv_mobilevet_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_mobilevet enable row level security;
drop policy if exists "svc only sv_mobilevet" on public.sv_mobilevet;
create policy "svc only sv_mobilevet" on public.sv_mobilevet
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_mobilevet from service_role;
grant select, insert, update on public.sv_mobilevet to service_role;

-- Practice locations.
create table if not exists public.sv_multisite (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  multisite_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, multisite_id),
  constraint sv_multisite_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_multisite enable row level security;
drop policy if exists "svc only sv_multisite" on public.sv_multisite;
create policy "svc only sv_multisite" on public.sv_multisite
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_multisite from service_role;
grant select, insert, update on public.sv_multisite to service_role;

-- Patients.
create table if not exists public.sv_patients (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  patient_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, patient_id),
  constraint sv_patients_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_patients enable row level security;
drop policy if exists "svc only sv_patients" on public.sv_patients;
create policy "svc only sv_patients" on public.sv_patients
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_patients from service_role;
grant select, insert, update on public.sv_patients to service_role;

-- Peer consultations.
create table if not exists public.sv_peerconsults (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  peerconsult_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, peerconsult_id),
  constraint sv_peerconsults_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_peerconsults enable row level security;
drop policy if exists "svc only sv_peerconsults" on public.sv_peerconsults;
create policy "svc only sv_peerconsults" on public.sv_peerconsults
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_peerconsults from service_role;
grant select, insert, update on public.sv_peerconsults to service_role;

-- Pet-insurance claims.
create table if not exists public.sv_petinsurance (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  petinsurance_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, petinsurance_id),
  constraint sv_petinsurance_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_petinsurance enable row level security;
drop policy if exists "svc only sv_petinsurance" on public.sv_petinsurance;
create policy "svc only sv_petinsurance" on public.sv_petinsurance
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_petinsurance from service_role;
grant select, insert, update on public.sv_petinsurance to service_role;

-- Client-portal requests.
create table if not exists public.sv_portal (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  portal_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, portal_id),
  constraint sv_portal_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_portal enable row level security;
drop policy if exists "svc only sv_portal" on public.sv_portal;
create policy "svc only sv_portal" on public.sv_portal
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_portal from service_role;
grant select, insert, update on public.sv_portal to service_role;

-- Pre-purchase examinations.
create table if not exists public.sv_prepurchase (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  prepurchase_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, prepurchase_id),
  constraint sv_prepurchase_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_prepurchase enable row level security;
drop policy if exists "svc only sv_prepurchase" on public.sv_prepurchase;
create policy "svc only sv_prepurchase" on public.sv_prepurchase
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_prepurchase from service_role;
grant select, insert, update on public.sv_prepurchase to service_role;

-- Referrals.
create table if not exists public.sv_referrals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  referral_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, referral_id),
  constraint sv_referrals_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_referrals enable row level security;
drop policy if exists "svc only sv_referrals" on public.sv_referrals;
create policy "svc only sv_referrals" on public.sv_referrals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_referrals from service_role;
grant select, insert, update on public.sv_referrals to service_role;

-- Reminders.
create table if not exists public.sv_reminders (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  reminder_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, reminder_id),
  constraint sv_reminders_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_reminders enable row level security;
drop policy if exists "svc only sv_reminders" on public.sv_reminders;
create policy "svc only sv_reminders" on public.sv_reminders
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_reminders from service_role;
grant select, insert, update on public.sv_reminders to service_role;

-- Saved report definitions.
create table if not exists public.sv_reports (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  report_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, report_id),
  constraint sv_reports_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_reports enable row level security;
drop policy if exists "svc only sv_reports" on public.sv_reports;
create policy "svc only sv_reports" on public.sv_reports
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_reports from service_role;
grant select, insert, update on public.sv_reports to service_role;

-- Reproduction records.
create table if not exists public.sv_reproduction (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  reproduction_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, reproduction_id),
  constraint sv_reproduction_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_reproduction enable row level security;
drop policy if exists "svc only sv_reproduction" on public.sv_reproduction;
create policy "svc only sv_reproduction" on public.sv_reproduction
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_reproduction from service_role;
grant select, insert, update on public.sv_reproduction to service_role;

-- Appointments.
create table if not exists public.sv_scheduling (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  scheduling_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, scheduling_id),
  constraint sv_scheduling_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_scheduling enable row level security;
drop policy if exists "svc only sv_scheduling" on public.sv_scheduling;
create policy "svc only sv_scheduling" on public.sv_scheduling
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_scheduling from service_role;
grant select, insert, update on public.sv_scheduling to service_role;

-- SOAP notes -- the clinical record.
create table if not exists public.sv_soapnotes (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  soapnote_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, soapnote_id),
  constraint sv_soapnotes_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_soapnotes enable row level security;
drop policy if exists "svc only sv_soapnotes" on public.sv_soapnotes;
create policy "svc only sv_soapnotes" on public.sv_soapnotes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_soapnotes from service_role;
grant select, insert, update on public.sv_soapnotes to service_role;

-- Species reference ranges, editable by the clinic.
create table if not exists public.sv_speciesref (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  speciesref_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, speciesref_id),
  constraint sv_speciesref_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_speciesref enable row level security;
drop policy if exists "svc only sv_speciesref" on public.sv_speciesref;
create policy "svc only sv_speciesref" on public.sv_speciesref
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_speciesref from service_role;
grant select, insert, update on public.sv_speciesref to service_role;

-- Staff roster.
create table if not exists public.sv_staff (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  staff_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, staff_id),
  constraint sv_staff_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_staff enable row level security;
drop policy if exists "svc only sv_staff" on public.sv_staff;
create policy "svc only sv_staff" on public.sv_staff
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_staff from service_role;
grant select, insert, update on public.sv_staff to service_role;

-- Surgeries.
create table if not exists public.sv_surgery (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  surgery_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, surgery_id),
  constraint sv_surgery_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_surgery enable row level security;
drop policy if exists "svc only sv_surgery" on public.sv_surgery;
create policy "svc only sv_surgery" on public.sv_surgery
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_surgery from service_role;
grant select, insert, update on public.sv_surgery to service_role;

-- Teleconsults.
create table if not exists public.sv_teleconsults (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  teleconsult_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, teleconsult_id),
  constraint sv_teleconsults_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_teleconsults enable row level security;
drop policy if exists "svc only sv_teleconsults" on public.sv_teleconsults;
create policy "svc only sv_teleconsults" on public.sv_teleconsults
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_teleconsults from service_role;
grant select, insert, update on public.sv_teleconsults to service_role;

-- Vitals.
create table if not exists public.sv_vitals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  vital_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vital_id),
  constraint sv_vitals_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_vitals enable row level security;
drop policy if exists "svc only sv_vitals" on public.sv_vitals;
create policy "svc only sv_vitals" on public.sv_vitals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_vitals from service_role;
grant select, insert, update on public.sv_vitals to service_role;

-- Wellness plans.
create table if not exists public.sv_wellness (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  wellness_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, wellness_id),
  constraint sv_wellness_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_wellness enable row level security;
drop policy if exists "svc only sv_wellness" on public.sv_wellness;
create policy "svc only sv_wellness" on public.sv_wellness
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_wellness from service_role;
grant select, insert, update on public.sv_wellness to service_role;

-- Treatment whiteboard.
create table if not exists public.sv_whiteboard (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  whiteboard_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, whiteboard_id),
  constraint sv_whiteboard_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_whiteboard enable row level security;
drop policy if exists "svc only sv_whiteboard" on public.sv_whiteboard;
create policy "svc only sv_whiteboard" on public.sv_whiteboard
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_whiteboard from service_role;
grant select, insert, update on public.sv_whiteboard to service_role;

-- Wildlife rehabilitation cases.
create table if not exists public.sv_wildliferehab (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnvet',
  wildliferehab_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, wildliferehab_id),
  constraint sv_wildliferehab_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sv_wildliferehab enable row level security;
drop policy if exists "svc only sv_wildliferehab" on public.sv_wildliferehab;
create policy "svc only sv_wildliferehab" on public.sv_wildliferehab
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sv_wildliferehab from service_role;
grant select, insert, update on public.sv_wildliferehab to service_role;

grant usage on schema public to service_role;
