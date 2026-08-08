-- sql/sb_employee_auth_schema.sql
-- SAIRNbiz per-employee credentials — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sb-auth.js's
-- login/setup/bootstrap actions will work.
--
-- WHY THIS EXISTS: closes the employees-write gap found auditing StoneDesk's
-- RBAC (sql/sd_employee_auth_schema.sql) — api/sd-data.js's employees WRITE
-- branch previously trusted a client-supplied body.app_id==='sairnbiz'
-- string with no real verification. That can't be fixed with a token baked
-- into sairnbiz.html itself: it's a static client-side file with no backend
-- of its own, so anything embedded in it is exactly as extractable as the
-- app_id string already was. The real fix is proving a specific PERSON with
-- Owner/HR authority is behind the write, the same model as StoneDesk's
-- side — hence a second, parallel credential table rather than a shared
-- secret.
--
-- Deliberately a SEPARATE table/role-set from sd_employee_auth, not a merge
-- (confirmed decision, 2026-08-03): SAIRNbiz's roles (owner/hr/accounting/
-- manager/staff, sairnbiz.html:737's existing PINS object) don't map onto
-- StoneDesk's (owner/admin/sales/install) — same shape, deliberately
-- distinct identity/role systems per app, both accepted by
-- api/sd-data.js's write gate (api/_lib/auth.js's ROLES_BY_APP + the signed
-- `app` claim distinguishes which is which; that claim is inside the HMAC
-- payload, not client-suppliable, unlike the old body.app_id check).
--
-- Same security notes as sd_employee_auth_schema.sql: pin_hash is
-- scrypt(pin, pin_salt), never the raw PIN; license_hash (not the raw
-- license key) scopes rows to a shop; no RLS by design (service-role only,
-- via api/sb-auth.js and api/sd-data.js).

create table if not exists sb_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','hr','accounting','manager','staff')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sb_employee_auth_license
  on sb_employee_auth (license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS (added 2026-08-08, found by a real live 502 during the platform
-- click-through audit, not preemptively): api/sb-auth.js's login and
-- bootstrap actions both failed against the live deployment with Postgres
-- 42501 "permission denied for table sb_employee_auth" -- the table existed
-- but service_role had no privileges on it, so every SAIRNbiz employee
-- login was broken in production. Identical root cause to the same finding
-- on sairnlaw_employee_auth the same day (see sql/sairnlaw_employee_auth_
-- schema.sql) -- Supabase's default privileges evidently didn't apply for
-- either table. Granting explicitly rather than relying on that default.
-- Safe to re-run. StoneDesk (sd_employee_auth), SAIRNgrounds
-- (grd_employee_auth), and SAIRNscape (scp_employee_auth) were probed live
-- the same day and do NOT have this problem -- this is not a platform-wide
-- gap, just this one table.
grant select, insert, update on public.sb_employee_auth to service_role;
revoke all on public.sb_employee_auth from anon, authenticated;
