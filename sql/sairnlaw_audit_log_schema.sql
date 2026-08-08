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
-- IMMUTABLE BY DESIGN: insert-only from api/_lib/audit.js using
-- SUPABASE_SERVICE_ROLE_KEY. No UPDATE/DELETE path exists anywhere in this
-- app's code. RLS is enabled with an insert-only policy for the service
-- role and no update/delete policy at all, so even a compromised anon key
-- (which is never used against this table in the first place) could not
-- alter or remove a row — belt-and-suspenders on top of "the app just
-- never does it."

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

alter table sairnlaw_audit_log enable row level security;

-- Insert-only for the service role (what api/_lib/audit.js uses). No
-- select/update/delete policy is defined for anon/authenticated at all,
-- so this table is unreadable and unwritable except via the service-role
-- key, same as every other *_employee_auth table in this codebase.
drop policy if exists sairnlaw_audit_log_service_insert on sairnlaw_audit_log;
create policy sairnlaw_audit_log_service_insert
  on sairnlaw_audit_log for insert
  to service_role
  with check (true);
