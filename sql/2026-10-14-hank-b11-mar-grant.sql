-- sql/2026-10-14-hank-b11-mar-grant.sql
-- ===========================================================================
-- TWO BLOCKS, IN ORDER, ONE AT A TIME. Paste ONE block into the Supabase SQL
-- editor, run it, run its VERIFY, check the answer against the expected result
-- printed beside it, and only then move to the next.
--
-- THIS FILE DOES NOT REPLACE sql/2026-10-14-michael-run-order.sql and does not
-- edit it. That file's six blocks still stand and none of them is repeated
-- here. These two are b11's additions and they are kept separate so that a
-- file already part-run does not change under you mid-migration.
--
-- ── ONE PREREQUISITE, AND IT IS IN THE OTHER FILE ─────────────────────────
-- BLOCK 5 of sql/2026-10-14-michael-run-order.sql adds `office_manager` to the
-- sairncare_employee_auth role CHECK. Nothing here depends on it to RUN -- both
-- blocks below are valid on their own -- but until it is run no employee can
-- hold the only role permitted to grant, so the feature has no grantor. If you
-- run only one thing, run that one first.
--
-- ── EVERY BLOCK IS INDEPENDENTLY RUNNABLE AND IDEMPOTENT ──────────────────
-- Running either twice is safe and changes nothing the second time. NO
-- TRANSACTION SPANS TWO BLOCKS.
--
-- BLOCK 2 CARRIES ITS OWN begin;/commit; AND MUST BE PASTED WHOLE. Between its
-- DROP and its ADD the audit table accepts ANY event_type, and the editor
-- reports success for the statements it did run.
--
-- ── WHY A VERIFY ON EVERY BLOCK, AND WHY ITS ANSWER IS PRINTED ────────────
-- `create table if not exists` SKIPS an existing table, constraint and all,
-- and the editor reports SUCCESS for it. Block 2 exists precisely because
-- block 1's source file cannot widen a constraint on a table that is already
-- there. A clean run is NOT evidence; the verify's answer is. "Could not tell"
-- is a third state and is never the same as "done".
--
-- ── THIS FILE IS AN EXTRACTION, NOT A SECOND AUTHORING ────────────────────
-- Block 1's statements are verbatim from the file named in its header. Block 2
-- is a MIGRATION and has no verbatim source -- it is the drop/add that the
-- schema file's `if not exists` cannot perform -- so its role list is instead
-- checked against that file's CHECK by the extraction note in the block.
--
-- THE SOURCES, AND THEIR SHA256 AT ASSEMBLY (LF-normalised):
--   0ad0ea4bb79404f1c0ef0fadfdb5b9a9fb9283959529fb603724b637c3ae549b  sql/sairncare_mar_access_grants_schema.sql
--   4a293a85899e4bf8ba92c00b1702f0083367a7c550dc9df7752ae6446e6ee1b0  sql/sairncare_audit_log_schema.sql
--
-- ── WHAT IS LIVE WITHOUT THIS FILE, SAID PLAINLY ──────────────────────────
-- The code half deploys with Vercel and is already fail-closed: `billing` is
-- refused on family_mar from the moment api/sd-data.js is live, which is the
-- security half of the decision and needs no SQL. What needs these two blocks
-- is the CAPABILITY half -- a grant that can be written, found and audited.
-- Until they run, `mar_access_grant` answers 503 NOT_PROVISIONED naming this
-- file, and the three audit event types are rejected by the audit table's
-- CHECK, so the writes return false and log nothing.
-- ===========================================================================


-- ===========================================================================
-- BLOCK 1 -- THE GRANT TABLE
-- source: sql/sairncare_mar_access_grants_schema.sql
-- ===========================================================================
-- One row is ONE grant: one named employee, one family contact and the one
-- resident on that contact's stored row, with an expiry.
--
-- UPDATE IS GRANTED AND DELETE IS NOT, which is a deliberate difference from
-- the audit log. Revocation before the expiry is an UPDATE of revoked_at; a
-- deleted grant is an access decision nobody can reconstruct, and the reads it
-- authorised point at a grant_id that would no longer resolve.

create table if not exists public.alf_mar_access_grants (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  grant_id text not null,
  contact_id text not null,
  resident_id text not null,
  grantee_employee_id text not null,
  granted_by text not null,
  reason text,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (license_hash, grant_id)
);

create index if not exists idx_alf_mar_access_grants_lookup
  on public.alf_mar_access_grants (license_hash, contact_id, grantee_employee_id);

alter table public.alf_mar_access_grants enable row level security;
drop policy if exists "svc all alf_mar_access_grants" on public.alf_mar_access_grants;
create policy "svc all alf_mar_access_grants" on public.alf_mar_access_grants for all using (true) with check (true);

revoke all on public.alf_mar_access_grants from anon, authenticated;
revoke all on public.alf_mar_access_grants from service_role;
grant select, insert, update on public.alf_mar_access_grants to service_role;

-- ── VERIFY BLOCK 1 ─────────────────────────────────────────────────────────
-- EXPECTED: exactly 3 rows -- 'SELECT', 'INSERT' and 'UPDATE' -- and NOTHING
-- ELSE. A 'DELETE' row means the revoke did not take and a grant can be
-- destroyed. ZERO rows means the table was not created at all; if you get zero
-- rows with no error, the block did not run.
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public'
   and table_name = 'alf_mar_access_grants'
   and grantee = 'service_role'
 order by privilege_type;

-- ── SECOND VERIFY FOR BLOCK 1 ──────────────────────────────────────────────
-- EXPECTED: exactly 1 row, with count = 0. The table exists and is empty. An
-- error here ("relation does not exist") is the answer that says block 1 did
-- not run, and is NOT the same as an empty table.
select count(*) as grant_rows from public.alf_mar_access_grants;


-- ===========================================================================
-- BLOCK 2 -- THE THREE MAR-GRANT AUDIT EVENT TYPES
-- source: sql/sairncare_audit_log_schema.sql (the CHECK list, widened)
-- ===========================================================================
-- WHY THIS IS A SEPARATE BLOCK AND NOT PART OF THE SCHEMA FILE. That file is
-- `create table if not exists`, which is a no-op on an existing table --
-- constraint and all -- and the editor reports SUCCESS. If sairncare_audit_log
-- already exists, running the schema file widens nothing.
--
-- WHAT GOES WRONG WITHOUT IT, and it is silent: an event_type outside the
-- CHECK makes writeAuditLog's POST fail; the function returns false and logs
-- server-side only (api/_lib/audit.js:131-134). The grant still succeeds -- a
-- logging outage must never block a legitimate action -- and the audit row
-- simply does not exist. A grant with no record of who made it is the one
-- outcome this feature must not have.
--
-- THE FULL LIST IS RESTATED because `add constraint` replaces the whole
-- predicate. It is a strict superset of the existing five, so every existing
-- row satisfies it. The eight values here are the eight in
-- sql/sairncare_audit_log_schema.sql's CHECK, in the same order.
--
-- WRAPPED IN begin;/commit; AND PASTED WHOLE: between the DROP and the ADD the
-- table accepts any event_type at all.
--
-- THE CONSTRAINT NAME. `create table` names an inline column CHECK
-- `<table>_<column>_check`, so sairncare_audit_log_event_type_check is the
-- name Postgres will have given it. `drop constraint if exists` makes a wrong
-- guess harmless rather than fatal -- but it also makes it SILENT, so the
-- verify below reads the constraint back and its answer is what tells you the
-- drop found its target. If the verify returns the OLD five-value definition,
-- the ADD collided with a constraint under a different name: list them with
--   select conname from pg_constraint
--    where conrelid = 'public.sairncare_audit_log'::regclass;
-- and re-run with the real name.

begin;
alter table public.sairncare_audit_log
  drop constraint if exists sairncare_audit_log_event_type_check;
alter table public.sairncare_audit_log
  add constraint sairncare_audit_log_event_type_check
  check (event_type in ('pin_bootstrap',
                        'pin_setup',
                        'credential_deactivated',
                        'credential_reactivated',
                        'credential_change_refused',
                        'mar_access_granted',
                        'mar_access_grant_refused',
                        'mar_access_read'));
commit;

-- ── VERIFY BLOCK 2 ─────────────────────────────────────────────────────────
-- EXPECTED: exactly 1 row, and its text must contain ALL THREE of
-- 'mar_access_granted', 'mar_access_grant_refused' and 'mar_access_read'
-- alongside the five existing values. If any of the three is absent the ALTER
-- did not run, and the audit writes will be rejected silently.
-- ZERO rows means the constraint is not there under this name -- see the note
-- above the block, and do not read zero rows as "nothing to do".
select pg_get_constraintdef(c.oid) as event_type_check
  from pg_constraint c
 where c.conname = 'sairncare_audit_log_event_type_check';

-- ── SECOND VERIFY FOR BLOCK 2 ──────────────────────────────────────────────
-- EXPECTED: exactly 1 row, with ok = true. This asks the same question as a
-- boolean rather than by eye, because reading three substrings out of a long
-- constraint definition is where a tired reviewer says yes to five values and
-- misses the third new one.
select pg_get_constraintdef(c.oid) like '%mar_access_granted%'
   and pg_get_constraintdef(c.oid) like '%mar_access_grant_refused%'
   and pg_get_constraintdef(c.oid) like '%mar_access_read%' as ok
  from pg_constraint c
 where c.conname = 'sairncare_audit_log_event_type_check';
