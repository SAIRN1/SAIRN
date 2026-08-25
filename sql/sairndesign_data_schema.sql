-- sql/sairndesign_data_schema.sql
-- SAIRNdesign application data — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sdn_clients/sdn_projects/sdn_specitems/sdn_proposals/sdn_vendors/
-- sdn_samplerequests/sdn_team/sdn_moodboards/sdn_colorcodes/sdn_pos/
-- sdn_invoices/sdn_timeentries/sdn_schedule/sdn_samples/sdn_contracts/
-- sdn_referrals/sdn_discounts/sdn_roomdims resources will work for
-- SAIRNdesign. Every statement is idempotent (create table if not exists),
-- safe to re-run. Until this runs, sairndesign.html falls back to its
-- existing localStorage-only behavior (client already degrades to that —
-- see sdnData()'s own graceful catch/null-return) rather than hard-failing.
--
-- WHY THIS FILE EXISTS (2026-08-07): SAIRNdesign shipped Phases 1-4 calling
-- sdnData('write', <bare resource name>, ...) at ~27 call sites across the
-- whole app, but NO 'sairndesign'-scoped resource was ever added to
-- api/sd-data.js's RESOURCES map. Every one of those calls has been hitting
-- the "resource must be one of: ..." 400 and silently degrading to
-- local-only storage since Phase 1 -- nothing has ever synced cross-device
-- for this app. This migration + the matching api/sd-data.js routes close
-- that gap.
--
-- NAMING: every resource here is prefixed sdn_, not left bare. Two of
-- SAIRNdesign's own resource names ('schedule', 'invoices') collide with
-- names already claimed bare by SAIRNscape in api/sd-data.js (see that
-- file's own RESOURCES comment) -- reusing them unprefixed would have
-- silently routed SAIRNdesign's schedule/invoice writes into SAIRNscape's
-- tables (or the reverse), a real cross-tenant data leak between two
-- different customers' businesses. Every resource is prefixed sdn_ for
-- consistency, not just the two that would have collided -- a mixed
-- "prefix only where it collides today" scheme is a landmine for the next
-- resource added to either app. Same reasoning already applied to
-- grd_/scp_/msb_ prefixes for SAIRNgrounds/SAIRNscape/mesobar.
--
-- SCOPING COLUMNS: unlike sql/sairngrounds_data_schema.sql, no table here
-- carries a required parent-id column (property_id equivalent). SAIRNdesign
-- has NEVER had a server-side "read this project's items" call -- every
-- read is "give me this whole resource's full array for this license,"
-- filtered client-side afterward (see sairndesign.html's rSpec()/rVendors()/
-- etc., which always load the full array via the ld()/specItems()-style
-- accessors then .filter() in JS). A NOT NULL parent column would add
-- schema surface with no operational use today; the parent id (project_id,
-- vendor_id, client_id, whichever applies) already lives inside each row's
-- own `data` jsonb, same as every other field on that record. Logged as a
-- deliberate simplification vs. the grd_* pattern, not an oversight.
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables. app_id is stamped 'sairndesign' explicitly on every write.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy — same
-- as every table in sql/stonedesk_data_schema.sql and
-- sql/sairngrounds_data_schema.sql. api/sd-data.js is the only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES (there is no useful per-resource override at the DB
-- layer -- see that file's own comment on this).

create extension if not exists pgcrypto;

create table if not exists public.sdn_clients (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  client_id    text not null,                        -- client-generated id
  data         jsonb not null default '{}'::jsonb,    -- name, company, phone, email, address, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint sdnclients_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnclients_license on public.sdn_clients(license_hash);

create table if not exists public.sdn_projects (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  project_id   text not null,
  data         jsonb not null default '{}'::jsonb,    -- client_id, name, budget, target_install_date, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, project_id),
  constraint sdnprojects_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnprojects_license on public.sdn_projects(license_hash);

create table if not exists public.sdn_specitems (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  specitem_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, item, vendor, sku, cost, retail, status, lead_time_weeks, one_of_a_kind, reserved, reserved_for, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, specitem_id),
  constraint sdnspecitems_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnspecitems_license on public.sdn_specitems(license_hash);

create table if not exists public.sdn_proposals (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  proposal_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, client_id, title, item_ids[], status, sent_date, decided_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, proposal_id),
  constraint sdnproposals_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnproposals_license on public.sdn_proposals(license_hash);

create table if not exists public.sdn_vendors (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  vendor_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, category, contact_name, phone, email, lead_time_typical_weeks, rating, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, vendor_id),
  constraint sdnvendors_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnvendors_license on public.sdn_vendors(license_hash);

create table if not exists public.sdn_samplerequests (
  id                uuid primary key default gen_random_uuid(),
  license_hash      text not null,
  app_id            text not null default 'sairndesign',
  samplerequest_id  text not null,
  data              jsonb not null default '{}'::jsonb, -- vendor_id, item_description, project_id, requested_date, status, notes
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (license_hash, samplerequest_id),
  constraint sdnsreq_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnsreq_license on public.sdn_samplerequests(license_hash);

create table if not exists public.sdn_team (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  team_id      text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, email, phone, role, status, start_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, team_id),
  constraint sdnteam_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnteam_license on public.sdn_team(license_hash);

create table if not exists public.sdn_moodboards (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  moodboard_id text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, title, description, image_urls[], status, color_code_ids[]
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, moodboard_id),
  constraint sdnmb_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnmb_license on public.sdn_moodboards(license_hash);

create table if not exists public.sdn_colorcodes (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairndesign',
  colorcode_id  text not null,
  data          jsonb not null default '{}'::jsonb,   -- brand, code, name, hex, notes
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, colorcode_id),
  constraint sdncc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdncc_license on public.sdn_colorcodes(license_hash);

create table if not exists public.sdn_pos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  po_id        text not null,
  data         jsonb not null default '{}'::jsonb,    -- po_number, project_id, vendor, item_ids[], total_cost, status
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, po_id),
  constraint sdnpos_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnpos_license on public.sdn_pos(license_hash);

create table if not exists public.sdn_invoices (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  invoice_id   text not null,
  data         jsonb not null default '{}'::jsonb,    -- invoice_number, proposal_id, project_id, client_id, amount, cost_basis, due_date, status, issued_date, paid_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, invoice_id),
  constraint sdninv_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdninv_license on public.sdn_invoices(license_hash);

create table if not exists public.sdn_timeentries (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairndesign',
  timeentry_id  text not null,
  data          jsonb not null default '{}'::jsonb,   -- employee_id, project_id, date, hours, billable_rate, billable, notes
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, timeentry_id),
  constraint sdntt_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdntt_license on public.sdn_timeentries(license_hash);

create table if not exists public.sdn_schedule (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  schedule_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, type, date, assignee, status, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, schedule_id),
  constraint sdnsched_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnsched_license on public.sdn_schedule(license_hash);

create table if not exists public.sdn_samples (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  sample_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- name, category, vendor_id, checked_out_to, project_id, checkout_date, due_back_date, returned_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, sample_id),
  constraint sdnsamples_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnsamples_license on public.sdn_samples(license_hash);

create table if not exists public.sdn_contracts (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  contract_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, client_id, title, scope_text, fee_structure, status, sent_date, esign_name, esign_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, contract_id),
  constraint sdnct_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnct_license on public.sdn_contracts(license_hash);

create table if not exists public.sdn_referrals (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  referral_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- from, to, phone, status, val, date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, referral_id),
  constraint sdnrf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnrf_license on public.sdn_referrals(license_hash);

create table if not exists public.sdn_discounts (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  discount_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- vendor_id, category, discount_pct, effective_date, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, discount_id),
  constraint sdndc_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdndc_license on public.sdn_discounts(license_hash);

create table if not exists public.sdn_roomdims (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairndesign',
  roomdim_id   text not null,
  data         jsonb not null default '{}'::jsonb,    -- project_id, width_ft, length_ft
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, roomdim_id),
  constraint sdnrd_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdnrd_license on public.sdn_roomdims(license_hash);

-- ── RLS: service-role only (mirror stonedesk_data_schema.sql / sairngrounds_data_schema.sql) ──
alter table public.sdn_clients        enable row level security;
alter table public.sdn_projects       enable row level security;
alter table public.sdn_specitems      enable row level security;
alter table public.sdn_proposals      enable row level security;
alter table public.sdn_vendors        enable row level security;
alter table public.sdn_samplerequests enable row level security;
alter table public.sdn_team           enable row level security;
alter table public.sdn_moodboards     enable row level security;
alter table public.sdn_colorcodes     enable row level security;
alter table public.sdn_pos            enable row level security;
alter table public.sdn_invoices       enable row level security;
alter table public.sdn_timeentries    enable row level security;
alter table public.sdn_schedule       enable row level security;
alter table public.sdn_samples        enable row level security;
alter table public.sdn_contracts      enable row level security;
alter table public.sdn_referrals      enable row level security;
alter table public.sdn_discounts      enable row level security;
alter table public.sdn_roomdims       enable row level security;

drop policy if exists "svc only sdn_clients"        on public.sdn_clients;
drop policy if exists "svc only sdn_projects"       on public.sdn_projects;
drop policy if exists "svc only sdn_specitems"      on public.sdn_specitems;
drop policy if exists "svc only sdn_proposals"      on public.sdn_proposals;
drop policy if exists "svc only sdn_vendors"        on public.sdn_vendors;
drop policy if exists "svc only sdn_samplerequests" on public.sdn_samplerequests;
drop policy if exists "svc only sdn_team"           on public.sdn_team;
drop policy if exists "svc only sdn_moodboards"     on public.sdn_moodboards;
drop policy if exists "svc only sdn_colorcodes"     on public.sdn_colorcodes;
drop policy if exists "svc only sdn_pos"            on public.sdn_pos;
drop policy if exists "svc only sdn_invoices"       on public.sdn_invoices;
drop policy if exists "svc only sdn_timeentries"    on public.sdn_timeentries;
drop policy if exists "svc only sdn_schedule"       on public.sdn_schedule;
drop policy if exists "svc only sdn_samples"        on public.sdn_samples;
drop policy if exists "svc only sdn_contracts"      on public.sdn_contracts;
drop policy if exists "svc only sdn_referrals"      on public.sdn_referrals;
drop policy if exists "svc only sdn_discounts"      on public.sdn_discounts;
drop policy if exists "svc only sdn_roomdims"       on public.sdn_roomdims;

create policy "svc only sdn_clients" on public.sdn_clients
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_projects" on public.sdn_projects
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_specitems" on public.sdn_specitems
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_proposals" on public.sdn_proposals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_vendors" on public.sdn_vendors
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_samplerequests" on public.sdn_samplerequests
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_team" on public.sdn_team
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_moodboards" on public.sdn_moodboards
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_colorcodes" on public.sdn_colorcodes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_pos" on public.sdn_pos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_invoices" on public.sdn_invoices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_timeentries" on public.sdn_timeentries
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_schedule" on public.sdn_schedule
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_samples" on public.sdn_samples
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_contracts" on public.sdn_contracts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_referrals" on public.sdn_referrals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_discounts" on public.sdn_discounts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sdn_roomdims" on public.sdn_roomdims
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.sdn_clients        to service_role;
grant select, insert, update on public.sdn_projects       to service_role;
grant select, insert, update on public.sdn_specitems      to service_role;
grant select, insert, update on public.sdn_proposals      to service_role;
grant select, insert, update on public.sdn_vendors        to service_role;
grant select, insert, update on public.sdn_samplerequests to service_role;
grant select, insert, update on public.sdn_team           to service_role;
grant select, insert, update on public.sdn_moodboards     to service_role;
grant select, insert, update on public.sdn_colorcodes     to service_role;
grant select, insert, update on public.sdn_pos            to service_role;
grant select, insert, update on public.sdn_invoices       to service_role;
grant select, insert, update on public.sdn_timeentries    to service_role;
grant select, insert, update on public.sdn_schedule       to service_role;
grant select, insert, update on public.sdn_samples        to service_role;
grant select, insert, update on public.sdn_contracts      to service_role;
grant select, insert, update on public.sdn_referrals      to service_role;
grant select, insert, update on public.sdn_discounts      to service_role;
grant select, insert, update on public.sdn_roomdims       to service_role;
