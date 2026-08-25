-- sql/sairnscape_data_schema_phase2.sql
-- SAIRNscape application data, PHASE 2 -- Supabase schema
--
-- NEW FILE, separate from sql/sairnscape_data_schema.sql (which Michael is
-- already running as of 2026-08-06). Run this AFTER the original file, as a
-- second step, not instead of it -- same relationship as
-- sql/sairngrounds_data_schema_phase2.sql to its own original (see that
-- file's header for the full sweep rationale; this file is the SAIRNscape
-- half of the same six shared resources).
--
-- WHAT THIS CLOSES: scp_designs had no route at all. scp_irr_controllers,
-- scp_irr_zones, scp_irr_schedules, scp_water_features, and scp_vendors
-- were all being called with BARE resource names ('irr_controllers',
-- 'irr_zones', 'irr_schedules', 'water_features', 'vendors') that collided
-- with SAIRNgrounds' identical bare calls -- same bug class as grd_schedule
-- (sql/sairngrounds_data_schema.sql), just never caught until this sweep
-- because neither side had a route yet, so both sides just 400'd
-- identically and looked "consistently broken" rather than "colliding."
--
-- KEYING: license_hash = sha256(license_key). Two shapes, same as the
-- SAIRNgrounds phase 2 file:
--   TYPE A (customer-scoped list): scp_designs, scp_irr_controllers,
--     scp_irr_zones, scp_water_features (customer_id parent) and
--     scp_irr_schedules (zone_id parent, confirmed by reading
--     scpSaveIrrSched()'s actual payload shape before designing this).
--   TYPE B (account-wide list): scp_vendors -- confirmed no customer_id in
--     the client's actual rec shape (saveVendor() in sairnscape.html).
--
-- SECURITY MODEL / SIZE CAP: identical to every other table in this
-- platform's sd-data.js-backed schema files -- service-role only RLS, 64KB
-- jsonb cap (api/sd-data.js's uniform MAX_PAYLOAD_BYTES).

create extension if not exists pgcrypto;

create table if not exists public.scp_designs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  design_id    text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- elements[], approved, approved_by, approved_at, quote_id
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, design_id),
  constraint scpdes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpdes_license on public.scp_designs(license_hash);

create table if not exists public.scp_irr_controllers (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnscape',
  controller_id text not null,
  customer_id   text not null,
  data          jsonb not null default '{}'::jsonb,    -- name, brand, model, zones_supported, install_date, notes
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, controller_id),
  constraint scpctl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpctl_license on public.scp_irr_controllers(license_hash);

create table if not exists public.scp_irr_zones (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  zone_id      text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, zone_type, controller_id, station, head_count, sqft, linear_ft, status, last_service, backflow, checklist[], notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, zone_id),
  constraint scpiz_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpiz_license on public.scp_irr_zones(license_hash);

-- Type A-variant: parented by zone_id, not customer_id -- matches grounds'
-- grd_irr_schedules shape exactly.
create table if not exists public.scp_irr_schedules (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  irrsched_id  text not null,
  zone_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- days[], start, duration, status
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, irrsched_id),
  constraint scpisch_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpisch_license_zone on public.scp_irr_schedules(license_hash, zone_id);

create table if not exists public.scp_water_features (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  feature_id   text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, type, scale, size, pump, filter, last_service, condition, checklist[]
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, feature_id),
  constraint scpwf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpwf_license on public.scp_water_features(license_hash);

create table if not exists public.scp_vendors (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  vendor_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, category, contact, phone, email, terms, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, vendor_id),
  constraint scpvend_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpvend_license on public.scp_vendors(license_hash);

-- === RLS: service-role only ================================================
alter table public.scp_designs         enable row level security;
alter table public.scp_irr_controllers enable row level security;
alter table public.scp_irr_zones       enable row level security;
alter table public.scp_irr_schedules   enable row level security;
alter table public.scp_water_features  enable row level security;
alter table public.scp_vendors         enable row level security;

drop policy if exists "svc only scp_designs"         on public.scp_designs;
drop policy if exists "svc only scp_irr_controllers" on public.scp_irr_controllers;
drop policy if exists "svc only scp_irr_zones"       on public.scp_irr_zones;
drop policy if exists "svc only scp_irr_schedules"   on public.scp_irr_schedules;
drop policy if exists "svc only scp_water_features"  on public.scp_water_features;
drop policy if exists "svc only scp_vendors"         on public.scp_vendors;

create policy "svc only scp_designs" on public.scp_designs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_irr_controllers" on public.scp_irr_controllers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_irr_zones" on public.scp_irr_zones
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_irr_schedules" on public.scp_irr_schedules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_water_features" on public.scp_water_features
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_vendors" on public.scp_vendors
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- DELETE REMOVED FROM ALL SIX LINES 2026-08-25, for the same reason and in
-- the same pass as sql/sairnscape_data_schema.sql's six. This is the THIRD
-- SAIRNscape file carrying the 2026-08-06 overcorrection, not the second:
-- sql/unused_delete_grant_revoke_2026-08-24.sql's header scoped the
-- signature at "2 files, both SAIRNscape, 7 grants" and this file was
-- missed. It is 3 files and 13 grants -- scp_employee_auth (1),
-- sairnscape_data_schema (6), and these 6.
--
-- All six of these tables had DELETE revoked live on 2026-08-25 by that
-- sweep, so until this edit the file and the database disagreed and any
-- routine re-run of this `create table if not exists` file would have
-- silently restored them. SAIRNscape has no delete path; the platform's
-- only DELETE is api/sd-data.js's SC_RESOURCES (SAIRNcode) branch.
grant usage on schema public to service_role;
grant select, insert, update on public.scp_designs         to service_role;
grant select, insert, update on public.scp_irr_controllers to service_role;
grant select, insert, update on public.scp_irr_zones       to service_role;
grant select, insert, update on public.scp_irr_schedules   to service_role;
grant select, insert, update on public.scp_water_features  to service_role;
grant select, insert, update on public.scp_vendors         to service_role;
