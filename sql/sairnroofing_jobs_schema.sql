-- sql/sairnroofing_jobs_schema.sql
-- SAIRNroofing job data + assignment-based privacy gate -- Supabase schema
--
-- WHY THIS EXISTS: the job is SAIRNroofing's core assignable entity --
-- Phase 1 needs a real gate for it from day one so a foreman/crew member
-- only ever sees jobs assigned to them, same as every other app's
-- assignment gate. This is deliberately a minimal Phase 1 shape (address,
-- status, job_class, assignment) -- scheduling, multi-location and the
-- measurement/estimate fields are Phase 2/4, not invented here early.
--
-- assigned_employee_id is a REAL top-level column, not buried in the
-- jsonb `data` blob -- it's what the privacy gate filters and checks
-- ownership against server-side. Same shape as every other assignment
-- gate on this platform (StoneDesk's sd_crm, SAIRNdesign's sdn_clients,
-- SAIRNbuild's bld_bids, SAIRNsenior's sen_clients, SAIRNcare's alf_clients).
--
-- job_class ('residential'|'commercial') is a REAL top-level column too,
-- not because the gate reads it (it does not -- see api/rf-auth.js's
-- header: job type is a property of the job, never of the identity, and
-- nothing branches visibility on it), but because commercial work is
-- confirmed first-class in v1 scope and a property this visible on every
-- job list belongs in a real column, not buried in jsonb, from the start.
--
-- Null assigned_employee_id means unassigned -- treated as
-- management-only-visible (owner/admin), same confirmed-correct default
-- as every prior app's assignment gate.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_jobs (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  job_id       text not null,                        -- client-generated id (RF-<timestamp>)
  job_class    text not null default 'residential' check (job_class in ('residential','commercial')),
  assigned_employee_id text,                          -- null = unassigned, management-only-visible
  data         jsonb not null default '{}'::jsonb,    -- address, contact, status, notes -- Phase 2/4
                                                        -- add measurement/estimate/schedule fields
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, job_id),
  constraint rfjobs_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfjobs_license on public.rf_jobs(license_hash);
create index if not exists idx_rfjobs_assignee on public.rf_jobs(license_hash, assigned_employee_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header on this platform (StoneDesk's fe730e2 real 502 incident taught
-- this platform that ALTER DEFAULT PRIVILEGES does not reliably auto-grant
-- to service_role for tables created in the SQL editor).
alter table public.rf_jobs enable row level security;
drop policy if exists "svc only rf_jobs" on public.rf_jobs;
create policy "svc only rf_jobs" on public.rf_jobs
  for all using (false) with check (false);

-- FIXED (2026-08-24, same platform-wide gap found live on dnt_credentials --
-- see sql/sairnroofing_photos_schema.sql's header for the full explanation).
-- REVOKE ALL first so the TRUNCATE/REFERENCES/TRIGGER Supabase grants by
-- default to a raw-SQL-created table doesn't sit unnoticed behind a GRANT
-- that only ever adds privileges.
revoke all on public.rf_jobs from service_role;
grant select, insert, update on public.rf_jobs to service_role;
revoke all on public.rf_jobs from anon, authenticated;
