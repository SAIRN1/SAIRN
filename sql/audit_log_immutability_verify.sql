-- sql/audit_log_immutability_verify.sql
-- CORRECTED immutability check for all three audit tables.
-- Read-only. Safe to run. Run this INSTEAD of the UPDATE/DELETE test.
--
-- ⚠ WHY THE PREVIOUS TEST WAS INVALID, and why its "SUCCESS" was not a
-- security finding:
--
-- The old check, printed at the bottom of each audit schema file, was:
--     update <table> set role = 'x';
--     delete from <table>;
--   ...run in the Supabase SQL editor, expecting "permission denied".
--   On 2026-08-24 both reported SUCCESS.
--
-- That is the expected result and it does NOT mean the grants are broken.
-- The SQL editor runs as the `postgres` role, and `postgres` OWNS these
-- tables -- every one of them was created by running these migrations in that
-- same editor. In PostgreSQL the owner of a table holds all privileges on it
-- implicitly. The migrations revoke from anon, authenticated and service_role.
-- They never revoke from postgres, so postgres was never subject to the
-- restriction being tested. The test asked the wrong role.
--
-- (Note the mechanism precisely: it is OWNERSHIP, not superuser. Supabase's
-- `postgres` role is deliberately NOT a superuser on hosted projects -- see
-- supabase.com/docs/guides/database/postgres/roles-superuser. It did not
-- bypass the grants; the grants simply never applied to it.)
--
-- WHAT ACTUALLY MATTERS: the application never connects as postgres. Every
-- write from api/_lib/audit.js authenticates with SUPABASE_SERVICE_ROLE_KEY,
-- which PostgREST maps to the `service_role` database role. service_role is
-- the role the immutability control is aimed at, so service_role is what has
-- to be tested.

-- ── CHECK 1: the definitive one. Non-destructive, exact, no role switching.
-- Expect for every row: sel = t, ins = t, upd = f, del = f
select
  t.tbl,
  has_table_privilege('service_role', t.tbl, 'SELECT') as sel,
  has_table_privilege('service_role', t.tbl, 'INSERT') as ins,
  has_table_privilege('service_role', t.tbl, 'UPDATE') as upd,
  has_table_privilege('service_role', t.tbl, 'DELETE') as del
from (values
  ('public.sairnlaw_audit_log'),
  ('public.sairncode_audit_log'),
  ('public.stonedesk_audit_log')
) as t(tbl);

-- Any row showing upd = t or del = t IS a real finding: that table's grants
-- are not doing their job and the fix belongs in that table's migration.

-- ── CHECK 2: behavioural confirmation, if you want to see the refusal.
-- Impersonates the role the app actually uses. Run one table at a time.
-- Wrapped in a transaction that is ROLLED BACK, so even if a statement
-- unexpectedly succeeds, nothing is lost -- unlike the original test, which
-- ran an unqualified DELETE outside a transaction.
--
--   begin;
--   set local role service_role;
--   -- expect: ERROR 42501 permission denied for table stonedesk_audit_log
--   update stonedesk_audit_log set role = 'x';
--   rollback;
--
--   begin;
--   set local role service_role;
--   -- expect: ERROR 42501 permission denied for table stonedesk_audit_log
--   delete from stonedesk_audit_log;
--   rollback;
--
-- `set local` confines the role change to the transaction, so a forgotten
-- `reset role` cannot leave the session impersonating service_role.

-- ── CHECK 3: what the grants literally are, if a number above looks wrong.
select grantee, privilege_type, table_name
  from information_schema.role_table_grants
 where table_name in ('sairnlaw_audit_log', 'sairncode_audit_log', 'stonedesk_audit_log')
 order by table_name, grantee, privilege_type;

-- ── WHAT THIS CONTROL DOES AND DOES NOT COVER, stated plainly because all
-- three schema headers previously overstated it as "IMMUTABLE BY DESIGN,
-- enforced at the DATABASE level" without this qualification:
--
--   COVERED: the application. No code path can alter or delete an audit row,
--   because service_role has no such privilege and api/_lib/audit.js issues
--   only POST. That is the threat this was built for -- a bug, a compromised
--   API key, or a future developer writing a "cleanup" routine.
--
--   NOT COVERED: anyone with dashboard/postgres access. They own the tables
--   and can always alter or drop them, and can re-grant themselves anything.
--   No table-level grant can prevent that; only moving the audit store
--   outside the same database's admin boundary would, which is a much larger
--   architectural decision and is NOT what these tables claim to do.
--
-- This is the normal and accepted posture -- dashboard access is trusted
-- administrative access -- but it should be written down rather than implied,
-- so nobody later reads "immutable" as "even I cannot change it".
