-- sql/sairnlaw_data_schema.sql
-- SAIRNlaw application data — Supabase schema (step 1 of trust disbursement
-- server-sync; see docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md)
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- law_clients/law_matters/law_trusttx resources will work. Every statement
-- is idempotent — safe to re-run. Until this runs, sairnlaw.html falls back
-- to its existing localStorage-only behavior (saveTrustTransaction() etc.
-- already toast "Saved on this device only -- server sync not yet enabled
-- for this app" on a failed sync, the same pattern render_usage/
-- shared_knowledge use for "migration not run yet").
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables. app_id is stamped 'sairnlaw' explicitly on every write.
--
-- client_id (on law_matters) and matter_id/client_id (on law_trusttx) are
-- real columns, not just fields inside the jsonb blob -- added now so a
-- later balance-check feature (step 2, not built in this migration) can
-- query trust transactions by client without a second migration + backfill.
-- Mirrors the existing grd_jobs.property_id precedent. These are NOT
-- foreign keys and are NOT validated against law_clients/law_matters at
-- write time (matches this platform's existing precedent of trusting
-- client-supplied linking ids) -- deliberately deferred, not an oversight.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy --
-- same as every table in sql/stonedesk_data_schema.sql /
-- sql/sairngrounds_data_schema.sql. api/sd-data.js is the only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.law_clients (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  client_id    text not null,                        -- client-generated id
  data         jsonb not null default '{}'::jsonb,    -- name, type, phone, email, address, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint lawclients_data_size check (octet_length(data::text) <= 65536)
);
-- idx_lawclients_license dropped (final review, 2026-08-16): redundant --
-- the `unique (license_hash, client_id)` constraint above already creates
-- a btree led by license_hash that fully serves this.
drop index if exists public.idx_lawclients_license;

create table if not exists public.law_matters (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  matter_id    text not null,                        -- client-generated id
  client_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- matter_number, matter_name, practice_area, status, ...
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, matter_id),
  constraint lawmatters_data_size check (octet_length(data::text) <= 65536)
);
-- Step-2-anticipatory composite index (final review, 2026-08-16): a future
-- balance-check query will filter by license_hash AND client_id together.
-- idx_lawmatters_license was redundant (unique(license_hash, matter_id)
-- above already covers it) and idx_lawmatters_client was a bare client_id
-- index, which would let Postgres match across every license before
-- re-checking license_hash -- a cross-tenant-scan smell. Both dropped and
-- replaced by one composite index.
drop index if exists public.idx_lawmatters_license;
drop index if exists public.idx_lawmatters_client;
create index if not exists idx_lawmatters_license_client on public.law_matters(license_hash, client_id);

create table if not exists public.law_trusttx (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  trusttx_id   text not null,                        -- client-generated id
  matter_id    text not null,
  client_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- type, amount, date, method, reference_number, description, status, ...
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, trusttx_id),
  constraint lawtrusttx_data_size check (octet_length(data::text) <= 65536)
);
-- Step-2-anticipatory composite index (final review, 2026-08-16): same
-- reasoning as law_matters above -- idx_lawtrusttx_license was redundant
-- (unique(license_hash, trusttx_id) above already covers it) and
-- idx_lawtrusttx_client was a bare client_id index (cross-tenant-scan
-- smell). Both dropped and replaced by one composite index.
drop index if exists public.idx_lawtrusttx_license;
drop index if exists public.idx_lawtrusttx_client;
create index if not exists idx_lawtrusttx_license_client on public.law_trusttx(license_hash, client_id);

-- ── RLS: service-role only (mirror sairngrounds_data_schema.sql) ─────────
alter table public.law_clients enable row level security;
alter table public.law_matters enable row level security;
alter table public.law_trusttx enable row level security;

drop policy if exists "svc only law_clients" on public.law_clients;
drop policy if exists "svc only law_matters" on public.law_matters;
drop policy if exists "svc only law_trusttx" on public.law_trusttx;

create policy "svc only law_clients" on public.law_clients
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only law_matters" on public.law_matters
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only law_trusttx" on public.law_trusttx
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.law_clients  to service_role;
grant select, insert, update on public.law_matters  to service_role;
grant select, insert, update on public.law_trusttx  to service_role;
