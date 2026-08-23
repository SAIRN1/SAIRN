-- sql/stonedesk_audit_log_schema.sql
-- StoneDesk immutable credential audit log — Supabase schema.
--
-- ⚠ NOT YET RUN. Written 2026-08-23 and flagged for Michael to run in the
-- Supabase SQL editor. Until it exists, api/sd-auth.js's credential-lifecycle
-- action cannot be audited, which is why StoneDesk's half of that feature is
-- deliberately NOT shipping ahead of this file. SAIRNcode's equivalent
-- already has its table (sql/sairncode_audit_log_schema.sql, live) and ships
-- first.
--
-- WHY THIS EXISTS: StoneDesk had no audit table at all. api/_lib/audit.js
-- allowlists exactly two targets (sairnlaw_audit_log, sairncode_audit_log),
-- so a StoneDesk credential change had nowhere to be recorded. That gap is
-- sharper than it sounds: deactivating an employee credential is an
-- access-control event, and the whole reason the credential-lifecycle action
-- is being added is that three StoneDesk licenses were already lost to
-- untracked, unrecoverable credential state (SD-PINNACLE-2026's PIN is still
-- undocumented; SD-AUDIT-2026 needed a hand-written DELETE; SD-PARTNER-2026
-- was provisioned to route around both). An unlogged fix for that problem
-- would repeat its root cause.
--
-- Modelled directly on sql/sairncode_audit_log_schema.sql -- same shape, same
-- immutability posture, same reasoning. Deliberately NOT a generalised
-- multi-app table: per-app tables keep one app's retention or access decision
-- from silently becoming every app's.
--
-- IMMUTABLE BY DESIGN, enforced at the DATABASE level. service_role (the only
-- role that ever reaches this table) is granted SELECT and INSERT and nothing
-- else, so an UPDATE or DELETE fails with a Postgres permission error even if
-- code is later written that attempts one. Per the correction recorded in
-- SAIRNlaw's schema header: service_role BYPASSES RLS, so the RLS policy
-- below is NOT what enforces immutability -- the grants are. RLS is kept only
-- as a second layer against anon/authenticated, which have no grants at all.

create table if not exists stonedesk_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_stonedesk_audit_log_license_time
  on stonedesk_audit_log (license_hash, created_at desc);

-- The event_type CHECK starts narrow ON PURPOSE -- only the credential
-- lifecycle events that exist today. Adding a value later is a deliberate,
-- reviewable migration; an open text column would let any future caller
-- invent an event name and quietly change what this log means.
--
-- DELIBERATELY NOT STORED: PIN hashes, PIN salts, lockout state, or any
-- credential material. `detail` carries only non-secret metadata about the
-- change: which employee_id was targeted, that employee's role, the previous
-- and new active state, the reason text an admin supplied, and the count of
-- remaining active admins. employee_id at the top level is the ACTOR who made
-- the change, not the target -- the target lives in detail, so "who did this"
-- and "who was it done to" can never be confused when reading the log back.

alter table stonedesk_audit_log enable row level security;
drop policy if exists "svc insert only stonedesk_audit_log" on stonedesk_audit_log;
create policy "svc insert only stonedesk_audit_log" on stonedesk_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
revoke all on stonedesk_audit_log from anon, authenticated;
revoke all on stonedesk_audit_log from service_role;
grant select, insert on stonedesk_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from stonedesk_audit_log;
-- Confirm immutability (both should FAIL with permission denied):
--   update stonedesk_audit_log set role = 'x';
--   delete from stonedesk_audit_log;
--
-- AFTER RUNNING THIS, one code change is still required before it records
-- anything: add 'stonedesk_audit_log' to AUDIT_TABLES in api/_lib/audit.js
-- (that allowlist exists precisely so a table name can never be interpolated
-- into a REST URL unchecked). That change ships with StoneDesk's
-- credential-lifecycle action, not with this file.
