-- sql/sairnroofing_locations_schema.sql
-- SAIRNroofing Phase 4a -- multi-location attribution + crew scheduling.
--
--   rf_locations  -- the branch registry. MUTABLE (a branch is renamed, moves,
--                    or is deactivated); deactivation is active=false, never a
--                    delete, because jobs point at it by id forever.
--   rf_schedule   -- MUTABLE crew days. A scheduled day genuinely changes
--                    (weather, a crew swap, a reschedule) and it asserts
--                    nothing about the past, so unlike rf_claim_agreements and
--                    rf_certifications this is an upsert, not append-only.
--                    Getting that distinction wrong in either direction is the
--                    error: append-only evidence that can be edited is not
--                    evidence, and an append-only schedule would be unusable.
--
--   ALTER on the LIVE rf_jobs to add location_id.
--
-- ── WHY location_id IS A REAL COLUMN AND NOT A KEY IN data ───────────────
-- Same reason assigned_employee_id and job_class already are: anything that
-- will be filtered, grouped or reported on belongs in a column where an index
-- can reach it. Phase 4c's CSV export groups by location; doing that through a
-- jsonb key would work and would then quietly not scale.
--
-- ── THE GATE IS DELIBERATELY UNCHANGED ───────────────────────────────────
-- location_id is ATTRIBUTION, not access control. The privacy gate stays the
-- Phase 1 three-tier assignment model. Decision recorded 2026-08-25 -- see the
-- header of api/_lib/roofing-locations.js for the full reasoning. Nothing in
-- this file grants or restricts anything on the basis of location, and a
-- future session adding that must do it deliberately, not by assuming these
-- columns already imply it.
--
-- ── GRANTS: THE SOUND IDIOM ──────────────────────────────────────────────
-- REVOKE ALL from service_role FIRST, then grant. `grant select, insert`
-- alone is not sufficient -- postgres's default ACL confers TRUNCATE/
-- REFERENCES/TRIGGER/MAINTAIN on every new table and GRANT cannot subtract.
-- See sql/append_only_grant_audit.sql. Both tables here are mutable, so both
-- take UPDATE; NEITHER takes DELETE.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. The branch registry.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_locations (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  location_id  text not null,                       -- client-generated (LOC-<slug>)
  name         text not null,
  active       boolean not null default true,       -- deactivate, never delete
  data         jsonb not null default '{}'::jsonb,  -- address, phone, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, location_id),
  constraint rfloc_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfloc_license on public.rf_locations(license_hash);

-- ---------------------------------------------------------------------------
-- 2. location_id on the LIVE rf_jobs table.
--
-- DEFAULT 'LOC-DEFAULT' and NOT NULL together are what make this invisible to
-- a single-branch shop: every row that already exists is backfilled to the
-- implicit default in the same statement, and every future write that omits a
-- location lands there too. There is no window in which a job has no location.
-- ---------------------------------------------------------------------------
alter table public.rf_jobs
  add column if not exists location_id text not null default 'LOC-DEFAULT';

create index if not exists idx_rfjobs_location on public.rf_jobs(license_hash, location_id);

-- ---------------------------------------------------------------------------
-- 3. Crew days.
--
-- crew is a jsonb ARRAY OF employee_ids rather than a join table. A roofing
-- crew is 2-6 people on a given day and is always read whole, with the day --
-- there is no query in this app that asks "every day this person worked"
-- without also wanting the day's job. A join table would be the right call the
-- moment that query appears; it has not, and building it now would be
-- speculative structure. Recorded so the tradeoff is a decision, not drift.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_schedule (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  app_id         text not null default 'sairnroofing',
  schedule_id    text not null,                     -- client-generated (RFSCH-<timestamp>)
  job_id         text not null,                     -- references rf_jobs.job_id
  location_id    text not null default 'LOC-DEFAULT',
  scheduled_date date not null,
  status         text not null default 'planned',
  crew           jsonb not null default '[]'::jsonb, -- employee_ids, de-duplicated server-side
  data           jsonb not null default '{}'::jsonb, -- window, notes
  created_by     text not null,                     -- server-stamped from the session
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (license_hash, schedule_id),
  constraint rfsch_status_check check (status in
    ('planned','confirmed','in_progress','done','cancelled')),
  constraint rfsch_crew_is_array check (jsonb_typeof(crew) = 'array'),
  constraint rfsch_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfsch_license_date on public.rf_schedule(license_hash, scheduled_date);
create index if not exists idx_rfsch_job on public.rf_schedule(license_hash, job_id);

-- ---------------------------------------------------------------------------
-- 4. RLS + grants.
-- ---------------------------------------------------------------------------
alter table public.rf_locations enable row level security;
alter table public.rf_schedule enable row level security;

drop policy if exists "svc only rf_locations" on public.rf_locations;
create policy "svc only rf_locations" on public.rf_locations
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only rf_schedule" on public.rf_schedule;
create policy "svc only rf_schedule" on public.rf_schedule
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.rf_locations from service_role;
grant select, insert, update on public.rf_locations to service_role;
revoke all on public.rf_schedule from service_role;
grant select, insert, update on public.rf_schedule to service_role;
revoke all on public.rf_locations from anon, authenticated;
revoke all on public.rf_schedule from anon, authenticated;

-- Verify after running:
--   select count(*) from rf_locations;   -- expect 0
--   select count(*) from rf_schedule;    -- expect 0
--
-- Every existing job now carries the implicit default (expect 0 rows with a
-- null or empty location, and a count equal to your live job count):
--   select location_id, count(*) from rf_jobs group by location_id;
--
-- Confirm the grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no
-- TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_locations','rf_schedule')
--    group by table_name;
