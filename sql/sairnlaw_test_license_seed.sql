-- sql/sairnlaw_test_license_seed.sql
-- Provisions a FRESH, dedicated test license_keys row for SAIRNlaw
--
-- WHY THIS EXISTS: LAW-PINNACLE-2026 (sql/sairnlaw_license_seed.sql) is
-- SAIRNlaw's real demo license and already has real employee credentials
-- provisioned on it from prior session work -- the PIN for that account
-- is not known to this session, and guessing against it risks tripping
-- its real lockout mechanism (LOCKOUT_THRESHOLD = 5 in api/law-auth.js).
-- Same pattern already used elsewhere tonight when a session needs a
-- clean, known-from-zero account to do real self-service first-login
-- setup (bootstrap) and get a real session token: provision a SEPARATE,
-- clearly-named test license instead of touching the shared demo one.
--
-- LAW-TEST-2026 is for exactly this kind of live-verification work --
-- not the same key sairnlaw.html's own gate error message suggests
-- (that's LAW-PINNACLE-2026, unchanged, still the app's real demo
-- license). Safe to leave provisioned; low-risk (license-gated same as
-- every other key in this table, no elevated access).
--
-- Verify after running:
--
--   curl -s -X POST https://sairn.vercel.app/api/law-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer LAW-TEST-2026' \
--     -d '{"action":"check_license"}'
--
-- 401 INVALID_LICENSE -> row still absent, this file has not been run.
-- 200 {"ok":true,"active":true,...} -> license row is good, ready for
-- a real bootstrap (action:'bootstrap') to create its first owner
-- credential from zero.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
select 'LAW-TEST-2026', 'active', 'test@sairnlaw-verification.example', 'sairnlaw', 'demo', null
where not exists (select 1 from public.license_keys where key = 'LAW-TEST-2026');
