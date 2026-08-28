-- sql/sairndental_license_seed.sql
-- Provisions a demo license_keys row for SAIRNdental
--
-- WHY THIS EXISTS: same root gap every prior new app has hit -- no
-- license_keys row exists for a demo key until one is explicitly
-- seeded. Key format matches this platform's "Try X-PINNACLE-2026"
-- gate-hint convention (sairndental.html's own gate names this key).
--
-- COLUMN LIST: same set every other demo row uses (confirmed live via
-- PostgREST's column-existence probe in earlier seed files, not
-- re-derived here): key, status, customer_email, app_id, plan,
-- stripe_subscription_id.
--
-- Uses ON CONFLICT (key) DO NOTHING -- CORRECTED 2026-08-28. This
-- previously said WHERE NOT EXISTS, on the grounds that no tracked
-- CREATE TABLE for license_keys existed and so a UNIQUE constraint on
-- `key` could not be confirmed. The constraint is confirmed:
-- license_keys_key_key, UNIQUE (key). Full correction, including why
-- the "no tracked CREATE TABLE" premise was also wrong, is in
-- sql/demo_license_keys_seed.sql. DO NOTHING, not DO UPDATE: an
-- existing row wins, so a re-run cannot reactivate or overwrite one.
--
-- Verify after running:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer DNT-PINNACLE-2026' \
--     -d '{"action":"read","resource":"dnt_patients"}'
--
-- 401 INVALID_LICENSE -> row still absent, this file has not been run.
-- 200 with "provisioned":false -> license row is good, but
-- sql/sairndental_data_schema.sql has NOT been run yet.
-- 200 with "provisioned":true -> both migrations confirmed live.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('DNT-PINNACLE-2026', 'active', 'demo@pinnacledental.example', 'sairndental', 'demo', null)
on conflict (key) do nothing;
