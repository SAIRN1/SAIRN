-- sql/sd_employee_auth_schema.sql
-- StoneDesk per-employee RBAC credentials — Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as sql/agent_schema.sql
-- / sql/network_schema.sql) before api/sd-auth.js's login/setup/bootstrap
-- actions will work. Until this runs, those return a clear 503
-- NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: replaces StoneDesk's old auth-gate role scaffolding
-- (currentRole var, body.is-admin/is-exec classes, role-pill switcher,
-- DEFAULT_PINS = one shared 4-digit PIN per role, plaintext in the client
-- bundle). That system had no server involvement at all and no per-employee
-- identity — every Technician shared one PIN, so nothing could ever be
-- scoped to an individual, and any role could be self-asserted by editing
-- the DOM. This table is what api/sd-auth.js checks against instead.
--
-- NOT the same table as `employees` (owned/written by SAIRNbiz, StoneDesk
-- read-only per api/sd-data.js — name/role/hourly_rate/etc). This table is
-- StoneDesk's own, holds ONLY auth material (hashed PIN + StoneDesk access
-- role), and is looked up by employee_id to link back to that roster.
-- Deliberately not merged into `employees` — StoneDesk has no write access
-- there, and mixing auth secrets into a table another app owns/writes is
-- exactly the cross-system collision risk flagged elsewhere in this app's
-- history (see STONEDESK-SESSION72-HANDOFF.md, sd_slabs/sd_slab_tracker).
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN. Written
-- and verified only by api/_lib/auth.js on the server; the raw PIN is never
-- stored or logged. license_hash (not the raw license key) scopes rows to
-- a shop, matching business_profiles/sd_slabs' existing convention.
--
-- Design note: no RLS policy defined on purpose, same reasoning as
-- bridge_data/network_insights — read/write exclusively via api/sd-auth.js
-- and api/sd-data.js using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS
-- regardless. The anon key is never used against this table.

create table if not exists sd_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','admin','sales','install')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sd_employee_auth_license
  on sd_employee_auth (license_hash);

-- ---------------------------------------------------------------------------
-- ADDITIVE MIGRATION (2026-08-03, security-auditor finding on api/sd-auth.js):
-- the original table above shipped with no brute-force protection on PIN
-- login — a 4-digit PIN with zero attempt throttling is guessable in well
-- under 10,000 requests. Run this block too (safe to re-run — IF NOT EXISTS
-- throughout) even if the table above already exists in your Supabase project.
-- ---------------------------------------------------------------------------
alter table sd_employee_auth add column if not exists failed_attempts integer not null default 0;
alter table sd_employee_auth add column if not exists locked_until timestamptz;
