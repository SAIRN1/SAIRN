-- sql/audit_license_seed_2026-09-28.sql
--
-- ONE FILE, EVERY MISSING AUDIT LICENCE. Run once in the Supabase SQL editor.
--
-- SUPERSEDES sql/audit_license_seed_mech_law_2026-09-28.sql, which covered two of
-- the five and was written before the probes were enumerated. That file is left
-- in place rather than deleted so a reader who finds it first is not confused by
-- a dangling reference; running BOTH is harmless (`on conflict do nothing`), and
-- running only this one is sufficient.
--
-- ── WHY AN AUDIT LICENCE AT ALL ────────────────────────────────────────────
-- sql/stonedesk_recovery_admin_seed.sql settled it: *"A published PIN cannot
-- safely persist on SD-PINNACLE-2026 ... THE FIX IS THE LICENCE, NOT THE PIN."*
-- Roofing applied it 2026-09-02. Nobody else did, because the rule lived in a
-- SQL comment rather than anywhere a writing probe would meet it.
--
-- The cost became concrete on 2026-09-28: verifying that api/legal-deadlines.js
-- strips forged identity fields REQUIRES a write -- what an endpoint STORES
-- cannot be read back any other way -- so a probe rule went to LAW-TEST-2026.
-- DELETE was revoked platform-wide on law_deadline_rules on 2026-08-25, so that
-- row cannot be removed by the API, by service_role, or by the session that
-- wrote it. It needs sql/zz_probe_residue_delete_2026-09-28.sql and a human.
--
-- tools/audit_licence.py now refuses a non-audit licence IN THE CODE PATH, which
-- is what makes these rows load-bearing rather than tidy: until they exist, four
-- live probes are OUT OF SERVICE by design.
--
-- ── MEASURED LIVE BEFORE WRITING THIS, one check_license per key ────────────
--     RF-AUDIT-2026     200  EXISTS   (seeded 2026-09-02)
--     SD-AUDIT-2026     200  EXISTS
--     ALF-AUDIT-2026    401  ABSENT
--     LAW-AUDIT-2026    401  ABSENT
--     SC-AUDIT-2026     401  ABSENT
--     MECH-AUDIT-2026   401  ABSENT
--     SV-AUDIT-2026     401  ABSENT
--
-- ── WHICH PROBE NEEDS WHICH, so no row here is speculative ─────────────────
--   ALF-AUDIT-2026   tools/alf_facility_role_gate_live_probe.py
--                    Upserts alf_facility (id ZZ-GATE-FAC). Tier A. Verifies
--                    whether a caregiver can rewrite `licensing_state`, which
--                    selects the state rule set the facility's staffing and
--                    training compliance is measured against. BLOCKED TODAY.
--   LAW-AUDIT-2026   tools/law_billing_code_trim_live_probe.py
--                    Writes a billing-code row per run. BLOCKED TODAY. Its own
--                    usage note used to name LAW-PINNACLE-2026, the demo-facing
--                    licence.
--   SC-AUDIT-2026    tools/sc_tier_a_write_gate_live_probe.py
--                    THE SHARPEST: drives write, setup, set_active AND delete
--                    against Tier A SAIRNcode resources. BLOCKED TODAY, and it
--                    should stay blocked rather than run on SC-PINNACLE-2026.
--   MECH-AUDIT-2026  tools/mech_panels_live_check.py signs into
--                    MECH-PINNACLE-2026. It only calls `login` today, so it is
--                    NOT in the writer set and is not blocked -- this row exists
--                    so the next mechanical write probe has somewhere to go, and
--                    because the insurance-policy work of 2026-09-27 touched a
--                    Tier A money path on that licence.
--
-- SV-AUDIT-2026 IS DELIBERATELY NOT HERE. No probe needs it: the enumeration
-- found no SAIRNvet writer. It appeared in tools/audit_licence.py's
-- KNOWN_AUDIT_KEYS by mistake -- a list of keys that "exist" containing one that
-- does not -- and that is corrected in the tool rather than papered over by
-- minting a licence nothing uses. An unused licence is unused surface.
--
-- ── NO CREDENTIAL ROW HERE, DELIBERATELY ───────────────────────────────────
-- This file touches ONLY public.license_keys. It writes to no *_employee_auth
-- table, so it needs no recoverability guard: a licence-key insert cannot reach
-- the zero-active-provisioner state PR §3.4 exists for.
--
-- The accounts are created afterwards through each app's own `bootstrap` action,
-- which is available precisely because these licences have no credential rows.
-- Same decision as sql/sairnroofing_audit_license_seed.sql, and better than
-- seeding a PIN hash: the PIN is chosen at bootstrap time and this file never
-- carries one.
--
-- ── AFTER RUNNING THIS: WHAT A HUMAN MUST DO, AND WHAT THEY NEED NOT ───────
-- MINIMUM HUMAN STEP: run this file. That is all.
--
-- Bootstrap and role provisioning are BOTH available through the product's own
-- endpoints with only a licence key, so they need no human and no SQL:
--   * `bootstrap` works only while a licence has ZERO credential rows, and
--     always creates role 'owner'. It is not a standing backdoor -- it answers
--     409 ALREADY_PROVISIONED once any row exists.
--   * `setup`, signed in as that owner, provisions the NON-MANAGEMENT account.
--     A role gate cannot be verified with one role: a probe that drives only the
--     allowed role proves a gate lets somebody in, never that it keeps anybody
--     out.
-- I can and will do both once the rows exist. The PINs are chosen at that point
-- and recorded in docs/2026-09-03-demo-credentials.md alongside every other
-- audit credential.
--
-- READ THE ANSWER, because all three mean different things:
--   401 INVALID_LICENSE     this file has not run
--   200 {"ok":true,...}     ready
--   409 ALREADY_PROVISIONED somebody already bootstrapped it. Do NOT re-run and
--       do NOT delete rows to force it -- that is the trapdoor
--       sql/stonedesk_recovery_admin_seed.sql was written about.
--
-- The non-management role per app, read from each app's own vocabulary in
-- api/_lib/auth.js ROLES_BY_APP rather than assumed:
--   sairncare        caregiver      (ALF_MANAGEMENT_ROLES is owner + billing)
--   sairnlaw         paralegal      (RULE_AUTHORING_ROLES is owner + attorney)
--   sairncode        coder          (provisioning role is `admin`, NOT owner)
--   sairnmechanical  technician
--
-- SAIRNCODE'S PROVISIONING ROLE IS `admin`, not `owner` -- CLAUDE.md PR §3.4
-- names this specifically. `bootstrap` there creates an admin.
--
-- Idempotent: `on conflict (key) do nothing`. Re-running changes nothing and
-- cannot disturb an existing licence.
-- ---------------------------------------------------------------------------

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values
  ('ALF-AUDIT-2026',  'active', 'audit@sairncare.example',       'sairncare',       'demo', null),
  ('LAW-AUDIT-2026',  'active', 'audit@sairnlaw.example',        'sairnlaw',        'demo', null),
  ('SC-AUDIT-2026',   'active', 'audit@sairncode.example',       'sairncode',       'demo', null),
  ('MECH-AUDIT-2026', 'active', 'audit@sairnmechanical.example', 'sairnmechanical', 'demo', null)
on conflict (key) do nothing;

-- ── VERIFY ─────────────────────────────────────────────────────────────────
-- Expect EXACTLY FOUR rows, every status `active`, app_id as paired above, plan
-- `demo`. RF-AUDIT-2026 and SD-AUDIT-2026 are deliberately NOT in this query --
-- they already exist and this file does not touch them.
select key, status, app_id, plan, created_at
  from public.license_keys
 where key in ('ALF-AUDIT-2026', 'LAW-AUDIT-2026', 'SC-AUDIT-2026', 'MECH-AUDIT-2026')
 order by key;
