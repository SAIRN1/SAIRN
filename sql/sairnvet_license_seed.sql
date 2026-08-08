-- sql/sairnvet_license_seed.sql
-- Provisions a demo license_keys row for SAIRNvet
--
-- WHY THIS EXISTS: found while starting the platform-wide click-through
-- audit (2026-08-08) -- SV-PINNACLE-2026 (the exact key SAIRNVET-FINAL-
-- SPEC.md already documents as the demo key, matching every other app's
-- placeholder-key convention) returns 401 INVALID_LICENSE against the live
-- api/sd-data.js endpoint. Confirmed live, not assumed: the row is absent,
-- not expired/misconfigured/wrong app_id -- same missing-data gap as
-- SAIRNbiz/SAIRNgrounds/SAIRNscape had before sql/demo_license_keys_seed.sql,
-- and SAIRNlaw before sql/sairnlaw_license_seed.sql. No code bug here.
--
-- Verify after running:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SV-PINNACLE-2026' \
--     -d '{"action":"read","resource":"profile","app_id":"sairnvet"}'
--
-- 401 INVALID_LICENSE -> row still absent. {"ok":true,...} -> provisioned.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
select 'SV-PINNACLE-2026', 'active', 'demo@pinnaclestone.example', 'sairnvet', 'demo', null
where not exists (select 1 from public.license_keys where key = 'SV-PINNACLE-2026');
