-- sql/sairnbuild_bids_schema.sql
-- Real server sync for SAIRNbuild's Bids & Proposals panel -- Supabase schema
--
-- WHY THIS EXISTS: bld_bids has had ZERO server sync since the panel was
-- built (confirmed by grep: no bld_bids reference anywhere in
-- api/sd-data.js, saveBid() only ever calls st('bld_bids', bids) --
-- localStorage only, one device, never shared). Task 3 of the platform
-- sales-lead-privacy rule (StoneDesk's sd_crm was item 1, SAIRNdesign's
-- sdn_clients was item 2) -- a bid is visible only to management
-- (Owner/Office) or the PM it's assigned to, enforced server-side in
-- api/sd-data.js's new bld_bids branch.
--
-- assigned_employee_id is a REAL top-level column, not buried in the jsonb
-- `data` blob -- it's what the privacy gate actually filters and checks
-- ownership against server-side, so it has to be a real queryable column.
-- Same shape as sql/sd_crm_schema.sql's assigned_employee_id (StoneDesk)
-- and sql/sairndesign_clients_assignment_migration.sql's (SAIRNdesign).
--
-- Null means unassigned -- treated as management-only-visible, same
-- confirmed-correct default as both prior apps in this rollout.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.bld_bids (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnbuild',
  bid_id       text not null,                        -- client-generated id (B-<timestamp>)
  assigned_employee_id text,                          -- null = unassigned, management-only-visible
  data         jsonb not null default '{}'::jsonb,    -- client, phone, type, source, stage, markup,
                                                        -- lines[], sent, decided, lostreason, notes,
                                                        -- converted_job_id
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, bid_id),
  constraint bldbids_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_bldbids_license on public.bld_bids(license_hash);
create index if not exists idx_bldbids_assignee on public.bld_bids(license_hash, assigned_employee_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session (a live 42501 the first time a table like this
-- was used, caught by sql/sairnlaw_employee_auth_schema.sql originally).
grant select, insert, update on public.bld_bids to service_role;
revoke all on public.bld_bids from anon, authenticated;
