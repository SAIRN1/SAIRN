-- sql/sairnscape_data_schema.sql
-- SAIRNscape application data — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- customers/jobs/quotes/schedule/invoices/scp_progress_photos resources
-- will work for SAIRNscape. Until this runs, sairnscape.html falls back to
-- its existing Phase 1 localStorage-only behavior — same graceful degrade
-- as SAIRNgrounds (see sql/sairngrounds_data_schema.sql for the precedent).
--
-- scp_progress_photos added 2026-08-06: closes item 3's disclosed
-- cross-device gap, same fix and reasoning as SAIRNgrounds'
-- grd_progress_photos (see that table's comment in
-- sql/sairngrounds_data_schema.sql) — a QC reviewer on a different device
-- could never previously see the crew's uploaded photo. Kept at this
-- file's usual 64KB cap; sairnscape.html's photo-upload path was updated
-- in the same push to compress each photo under that budget first.
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables. app_id is stamped 'sairnscape' explicitly on every write.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy.
-- api/sd-data.js is the only door in.
--
-- GRANT statements included explicitly this session (2026-08-06) — see
-- sql/scp_employee_auth_schema.sql's header for why this is now standard
-- going forward rather than relying on the service-role RLS-bypass default
-- silently.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.scp_customers (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, service_type, recurring, phone, email, address, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, customer_id),
  constraint scpcust_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpcust_license on public.scp_customers(license_hash);

create table if not exists public.scp_jobs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  job_id       text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- scope, target_date, status, recurring_schedule_id
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, job_id),
  constraint scpjobs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpjobs_license on public.scp_jobs(license_hash);

create table if not exists public.scp_quotes (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  quote_id     text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- line_items[], status, valid_until
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, quote_id),
  constraint scpquotes_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpquotes_license on public.scp_quotes(license_hash);

create table if not exists public.scp_schedule (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  schedule_id  text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- frequency, next_date, assigned_crew, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, schedule_id),
  constraint scpsched_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpsched_license on public.scp_schedule(license_hash);

create table if not exists public.scp_invoices (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  invoice_id   text not null,
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- amount, status, issued_date, paid_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint scpinv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpinv_license on public.scp_invoices(license_hash);

create table if not exists public.scp_progress_photos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnscape',
  photo_id     text not null,
  schedule_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- photo_b64, is_final, ai_analysis, qc_status, captured_by, qc_by, qc_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, photo_id),
  constraint scpphotos_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_scpphotos_license_sched on public.scp_progress_photos(license_hash, schedule_id);

-- ── RLS: service-role only ────────────────────────────────────────────────
alter table public.scp_customers        enable row level security;
alter table public.scp_jobs             enable row level security;
alter table public.scp_quotes           enable row level security;
alter table public.scp_schedule         enable row level security;
alter table public.scp_invoices         enable row level security;
alter table public.scp_progress_photos  enable row level security;

drop policy if exists "svc only scp_customers" on public.scp_customers;
drop policy if exists "svc only scp_jobs"      on public.scp_jobs;
drop policy if exists "svc only scp_quotes"    on public.scp_quotes;
drop policy if exists "svc only scp_schedule"  on public.scp_schedule;
drop policy if exists "svc only scp_invoices"  on public.scp_invoices;
drop policy if exists "svc only scp_progress_photos" on public.scp_progress_photos;

create policy "svc only scp_customers" on public.scp_customers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_jobs" on public.scp_jobs
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_quotes" on public.scp_quotes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_schedule" on public.scp_schedule
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_invoices" on public.scp_invoices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only scp_progress_photos" on public.scp_progress_photos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- ── GRANTs: explicit, not left to the RLS-bypass default alone ─────────────
--
-- DELETE REMOVED FROM ALL SIX LINES 2026-08-25. They previously read
-- `grant select, insert, update, delete`. Same overcorrection this file's
-- header points at, and the same one already fixed in
-- sql/scp_employee_auth_schema.sql: the 2026-08-06 session was closing a
-- pattern of MISSING grants and, being explicit, wrote the full CRUD verb
-- list rather than the verbs SAIRNscape actually uses. SAIRNscape has no
-- delete path -- the platform's only DELETE is api/sd-data.js's
-- SC_RESOURCES (SAIRNcode) branch -- so these six were never used.
--
-- Fixed at SOURCE separately from the live sweep, on purpose and for the
-- reason that makes this urgent rather than tidy: this file is
-- `create table if not exists` and safe to re-run, and
-- sql/unused_delete_grant_revoke_2026-08-24.sql revoked these six live on
-- 2026-08-25. Until this edit, file and database DISAGREED, and any
-- routine re-run of this file would have silently restored all six --
-- undoing part of a verified sweep with no error and no signal. The sweep
-- fixes the database; these lines fix the file. Both halves are required.
grant usage on schema public to service_role;
grant select, insert, update on public.scp_customers to service_role;
grant select, insert, update on public.scp_jobs      to service_role;
grant select, insert, update on public.scp_quotes    to service_role;
grant select, insert, update on public.scp_schedule  to service_role;
grant select, insert, update on public.scp_invoices  to service_role;
grant select, insert, update on public.scp_progress_photos to service_role;
