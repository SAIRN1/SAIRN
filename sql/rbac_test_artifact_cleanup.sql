-- sql/rbac_test_artifact_cleanup.sql
-- Removes the RBAC live-verification test artifacts created against the
-- GRD-DEMO-2026 / SCP-DEMO-2026 demo licenses.
--
-- CANNOT BE DONE VIA THE APP'S OWN API -- checked, not assumed: neither
-- api/sd-data.js nor api/grd-auth.js/api/scp-auth.js expose any
-- delete/remove action (only read/write on data resources; only
-- bootstrap/login/setup on employee auth). anon is locked out of these
-- tables the same way as every other table probed this session. This
-- needs direct Supabase access -- same hand-off as every other
-- provisioning/schema step tonight.
--
-- Confirmed still present before writing this (2026-08-07, via the app's
-- own read endpoints, real session tokens, not assumed):
--   msb_sales:            rbac-test-sale-2 only -- rbac-test-sale-1 was
--                          NEVER created (that void attempt correctly got
--                          403'd by the RBAC gate before any write
--                          happened, so there is nothing to delete for it)
--   grd_progress_photos:  rbac-photo-a, rbac-photo-b
--   scp_progress_photos:  rbac-photo-a, rbac-photo-b
--   grd_employee_auth:    rbac-owner, rbac-crew (license_hash for GRD-DEMO-2026)
--   scp_employee_auth:    rbac-owner, rbac-office (license_hash for SCP-DEMO-2026)
--
-- Real DELETEs (not a status/active flip -- grd_employee_auth/
-- scp_employee_auth have no soft-delete column exposed by the API either,
-- and the task asked for gone, not archived).

delete from public.msb_sales
  where sale_id = 'rbac-test-sale-2';

delete from public.grd_progress_photos
  where photo_id in ('rbac-photo-a', 'rbac-photo-b');

delete from public.scp_progress_photos
  where photo_id in ('rbac-photo-a', 'rbac-photo-b');

delete from public.grd_employee_auth
  where employee_id in ('rbac-owner', 'rbac-crew');

delete from public.scp_employee_auth
  where employee_id in ('rbac-owner', 'rbac-office');

-- Verification (run these after the deletes above -- all five should
-- return 0 rows):
--   select count(*) from public.msb_sales where sale_id = 'rbac-test-sale-2';
--   select count(*) from public.grd_progress_photos where photo_id in ('rbac-photo-a','rbac-photo-b');
--   select count(*) from public.scp_progress_photos where photo_id in ('rbac-photo-a','rbac-photo-b');
--   select count(*) from public.grd_employee_auth where employee_id in ('rbac-owner','rbac-crew');
--   select count(*) from public.scp_employee_auth where employee_id in ('rbac-owner','rbac-office');
