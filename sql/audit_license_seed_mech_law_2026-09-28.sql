-- sql/audit_license_seed_mech_law_2026-09-28.sql
--
-- Mints TWO dedicated AUDIT licences -- MECH-AUDIT-2026 and LAW-AUDIT-2026 --
-- so live verification stops writing to the licences a prospect is shown.
--
-- ── WHY, AND IT IS NOT A NEW ARGUMENT ──────────────────────────────────────
-- StoneDesk settled this. sql/stonedesk_recovery_admin_seed.sql:
--
--     "A published PIN cannot safely persist on SD-PINNACLE-2026 ...
--      THE FIX IS THE LICENCE, NOT THE PIN."
--
-- SAIRNroofing got the same treatment on 2026-09-02
-- (sql/sairnroofing_audit_license_seed.sql). SAIRNmechanical and SAIRNlaw never
-- did, and the cost is now measured rather than predicted:
--
--   * `tools/alf_facility_role_gate_live_probe.py` writes to `alf_facility` as
--     its management CONTROL, on ALF-TEST-2026.
--   * `tools/mech_panels_live_check.py` signs into MECH-PINNACLE-2026, which is
--     the DEMO-FACING mechanical licence.
--   * And on 2026-09-28 I wrote a probe rule onto LAW-TEST-2026 to verify that
--     `add_rule` strips forged identity fields -- because seeing what an
--     endpoint STORES requires a write. That row is real residue and needs
--     sql/zz_probe_residue_delete_2026-09-28.sql to remove it, because DELETE
--     was revoked platform-wide on that table. One probe, one un-deletable row,
--     on a licence somebody may be shown.
--
-- ── NO CREDENTIAL ROW HERE, DELIBERATELY ───────────────────────────────────
-- This file touches ONLY `public.license_keys`. It does NOT write to
-- `mech_employee_auth` or `sairnlaw_employee_auth`, so it needs no
-- recoverability guard: a licence-key insert cannot reach the
-- zero-active-provisioner state that CLAUDE.md's PR 3.4 exists for.
--
-- The accounts are created AFTERWARDS through each app's own `bootstrap`
-- action, which is available precisely because these licences have no
-- credential rows yet. Same decision as the roofing file, and better than
-- seeding a PIN hash here: the PIN is chosen at bootstrap time and this file
-- never carries one.
--
-- ── AFTER RUNNING THIS ─────────────────────────────────────────────────────
-- Bootstrap each one. SAIRNmechanical's provisioning role and SAIRNlaw's are
-- both `owner`, read from api/mech-auth.js and api/law-auth.js rather than
-- assumed -- law-auth.js:130 states `PROVISIONING_ROLES = ['owner']` in so many
-- words.
--
--   POST https://sairn.vercel.app/api/mech-auth
--     Authorization: Bearer MECH-AUDIT-2026
--     {"action":"bootstrap","employee_id":"audit-owner",
--      "display_name":"Audit Owner","pin":"<choose one>"}
--
--   POST https://sairn.vercel.app/api/law-auth
--     Authorization: Bearer LAW-AUDIT-2026
--     {"action":"bootstrap","employee_id":"audit-owner",
--      "display_name":"Audit Owner","pin":"<choose one>"}
--
-- READ THE ANSWER, because all three mean different things:
--   401 INVALID_LICENSE  -> the row below is still absent; this file has not run
--   200 {"ok":true,...}  -> ready to use
--   409 ALREADY_PROVISIONED -> somebody has already bootstrapped it. Do NOT
--       re-run and do NOT delete rows to force it -- that is the trapdoor
--       sql/stonedesk_recovery_admin_seed.sql was written about.
--
-- A PIN on an audit licence is safe for the reason the roofing file gives: the
-- licence holds no customer data and exists to be written to by tests. The same
-- PIN on MECH-PINNACLE-2026 would not be, which is the entire point.
--
-- ── AND THE NON-MANAGEMENT ACCOUNT, WHICH IS THE ONE THAT WAS MISSING ──────
-- A role gate cannot be verified with one role. After bootstrap, provision a
-- second, DELIBERATELY NON-MANAGEMENT account through the app's own `setup`
-- action, signed in as the owner above. SAIRNmechanical's role vocabulary is in
-- api/_lib/auth.js ROLES_BY_APP; `technician` is the non-management one for the
-- insurance and facility gates.
--
--   POST /api/mech-auth  (as audit-owner)
--     {"action":"setup","employee_id":"audit-tech","display_name":"Audit Tech",
--      "pin":"<choose another>","role":"technician"}
--
-- Every role-gate live probe needs BOTH: without the second account the
-- excluded-role arm cannot run, and a probe that only drives the allowed role
-- proves a gate lets somebody in rather than that it keeps anybody out.
--
-- Idempotent: `on conflict (key) do nothing`, so re-running changes nothing and
-- cannot disturb an existing licence.
-- ---------------------------------------------------------------------------

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('MECH-AUDIT-2026', 'active', 'audit@sairnmechanical.example', 'sairnmechanical', 'demo', null)
on conflict (key) do nothing;

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('LAW-AUDIT-2026', 'active', 'audit@sairnlaw.example', 'sairnlaw', 'demo', null)
on conflict (key) do nothing;

-- ── VERIFY ─────────────────────────────────────────────────────────────────
-- Expect exactly two rows, both status active, app_id as named.
select key, status, app_id, plan, created_at
  from public.license_keys
 where key in ('MECH-AUDIT-2026', 'LAW-AUDIT-2026')
 order by key;
