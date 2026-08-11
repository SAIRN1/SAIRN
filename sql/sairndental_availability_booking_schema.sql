-- sql/sairndental_availability_booking_schema.sql
-- SAIRNdental availability engine + self-scheduling -- Supabase schema
--
-- Run once in the Supabase SQL editor, after
-- sql/sairndental_data_schema.sql. See
-- docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md
-- for the full design reasoning.
--
-- dnt_settings: new generic-jsonb resource, but booking_slug also gets
-- a real, indexed, unique column -- the public booking page resolves
-- a practice by this slug on every request, and it must never be
-- confused with the license key (a Bearer secret elsewhere on this
-- platform) or leaked to a full-table scan pattern.
create table if not exists public.dnt_settings (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  settings_id text not null, booking_slug text unique, data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, settings_id), constraint dntst_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntst_license on public.dnt_settings(license_hash);
create index if not exists idx_dntst_slug on public.dnt_settings(booking_slug);

alter table public.dnt_settings enable row level security;
drop policy if exists "svc only dnt_settings" on public.dnt_settings;
create policy "svc only dnt_settings" on public.dnt_settings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_settings to service_role;

-- dnt_appointments: promote real columns alongside the existing
-- generic data jsonb (kept for patient_id/procedure_type_id/source/
-- notes -- anything not needed in a constraint or a fast lookup).
-- Deliberate deviation from this platform's usual generic-jsonb-blob
-- pattern -- the first resource here that needs genuine interval-
-- overlap prevention (a provider or operatory double-booked across
-- overlapping time ranges), not just an exact-match unique constraint.
alter table public.dnt_appointments
  add column if not exists provider_id text,
  add column if not exists operatory_id text,
  add column if not exists start_time timestamptz,
  add column if not exists end_time timestamptz,
  add column if not exists status text;

create extension if not exists btree_gist;

-- RISK FLAGGED, NOT VERIFIED (no DB execution access from this
-- environment): any dnt_appointments rows written before this
-- migration runs (e.g. via the foundation plan's generic write path,
-- if it was ever exercised against this specific table) will have
-- NULL provider_id/start_time/end_time. Postgres's multi-arg range
-- constructors return NULL when either bound is NULL, and a NULL
-- value in an EXCLUDE constraint's key is treated like a UNIQUE
-- constraint treats NULL -- not equal to anything, never triggers an
-- exclusion. This SHOULD mean constraint creation against pre-
-- existing NULL-columned rows succeeds harmlessly (no validation
-- error), but this has not been empirically confirmed against the
-- real live table. If ADD CONSTRAINT below fails, check for this
-- exact cause first before assuming something else is wrong.
alter table public.dnt_appointments
  add constraint dntap_no_provider_overlap
    exclude using gist (
      license_hash with =, provider_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed')),
  add constraint dntap_no_operatory_overlap
    exclude using gist (
      license_hash with =, operatory_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed'));

-- dnt_booking_rate_limits: real, new -- first rate-limiter on this
-- platform (confirmed no existing pattern to reuse before writing
-- this; every prior "rate limit" mention elsewhere in this codebase
-- is a documented gap, not an implementation). ip_hash =
-- sha256(ip + a server-side salt), never a raw IP stored, same
-- discipline as license_hash = sha256(license_key) elsewhere.
create table if not exists public.dnt_booking_rate_limits (
  id uuid primary key default gen_random_uuid(),
  ip_hash text not null, window_start timestamptz not null, count int not null default 1,
  unique (ip_hash, window_start)
);
create index if not exists idx_dntbrl_iphash on public.dnt_booking_rate_limits(ip_hash);

alter table public.dnt_booking_rate_limits enable row level security;
drop policy if exists "svc only dnt_booking_rate_limits" on public.dnt_booking_rate_limits;
create policy "svc only dnt_booking_rate_limits" on public.dnt_booking_rate_limits
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_booking_rate_limits to service_role;

-- Verify after running:
--   select indexname from pg_indexes where tablename='dnt_appointments';
-- should include the two dntap_no_*_overlap constraint indexes.
--   select conname from pg_constraint where conname like 'dntap_no_%';
-- should return both exclusion constraints.
