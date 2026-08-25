-- sql/sairngrounds_data_schema_phase2.sql
-- SAIRNgrounds application data, PHASE 2 -- Supabase schema
--
-- NEW FILE, separate from sql/sairngrounds_data_schema.sql (which Michael is
-- already running as of 2026-08-06). This file is everything the full
-- resource-name sweep found beyond that one: run this AFTER the original
-- file, as a second step, not instead of it. Both files are idempotent
-- (create table if not exists) so order between the two doesn't matter for
-- safety, but the original file's tables (grd_properties, grd_schedule,
-- grd_progress_photos, grd_invoices, grd_dreamclose, etc.) are NOT
-- duplicated here -- this file is purely additive.
--
-- WHAT THIS CLOSES: every one of these resources has been calling
-- grdData('write', <resource>, ...) with either (a) no matching route in
-- api/sd-data.js at all, or (b) a bare resource name that collided with
-- SAIRNscape's identically-named resource (see sql/sairngrounds_data_schema.sql's
-- own header for the first three examples of this exact bug class:
-- grd_schedule, grd_invoices, grd_dreamclose). Every one of them has been
-- localStorage-only, on this device, since it shipped.
--
-- KEYING: license_hash = sha256(license_key). Two shapes used here:
--   TYPE A (property-scoped list): has its own <resource>_id plus a
--     property_id (or, for irr_schedules, a zone_id) column so records can
--     be filtered/joined by their real parent -- same shape as
--     grd_properties/grd_jobs/grd_schedule etc.
--   TYPE B (account-wide list): license-scoped only, no parent column --
--     used where the client code itself never scopes these by property
--     (Merchandise/Bar module, training, vendors, BOQ rates -- confirmed by
--     reading every actual payload shape client-side before writing this,
--     not assumed from the resource name).
--   TYPE C (single config row per license): msb_sale_hours only -- the
--     client sends the WHOLE 7-day array as one payload with no per-record
--     id, same shape as sd_shared_knowledge's one-row-per-license pattern.
--
-- MSB_* NAMING: kept as msb_* (not grd_msb_*) deliberately -- the
-- Merchandise/Bar module's own in-app comment states it's built
-- app-agnostic on purpose, ready to spin out into SAIRNspirits/a restaurant
-- app later by copying the block wholesale. It's SAIRNgrounds-only today
-- (SAIRNscape has no msb_* calls, confirmed by grep), so there is zero
-- collision risk right now, and adding a grd_ prefix now would work against
-- that stated spin-out design for no real benefit today.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- same as
-- every table in sql/sairngrounds_data_schema.sql. api/sd-data.js is the
-- only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES (not per-resource-overridable -- see that constant's
-- own comment in api/sd-data.js).

create extension if not exists pgcrypto;

-- === TYPE A: property-scoped lists ==========================================

create table if not exists public.grd_invasive_sightings (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  sighting_id  text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- species, location, found, severity, status, reportable, method, scheduled, treated, outcome, report_filed, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, sighting_id),
  constraint grdiv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdiv_license on public.grd_invasive_sightings(license_hash);

create table if not exists public.grd_ecosystem_reports (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  report_id    text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- date, summary (7-layer report text)
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, report_id),
  constraint grdeco_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdeco_license on public.grd_ecosystem_reports(license_hash);

create table if not exists public.grd_designs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  design_id    text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- elements[], approved, approved_by, approved_at, quote_id
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, design_id),
  constraint grddes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grddes_license on public.grd_designs(license_hash);

create table if not exists public.grd_irr_controllers (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  controller_id text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, brand, model, zones_supported, install_date, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, controller_id),
  constraint grdctl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdctl_license on public.grd_irr_controllers(license_hash);

create table if not exists public.grd_irr_zones (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  zone_id      text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, zone_type, controller_id, station, head_count, sqft, linear_ft, status, last_service, backflow, checklist[], notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, zone_id),
  constraint grdiz_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdiz_license on public.grd_irr_zones(license_hash);

-- Type A-variant: parented by zone_id (an irr_zones record), not property_id
-- directly -- matches the client's own rec shape ({id, zone_id, days, start,
-- duration, status}), confirmed by reading saveIrrSched() before designing this.
create table if not exists public.grd_irr_schedules (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  irrsched_id  text not null,
  zone_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- days[], start, duration, status
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, irrsched_id),
  constraint grdisch_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdisch_license_zone on public.grd_irr_schedules(license_hash, zone_id);

create table if not exists public.grd_water_features (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  feature_id   text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, type, scale, size, pump, filter, last_service, condition, checklist[]
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, feature_id),
  constraint grdwf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdwf_license on public.grd_water_features(license_hash);

-- === TYPE B: account-wide lists (no property/customer parent) ==============

create table if not exists public.grd_training_courses (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  course_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- title, category, duration, required
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, course_id),
  constraint grdcrs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdcrs_license on public.grd_training_courses(license_hash);

create table if not exists public.grd_training_completions (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  completion_id text not null,
  data         jsonb not null default '{}'::jsonb,    -- employee_name, course_id, status, completed_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, completion_id),
  constraint grdcpl_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdcpl_license on public.grd_training_completions(license_hash);

create table if not exists public.grd_boq_rates (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  rate_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- item_type, brand, unit, rate, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, rate_id),
  constraint grdboq_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdboq_license on public.grd_boq_rates(license_hash);

create table if not exists public.grd_vendors (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  vendor_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, category, contact, phone, email, terms, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, vendor_id),
  constraint grdvend_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdvend_license on public.grd_vendors(license_hash);

-- === TYPE B: Merchandise/Bar module (item 9), msb_* naming preserved =======

create table if not exists public.msb_products (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  product_id   text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, category, sku, price, cost, qty, reorder, bottle_oz
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, product_id),
  constraint msbprod_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbprod_license on public.msb_products(license_hash);

create table if not exists public.msb_sales (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  sale_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- cart_type, items[], total, payment, age_verified, employee, timestamp, voided, void_reason, void_by, void_role
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, sale_id),
  constraint msbsale_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbsale_license on public.msb_sales(license_hash);

create table if not exists public.msb_licenses (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  msblicense_id text not null,
  data         jsonb not null default '{}'::jsonb,    -- state, permit_type, number, issued, expiry, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, msblicense_id),
  constraint msblic_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msblic_license on public.msb_licenses(license_hash);

-- Append-only by construction on the client (msbLogInventoryChange never
-- edits or deletes an existing row) -- the table itself doesn't need to
-- enforce that; it's a real, disclosed limitation that durability still
-- depends on this table actually being provisioned, same as the client
-- comment on msbLogInventoryChange already states.
create table if not exists public.msb_inventory_log (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  log_id       text not null,
  data         jsonb not null default '{}'::jsonb,    -- product_id, product_name, change_type, qty_delta, employee, note, timestamp
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, log_id),
  constraint msbinvlog_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbinvlog_license on public.msb_inventory_log(license_hash);

create table if not exists public.msb_bottle_scans (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  scan_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- product_id, brand_read, fill_pct, date, note
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, scan_id),
  constraint msbbscan_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbbscan_license on public.msb_bottle_scans(license_hash);

create table if not exists public.msb_food_scans (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  foodscan_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- date, items[], raw
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, foodscan_id),
  constraint msbfscan_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbfscan_license on public.msb_food_scans(license_hash);

create table if not exists public.msb_food_waste (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  waste_id     text not null,
  data         jsonb not null default '{}'::jsonb,    -- item, cost, reason, date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, waste_id),
  constraint msbwaste_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbwaste_license on public.msb_food_waste(license_hash);

create table if not exists public.msb_food_cost_log (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  costlog_id   text not null,
  data         jsonb not null default '{}'::jsonb,    -- amount, date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, costlog_id),
  constraint msbcost_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_msbcost_license on public.msb_food_cost_log(license_hash);

-- Type C: one row per license, whole 7-day array as the payload, no
-- per-record id -- matches saveMsbHours()'s actual client call
-- (grdData('write','msb_sale_hours', hours) where hours is the full array,
-- not a single record).
create table if not exists public.msb_sale_hours (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  data         jsonb not null default '{}'::jsonb,    -- the full 7-day [{day,start,end}] array
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash),
  constraint msbhours_data_size check (octet_length(data::text) <= 65536)
);

-- === RLS: service-role only ================================================
alter table public.grd_invasive_sightings   enable row level security;
alter table public.grd_ecosystem_reports    enable row level security;
alter table public.grd_designs              enable row level security;
alter table public.grd_irr_controllers      enable row level security;
alter table public.grd_irr_zones            enable row level security;
alter table public.grd_irr_schedules        enable row level security;
alter table public.grd_water_features       enable row level security;
alter table public.grd_training_courses     enable row level security;
alter table public.grd_training_completions enable row level security;
alter table public.grd_boq_rates            enable row level security;
alter table public.grd_vendors              enable row level security;
alter table public.msb_products             enable row level security;
alter table public.msb_sales                enable row level security;
alter table public.msb_licenses             enable row level security;
alter table public.msb_inventory_log        enable row level security;
alter table public.msb_bottle_scans         enable row level security;
alter table public.msb_food_scans           enable row level security;
alter table public.msb_food_waste           enable row level security;
alter table public.msb_food_cost_log        enable row level security;
alter table public.msb_sale_hours           enable row level security;

drop policy if exists "svc only grd_invasive_sightings"   on public.grd_invasive_sightings;
drop policy if exists "svc only grd_ecosystem_reports"    on public.grd_ecosystem_reports;
drop policy if exists "svc only grd_designs"              on public.grd_designs;
drop policy if exists "svc only grd_irr_controllers"      on public.grd_irr_controllers;
drop policy if exists "svc only grd_irr_zones"            on public.grd_irr_zones;
drop policy if exists "svc only grd_irr_schedules"        on public.grd_irr_schedules;
drop policy if exists "svc only grd_water_features"       on public.grd_water_features;
drop policy if exists "svc only grd_training_courses"     on public.grd_training_courses;
drop policy if exists "svc only grd_training_completions" on public.grd_training_completions;
drop policy if exists "svc only grd_boq_rates"             on public.grd_boq_rates;
drop policy if exists "svc only grd_vendors"               on public.grd_vendors;
drop policy if exists "svc only msb_products"              on public.msb_products;
drop policy if exists "svc only msb_sales"                 on public.msb_sales;
drop policy if exists "svc only msb_licenses"              on public.msb_licenses;
drop policy if exists "svc only msb_inventory_log"         on public.msb_inventory_log;
drop policy if exists "svc only msb_bottle_scans"          on public.msb_bottle_scans;
drop policy if exists "svc only msb_food_scans"            on public.msb_food_scans;
drop policy if exists "svc only msb_food_waste"            on public.msb_food_waste;
drop policy if exists "svc only msb_food_cost_log"         on public.msb_food_cost_log;
drop policy if exists "svc only msb_sale_hours"            on public.msb_sale_hours;

create policy "svc only grd_invasive_sightings" on public.grd_invasive_sightings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_ecosystem_reports" on public.grd_ecosystem_reports
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_designs" on public.grd_designs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_irr_controllers" on public.grd_irr_controllers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_irr_zones" on public.grd_irr_zones
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_irr_schedules" on public.grd_irr_schedules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_water_features" on public.grd_water_features
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_training_courses" on public.grd_training_courses
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_training_completions" on public.grd_training_completions
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_boq_rates" on public.grd_boq_rates
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_vendors" on public.grd_vendors
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_products" on public.msb_products
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_sales" on public.msb_sales
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_licenses" on public.msb_licenses
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_inventory_log" on public.msb_inventory_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_bottle_scans" on public.msb_bottle_scans
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_food_scans" on public.msb_food_scans
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_food_waste" on public.msb_food_waste
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_food_cost_log" on public.msb_food_cost_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only msb_sale_hours" on public.msb_sale_hours
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.grd_invasive_sightings   to service_role;
grant select, insert, update on public.grd_ecosystem_reports    to service_role;
grant select, insert, update on public.grd_designs              to service_role;
grant select, insert, update on public.grd_irr_controllers      to service_role;
grant select, insert, update on public.grd_irr_zones            to service_role;
grant select, insert, update on public.grd_irr_schedules        to service_role;
grant select, insert, update on public.grd_water_features       to service_role;
grant select, insert, update on public.grd_training_courses     to service_role;
grant select, insert, update on public.grd_training_completions to service_role;
grant select, insert, update on public.grd_boq_rates            to service_role;
grant select, insert, update on public.grd_vendors              to service_role;
grant select, insert, update on public.msb_products             to service_role;
grant select, insert, update on public.msb_sales                to service_role;
grant select, insert, update on public.msb_licenses             to service_role;
grant select, insert, update on public.msb_inventory_log        to service_role;
grant select, insert, update on public.msb_bottle_scans         to service_role;
grant select, insert, update on public.msb_food_scans           to service_role;
grant select, insert, update on public.msb_food_waste           to service_role;
grant select, insert, update on public.msb_food_cost_log        to service_role;
grant select, insert, update on public.msb_sale_hours           to service_role;
