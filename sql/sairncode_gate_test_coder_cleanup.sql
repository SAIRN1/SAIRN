-- sql/sairncode_gate_test_coder_cleanup.sql
-- Removes the gate-test-coder credential from SC-PINNACLE-2026.
--
-- WHY THIS FILE EXISTS INSTEAD OF AN API CALL: api/sc-auth.js exposes exactly
-- four actions -- bootstrap, login, setup, check_license. There is NO delete
-- and NO deactivate. Verified live 2026-08-23 by probing all four candidate
-- verbs against production with a real Compliance Admin session; each returned
-- the action-allowlist error, not a permission error, so the capability is
-- genuinely absent rather than merely gated. The account was confirmed still
-- live in the same pass (a real login returned ok:true, role coder).
--
-- 'setup' cannot substitute for a delete: it upserts with active:true and
-- accepts no active/enabled parameter, so re-running it can only rotate the
-- PIN, never remove or disable the row. Rotating to an unrecorded PIN would
-- leave an orphaned account nobody can clean up later -- worse than leaving it
-- intact and documented -- so that was deliberately NOT done.
--
-- WHAT THIS DELETES: one row. gate-test-coder was created 2026-08-23 through
-- the app's own real setup action to verify the sc_settings admin-only gate
-- against a genuine non-admin session (the first such session SAIRNcode had).
-- It holds no practice data -- credentials only.
--
-- license_hash below is sha256('SC-PINNACLE-2026'), the same hashLicense()
-- the API uses (api/_lib/license.js). Verify before running:
--   node -e "console.log(require('crypto').createHash('sha256').update('SC-PINNACLE-2026').digest('hex'))"

-- Optional: confirm exactly what is about to be removed, and that the admin
-- account is NOT caught by this.
-- select employee_id, display_name, role, active
--   from public.sairncode_employee_auth
--  where license_hash = 'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed';

delete from public.sairncode_employee_auth
 where license_hash = 'fce80ce1bc131249e98a7caf1235bc769ce703331775e4ba1c870c65c8a0e9ed'
   and employee_id  = 'gate-test-coder';

-- Scoped to that one employee_id on purpose. Do NOT drop the license_hash
-- predicate and do NOT widen this to the whole license: the Compliance Admin
-- ('owner') lives in this same table, and removing it would lock SAIRNcode's
-- demo license out entirely with no recovery path -- exactly the failure that
-- burned three StoneDesk keys and required
-- sql/stonedesk_audit_license_credential_reset.sql.
--
-- Verify after running (expect 401 INVALID_CREDENTIALS -- the row is gone):
--   curl -s -X POST https://sairn.vercel.app/api/sc-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SC-PINNACLE-2026' \
--     -d '{"action":"login","employee_id":"gate-test-coder","pin":"357913"}'
--
-- And confirm the admin still works (expect ok:true, role admin):
--   curl -s -X POST https://sairn.vercel.app/api/sc-auth \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SC-PINNACLE-2026' \
--     -d '{"action":"login","employee_id":"owner","pin":"666366"}'
