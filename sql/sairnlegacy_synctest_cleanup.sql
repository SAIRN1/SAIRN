-- sql/sairnlegacy_synctest_cleanup.sql
-- Removes the live write-then-read round-trip test rows created 2026-08-07
-- to verify sql/sairnlegacy_data_schema.sql + sql/sairnlegacy_license_seed.sql
-- work end-to-end (not just resource-name validation) -- same pattern as
-- sql/sairndesign_synctest_cleanup.sql and sql/rbac_test_artifact_cleanup.sql.
--
-- Test performed: wrote one record each to leg_cases, leg_vehicles, and
-- leg_monuments via LEG-PINNACLE-2026 in one request, then read each back
-- in a completely separate request (no shared connection/session) and
-- confirmed the written record was present. All three passed.
--
-- Safe to run once; matches on the exact test ids only, nothing else in
-- any of these tables is touched.

delete from public.leg_cases     where case_id     = 'SYNCTEST-CS-1786145858';
delete from public.leg_vehicles  where vehicle_id   = 'SYNCTEST-FV-1786145858';
delete from public.leg_monuments where monument_id  = 'SYNCTEST-MN-1786145858';
