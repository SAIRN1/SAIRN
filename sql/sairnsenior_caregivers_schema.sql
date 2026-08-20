-- sql/sairnsenior_caregivers_schema.sql
-- SAIRNsenior caregiver/staff roster -- Supabase schema
--
-- WHY THIS EXISTS: closes the real gap flagged in Phase 1's own commit --
-- Caregivers/Staff shipped local-storage-only while Clients (the PHI-
-- bearing resource) got real sync from day one. Caregiver records are
-- employment/certification data (CPR expiry, background-check date), not
-- client PHI, so this gets a lighter gate than sen_clients: readable by
-- any authenticated employee (a scheduler/coordinator genuinely needs to
-- see the whole roster to staff a visit), writable only by management
-- (owner/billing) -- same read-broad/write-narrow shape as StoneDesk's
-- employees resource, not the assignee-based gate sen_clients uses.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_caregivers (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  caregiver_id text not null,                        -- client-generated id (CG-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- name, phone, cpr_expiry, bgcheck_date,
                                                        -- status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, caregiver_id),
  constraint sencaregivers_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sencaregivers_license on public.sen_caregivers(license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.sen_caregivers to service_role;
revoke all on public.sen_caregivers from anon, authenticated;
