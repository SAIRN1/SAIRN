-- sql/sairnsenior_audit_log_event_types_widen_2026-10-20.sql
--
-- ROOT CAUSE OF THE LIVE 503 AUDIT_UNAVAILABLE ON A PAY-PERIOD CLOSE (b33, hank).
-- An INFRA (schema-drift) gap, not an app bug: the close path is right to refuse.
--
-- b17 (2026-10-15/16) added 'pay_period_closed' and 'pay_period_reopened' to the
-- CHECK constraint inside sql/sairnsenior_audit_log_schema.sql -- but inside a
-- `create table if not exists`, which SKIPS an existing table, constraint and all.
-- The table was created on 2026-10-12, before b17. MEASURED in
-- db/schema_snapshot.json (generated 2026-10-20 07:55 UTC): the live constraint
-- sairnsenior_audit_log_event_type_check lists five values and NOT these two.
--
-- So every close inserts an audit row the database rejects (23514), writeAuditLog
-- returns false, and api/sd-data.js refuses the close 503 AUDIT_UNAVAILABLE --
-- deliberately, because a wage freeze nobody is recorded as having made is worse
-- than one retried. The same trap is already written up at the bottom of
-- sql/sairnlaw_employee_auth_schema.sql; this is that fix for this table.
--
-- RUN THIS ONCE in the Supabase SQL editor. Not run by me (no database access).
-- IF RUN TWICE: identical result -- the constraint is dropped and re-added with
-- the same seven values inside one transaction; no rows change.
-- EXISTING ROWS ARE SAFE: all of them carry one of the five old values, which are
-- all kept, so the new constraint validates against them.
-- ---------------------------------------------------------------------------

begin;
alter table public.sairnsenior_audit_log
  drop constraint if exists sairnsenior_audit_log_event_type_check;
alter table public.sairnsenior_audit_log
  add constraint sairnsenior_audit_log_event_type_check
  check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused',
    'pay_period_closed',
    'pay_period_reopened'
  ));
commit;

-- VERIFY (read-only). Expect ONE row whose definition contains both
-- 'pay_period_closed' and 'pay_period_reopened'.
select conname, pg_get_constraintdef(c.oid) as definition,
       (pg_get_constraintdef(c.oid) like '%pay_period_closed%'
        and pg_get_constraintdef(c.oid) like '%pay_period_reopened%') as has_both
  from pg_constraint c
 where c.conrelid = 'public.sairnsenior_audit_log'::regclass
   and c.contype = 'c';
