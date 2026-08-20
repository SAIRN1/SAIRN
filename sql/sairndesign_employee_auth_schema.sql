-- sql/sairndesign_employee_auth_schema.sql
-- SAIRNdesign per-employee credentials -- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sdn-auth.js's
-- bootstrap/login/setup/roster actions will work. Until this runs, those
-- return a clear 503 NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: replaces sairndesign.html's old client-only auth gate
-- (DEFAULT_PINS = one shared PIN per role -- owner/designer/office --
-- stored in localStorage, zero server involvement, any role self-
-- assertable by editing the DOM). Direct model: sql/sairnlegacy_employee_auth_schema.sql
-- (built 2026-08-19 for the exact same reason -- SAIRNlegacy's shared-
-- knowledge permission gate). Per-employee identity is the prerequisite
-- for the real client/lead privacy rule this build exists for (Task 2,
-- platform-wide sales-lead-privacy rule): there is no way to scope a
-- client to "the assigned designer" when the server can't tell designers
-- apart in the first place.
--
-- SCOPE, deliberately minimal: no MFA, no SSO, no extra permission column
-- (unlike sairnlegacy_employee_auth's shared_knowledge_access -- this
-- app's assignment lives on the CLIENT record itself, see
-- sql/sairndesign_clients_assignment_migration.sql, not on the employee
-- row). Add more later as its own scoped change if actually needed.
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw license key) scopes rows to a studio,
-- matching every other *_employee_auth table's convention.
--
-- Design note: no RLS policy defined on purpose, same reasoning as every
-- other *_employee_auth table -- read/write exclusively via
-- api/sdn-auth.js (and api/sd-data.js's sdn_clients gate, read-only)
-- using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The
-- anon key is never used against this table.

create table if not exists sairndesign_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','designer','office')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairndesign_employee_auth_license
  on sairndesign_employee_auth (license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- same real incident sql/sairnlaw_employee_auth_schema.sql's own
-- header documents (a live 42501 "permission denied" the first time that
-- table was used, because Supabase's ALTER DEFAULT PRIVILEGES did not
-- apply automatically) -- granting explicitly up front here instead of
-- waiting to rediscover the same failure mode live.
--
-- Only the three verbs api/sdn-auth.js actually uses. No DELETE: nothing
-- in the codebase deletes a credential row (deactivation is active=false),
-- so withholding it costs nothing and removes a way to lose an audit
-- subject.
grant select, insert, update on public.sairndesign_employee_auth to service_role;

-- anon/authenticated must never touch this table -- it holds PIN hashes,
-- and is only ever reached through the server using the service-role key.
-- Revoking explicitly rather than assuming.
revoke all on public.sairndesign_employee_auth from anon, authenticated;
