-- sql/sairnfreedom_audit_log_schema.sql
-- ---------------------------------------------------------------------------
-- EXTRACTED 2026-10-11 FROM docs/2026-10-07-hank-migration-sql-for-michael.md
-- (STEP 12), BYTE-FOR-BYTE. Not re-authored here. That document remains the
-- one place the ORDER of the migration is stated; this file exists so the
-- statement is a .sql file in sql/ like every other schema on this platform.
--
-- WHY IT WAS EXTRACTED, which is a real reason and not tidying:
-- tools/audit_event_type_check.py compares every `event_type` a caller emits
-- against the CHECK constraint of the table it lands in, and it reads the
-- CHECK out of sql/*.sql. While this DDL existed only inside a markdown
-- document, the checker could not see the table at all -- so the thirteen
-- api/*-auth.js callers that gained `pin_setup` attribution on 2026-10-11
-- were reported CLEAN BY ABSENCE, which is the "silent universe" that tool's
-- own header warns about. With this file present the comparison is real.
--
-- NOT RUN. Nothing in this file has been executed against Supabase. Until
-- Michael runs it, api/_lib/audit.js's auditPinSetup() gets a 404 from
-- PostgREST for sairnfreedom, returns false, and the endpoint answers
-- `attributed: false`. The grant still succeeds -- a logging outage must never
-- block a legitimate grant -- but the attribution is absent and SAYS it is.
--
-- The code half is in api/sf-auth.js.
-- ---------------------------------------------------------------------------

create table if not exists public.sairnfreedom_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnfreedom_audit_log_license_time
  on public.sairnfreedom_audit_log (license_hash, created_at desc);

alter table public.sairnfreedom_audit_log enable row level security;
drop policy if exists "svc insert only sairnfreedom_audit_log" on public.sairnfreedom_audit_log;
create policy "svc insert only sairnfreedom_audit_log" on public.sairnfreedom_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnfreedom_audit_log from anon, authenticated;
revoke all on public.sairnfreedom_audit_log from service_role;
grant select, insert on public.sairnfreedom_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnfreedom_audit_log;
