-- sql/stonedesk_partner_demo_license_seed.sql
-- Provisions a genuinely fresh, unprovisioned StoneDesk demo license for
-- the partner's setup attempt.
--
-- WHY THIS EXISTS: SD-PINNACLE-2026 already has real employee credentials
-- on it (confirmed live via a 409 ALREADY_PROVISIONED bootstrap response,
-- 2026-08-10 -- documented origin: sql/stonedesk_audit_license_seed.sql,
-- a 2026-08-08 audit session, employee "Headless Check Co", PIN unknown/
-- undocumented). The other existing spare key, SD-AUDIT-2026, could not
-- be confirmed fresh either way without risking consuming it if it
-- actually still was -- its documented demo credentials no longer log in,
-- which is ambiguous (StoneDesk's login intentionally returns the same
-- generic error for "wrong PIN" and "employee doesn't exist"). Rather
-- than guess against a live endpoint with lockout protection, this
-- provisions a third, dedicated key -- same reasoning as every other
-- *_license_seed.sql in this repo.
--
-- Run this in Supabase's SQL editor, then have the partner do their own
-- self-service first-time setup (see steps below) -- nobody needs to
-- hand them a PIN in plaintext.
insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
select 'SD-PARTNER-2026', 'active', 'partner@pinnaclestone.example', 'stonedesk', 'demo', null
where not exists (select 1 from public.license_keys where key = 'SD-PARTNER-2026');

-- Verify after running (expect 401 INVALID_LICENSE -> row still absent;
-- {"ok":true,...} -> ready):
--   curl -s -X POST https://sairn.vercel.app/api/sd-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SD-PARTNER-2026' \
--     -d '{"action":"check_license"}'
