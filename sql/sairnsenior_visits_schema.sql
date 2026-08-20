-- sql/sairnsenior_visits_schema.sql
-- SAIRNsenior scheduled visits + EVV (Electronic Visit Verification) --
-- Supabase schema
--
-- WHY THIS EXISTS: a visit is scheduled (client + caregiver + time window)
-- and later clocked in/out against by the assigned caregiver at the
-- client's location -- EVV is federally mandated (21st Century Cures Act)
-- for Medicaid-funded personal care services, so the clock-in/out record
-- IS the compliance artifact, not a nice-to-have. One entity covers both
-- halves (scheduling + verification) because that's how EVV actually
-- works: it verifies a scheduled (or unscheduled) visit occurred, it
-- isn't a separate concept from the schedule.
--
-- assigned_employee_id is a REAL top-level column, same reasoning as
-- every other assignment-based privacy gate this session -- a caregiver
-- only ever sees/clocks-in-on visits assigned to them.
--
-- Field-level write split (enforced in api/sd-data.js, not here): the
-- SCHEDULING fields (client, caregiver assignment, scheduled time) are
-- writable by management/coordinator/scheduler -- scheduling IS their
-- job, unlike sen_clients where only management may (re)assign. The EVV
-- fields (clock_in/out, GPS, service notes) are writable ONLY by the
-- assigned caregiver, and only on a visit that already exists -- nobody
-- schedules by clocking in.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_visits (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  visit_id     text not null,                        -- client-generated id (VS-<timestamp>)
  assigned_employee_id text,                          -- the caregiver this visit is assigned to
  data         jsonb not null default '{}'::jsonb,    -- client_id, client_name, scheduled_date,
                                                        -- scheduled_start, scheduled_end, status,
                                                        -- clock_in_at, clock_in_lat, clock_in_lng,
                                                        -- clock_out_at, clock_out_lat, clock_out_lng,
                                                        -- services_notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, visit_id),
  constraint senvisits_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_senvisits_license on public.sen_visits(license_hash);
create index if not exists idx_senvisits_assignee on public.sen_visits(license_hash, assigned_employee_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.sen_visits to service_role;
revoke all on public.sen_visits from anon, authenticated;
