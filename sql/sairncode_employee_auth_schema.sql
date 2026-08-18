-- sql/sairncode_employee_auth_schema.sql
-- SAIRNcode per-employee RBAC credentials -- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sc-auth.js's
-- bootstrap/login/setup actions will work. Until this runs, those return
-- a clear 503 NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: replaces sairncode.html's old client-only auth gate
-- (PINS = {coder:'1234', biller:'2345', auditor:'3456', admin:'4567'} --
-- one shared, hardcoded, identical-for-every-customer PIN per role,
-- baked into this PUBLIC repo's client source, zero server involvement,
-- any role self-assertable by editing the DOM). Same problem StoneDesk's
-- old scaffold had (sql/sd_employee_auth_schema.sql), same fix, one
-- addition -- explicit grants from the start (see StoneDesk's own
-- follow-up 502 fix commit fe730e2 for why that matters; SAIRNlaw's
-- schema already learned this lesson, this file copies that version).
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw license key) scopes rows to a practice,
-- matching every other *_employee_auth table's convention.
--
-- Design note: no RLS policy needed beyond deny-all -- read/write
-- exclusively via api/sc-auth.js using SUPABASE_SERVICE_ROLE_KEY, which
-- bypasses RLS regardless. The anon key is never used against this table.

create table if not exists sairncode_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('admin','coder','biller','auditor')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairncode_employee_auth_license
  on sairncode_employee_auth (license_hash);

alter table sairncode_employee_auth enable row level security;
drop policy if exists "svc only sairncode_employee_auth" on sairncode_employee_auth;
create policy "svc only sairncode_employee_auth" on sairncode_employee_auth
  for all using (false) with check (false);

-- Explicit grants (learned from StoneDesk's fe730e2 real 502 incident --
-- Supabase's ALTER DEFAULT PRIVILEGES does not reliably auto-grant to
-- service_role for tables created in the SQL editor). No DELETE: nothing
-- in api/sc-auth.js deletes a credential row (deactivation is
-- active=false), so withholding it costs nothing and removes a way to
-- lose an audit subject.
grant select, insert, update on sairncode_employee_auth to service_role;
revoke all on sairncode_employee_auth from anon, authenticated;

-- Verify after running:
--   select count(*) from sairncode_employee_auth;
-- should return 0 (empty table, no error).
