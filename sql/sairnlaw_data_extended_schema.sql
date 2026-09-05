-- sql/sairnlaw_data_extended_schema.sql
-- SAIRNlaw application data, part 2 -- the fifteen resources that never
-- reached the server.
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run.
--
-- WHY THIS FILE EXISTS, measured and then PROVEN LIVE rather than inferred.
-- On 2026-09-04 sairnlaw.html wrote TWENTY distinct resources across 31 call
-- sites and api/_resources/sairnlaw.js registered FOUR. The other fifteen were
-- refused by api/sd-data.js's resource allowlist before any credential
-- mattered. The control that proves it, same bogus licence key both times:
--   law_invoices -> 400 "resource must be one of ..."   (refused at the gate)
--   law_matters  -> 401 INVALID_LICENSE                 (past the gate)
-- Same request shape; only the resource name differed.
--
-- 23 call sites among them, including BILLABLE TIME (law_timeentries),
-- invoices, matter documents (six sites), operating-account transactions and
-- bank statements. Every failure rendered as "server sync not yet enabled for
-- this app" -- a sentence that was false and was hiding all of it.
--
-- Same generic jsonb-blob pattern as sql/sairnlaw_data_schema.sql and every
-- other app's: license_hash + app_id + <resource>_id + data jsonb +
-- created_at/updated_at, unique(license_hash, <resource>_id), 64KB cap
-- matching api/sd-data.js's uniform MAX_PAYLOAD_BYTES. Service-role only, RLS
-- enabled with no anon policy -- api/sd-data.js is the only door in.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name (strip
-- law_, singularise), the same rule sairnlegacy's and sairnbuild's schemas
-- document -- including -ies -> -y, so law_timeentries is timeentry_id.
--
-- SECURITY MODEL, STATED PLAINLY BECAUSE ONE OF THESE IS HEALTH INFORMATION.
-- These tables are gated on the LICENCE KEY ONLY, exactly like the four in
-- sairnlaw_data_schema.sql -- including law_trusttx, which is client trust
-- money. SAIRNlaw has real per-employee auth (api/law-auth.js) and its
-- sdnData() does not send the session token at all, so gating these fifteen
-- while the original four stay open would be a split posture rather than a
-- protection. The whole-app gap is recorded as its own row in
-- docs/SAIRN-OPEN-WORK-INDEX.md; it is one coherent change across all
-- nineteen, not a thing to do by halves here. law_pimedical carries provider
-- names and billed amounts on a personal-injury matter.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE, and do NOT add one when fixing a
-- missing grant. The platform removed explicit delete grants from every
-- non-sc_* schema on 2026-08-25.

create extension if not exists pgcrypto;

-- Documents filed on a matter -- metadata and the e-sign stamp, no file bytes. SIX call sites, the most-written of the fifteen.
create table if not exists public.law_matterdocs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  matterdoc_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, matterdoc_id),
  constraint law_matterdocs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_matterdocs_license on public.law_matterdocs(license_hash);
alter table public.law_matterdocs enable row level security;
revoke all on public.law_matterdocs from service_role;
grant select, insert, update on public.law_matterdocs to service_role;
-- Tasks on a matter, with a due date and an assignee.
create table if not exists public.law_mattertasks (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  mattertask_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, mattertask_id),
  constraint law_mattertasks_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_mattertasks_license on public.law_mattertasks(license_hash);
alter table public.law_mattertasks enable row level security;
revoke all on public.law_mattertasks from service_role;
grant select, insert, update on public.law_mattertasks to service_role;
-- Dated milestones on a matter -- the case chronology.
create table if not exists public.law_mattermilestones (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  mattermilestone_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, mattermilestone_id),
  constraint law_mattermilestones_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_mattermilestones_license on public.law_mattermilestones(license_hash);
alter table public.law_mattermilestones enable row level security;
revoke all on public.law_mattermilestones from service_role;
grant select, insert, update on public.law_mattermilestones to service_role;
-- BILLABLE TIME. What invoices are built from; losing it loses the fee.
create table if not exists public.law_timeentries (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  timeentry_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, timeentry_id),
  constraint law_timeentries_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_timeentries_license on public.law_timeentries(license_hash);
alter table public.law_timeentries enable row level security;
revoke all on public.law_timeentries from service_role;
grant select, insert, update on public.law_timeentries to service_role;
-- Client invoices, with their line items and status.
create table if not exists public.law_invoices (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  invoice_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint law_invoices_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_invoices_license on public.law_invoices(license_hash);
alter table public.law_invoices enable row level security;
revoke all on public.law_invoices from service_role;
grant select, insert, update on public.law_invoices to service_role;
-- OPERATING accounts -- the firm side of the ledger, distinct from client trust.
create table if not exists public.law_opaccounts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  opaccount_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, opaccount_id),
  constraint law_opaccounts_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_opaccounts_license on public.law_opaccounts(license_hash);
alter table public.law_opaccounts enable row level security;
revoke all on public.law_opaccounts from service_role;
grant select, insert, update on public.law_opaccounts to service_role;
-- Operating-account transactions. Firm money moving.
create table if not exists public.law_optx (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  optx_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, optx_id),
  constraint law_optx_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_optx_license on public.law_optx(license_hash);
alter table public.law_optx enable row level security;
revoke all on public.law_optx from service_role;
grant select, insert, update on public.law_optx to service_role;
-- Bank statement balances, used to reconcile against the ledger.
create table if not exists public.law_bankstatements (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  bankstatement_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, bankstatement_id),
  constraint law_bankstatements_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_bankstatements_license on public.law_bankstatements(license_hash);
alter table public.law_bankstatements enable row level security;
revoke all on public.law_bankstatements from service_role;
grant select, insert, update on public.law_bankstatements to service_role;
-- Personal-injury cases: gross settlement, fee percentage, costs.
create table if not exists public.law_picases (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  picase_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, picase_id),
  constraint law_picases_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_picases_license on public.law_picases(license_hash);
alter table public.law_picases enable row level security;
revoke all on public.law_picases from service_role;
grant select, insert, update on public.law_picases to service_role;
-- Medical providers and billed amounts on a PI case. See the security note in this header -- health information, at the same tier as everything else here.
create table if not exists public.law_pimedical (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  pimedical_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, pimedical_id),
  constraint law_pimedical_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_pimedical_license on public.law_pimedical(license_hash);
alter table public.law_pimedical enable row level security;
revoke all on public.law_pimedical from service_role;
grant select, insert, update on public.law_pimedical to service_role;
-- Messages exchanged with a client through the portal.
create table if not exists public.law_portalmessages (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  portalmessage_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, portalmessage_id),
  constraint law_portalmessages_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_portalmessages_license on public.law_portalmessages(license_hash);
alter table public.law_portalmessages enable row level security;
revoke all on public.law_portalmessages from service_role;
grant select, insert, update on public.law_portalmessages to service_role;
-- E-signature stamps: who signed what, and when.
create table if not exists public.law_portalesign (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  portalesign_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, portalesign_id),
  constraint law_portalesign_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_portalesign_license on public.law_portalesign(license_hash);
alter table public.law_portalesign enable row level security;
revoke all on public.law_portalesign from service_role;
grant select, insert, update on public.law_portalesign to service_role;
-- Bar admissions per staff member and their status.
create table if not exists public.law_barcerts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  barcert_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, barcert_id),
  constraint law_barcerts_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_barcerts_license on public.law_barcerts(license_hash);
alter table public.law_barcerts enable row level security;
revoke all on public.law_barcerts from service_role;
grant select, insert, update on public.law_barcerts to service_role;
-- CLE credits earned, per staff member and jurisdiction.
create table if not exists public.law_clecredits (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  clecredit_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, clecredit_id),
  constraint law_clecredits_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_clecredits_license on public.law_clecredits(license_hash);
alter table public.law_clecredits enable row level security;
revoke all on public.law_clecredits from service_role;
grant select, insert, update on public.law_clecredits to service_role;
-- CLE requirements per jurisdiction -- hours and period.
create table if not exists public.law_clerequirements (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnlaw',
  clerequirement_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, clerequirement_id),
  constraint law_clerequirements_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_clerequirements_license on public.law_clerequirements(license_hash);
alter table public.law_clerequirements enable row level security;
revoke all on public.law_clerequirements from service_role;
grant select, insert, update on public.law_clerequirements to service_role;

-- Verify after running. Expect these fifteen, each with INSERT / SELECT /
-- UPDATE and nothing else:
--
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type) as privs
--     from information_schema.role_table_grants
--    where grantee = 'service_role'
--      and table_schema = 'public'
--      and table_name in ('law_matterdocs','law_mattertasks','law_mattermilestones','law_timeentries','law_invoices','law_opaccounts','law_optx','law_bankstatements','law_picases','law_pimedical','law_portalmessages','law_portalesign','law_barcerts','law_clecredits','law_clerequirements')
--    group by table_name
--    order by table_name;
--
-- Then through the DEPLOYED API, which is the only real proof -- a clean
-- create is not evidence the app can use it:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer LAW-PINNACLE-2026' \
--     -d '{"action":"read","resource":"law_timeentries"}'
--
--   {"ok":true,"data":[],"provisioned":true}   -> this file has been run
--   {"ok":true,"data":[],"provisioned":false}  -> it has not
--   400 "resource must be one of"              -> the code half did not deploy

