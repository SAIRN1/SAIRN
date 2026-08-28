-- sql/stonedesk_audit_license_seed.sql
-- Provisions a FRESH, unprovisioned StoneDesk demo license for click-through testing
--
-- WHY THIS EXISTS: the platform click-through audit (2026-08-08) hit a real
-- blocker on StoneDesk's existing demo key, SD-PINNACLE-2026 -- it already
-- has employee credentials from a prior session ("Headless Check Co",
-- api/sd-auth.js's action:'bootstrap' returns 409 ALREADY_PROVISIONED), and
-- those credentials aren't documented anywhere in this repo's handoffs.
-- Rather than guess PINs against a live endpoint (exactly the brute-force
-- pattern api/sd-auth.js's own lockout exists to catch) or touch whatever
-- that existing account's data represents, this provisions a second,
-- clean StoneDesk license dedicated to this kind of automated testing --
-- same reasoning as every other *_license_seed.sql in this repo, applied
-- to get a known-empty account instead of an unknown-state one.
--
-- Uses ON CONFLICT (key) DO NOTHING -- CORRECTED 2026-08-28, along with
-- every other license seed here; they all previously used WHERE NOT EXISTS
-- because a UNIQUE constraint on `key` was believed unconfirmable from the
-- repo. It is confirmed: license_keys_key_key, UNIQUE (key). Full correction
-- in sql/demo_license_keys_seed.sql. DO NOTHING, not DO UPDATE: an existing
-- row wins -- which matters here specifically, since this key may already
-- have credentials bootstrapped against it (see
-- sql/stonedesk_partner_demo_license_seed.sql) and a re-run must not disturb
-- it.
--
-- Verify after running:
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SD-AUDIT-2026' \
--     -d '{"action":"bootstrap","employee_id":"audit-owner","display_name":"Audit Owner","pin":"135790"}'
--
-- 401 INVALID_LICENSE -> row still absent. {"ok":true,"token":...} -> ready to use.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('SD-AUDIT-2026', 'active', 'audit@pinnaclestone.example', 'stonedesk', 'demo', null)
on conflict (key) do nothing;
