-- sql/sairnlegacy_employee_auth_schema.sql
-- SAIRNlegacy per-employee credentials -- Supabase schema
--
-- Run this once in the Supabase SQL editor before api/leg-auth.js's
-- bootstrap/login/setup/grant_shared_knowledge_access actions will work.
-- Until this runs, those return a clear 503 NOT_PROVISIONED rather than a
-- generic 500.
--
-- WHY THIS EXISTS: replaces sairnlegacy.html's old client-only auth gate
-- (DEFAULT_PINS = one shared PIN per role -- owner/director/staff --
-- stored in localStorage, zero server involvement, any role self-
-- assertable by editing the DOM). Direct model: sql/sairnlaw_employee_auth_schema.sql
-- (SAIRNlaw's own Phase 3 hardening away from the identical starting
-- scaffold). Per-employee identity is a prerequisite for the real
-- shared-knowledge permission gate Michael asked for (management/owner-
-- tier by default, individually grantable to specific staff) -- there is
-- no way to grant access to "a specific individual staff member" when the
-- server has no way to tell staff members apart in the first place.
--
-- SCOPE, deliberately smaller than SAIRNlaw's table: no MFA columns, no
-- SSO columns -- not asked for here, and an unused column is exactly the
-- kind of dead-schema drift Guardian's dormant-code rule flags elsewhere
-- in this project. Add them later as their own scoped change if actually
-- needed, same as SAIRNlaw did in a later pass on top of its own simpler
-- start.
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw license key) scopes rows to a funeral home,
-- matching every other *_employee_auth table's convention.
--
-- Design note: no RLS policy defined on purpose, same reasoning as every
-- other *_employee_auth table -- read/write exclusively via
-- api/leg-auth.js (and api/sd-data.js's shared_knowledge gate, read-only)
-- using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The
-- anon key is never used against this table.

create table if not exists sairnlegacy_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  -- 'staff' is DEPRECATED (2026-10-14) and stays in this list on purpose:
  -- every existing row has to remain valid while a human re-assigns each
  -- person to a task role. api/_lib/leg-roles.js maps it to the NARROWEST
  -- band -- operations read/write, no money, no regulated write -- because a
  -- migration that promoted it to 'arranger' would grant 15 money resources
  -- to everyone who had a login yesterday.
  role text not null check (role in ('owner','director','arranger','prep','office','apprentice','livery','staff')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,

  -- The real permission-grant mechanism (2026-08-19): owner/director get
  -- shared-knowledge access by role alone (checked in code, not this
  -- column); this column is what lets an owner extend that to one named
  -- staff member without changing their role. Checked fresh from this
  -- table on every shared_knowledge call (api/sd-data.js), not embedded
  -- in the session token -- a revoke takes effect immediately rather than
  -- waiting out the token's 12h lifetime.
  shared_knowledge_access boolean not null default false,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnlegacy_employee_auth_license
  on sairnlegacy_employee_auth (license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- same real incident sql/sairnlaw_employee_auth_schema.sql's own
-- header documents (a live 42501 "permission denied" the first time that
-- table was used, because Supabase's ALTER DEFAULT PRIVILEGES did not
-- apply automatically) -- granting explicitly up front here instead of
-- waiting to rediscover the same failure mode live.
--
-- Only the three verbs api/leg-auth.js actually uses. No DELETE: nothing
-- in the codebase deletes a credential row (deactivation is active=false),
-- so withholding it costs nothing and removes a way to lose an audit
-- subject.
grant select, insert, update on public.sairnlegacy_employee_auth to service_role;

-- anon/authenticated must never touch this table -- it holds PIN hashes,
-- and is only ever reached through the server using the service-role key.
-- Revoking explicitly rather than assuming.
revoke all on public.sairnlegacy_employee_auth from anon, authenticated;

-- ═══════════════════════════════════════════════════════════════════════════
-- THE FIVE TASK ROLES -- 2026-10-14, ONE IDEMPOTENT BLOCK
-- ═══════════════════════════════════════════════════════════════════════════
-- RUN THIS. The `create table if not exists` above does NOT amend an existing
-- table, so on the live database the five task roles are REJECTED until these
-- two statements run, even though the inline list now carries them -- and the
-- 36-resource role matrix in api/_lib/leg-roles.js cannot be USED, because
-- nobody can be given a role other than owner/director/staff.
--
-- 'staff' IS IN THE LIST AND MUST STAY. It is deprecated, not removed: every
-- existing credential row holds it, and dropping the value here would make
-- every one of them violate the constraint and the ALTER itself would fail on
-- the validation scan. The deprecation is enforced where it belongs -- in
-- api/_lib/leg-roles.js, which maps it to the narrowest band, and in
-- sairnlegacy.html's provisioning picker, which no longer offers it.
--
-- IDEMPOTENT BY CONSTRUCTION, SAFE AGAINST EXISTING ROWS (strict superset),
-- FULL LIST RESTATED because `add constraint` replaces the whole predicate.
alter table public.sairnlegacy_employee_auth
  drop constraint if exists sairnlegacy_employee_auth_role_check;
alter table public.sairnlegacy_employee_auth
  add constraint sairnlegacy_employee_auth_role_check
  check (role in ('owner','director','arranger','prep','office',
                  'apprentice','livery','staff'));

-- VERIFY. Expect exactly 1 row, and the definition must contain all eight.
select pg_get_constraintdef(c.oid) as role_check
  from pg_constraint c
 where c.conname = 'sairnlegacy_employee_auth_role_check';
