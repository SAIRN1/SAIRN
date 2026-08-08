-- sql/sairnlaw_employee_auth_schema.sql
-- SAIRNlaw per-employee RBAC credentials + MFA + SSO — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/law-auth.js's
-- bootstrap/login/setup/mfa_*/sso_* actions will work. Until this runs,
-- those return a clear 503 NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: replaces sairnlaw.html's old client-only auth gate
-- (DEFAULT_PINS = one shared PIN per role — owner/attorney/paralegal —
-- stored in localStorage, zero server involvement, any role self-assertable
-- by editing the DOM). Same problem StoneDesk's old scaffold had, same
-- fix: sql/sd_employee_auth_schema.sql is the direct model for this file.
-- Per-employee identity is a prerequisite for MFA (a TOTP secret belongs
-- to one person, not a shared role PIN) and for real session independence
-- (see api/_lib/auth.js's 2026-08-08 comment on this exact point).
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- mfa_secret_encrypted is AES-256-GCM ciphertext (api/_lib/auth.js
-- encryptSecret/decryptSecret), never the raw TOTP secret — a TOTP secret
-- is a long-lived credential and can't be one-way hashed like a PIN
-- because the server must recompute the expected code from it.
-- license_hash (not the raw license key) scopes rows to a firm, matching
-- every other *_employee_auth table's convention.
--
-- Design note: no RLS policy defined on purpose, same reasoning as
-- sd_employee_auth — read/write exclusively via api/law-auth.js using
-- SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The anon key
-- is never used against this table.

create table if not exists sairnlaw_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','attorney','paralegal')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,

  -- MFA (TOTP, RFC 6238) — api/_lib/auth.js generateTotpSecret/verifyTotpCode.
  -- mfa_enabled only flips true once mfa_secret_encrypted has been confirmed
  -- with one real code (see api/law-auth.js mfa_enable) — a secret alone
  -- being present does not mean MFA is actually being enforced.
  mfa_enabled boolean not null default false,
  mfa_secret_encrypted text,

  -- SSO (OIDC) — the subject ("sub") claim from the identity provider's
  -- id_token, linking this employee record to their SSO identity. Null
  -- until the employee has completed an SSO login at least once and been
  -- linked (see api/law-auth.js sso_callback). A given sso_subject is
  -- unique per firm, not globally — two firms could share an IdP tenant.
  sso_subject text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnlaw_employee_auth_license
  on sairnlaw_employee_auth (license_hash);

create unique index if not exists idx_sairnlaw_employee_auth_sso_subject
  on sairnlaw_employee_auth (license_hash, sso_subject)
  where sso_subject is not null;

-- ---------------------------------------------------------------------------
-- GRANTS (added 2026-08-08 after a REAL live failure, not preemptively):
-- the first live call after this table was created returned Postgres 42501
-- "permission denied for table sairnlaw_employee_auth" — the table existed
-- but service_role had no privileges on it, so api/law-auth.js answered a
-- generic 502. Supabase's ALTER DEFAULT PRIVILEGES normally grants these
-- automatically for tables created in the SQL editor; it evidently did not
-- here. Granting explicitly rather than relying on that default, so this
-- file is self-sufficient and re-runnable. Safe to re-run.
--
-- Only the three verbs api/law-auth.js actually uses. No DELETE: nothing in
-- the codebase deletes a credential row (deactivation is active=false), so
-- withholding it costs nothing and removes a way to lose an audit subject.
grant select, insert, update on public.sairnlaw_employee_auth to service_role;

-- anon/authenticated must never touch this table — it holds PIN hashes and
-- encrypted MFA secrets, and is only ever reached through the server using
-- the service-role key. Revoking explicitly rather than assuming.
revoke all on public.sairnlaw_employee_auth from anon, authenticated;
