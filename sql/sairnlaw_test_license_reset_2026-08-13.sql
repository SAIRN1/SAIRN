-- sql/sairnlaw_test_license_reset_2026-08-13.sql
-- Resets LAW-TEST-2026's employee credentials so it can be re-bootstrapped
-- from zero -- the PIN set on 'coc-verify' in an earlier session is not
-- known to this session, and the login lockout (LOCKOUT_THRESHOLD = 5,
-- api/law-auth.js) makes blind guessing unsafe. LAW-TEST-2026 is a
-- dedicated, low-risk test license created exactly for this kind of
-- live-verification work (see sql/sairnlaw_test_license_seed.sql) -- no
-- real customer data at stake.
--
-- license_hash below is sha256('LAW-TEST-2026') hex, computed the same way
-- api/_lib/license.js's hashLicense() does -- verified via:
--   node -e "console.log(require('crypto').createHash('sha256').update('LAW-TEST-2026').digest('hex'))"
--   -> 7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198
--
-- After running this, action:'bootstrap' (not 'setup') becomes available
-- again against LAW-TEST-2026, since sairnlaw_employee_auth has zero rows
-- for this license_hash.

delete from public.sairnlaw_employee_auth
where license_hash = '7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198';

-- Verify after running (expect 0 rows):
--   select count(*) from public.sairnlaw_employee_auth
--   where license_hash = '7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198';
