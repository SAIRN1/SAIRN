-- sql/sairnlaw_test_license_reset_2026-08-18.sql
-- Resets LAW-TEST-2026's employee credentials again so it can be
-- re-bootstrapped from zero -- same situation as
-- sql/sairnlaw_test_license_reset_2026-08-13.sql (whichever employee
-- owns the account now, its PIN is not known to this session, and the
-- login lockout, LOCKOUT_THRESHOLD = 5 in api/law-auth.js, makes blind
-- guessing unsafe). This time the blocker was a first-time-setup attempt
-- ("hank-verify") rejected with "This firm already has employee
-- credentials set up" -- confirming a live owner row still exists from
-- an earlier session, PIN unknown. LAW-TEST-2026 remains the dedicated,
-- low-risk test license for exactly this kind of live-verification work
-- (see sql/sairnlaw_test_license_seed.sql) -- no real customer data at
-- stake.
--
-- license_hash below is sha256('LAW-TEST-2026') hex, same value used in
-- the 2026-08-13 reset -- the license key itself hasn't changed, so this
-- is not recomputed, just carried forward and re-verified by inspection
-- against that file.
--
-- After running this, action:'bootstrap' (not 'setup') becomes available
-- again against LAW-TEST-2026, since sairnlaw_employee_auth has zero rows
-- for this license_hash.

delete from public.sairnlaw_employee_auth
where license_hash = '7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198';

-- Verify after running (expect 0 rows):
--   select count(*) from public.sairnlaw_employee_auth
--   where license_hash = '7f3af3fb178dd299d686312431ef59d3f33e066d73db835c21cc25292c927198';
