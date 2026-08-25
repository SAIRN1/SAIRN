-- sql/sd_crm_schema.sql
-- StoneDesk CRM / Lead Pipeline -- real server sync + per-lead assignment,
-- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- 'sd_crm' resource will work. Until this runs, that resource's read
-- branch degrades to an empty-but-ok response (provisioned:false), same
-- graceful pattern as every other newer resource in this file.
--
-- WHY THIS EXISTS (2026-08-19, confirmed with Michael): the CRM/Lead
-- Pipeline panel (stonedesk.html panel-crm) has existed for a while but
-- was pure localStorage -- no sd_crm resource was ever added to
-- api/sd-data.js, so leads were never shared across devices at all, let
-- alone scoped per salesperson. This is the same class of gap as the
-- earlier progress_photos/schedule sync fixes -- fixed as part of adding
-- the real per-lead-assignment privacy rule, not as a separate task.
--
-- KEYING: license_hash = sha256(license_key), same as every other
-- StoneDesk-owned table. lead_id is a client-generated id (this app has
-- no shared newId() helper -- matches the CRM-<timestamp>-<rand> shape
-- used elsewhere in this rollout).
--
-- assigned_employee_id is a REAL top-level column, not buried in the
-- jsonb blob -- it's what api/sd-data.js's read/write gates actually
-- filter and check ownership against server-side, so it has to be a real
-- queryable column, not something only the client could see and trust.
-- Null means unassigned -- api/sd-data.js treats an unassigned lead as
-- management-only-visible until someone assigns it (a new/untriaged lead
-- shouldn't be visible firm-wide by default any more than an assigned
-- one should be visible outside its owner).
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy.
-- api/sd-data.js is the only door in, and its own session-token gate
-- (owner/admin = full visibility + reassignment; sales/install = only
-- their own assigned leads, cannot reassign) is the real privacy
-- enforcement -- this schema's RLS is defense in depth underneath that,
-- same as every other StoneDesk table.

create table if not exists public.sd_crm (
  id                   uuid primary key default gen_random_uuid(),
  license_hash         text not null,
  lead_id              text not null,
  assigned_employee_id text,
  data                 jsonb not null default '{}'::jsonb,  -- name, proj, val, stage, source, date, phone, notes, won, lost
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (license_hash, lead_id),
  constraint sdcrm_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_crm_license on public.sd_crm(license_hash);
create index if not exists idx_sd_crm_assignee on public.sd_crm(license_hash, assigned_employee_id);

alter table public.sd_crm enable row level security;
drop policy if exists "svc only sd_crm" on public.sd_crm;
create policy "svc only sd_crm" on public.sd_crm
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.sd_crm to service_role;
