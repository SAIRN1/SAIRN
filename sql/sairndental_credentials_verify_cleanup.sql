-- sql/sairndental_credentials_verify_cleanup.sql
-- Two jobs, both needing DB access this session did not have.
-- NOT RUN as of 2026-08-24. Run in the Supabase SQL editor.
--
-- ── 1. THE APPEND-ONLY GRANT CHECK I COULD NOT RUN ───────────────────────
-- The production round trip proved append-only AT THE API LAYER: a duplicate
-- entry_id returned 409 DUPLICATE_ENTRY (a merge-duplicates upsert would have
-- returned 200), the 'delete' verb was refused by the action gate, and the
-- original row was byte-identical afterward.
--
-- That is NOT the same as proving the database grant. api/sd-data.js can only
-- issue the queries it is coded to issue, and it is coded never to UPDATE or
-- DELETE these rows -- so no request I can make through it will ever exercise
-- the grant. Proving the grant needs SQL run as service_role, which is this
-- file. Until it is run, "append-only is enforced at the database" is an
-- unverified claim, and should be described that way.
--
-- Expect the SELECT to return only INSERT and SELECT for dnt_credentials --
-- no UPDATE, no DELETE. If UPDATE or DELETE appears, the grant in
-- sairndental_credentials_schema.sql did not take and the append-only
-- guarantee is only as strong as the application code.
select privilege_type
  from information_schema.role_table_grants
 where grantee = 'service_role'
   and table_schema = 'public'
   and table_name = 'dnt_credentials'
 order by privilege_type;

-- And the direct proof. Run as service_role (NOT as postgres -- postgres owns
-- these tables and holds every privilege on them implicitly, so it would
-- succeed and tell you nothing; this is the same trap recorded in
-- sql/audit_log_immutability_verify.sql on 2026-08-23).
-- Both statements below should FAIL with permission denied:
--
--   set role service_role;
--   update public.dnt_credentials set data = '{}'::jsonb where entry_id = 'DCRED-VERIFY-LIC';
--   delete from public.dnt_credentials where entry_id = 'DCRED-VERIFY-LIC';
--   reset role;

-- ── 2. CLEAN UP THE VERIFICATION ROWS ────────────────────────────────────
-- Five rows written by the 2026-08-24 production round trip, all under the
-- existing test provider PV-VERIFY-1, all carrying VERIFY-ONLY as the licence
-- and DEA number so none can be mistaken for a real clinician's credential:
--
--   DCRED-VERIFY-LIC    state_license     expires 2026-09-23 (exactly 30 days out)
--   DCRED-VERIFY-DEA    dea_registration  expires 2026-10-23 (exactly 60 days out)
--   DCRED-VERIFY-CE     ce_cycle          2025-01-01 -> 2026-12-31, 5 hours logged
--   DCRED-VERIFY-CERT   certification     expires 2026-09-24 (31 days out)
--   DCRED-VERIFY-LIC2   state_license     expires 2028-09-23 (supersedes LIC)
--
-- THEY CANNOT BE REMOVED THROUGH THE APP, and that is the design working, not
-- a gap: dnt_credentials has no delete verb and no update path, deliberately,
-- because a credential row asserts that a named clinician held a real licence
-- on a real date. The same property that makes the record trustworthy makes a
-- test row permanent without SQL. Worth knowing before the next probe: write
-- fewer rows against this table than against a normal resource.
--
-- Scoped to the DCRED-VERIFY- prefix AND the test provider, so no real record
-- can be caught by it even if a prefix were reused by accident.
delete from public.dnt_credentials
 where entry_id like 'DCRED-VERIFY-%'
   and provider_id = 'PV-VERIFY-1';

-- Deliberately NOT deleted: the six rows in dnt_cred_rules. Those are the real
-- Ohio + federal requirements, loaded from
-- sql/sairndental_credentials_seed_ohio.json with their citations intact --
-- production data the practice needs, not test data. Leave them.

-- Verify after (expect 0):
--   select count(*) from dnt_credentials where entry_id like 'DCRED-VERIFY-%';
-- And confirm the real rules survived (expect 6):
--   select count(*) from dnt_cred_rules;
