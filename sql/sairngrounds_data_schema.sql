-- sql/sairngrounds_data_schema.sql
-- SAIRNgrounds application data — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- properties/jobs/quotes/golf_zones/grd_schedule/grd_progress_photos/
-- grd_invoices/grd_dreamclose resources will work for SAIRNgrounds.
-- If you already ran an earlier version of this file (before
-- grd_invoices/grd_dreamclose existed), re-running this version is safe --
-- every statement is idempotent (create table if not exists) and only adds
-- the two new tables. Until this runs, sairngrounds.html
-- falls back to its existing Phase 1 localStorage-only behavior (see
-- SAIRNGROUNDS-SCOPE.md section 3) — the client is written to degrade to
-- that, not to hard-fail, the same pattern sd_render_usage/sd_shared_knowledge
-- use for "migration not run yet".
--
-- grd_schedule + grd_progress_photos added 2026-08-06: grd_schedule closes a
-- related bug (SAIRNgrounds' schedule writes were silently hitting
-- SAIRNscape's 'schedule' handler and 400ing -- see api/sd-data.js's own
-- comment on that block). grd_progress_photos closes item 3's disclosed
-- cross-device gap: a QC reviewer on a different device could never
-- previously see the crew's uploaded photo, because no route for that
-- resource existed at all. grd_progress_photos keeps this file's usual
-- 64KB cap (api/sd-data.js's MAX_PAYLOAD_BYTES rejects anything over that
-- for EVERY resource on this endpoint, not per-resource-overridable — see
-- that constant's own comment — so a looser DB constraint here would never
-- actually be reachable). sairngrounds.html's photo-upload path was updated
-- in the same push to compress each photo (same canvas-resize + JPEG-
-- quality-ladder technique as stonedesk.html's bsuCompressUnderBudget,
-- referenced directly in that comment as this endpoint's own documented
-- fix for exactly this problem) to comfortably fit under 64KB before send.
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables (sd_slabs, bld_jobs, etc.) — the raw license key never lands in
-- these rows. app_id is stamped 'sairngrounds' explicitly on every write
-- (mirrors sd_slabs' own explicit app_id:'stonedesk' stamp) so these rows
-- are unambiguously grounds-owned inside the platform's shared data-sync
-- endpoint, even though the endpoint file itself is historically named
-- api/sd-data.js.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy — same
-- as every table in sql/stonedesk_data_schema.sql. api/sd-data.js is the
-- only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES (confirmed there is no useful per-resource override at
-- the DB layer, per that file's own comment on sd_slabs' identical cap).

create extension if not exists pgcrypto;

create table if not exists public.grd_properties (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  property_id  text not null,                        -- client-generated id
  data         jsonb not null default '{}'::jsonb,    -- name, type, contact*, acreage, address, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, property_id),
  constraint grdprop_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdprop_license on public.grd_properties(license_hash);

create table if not exists public.grd_jobs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  job_id       text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- scope, target_date, status, site_notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, job_id),
  constraint grdjobs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdjobs_license on public.grd_jobs(license_hash);

create table if not exists public.grd_quotes (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  quote_id     text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- line_items[], status, valid_until
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, quote_id),
  constraint grdquotes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdquotes_license on public.grd_quotes(license_hash);

create table if not exists public.grd_golf_zones (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  zone_id      text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- hole_or_zone_name, acreage, last_serviced, condition_note
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, zone_id),
  constraint grdzones_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdzones_license on public.grd_golf_zones(license_hash);

create table if not exists public.grd_schedule (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  schedule_id  text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- freq, next, crew, quote_id, status
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, schedule_id),
  constraint grdsched_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdsched_license on public.grd_schedule(license_hash);

create table if not exists public.grd_progress_photos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  photo_id     text not null,
  schedule_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- photo_b64, is_final, ai_analysis, qc_status, captured_by, qc_by, qc_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, photo_id),
  constraint grdphotos_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdphotos_license_sched on public.grd_progress_photos(license_hash, schedule_id);

create table if not exists public.grd_invoices (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  invoice_id   text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- quote_id, amount, status, issued, due, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint grdinv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdinv_license on public.grd_invoices(license_hash);

create table if not exists public.grd_dreamclose (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairngrounds',
  dreamclose_id text not null,
  property_id   text not null,
  data          jsonb not null default '{}'::jsonb,    -- approved, approved_by, quote_id, invoice_id, schedule_id
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, dreamclose_id),
  constraint grddc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grddc_license on public.grd_dreamclose(license_hash);

-- ── RLS: service-role only (mirror stonedesk_data_schema.sql) ────────────
alter table public.grd_properties       enable row level security;
alter table public.grd_jobs             enable row level security;
alter table public.grd_quotes           enable row level security;
alter table public.grd_golf_zones       enable row level security;
alter table public.grd_schedule         enable row level security;
alter table public.grd_progress_photos  enable row level security;
alter table public.grd_invoices         enable row level security;
alter table public.grd_dreamclose       enable row level security;

drop policy if exists "svc only grd_properties" on public.grd_properties;
drop policy if exists "svc only grd_jobs"       on public.grd_jobs;
drop policy if exists "svc only grd_quotes"     on public.grd_quotes;
drop policy if exists "svc only grd_golf_zones" on public.grd_golf_zones;
drop policy if exists "svc only grd_schedule" on public.grd_schedule;
drop policy if exists "svc only grd_progress_photos" on public.grd_progress_photos;
drop policy if exists "svc only grd_invoices" on public.grd_invoices;
drop policy if exists "svc only grd_dreamclose" on public.grd_dreamclose;

create policy "svc only grd_properties" on public.grd_properties
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_jobs" on public.grd_jobs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_quotes" on public.grd_quotes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_golf_zones" on public.grd_golf_zones
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_schedule" on public.grd_schedule
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_progress_photos" on public.grd_progress_photos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_invoices" on public.grd_invoices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_dreamclose" on public.grd_dreamclose
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.grd_schedule        to service_role;
grant select, insert, update on public.grd_progress_photos to service_role;
grant select, insert, update on public.grd_invoices        to service_role;
grant select, insert, update on public.grd_dreamclose      to service_role;
