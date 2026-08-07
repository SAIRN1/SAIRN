-- sql/sairnlegacy_data_schema.sql
-- SAIRNlegacy application data — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's 36
-- leg_-prefixed resources will work for SAIRNlegacy. Every statement is
-- idempotent (create table if not exists), safe to re-run.
--
-- WHY THIS FILE EXISTS (2026-08-07): same root gap as SAIRNdesign hit and
-- fixed the same day. SAIRNlegacy's client (sairnlegacy.html) calls the
-- shared sdnData() helper -- the same generically-named function every
-- SAIRN app's client copies verbatim (it is not literally scoped to
-- "SAIRNdesign"; "sdn" is this platform's shared data-sync-helper name,
-- confirmed by checking sairnlegacy.html directly: the function is
-- defined and called as sdnData() there too, unrenamed) -- at 55 call
-- sites across all 26 panels, using leg_-prefixed resource names
-- throughout (unlike SAIRNdesign, which called bare names and needed
-- retrofitting -- SAIRNlegacy's client already used the leg_ prefix from
-- Phase 1 onward, so no client-side resource renaming was needed for this
-- fix, only the missing backend half). None of those 36 resource names
-- were ever registered in api/sd-data.js's RESOURCES map, so every write
-- has been silently 400ing and falling back to local-only storage since
-- Phase 1 -- confirmed via a live curl returning "resource must be one
-- of: ..." with no leg_ entries present, and via a direct read of
-- api/sd-data.js showing zero "leg_" occurrences before this fix.
--
-- NAMING: every table/resource here is prefixed leg_. No collision check
-- against other apps' resource names was needed the way SAIRNdesign's
-- sdn_ vs bare 'schedule'/'invoices' was -- 'leg_' was not claimed by any
-- other app's RESOURCES entries before this file (confirmed by grep),
-- so there is no equivalent of that near-miss here. Still using a
-- distinct prefix on every resource for the same forward-looking
-- consistency reason: a mixed "prefix only where something already
-- collides" scheme is a landmine for the next resource added to any app.
--
-- ID COLUMN NAMING: mechanical singularization of each resource name
-- (strip leg_, strip a trailing 's'/'es'/'ies'→'y'), not a bespoke name
-- per table. This is a large surface (36 tables) where a fully manual
-- naming pass for each one would have cost more than it returned -- the
-- id column name has no functional effect on the client (only
-- api/sd-data.js's generic LEG_RESOURCES lookup table references it, and
-- that lookup is what actually ties each resource string to its column),
-- so a uniform mechanical rule here is a deliberate simplification, not
-- an oversight. Logged as the judgment call it is.
--
-- SCOPING COLUMNS: no table carries a required parent-id column (the same
-- simplification sql/sairndesign_data_schema.sql already used and
-- explained) -- SAIRNlegacy has no server-side filtered read anywhere;
-- every client read is "give me the whole array for this license,"
-- filtered client-side after. The parent id (case_id, vehicle_id,
-- whichever applies) already lives inside each row's own `data` jsonb.
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables. app_id is stamped 'sairnlegacy' explicitly on every write.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy --
-- same as every table in sql/stonedesk_data_schema.sql and
-- sql/sairndesign_data_schema.sql. api/sd-data.js is the only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES (no useful per-resource override at the DB layer).

create extension if not exists pgcrypto;

create table if not exists public.leg_aftercare (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  aftercare_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, aftercare_id), constraint legac_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legac_license on public.leg_aftercare(license_hash);

create table if not exists public.leg_bookings (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  booking_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, booking_id), constraint legbk_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legbk_license on public.leg_bookings(license_hash);

create table if not exists public.leg_cases (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  case_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, case_id), constraint legcs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcs_license on public.leg_cases(license_hash);

create table if not exists public.leg_catererorders (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  catererorder_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, catererorder_id), constraint legcao_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcao_license on public.leg_catererorders(license_hash);

create table if not exists public.leg_caterers (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  caterer_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, caterer_id), constraint legca_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legca_license on public.leg_caterers(license_hash);

create table if not exists public.leg_certs (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  cert_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, cert_id), constraint legct_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legct_license on public.leg_certs(license_hash);

create table if not exists public.leg_clergy (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  clergy_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, clergy_id), constraint legcg_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcg_license on public.leg_clergy(license_hash);

create table if not exists public.leg_clergybookings (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  clergybooking_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, clergybooking_id), constraint legcgb_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcgb_license on public.leg_clergybookings(license_hash);

create table if not exists public.leg_cremations (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  cremation_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, cremation_id), constraint legcr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcr_license on public.leg_cremations(license_hash);

create table if not exists public.leg_custodylog (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  custodylog_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, custodylog_id), constraint legcl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legcl_license on public.leg_custodylog(license_hash);

create table if not exists public.leg_deathrecords (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  deathrecord_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, deathrecord_id), constraint legdr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legdr_license on public.leg_deathrecords(license_hash);

create table if not exists public.leg_dispatches (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  dispatch_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, dispatch_id), constraint legds_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legds_license on public.leg_dispatches(license_hash);

create table if not exists public.leg_documents (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  document_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, document_id), constraint legdc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legdc_license on public.leg_documents(license_hash);

create table if not exists public.leg_facilities (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  facility_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, facility_id), constraint legfc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legfc_license on public.leg_facilities(license_hash);

create table if not exists public.leg_floristorders (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  floristorder_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, floristorder_id), constraint legfo_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legfo_license on public.leg_floristorders(license_hash);

create table if not exists public.leg_florists (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  florist_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, florist_id), constraint legfl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legfl_license on public.leg_florists(license_hash);

create table if not exists public.leg_gplservices (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  gplservice_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, gplservice_id), constraint leggp_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_leggp_license on public.leg_gplservices(license_hash);

create table if not exists public.leg_guestbook (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  guestbook_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, guestbook_id), constraint leggb_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_leggb_license on public.leg_guestbook(license_hash);

create table if not exists public.leg_insurance (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  insurance_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, insurance_id), constraint legin_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legin_license on public.leg_insurance(license_hash);

create table if not exists public.leg_invoices (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  invoice_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, invoice_id), constraint legiv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legiv_license on public.leg_invoices(license_hash);

create table if not exists public.leg_keepsakeorders (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  keepsakeorder_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, keepsakeorder_id), constraint legko_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legko_license on public.leg_keepsakeorders(license_hash);

create table if not exists public.leg_keepsakes (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  keepsake_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, keepsake_id), constraint legks_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legks_license on public.leg_keepsakes(license_hash);

create table if not exists public.leg_liverybookings (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  liverybooking_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, liverybooking_id), constraint leglb_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_leglb_license on public.leg_liverybookings(license_hash);

create table if not exists public.leg_liveryvendors (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  liveryvendor_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, liveryvendor_id), constraint leglv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_leglv_license on public.leg_liveryvendors(license_hash);

create table if not exists public.leg_maintenance (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  maintenance_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, maintenance_id), constraint legmt_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legmt_license on public.leg_maintenance(license_hash);

create table if not exists public.leg_memorials (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  memorial_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, memorial_id), constraint legmm_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legmm_license on public.leg_memorials(license_hash);

create table if not exists public.leg_merch_catalog (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  merch_catalog_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, merch_catalog_id), constraint legmc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legmc_license on public.leg_merch_catalog(license_hash);

create table if not exists public.leg_merch_units (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  merch_unit_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, merch_unit_id), constraint legmu_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legmu_license on public.leg_merch_units(license_hash);

create table if not exists public.leg_monuments (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  monument_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, monument_id), constraint legmn_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legmn_license on public.leg_monuments(license_hash);

create table if not exists public.leg_obituaries (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  obituary_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, obituary_id), constraint legob_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legob_license on public.leg_obituaries(license_hash);

create table if not exists public.leg_petcases (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  petcase_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, petcase_id), constraint legpt_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legpt_license on public.leg_petcases(license_hash);

create table if not exists public.leg_plots (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  plot_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, plot_id), constraint legpl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legpl_license on public.leg_plots(license_hash);

create table if not exists public.leg_preneed (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  preneed_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, preneed_id), constraint legpn_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legpn_license on public.leg_preneed(license_hash);

create table if not exists public.leg_processions (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  procession_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, procession_id), constraint legpr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legpr_license on public.leg_processions(license_hash);

create table if not exists public.leg_tributes (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  tribute_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, tribute_id), constraint legtr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legtr_license on public.leg_tributes(license_hash);

create table if not exists public.leg_vehicles (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairnlegacy',
  vehicle_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, vehicle_id), constraint legvh_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_legvh_license on public.leg_vehicles(license_hash);

-- ── RLS: service-role only (mirror stonedesk_data_schema.sql / sairndesign_data_schema.sql) ──
do $$
declare t text;
begin
  for t in select unnest(array[
    'leg_aftercare','leg_bookings','leg_cases','leg_catererorders','leg_caterers','leg_certs','leg_clergy',
    'leg_clergybookings','leg_cremations','leg_custodylog','leg_deathrecords','leg_dispatches','leg_documents',
    'leg_facilities','leg_floristorders','leg_florists','leg_gplservices','leg_guestbook','leg_insurance',
    'leg_invoices','leg_keepsakeorders','leg_keepsakes','leg_liverybookings','leg_liveryvendors','leg_maintenance',
    'leg_memorials','leg_merch_catalog','leg_merch_units','leg_monuments','leg_obituaries','leg_petcases',
    'leg_plots','leg_preneed','leg_processions','leg_tributes','leg_vehicles'
  ])
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %L on public.%I', 'svc only ' || t, t);
    execute format(
      'create policy %L on public.%I for all using (auth.role() = ''service_role'') with check (auth.role() = ''service_role'')',
      'svc only ' || t, t
    );
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
  end loop;
end $$;

grant usage on schema public to service_role;
