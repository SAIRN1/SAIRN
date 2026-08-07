-- sql/sairndesign_synctest_cleanup.sql
-- Removes the live write-then-read round-trip test rows created 2026-08-07
-- to verify sql/sairndesign_data_schema.sql + sql/sairndesign_license_seed.sql
-- actually work end-to-end (not just resource-name validation) -- same
-- verify-live, clean-up-after pattern as sql/rbac_test_artifact_cleanup.sql.
--
-- Test performed: wrote one record each to sdn_clients, sdn_vendors, and
-- sdn_roomdims via SDN-PINNACLE-2026 in one request, then read each back
-- in a completely separate request (no shared connection/session) and
-- confirmed the written record was present. All three passed.
--
-- Safe to run once; matches on the exact test ids only, nothing else in
-- any of these tables is touched.

delete from public.sdn_clients  where client_id  = 'SYNCTEST-CL-1786141544';
delete from public.sdn_vendors  where vendor_id  = 'SYNCTEST-VN-1786141544';
delete from public.sdn_roomdims where roomdim_id = 'SYNCTEST-RD-1786141544';
