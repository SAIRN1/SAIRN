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
-- Uses WHERE NOT EXISTS rather than ON CONFLICT, same reasoning as
-- every other license seed file in this repo -- no tracked CREATE
-- TABLE for license_keys, so a UNIQUE constraint on `key` can't be
-- confirmed without live DB access.
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
select 'DNT-PINNACLE-2026', 'active', 'demo@pinnacledental.example', 'sairndental', 'demo', null
where not exists (select 1 from public.license_keys where key = 'DNT-PINNACLE-2026');
