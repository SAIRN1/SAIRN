-- sql/sairndental_data_schema.sql
-- SAIRNdental application data -- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's 12
-- dnt_-prefixed resources will work for SAIRNdental. Every statement is
-- idempotent (create table if not exists), safe to re-run.
--
-- Same generic jsonb-blob pattern as every prior app's schema file
-- (sql/sairnlegacy_data_schema.sql is the direct template): license_hash
-- + app_id + <resource>_id + data jsonb + created_at/updated_at,
-- unique(license_hash, <resource>_id), 64KB size cap matching
-- api/sd-data.js's uniform MAX_PAYLOAD_BYTES. Service-role only, RLS
-- enabled with no anon policy -- api/sd-data.js is the only door in.
--
-- NAMING: dnt_ prefix on every resource, checked for collision against
-- every other app's resource names in api/sd-data.js before this file
-- was written (none found).
--
-- ID COLUMN NAMING: mechanical singularization of each resource name
-- (strip dnt_, strip a trailing 's'), same rule sairnlegacy's schema
-- documents and applies uniformly rather than a bespoke name per table.
--
-- NOTE ON sc_denial/sc_ar/sc_revenue (design spec §2, §6): SAIRNcode's
-- resources of those names are reused for their DATA SHAPE and KPI math
-- only. The actual storage-key names here are dnt_denial/dnt_ar/
-- dnt_revenue -- a genuinely separate namespace on the shared backend,
-- not a shared table with SAIRNcode. Reusing SAIRNcode's literal
-- sc_denial/sc_ar/sc_revenue resource strings for a different app_id
-- would be exactly the resource-name-collision bug class this
-- platform has been bitten by before (see api/sd-data.js's own header
-- on grd_schedule/scp_progress_photos).

create extension if not exists pgcrypto;

create table if not exists public.dnt_patients (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  patient_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, patient_id), constraint dntpt_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntpt_license on public.dnt_patients(license_hash);

create table if not exists public.dnt_providers (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  provider_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, provider_id), constraint dntpv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntpv_license on public.dnt_providers(license_hash);

create table if not exists public.dnt_operatories (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  operatory_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, operatory_id), constraint dntop_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntop_license on public.dnt_operatories(license_hash);

create table if not exists public.dnt_provider_hours (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  provider_hour_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, provider_hour_id), constraint dntph_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntph_license on public.dnt_provider_hours(license_hash);

create table if not exists public.dnt_procedure_types (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  procedure_type_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, procedure_type_id), constraint dntpc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntpc_license on public.dnt_procedure_types(license_hash);

create table if not exists public.dnt_coverage_rules (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  coverage_rule_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, coverage_rule_id), constraint dntcv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntcv_license on public.dnt_coverage_rules(license_hash);

create table if not exists public.dnt_appointments (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  appointment_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, appointment_id),
  -- 1291059 = MAX_PHOTOS_PAYLOAD_BYTES (1258291) + 32768 for notes, fixed
  -- fields and JSON overhead. NOT 64KiB like the other dnt_ tables: this is
  -- the only one on the patient photo-upload path, and a real booking with
  -- photos is ~19x over 64KiB. Derivation and the safe ALTER for existing
  -- databases: sql/sairndental_appointments_photo_size_migration.sql
  constraint dntap_data_size check (octet_length(data::text) <= 1291059)
);
create index if not exists idx_dntap_license on public.dnt_appointments(license_hash);

create table if not exists public.dnt_charges (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  charge_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, charge_id), constraint dntch_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntch_license on public.dnt_charges(license_hash);

create table if not exists public.dnt_payments (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  payment_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, payment_id), constraint dntpm_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntpm_license on public.dnt_payments(license_hash);

create table if not exists public.dnt_denial (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  denial_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, denial_id), constraint dntdn_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntdn_license on public.dnt_denial(license_hash);

create table if not exists public.dnt_ar (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  ar_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, ar_id), constraint dntar_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntar_license on public.dnt_ar(license_hash);

create table if not exists public.dnt_revenue (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  revenue_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, revenue_id), constraint dntrv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntrv_license on public.dnt_revenue(license_hash);

-- ── RLS: service-role only (mirror sairnlegacy_data_schema.sql) ──
do $$
declare t text;
begin
  for t in select unnest(array[
    'dnt_patients','dnt_providers','dnt_operatories','dnt_provider_hours','dnt_procedure_types',
    'dnt_coverage_rules','dnt_appointments','dnt_charges','dnt_payments','dnt_denial','dnt_ar','dnt_revenue'
  ])
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', 'svc only ' || t, t);
    execute format(
      'create policy %I on public.%I for all using (auth.role() = ''service_role'') with check (auth.role() = ''service_role'')',
      'svc only ' || t, t
    );
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

grant usage on schema public to service_role;
