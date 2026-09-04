-- sql/sairnbiz_data_schema.sql
-- SAIRNbiz application data -- Supabase schema
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run.
--
-- WHY THIS FILE EXISTS, measured rather than described. On 2026-09-04
-- sairnbiz.html wrote SEVENTEEN localStorage collections through st()/ld() and
-- exactly ONE of them reached a server: sb_emps, through the bespoke
-- `employees` branch. Invoices, expenses, AP bills, vendors, PAYROLL RUNS,
-- training certifications, performance reviews, the hiring pipeline and the
-- budget existed in one browser and nowhere else. Clearing that browser lost
-- the company's records, permanently, with no copy on any server.
-- docs/SAIRN-OPEN-WORK-INDEX.md carried this as "No server-side persistence
-- for anything except the employee roster", size L, unassigned.
--
-- THE PART THAT MAKES THIS APP DIFFERENT FROM THE OTHERS, and the reason its
-- row was written separately from SAIRNbuild's: SAIRNbiz posts real
-- double-entry journal entries to Postgres through /api/ledger, and those
-- entries are durable, balanced and idempotent. That durability does not
-- extend backwards to anything they are derived from. A ledger row saying
-- "Paid Erie Insurance $1,140" survives; the bill it settled does not. The
-- books can be intact while the records that justify them are gone -- which is
-- worse than both halves being device-local, because the surviving half looks
-- authoritative. Nothing here is a ledger defect.
--
-- Same generic jsonb-blob pattern as every prior app's schema file
-- (sql/sairnbuild_data_schema.sql is the direct template): license_hash +
-- app_id + <resource>_id + data jsonb + created_at/updated_at,
-- unique(license_hash, <resource>_id), 64KB size cap matching
-- api/sd-data.js's uniform MAX_PAYLOAD_BYTES. Service-role only, RLS enabled
-- with no anon policy -- api/sd-data.js is the only door in.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name (strip
-- sb_, singularise), the same rule sairnlegacy's and sairnbuild's schemas
-- document and apply. sb_invs -> inv_id, sb_exps -> exp_id, sb_vends ->
-- vend_id, sb_payruns -> payrun_id. The other five are already singular
-- (sb_ap, sb_train, sb_perf, sb_hire, sb_bud) and keep their name unchanged.
--
-- NAMING COLLISION CHECK: every table here carries the sb_ prefix. Checked
-- before writing, not assumed -- the only pre-existing sb_ table anywhere in
-- sql/ is sb_employee_auth (sql/sb_employee_auth_schema.sql), which does not
-- appear below, and no sb_ RESOURCE was registered by any app.
--
-- WHY THESE NINE AND NOT ALL SEVENTEEN: see api/_resources/sairnbiz.js, which
-- carries the reason for each of the eight left out, in the registry itself,
-- so the next reader does not have to re-derive the judgement.
--
-- THE READ PATH REQUIRES A SIGNED-IN EMPLOYEE SESSION, not just the licence
-- key -- a deliberate divergence from the bld_ tables, argued in full at the
-- SB_RESOURCES block in api/sd-data.js. Short version: these are payroll
-- history, performance scores and PIP flags, and the licence key is a string
-- the app itself documents as not being auth.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE, and do NOT add one when fixing a
-- missing grant. The platform removed explicit delete grants from every
-- non-sc_* schema on 2026-08-25, and re-adding delete is precisely the
-- overcorrection that caused the 2026-08-06 incident. api/sd-data.js's
-- generic block handles read and write only; there is no delete path to grant
-- for.

create extension if not exists pgcrypto;

-- Accounts receivable. Carries paid/paidDate; the AR aging report is computed
-- straight off these rows.
create table if not exists public.sb_invs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  inv_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, inv_id),
  constraint sb_invs_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_invs_license on public.sb_invs(license_hash);
alter table public.sb_invs enable row level security;
revoke all on public.sb_invs from service_role;
grant select, insert, update on public.sb_invs to service_role;
-- Expenses. The deductible flag and receipt status are the tax substantiation
-- trail -- losing them loses the evidence, not just the total.
create table if not exists public.sb_exps (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  exp_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, exp_id),
  constraint sb_exps_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_exps_license on public.sb_exps(license_hash);
alter table public.sb_exps enable row level security;
revoke all on public.sb_exps from service_role;
grant select, insert, update on public.sb_exps to service_role;
-- Accounts payable. Bills received, balance outstanding, and whether settled.
-- The ledger records that a bill was PAID; this is the bill.
create table if not exists public.sb_ap (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  ap_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, ap_id),
  constraint sb_ap_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_ap_license on public.sb_ap(license_hash);
alter table public.sb_ap enable row level security;
revoke all on public.sb_ap from service_role;
grant select, insert, update on public.sb_ap to service_role;
-- Vendor roster with YTD spend, payment terms and W-9 status.
create table if not exists public.sb_vends (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  vend_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vend_id),
  constraint sb_vends_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_vends_license on public.sb_vends(license_hash);
alter table public.sb_vends enable row level security;
revoke all on public.sb_vends from service_role;
grant select, insert, update on public.sb_vends to service_role;
-- PAYROLL RUNS. Each row records that a calculation was performed and the basis
-- it was computed on. Nothing else in the app can answer "did we run payroll
-- this period, and on what figures". No money moves in this app; the row says
-- so itself rather than relying on a panel heading to convey it.
create table if not exists public.sb_payruns (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  payrun_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, payrun_id),
  constraint sb_payruns_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_payruns_license on public.sb_payruns(license_hash);
alter table public.sb_payruns enable row level security;
revoke all on public.sb_payruns from service_role;
grant select, insert, update on public.sb_payruns to service_role;
-- Training certifications and expiries -- OSHA 30, forklift, wet saw. Status is
-- DERIVED from the expiry date on read, deliberately not stored.
create table if not exists public.sb_train (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  train_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, train_id),
  constraint sb_train_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_train_license on public.sb_train(license_hash);
alter table public.sb_train enable row level security;
revoke all on public.sb_train from service_role;
grant select, insert, update on public.sb_train to service_role;
-- Performance reviews: scores, raise flags, PIP flags.
create table if not exists public.sb_perf (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  perf_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, perf_id),
  constraint sb_perf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_perf_license on public.sb_perf(license_hash);
alter table public.sb_perf enable row level security;
revoke all on public.sb_perf from service_role;
grant select, insert, update on public.sb_perf to service_role;
-- Open positions and where each candidate pipeline stands.
create table if not exists public.sb_hire (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  hire_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, hire_id),
  constraint sb_hire_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_hire_license on public.sb_hire(license_hash);
alter table public.sb_hire enable row level security;
revoke all on public.sb_hire from service_role;
grant select, insert, update on public.sb_hire to service_role;
-- Annual budget by category, with actuals synced from recorded expenses.
create table if not exists public.sb_bud (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnbiz',
  bud_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, bud_id),
  constraint sb_bud_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sb_bud_license on public.sb_bud(license_hash);
alter table public.sb_bud enable row level security;
revoke all on public.sb_bud from service_role;
grant select, insert, update on public.sb_bud to service_role;

-- Verify after running. Expect exactly 10 rows -- the nine above plus the
-- pre-existing sb_employee_auth -- each with INSERT / SELECT / UPDATE and
-- nothing else:
--
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type) as privs
--     from information_schema.role_table_grants
--    where grantee = 'service_role'
--      and table_schema = 'public'
--      and table_name like 'sb\_%'
--    group by table_name
--    order by table_name;
--
-- Then through the DEPLOYED API, which is the only real proof -- a clean
-- create is not evidence the app can use it. NOTE the X-SD-Auth header: these
-- resources require a signed-in SAIRNbiz employee session, so a licence-only
-- call answers 401 NO_SESSION whether or not this file has been run, and is
-- NOT a test of provisioning:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SD-PINNACLE-2026' \
--     -H 'X-SD-Auth: <session token from api/sb-auth.js login>' \
--     -d '{"action":"read","resource":"sb_payruns"}'
--
--   {"ok":true,"data":[],"provisioned":true}   -> this file has been run
--   503 NOT_PROVISIONED (on a write)           -> it has not
--   {"ok":true,"data":[],"provisioned":false}  -> it has not (read side)

