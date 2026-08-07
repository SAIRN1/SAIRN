-- sql/demo_license_keys_seed.sql
-- Provisions demo license_keys rows for SAIRNbiz, SAIRNgrounds, SAIRNscape
--
-- WHY THIS EXISTS: api/_lib/license.js validates against public.license_keys
-- by raw `key` -- there is no self-service key-generation system anywhere in
-- this codebase yet (that's separate, unbuilt, tied to next week's Stripe
-- integration -- see SAIRN-PLATFORM-SESSION1-HANDOFF.md). SAIRNbuild's own
-- demo key (BLD-PINNACLE-2026) was already manually provisioned this same
-- way (see SAIRNBUILD-SCOPE.md section 6) and is confirmed working. These
-- three apps' equivalent demo keys were never created -- confirmed live,
-- not assumed: GRD-DEMO-2026, SCP-DEMO-2026, and SB-PINNACLE-2026 (the
-- exact placeholder each app's own license-gate error message already
-- suggests, e.g. sairnbiz.html: "Invalid key. Try SB-PINNACLE-2026") all
-- return 401 INVALID_LICENSE against the live endpoint -- the row is
-- absent, not expired/misconfigured/wrong-table. No code fix exists here
-- because there is no bug in the validation code; this is a missing-data
-- gap, same category as every other Supabase provisioning step in this
-- project (run by Michael in the SQL editor, service-role only -- anon
-- cannot read or insert license_keys by design, confirmed by probe
-- returning 42501 against SAIRNbuild's own equivalent provisioning).
--
-- Client-side prefix allowlists already accept these keys with no further
-- code change needed -- confirmed by reading each app's own gate:
--   sairnbiz.html:841     VALID=['SB-','SD-','DEMO-','SAIRN-','BIZ-']
--   sairngrounds.html:1094 VALID=['GRD-','DEMO-','SAIRN-']
--   sairnscape.html:1627   SCP_VALID=['SCP-','DEMO-','SAIRN-']
--
-- Column set matches api/_lib/license.js's own SELECT list exactly (key,
-- status, customer_email, app_id, plan, trial_ends_at,
-- stripe_subscription_id) -- same shape as BLD-PINNACLE-2026's row.
--
-- Verify after running, before writing/re-running any client code against
-- these keys (same "verify against the deployed endpoint" discipline
-- SAIRNBUILD-SCOPE.md section 6 already used for BLD-PINNACLE-2026):
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SB-PINNACLE-2026' \
--     -d '{"action":"read","resource":"profile","app_id":"sairnbiz"}'
--
-- (repeat for GRD-DEMO-2026/app_id sairngrounds and SCP-DEMO-2026/app_id
-- sairnscape). 401 INVALID_LICENSE -> row still absent. 403
-- LICENSE_INACTIVE -> status not 'active'. 200 -> provisioned correctly.

-- Uses WHERE NOT EXISTS rather than ON CONFLICT: this repo has no tracked
-- CREATE TABLE for license_keys (owned by a separate, not-yet-built
-- generation system per license.js's own header), so a UNIQUE constraint
-- on `key` can't be confirmed without live DB access -- ON CONFLICT
-- against a column with no matching constraint fails with 42P10 (the
-- exact class of error this project already hit once tonight on a
-- different table). NOT EXISTS has no such requirement and is safe to
-- re-run regardless.

insert into public.license_keys (key, status, customer_email, app_id, plan, trial_ends_at, stripe_subscription_id)
select 'SB-PINNACLE-2026', 'active', 'demo@pinnaclestone.example', 'sairnbiz', 'demo', null, null
where not exists (select 1 from public.license_keys where key = 'SB-PINNACLE-2026');

insert into public.license_keys (key, status, customer_email, app_id, plan, trial_ends_at, stripe_subscription_id)
select 'GRD-DEMO-2026', 'active', 'demo@pinnaclestone.example', 'sairngrounds', 'demo', null, null
where not exists (select 1 from public.license_keys where key = 'GRD-DEMO-2026');

insert into public.license_keys (key, status, customer_email, app_id, plan, trial_ends_at, stripe_subscription_id)
select 'SCP-DEMO-2026', 'active', 'demo@pinnaclestone.example', 'sairnscape', 'demo', null, null
where not exists (select 1 from public.license_keys where key = 'SCP-DEMO-2026');
