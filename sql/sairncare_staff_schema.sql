-- sql/sairncare_staff_schema.sql
-- SAIRNcare staff roster -- Supabase schema
--
-- WHY THIS EXISTS: SAIRNsenior shipped Caregivers/Staff local-storage-only
-- in its Phase 1 and had to close that gap in a later batch (see
-- sql/sairnsenior_caregivers_schema.sql's own header). Doing it here from
-- the start, per the original SAIRNcare v1 scope doc's explicit plan to
-- close that gap proactively.
--
-- Staff records are employment/certification data (a Med Aide's
-- medication-administration certification expiry, a background-check
-- date), not resident PHI, so this gets a lighter gate than alf_clients:
-- readable by any authenticated employee (anyone scheduling or covering a
-- shift needs to see the whole roster), writable only by management
-- (owner/billing) -- same read-broad/write-narrow shape as
-- sen_caregivers/StoneDesk's employees resource, not the four-tier
-- assignee-based gate alf_clients uses.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_staff (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  staff_id     text not null,                        -- client-generated id (ST-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- name, phone, position, cert_expiry,
                                                        -- bgcheck_date, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, staff_id),
  constraint alfstaff_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfstaff_license on public.alf_staff(license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.alf_staff to service_role;
revoke all on public.alf_staff from anon, authenticated;
