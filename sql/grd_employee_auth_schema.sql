-- sql/grd_employee_auth_schema.sql
-- SAIRNgrounds per-employee credentials — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/grd-auth.js's
-- login/setup/bootstrap actions will work.
--
-- Mirrors sql/sb_employee_auth_schema.sql exactly (same design, separate
-- table + separate role vocabulary) — a DELIBERATELY separate identity
-- system from StoneDesk/SAIRNbiz, not a merge, per the platform's existing
-- cross-app-collision discipline (api/_lib/auth.js's ROLES_BY_APP + the
-- signed `app` claim inside each token, unforgeable and distinct per app).
--
-- Roles match SAIRNgrounds' Phase 1 role picker (sairngrounds.html) plus
-- 'owner' for bootstrap, consistent with every other app's convention that
-- the first credential provisioned for a license is always Owner.
--
-- Same security notes as every prior *_employee_auth_schema.sql: pin_hash
-- is scrypt(pin, pin_salt), never the raw PIN; license_hash (not the raw
-- license key) scopes rows to one tenant; no RLS by design (service-role
-- only, reached exclusively through api/grd-auth.js and api/sd-data.js).

create table if not exists grd_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','superintendent','manager','crew','office')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_grd_employee_auth_license
  on grd_employee_auth (license_hash);
