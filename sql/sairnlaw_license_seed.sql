-- sql/sairnlaw_license_seed.sql
-- Provisions a demo license_keys row for SAIRNlaw
--
-- WHY THIS EXISTS: found while live-verifying the new legal-research
-- citator (api/courtlistener.js, api/legal-citator.js) after pushing it --
-- both endpoints require a valid SAIRNlaw license for every action,
-- including basic search, and LAW-PINNACLE-2026 (the exact key
-- sairnlaw.html's own gate error message already suggests) had never been
-- provisioned -- confirmed via a live 401 INVALID_LICENSE against
-- api/sd-data.js. Same missing-demo-key gap SAIRNdesign and SAIRNlegacy
-- both had, same fix, same column list as every other license seed file in
-- this repo.
--
-- Uses ON CONFLICT (key) DO NOTHING -- CORRECTED 2026-08-28, along with
-- every other license seed here; they all previously used WHERE NOT EXISTS
-- because a UNIQUE constraint on `key` was believed unconfirmable from the
-- repo. It is confirmed: license_keys_key_key, UNIQUE (key). Full correction
-- in sql/demo_license_keys_seed.sql. DO NOTHING, not DO UPDATE: an existing
-- row wins, so a re-run cannot reactivate or overwrite one.
--
-- Note this is a SEPARATE blocker from the citator's other one
-- (COURTLISTENER_API_TOKEN not configured, see api/courtlistener.js) --
-- running this file unblocks license validation and the two unauthenticated
-- CourtListener actions (search, courts); the token-gated actions
-- (citing/citation_lookup/opinion_text/cluster, and the citator's 'process'
-- action built on them) still need the CourtListener token separately.
--
-- Verify after running:
--
--   curl -s -X POST https://sairn.vercel.app/api/courtlistener \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer LAW-PINNACLE-2026' \
--     -d '{"action":"search","q":"promissory estoppel"}'
--
-- 401 INVALID_LICENSE -> row still absent, this file has not been run.
-- 200 with real CourtListener search results -> license row is good.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('LAW-PINNACLE-2026', 'active', 'demo@pinnaclestone.example', 'sairnlaw', 'demo', null)
on conflict (key) do nothing;
