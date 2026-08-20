-- sql/sairnsenior_employee_auth_schema.sql
-- SAIRNsenior per-employee credentials -- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/sen-auth.js's
-- bootstrap/login/setup/roster actions will work. Until this runs, those
-- return a clear 503 NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: SAIRNsenior is built ground-up (like SAIRNlegacy/
-- SAIRNlaw/SAIRNbuild) -- real per-employee auth from day one, never a
-- client-only shared-PIN scaffold to begin with. Per-employee identity is
-- the prerequisite for the HIPAA minimum-necessary client-visibility gate
-- this app is built around: a caregiver must only ever see their own
-- assigned clients' health information, which is impossible to enforce
-- server-side without the server being able to tell caregivers apart.
--
-- SCOPE, deliberately minimal, same discipline as every other
-- *_employee_auth table this session: no MFA, no SSO, no extra permission
-- column -- add more later as its own scoped change if actually needed.
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw license key) scopes rows to one agency's
-- install, matching every other *_employee_auth table's convention.
--
-- Design note: no RLS policy defined on purpose, same reasoning as every
-- other *_employee_auth table -- read/write exclusively via
-- api/sen-auth.js (and api/sd-data.js's sen_clients gate, read-only)
-- using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The
-- anon key is never used against this table.

create table if not exists sairnsenior_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','scheduler','coordinator','billing','caregiver')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnsenior_employee_auth_license
  on sairnsenior_employee_auth (license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same real incident sql/sairnlaw_employee_
-- auth_schema.sql's own header documents (a live 42501 "permission denied"
-- the first time a table like this was used, because Supabase's ALTER
-- DEFAULT PRIVILEGES did not apply automatically).
--
-- Only the three verbs api/sen-auth.js actually uses. No DELETE: nothing
-- in the codebase deletes a credential row (deactivation is active=false),
-- so withholding it costs nothing and removes a way to lose an audit
-- subject.
grant select, insert, update on public.sairnsenior_employee_auth to service_role;

-- anon/authenticated must never touch this table -- it holds PIN hashes,
-- and is only ever reached through the server using the service-role key.
-- Revoking explicitly rather than assuming.
revoke all on public.sairnsenior_employee_auth from anon, authenticated;
