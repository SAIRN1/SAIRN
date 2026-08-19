-- sql/sairnlegacy_audit_test_cleanup.sql
-- Removes one leftover audit-test case row found live on LEG-PINNACLE-2026
-- (2026-08-19) while checking for leftover sync-test rows before starting
-- SAIRNlegacy's AI-advancement rollout -- NOT the row
-- sql/sairnlegacy_synctest_cleanup.sql already covers (different id,
-- different origin: a manual "AUDIT TEST"-labeled case from an earlier
-- QA/audit pass, not the write-then-read sync-verification test). That
-- script's own target rows were confirmed already absent before this file
-- was written.
--
-- Confirmed live via:
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' -H 'Authorization: Bearer LEG-PINNACLE-2026' \
--     -d '{"action":"read","resource":"leg_cases"}'
--   -> {"ok":true,"data":[{"id":"CS-1786203942983-824","case_number":"FH-2026-004",
--        "decedent_name":"Dorothy Fenwick (AUDIT TEST)",...}],...}
--
-- No delete action exists in api/sd-data.js for leg_* resources (checked --
-- same as sdn_*, only SAIRNcode's sc_* resources have one), so this can't
-- be run through the app's own API; needs a direct Supabase SQL run, same
-- as every other one-off cleanup script in this directory.
--
-- Safe to run once; matches on the exact case_id only, nothing else in
-- this table is touched.

delete from public.leg_cases where case_id = 'CS-1786203942983-824';

-- Verify after running (expect 0 rows):
--   select count(*) from public.leg_cases where case_id = 'CS-1786203942983-824';
