-- sql/sairnbiz_test_license_seed.sql
-- Provisions a FRESH, dedicated test license_keys row for SAIRNbiz --
-- SB-TEST-2026 -- kept deliberately separate from SB-PINNACLE-2026 (the
-- existing demo key from sql/demo_license_keys_seed.sql), which already
-- has employee credentials provisioned and may be in active use by
-- another session. This lets a throwaway test owner be bootstrapped
-- without touching anything already in use.
--
-- Same shape/precedent as sql/sairnlaw_test_license_seed.sql. Uses
-- ON CONFLICT (key) DO NOTHING -- CORRECTED 2026-08-28; this previously said
-- WHERE NOT EXISTS, citing "no confirmed UNIQUE constraint on
-- license_keys.key without live DB access." The constraint is confirmed:
-- license_keys_key_key, UNIQUE (key). Full correction, including why the
-- "no tracked CREATE TABLE" premise was also wrong, is in
-- sql/demo_license_keys_seed.sql. DO NOTHING, not DO UPDATE: an existing
-- row wins, so a re-run cannot reactivate or overwrite one. Safe to re-run.
--
-- Verify after running:
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SB-TEST-2026' \
--     -d '{"action":"read","resource":"profile","app_id":"sairnbiz"}'
-- Expected: 200 {"ok":true,"data":null} (row present, license active).

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('SB-TEST-2026', 'active', 'test@sairnbiz-verification.example', 'sairnbiz', 'demo', null)
on conflict (key) do nothing;
