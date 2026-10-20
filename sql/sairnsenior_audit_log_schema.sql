-- sql/sairnsenior_audit_log_schema.sql
-- ---------------------------------------------------------------------------
-- EXTRACTED 2026-10-11 FROM docs/2026-10-07-hank-migration-sql-for-michael.md
-- (STEP 11), BYTE-FOR-BYTE. Not re-authored here. That document remains the
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
-- PostgREST for sairnsenior, returns false, and the endpoint answers
-- `attributed: false`. The grant still succeeds -- a logging outage must never
-- block a legitimate grant -- but the attribution is absent and SAYS it is.
--
-- The code half is in api/sen-auth.js.
-- ---------------------------------------------------------------------------

create table if not exists public.sairnsenior_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused',
    -- ── b17, 2026-10-15. CLOSING A PAY PERIOD FREEZES WAGES ALREADY PAID,
    -- so the endpoint REFUSES the close when this row cannot be written
    -- (503 AUDIT_UNAVAILABLE) rather than closing unattributed. That is a
    -- deliberate departure from this platform's best-effort audit posture
    -- and api/sd-data.js's branch states why: a grant blocked by a logging
    -- outage locks somebody out of their own app, whereas a pay-period close
    -- is retryable a minute later and is audited precisely because it moves
    -- money.
    --
    -- SO THIS LINE IS LOAD-BEARING. Until this file is RUN, every attempt to
    -- close a pay period answers 503 and names this file. An event_type
    -- missing from a CHECK constraint is a SILENTLY DROPPED audit row
    -- everywhere else on this platform; here it is a refusal, which is the
    -- one place that failure mode is visible.
    'pay_period_closed',
    -- b17, 2026-10-16. REOPENING a closed period is the other half of the
    -- same control and is audited for a stronger reason: a close freezes a
    -- figure, a REOPEN un-freezes one, and an un-freeze nobody is recorded as
    -- having made is the silent restatement the whole mechanism exists to
    -- prevent. The handler refuses the reopen (503 AUDIT_UNAVAILABLE) if this
    -- row cannot be written, same as the close. One row per event, in
    -- public.sen_period_closings, and this is its audit trail.
    'pay_period_reopened'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnsenior_audit_log_license_time
  on public.sairnsenior_audit_log (license_hash, created_at desc);

alter table public.sairnsenior_audit_log enable row level security;
drop policy if exists "svc insert only sairnsenior_audit_log" on public.sairnsenior_audit_log;
create policy "svc insert only sairnsenior_audit_log" on public.sairnsenior_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnsenior_audit_log from anon, authenticated;
revoke all on public.sairnsenior_audit_log from service_role;
grant select, insert on public.sairnsenior_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnsenior_audit_log;

-- ── ON AN EXISTING TABLE THE CHECK ABOVE DOES NOTHING (b33, 2026-10-20) ─────
-- `create table if not exists` skips a table that is already there, constraint
-- and all. The live table predates 'pay_period_closed'/'pay_period_reopened', so
-- every pay-period close answered 503 AUDIT_UNAVAILABLE. The widening is
-- sql/sairnsenior_audit_log_event_types_widen_2026-10-20.sql -- run that.
