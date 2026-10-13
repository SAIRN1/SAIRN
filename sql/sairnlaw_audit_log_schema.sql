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
  -- ── AMENDED 2026-10-13 TO MATCH THE DATABASE, not to change it ───────────
  -- THE SOURCE IS STEP 0c of docs/2026-10-07-hank-migration-sql-for-michael.md,
  -- copied value-for-value, which Michael ran live on 2026-10-13. This was the
  -- biggest of the three stale files -- six values the code emits and this list
  -- rejected -- and it was the one the first printing of that migration MISSED
  -- entirely; it was found only when the sweep was run over the whole
  -- population instead of by hand on two tables.
  --
  -- RE-RUNNING THIS FILE DOES NOT WIDEN AN EXISTING TABLE -- `create table if
  -- not exists` skips it, constraint and all.
  --
  -- TWO ALTERs NOW APPLY TO THIS TABLE AND THEY ARE IN DIFFERENT STATES. Said
  -- plainly, because a reader who saw only the first sentence would conclude the
  -- list below is live:
  --   * STEP 0c of docs/2026-10-07-hank-migration-sql-for-michael.md -- the six
  --     ai_/deadline_/legal_reference values. RUN on 2026-10-13. APPLIED.
  --   * the block AT THE FOOT OF THIS FILE -- the three credential-lifecycle
  --     values added 2026-10-13 (b8). NOT RUN AS AT THIS COMMIT. Until it is,
  --     every deactivation, reactivation and refusal in SAIRNlaw silently
  --     writes no audit row.
  event_type text not null check (event_type in (
    'login_success', 'login_failed', 'lockout',
    'pin_bootstrap', 'pin_setup',
    'mfa_enrolled', 'mfa_verified', 'mfa_failed',
    'sso_login', 'sso_link',
    'citator_lookup',
    'ai_interaction',
    'ai_rejected',
    'ai_reviewed',
    'ai_used_in_filing',
    'deadline_engine',
    'legal_reference_lookup',
    -- ── THE CREDENTIAL LIFECYCLE, ADDED 2026-10-13 ─────────────────────────
    -- EVERY DEACTIVATION, REACTIVATION AND REFUSAL IN SAIRNlaw WAS FAILING TO
    -- WRITE ITS AUDIT ROW, silently. api/law-auth.js's set_active calls the
    -- shared engine in api/_lib/employee-lifecycle.js, which emits
    -- `credential_deactivated` / `credential_reactivated` (line 301) and
    -- `credential_change_refused` on three separate refusal paths (lines 202,
    -- 214, 267). This CHECK rejected all three, and writeAuditLog is NON-FATAL
    -- and returns false -- so the calling code carried on, the caller got its
    -- 200, and the row was simply absent. An audit log that silently drops the
    -- one event class it exists to record for credentials is worse than no log,
    -- because its emptiness reads as "nothing happened".
    --
    -- MEASURED ACROSS THE WHOLE POPULATION, not just here: ELEVEN api/*-auth.js
    -- files call lifecycle.setActive, and SAIRNlaw was the ONLY ONE of the
    -- eleven whose CHECK rejected these three. The other ten already permit
    -- them. That is why this is a one-table fix and the denominator is stated
    -- rather than implied.
    --
    -- WHY NO CHECKER CAUGHT IT: tools/audit_event_type_check.py resolves helper
    -- call sites through `const APP`, and it follows ONE helper -- the pin-setup
    -- one -- which its own LIMITS section says out loud. The lifecycle engine is
    -- a second helper and is not followed, so these emissions are invisible to
    -- it. The tool exits 0 today with this gap live. Extending it is routed
    -- rather than done here: tools/ is cc's.
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
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

-- ═══════════════════════════════════════════════════════════════════════════
-- THE CREDENTIAL-LIFECYCLE WIDENING -- 2026-10-13, ONE IDEMPOTENT BLOCK
-- ═══════════════════════════════════════════════════════════════════════════
-- RUN THIS. The `create table if not exists` above does NOT amend an existing
-- table -- it skips it, constraint and all -- so on the live database the three
-- values added to the inline list above are not permitted until these two
-- statements run. A re-run of the file alone reports success and changes
-- nothing, which is the silent no-op that cost thirteen audit logs their
-- tamper-evidence until 2026-10-13.
--
-- WHAT IS BROKEN UNTIL IT RUNS: every credential deactivation, reactivation and
-- refusal in SAIRNlaw writes no audit row. The INSERT is rejected 23514,
-- writeAuditLog is non-fatal and returns false, api/law-auth.js carries on, and
-- the caller gets a 200. Nothing anywhere says the row is missing.
--
-- IDEMPOTENT BY CONSTRUCTION: `drop constraint if exists` makes the `add` safe
-- on a second run, and the name is the one Postgres generates for the inline
-- CHECK above.
--
-- SAFE AGAINST EXISTING ROWS: the new list is a strict SUPERSET of the old
-- seventeen, so every stored row satisfies it and the validation scan cannot
-- fail.
--
-- THE FULL LIST IS RESTATED rather than appended to, because `add constraint`
-- replaces the whole predicate. Dropping a value here REVOKES it, so the
-- seventeen that were already permitted are all present below -- checked
-- against the inline CHECK above, not retyped from memory.
alter table public.sairnlaw_audit_log
  drop constraint if exists sairnlaw_audit_log_event_type_check;
alter table public.sairnlaw_audit_log
  add constraint sairnlaw_audit_log_event_type_check
  check (event_type in (
    'login_success',
    'login_failed',
    'lockout',
    'pin_bootstrap',
    'pin_setup',
    'mfa_enrolled',
    'mfa_verified',
    'mfa_failed',
    'sso_login',
    'sso_link',
    'citator_lookup',
    'ai_interaction',
    'ai_rejected',
    'ai_reviewed',
    'ai_used_in_filing',
    'deadline_engine',
    'legal_reference_lookup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  ));

-- ── VERIFY, with the answer each must give ────────────────────────────────
-- 1. TWENTY event types are permitted. Expect: 20
select count(*)
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairnlaw_audit_log_event_type_check';

-- 2. And the three new ones are among them. Expect exactly 3 rows.
select m[1] as event_type
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z0-9_]+)''', 'g') m
 where c.conname = 'sairnlaw_audit_log_event_type_check'
   and m[1] in ('credential_deactivated', 'credential_reactivated',
                'credential_change_refused')
 order by 1;

-- 3. THEN PROVE IT END TO END, because a permitted value is not a written row.
--    Deactivate a non-provisioning SAIRNlaw credential through the API, then:
--
--      select event_type, employee_id, created_at
--        from public.sairnlaw_audit_log
--       where event_type like 'credential_%'
--       order by created_at desc limit 5;
--
--    One or more rows -> the widening landed AND the emission path works
--    ZERO rows        -> this block has not been run, or the emission never
--                        fired. Those are different problems: query 1 tells
--                        them apart.
