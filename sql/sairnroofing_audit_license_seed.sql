-- sql/sairnroofing_audit_license_seed.sql
--
-- Mints a dedicated SAIRNroofing AUDIT licence so verification stops being run
-- against the customer licence.
--
-- WHY, and this is not a new argument -- it is the one StoneDesk already
-- settled. sql/stonedesk_recovery_admin_seed.sql states it plainly:
--
--     "A published PIN cannot safely persist on SD-PINNACLE-2026 ... THE FIX IS
--      THE LICENCE, NOT THE PIN."
--
-- StoneDesk therefore deleted its published-PIN account from the customer
-- licence and moved verification to SD-AUDIT-2026. SAIRNroofing never had the
-- same treatment: sql/sairnroofing_verify_admin_seed.sql still seeds
-- `rf-verify-admin` with a repo-published PIN onto RF-PINNACLE-2026, the real
-- customer licence. This file is half of the correction; the removal is in
-- sql/sairnroofing_verify_admin_removal_2026-09-02.sql and the two are meant to
-- be run together, licence first.
--
-- It was also blocking work: as of 2026-09-02 all four previous roofing
-- verification licences -- RF-UIVERIFY-1787700000, RF-P4BVERIFY-1787664940,
-- RF-TAXVERIFY-1787780000, RF-VERIFY-PROBE-20260825 -- return 401
-- INVALID_LICENSE, having been removed by the sairnroofing_verify_*_cleanup.sql
-- files. Verified live before writing this, one check_license call each. So the
-- only live roofing licence was the customer one, and there was nowhere safe to
-- drive the NOT_A_DRAFT invoice refusal end to end.
--
-- ── NO CREDENTIAL ROW HERE, DELIBERATELY ────────────────────────────────────
-- This file touches ONLY public.license_keys. It does NOT write to
-- sairnroofing_employee_auth, which is why it needs no recoverability guard:
-- there is no way for a licence-key insert to reach the zero-active-provisioner
-- state.
--
-- The admin account is created afterwards through the API's own `bootstrap`
-- action, which is available precisely because this licence has no credential
-- rows yet. Same shape as sql/stonedesk_audit_license_seed.sql, and better than
-- seeding a PIN hash here: the PIN is chosen at bootstrap time and the SQL file
-- never carries one.
--
-- ── AFTER RUNNING THIS ──────────────────────────────────────────────────────
--   curl -s -X POST https://sairn.vercel.app/api/rf-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer RF-AUDIT-2026' \
--     -d '{"action":"bootstrap","employee_id":"audit-owner","display_name":"Audit Owner","pin":"624815"}'
--
-- 401 INVALID_LICENSE -> the row below is still absent, this file has not run.
-- 200 {"ok":true,"token":...} -> ready to use.
-- 409 ALREADY_PROVISIONED -> someone has already bootstrapped it; do not
--     re-run, and do not delete rows to force it -- that is the trapdoor.
--
-- The PIN above is published on purpose and is safe HERE for the same reason
-- SD-AUDIT-2026's is: this licence holds no customer data and exists to be
-- written to by tests. It would not be safe on RF-PINNACLE-2026, which is the
-- entire point of this file.
--
-- ROOFING'S PROVISIONING ROLE IS `owner`, not `admin` (api/rf-auth.js:101).
-- bootstrap creates an owner, so the account below can then provision others.
--
-- Idempotent: `on conflict (key) do nothing`, so re-running changes nothing and
-- cannot disturb an existing licence.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('RF-AUDIT-2026', 'active', 'audit@pinnacleroofing.example', 'sairnroofing', 'demo', null)
on conflict (key) do nothing;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect exactly one row, status active, app_id sairnroofing.
select key, status, app_id, plan, created_at
  from public.license_keys
 where key = 'RF-AUDIT-2026';
