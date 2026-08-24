-- sql/sairnlaw_audit_log_schema.sql
-- SAIRNlaw immutable security audit log — Supabase schema
--
-- WHY THIS EXISTS: SAIRNlaw Phase 3 security hardening asked for full audit
-- logging of every sensitive action. Real scope check found that trust
-- transactions, document access, and matter changes are currently
-- localStorage-only in sairnlaw.html — they never reach the server, so
-- there is nothing for a server-side audit log to observe today. Building
-- a client-side "audit log" for those would be tamperable by the very user
-- it's meant to audit, which defeats the point. Decision (2026-08-08,
-- confirmed with Michael): scope this table to what genuinely already
-- crosses the server boundary — auth events and citator lookups — and
-- disclose the gap explicitly (see sairnlaw.html's security panel) rather
-- than fake coverage. Extending real audit logging to trust/document/
-- matter actions requires those features to become server-backed first
-- (a real sync layer, its own future build) — not done here.
--
--
-- SCOPE CORRECTION 2026-08-24. "Enforced at the DATABASE level" above is true
-- of the ROLE THE APPLICATION USES and nothing wider. It restricts
-- service_role, which is what api/_lib/audit.js authenticates as. It does NOT
-- restrict `postgres`, which OWNS this table and therefore holds every
-- privilege on it implicitly -- the revokes below never named postgres, so it
-- was never subject to them.
--
-- Found the hard way: the UPDATE/DELETE test printed at the bottom of this
-- file was run in the Supabase SQL editor on 2026-08-24 and both statements
-- SUCCEEDED. That was the expected result for that role, not a broken grant,
-- but the test as written could not tell the difference -- and on
-- stonedesk_audit_log the unqualified DELETE removed every row in the table.
--
-- Use sql/audit_log_immutability_verify.sql instead. It checks
-- has_table_privilege('service_role', ...) directly, which is exact,
-- non-destructive, and asks about the role that actually matters.
--
-- What this control covers: the application. No code path can alter or delete
-- an audit row. What it does not cover: anyone with dashboard/postgres
-- access, who owns these tables and can always change them. That is the
-- normal posture for a hosted Postgres, but it is written down here rather
-- than implied so nobody reads "immutable" as "even an administrator cannot
-- change it".
-- IMMUTABLE BY DESIGN, enforced at the DATABASE level, not just by
-- convention. Two independent things make that true:
--
--   1. service_role (the ONLY role this app uses against this table) is
--      granted SELECT and INSERT and nothing else. An UPDATE or DELETE
--      against this table fails with a Postgres permission error even if
--      someone later writes code that attempts one. This is the real
--      guarantee.
--   2. No UPDATE/DELETE path exists anywhere in the codebase today.
--
-- CORRECTION (2026-08-08): an earlier version of this header credited the
-- RLS insert-only policy below with preventing tampering. That was wrong
-- and is worth stating plainly rather than quietly editing — service_role
-- BYPASSES RLS entirely, so that policy does nothing for the only role
-- that ever reaches this table. The grants in point 1 are what actually
-- enforce immutability. The RLS policy is kept only as a second layer
-- against anon/authenticated, which additionally have no grants at all.

create table if not exists sairnlaw_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'login_success', 'login_failed', 'lockout',
    'pin_bootstrap', 'pin_setup',
    'mfa_enrolled', 'mfa_verified', 'mfa_failed',
    'sso_login', 'sso_link',
    'citator_lookup'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnlaw_audit_log_license_time
  on sairnlaw_audit_log (license_hash, created_at desc);

-- THE ACTUAL IMMUTABILITY CONTROL. Added 2026-08-08 after a real live
-- 42501 "permission denied" on the sibling employee_auth table proved
-- Supabase's default privileges had not been applied here. Safe to re-run.
--
-- SELECT + INSERT only. Deliberately NO update, NO delete: an audit trail
-- that the application can rewrite is not an audit trail, and this is the
-- line of SQL that makes that structural instead of aspirational.
grant select, insert on public.sairnlaw_audit_log to service_role;
revoke update, delete on public.sairnlaw_audit_log from service_role;
revoke all on public.sairnlaw_audit_log from anon, authenticated;

alter table sairnlaw_audit_log enable row level security;

-- Second layer, for anon/authenticated only (service_role bypasses RLS —
-- see the correction in this file's header). Those roles have no grants
-- either, so this is defense in depth, not the primary control.
drop policy if exists sairnlaw_audit_log_service_insert on sairnlaw_audit_log;
create policy sairnlaw_audit_log_service_insert
  on sairnlaw_audit_log for insert
  to service_role
  with check (true);
