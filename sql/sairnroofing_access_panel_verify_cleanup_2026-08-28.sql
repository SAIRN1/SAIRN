-- sql/sairnroofing_access_panel_verify_cleanup_2026-08-28.sql
-- Teardown for the SAIRNroofing Access-panel live round trip, 2026-08-28.
--
-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║ NOT RUN by the session that wrote this file — it has no DB access.      ║
-- ║ Read the drift warning below before trusting that label.                ║
-- ╚════════════════════════════════════════════════════════════════════════╝
--
-- ── DO NOT TRUST A "NOT RUN" LABEL, INCLUDING THIS ONE ───────────────────
-- This exact trap has now sprung four times on this platform, twice on
-- SAIRNroofing alone and once during THIS round trip:
--   * sairnsenior_verify_cleanup_2026-08-25.sql says NOT RUN; it had run
--     (bootstrap succeeded on a licence its label implied held a credential).
--   * A 2026-08-26 spot-check found 6 of 8 measurable probe rows GONE across
--     five other cleanup files, all still labelled NOT RUN.
--   * sairnroofing_verify_admin_seed.sql said its account existed; login
--     returned 401 while the sibling FOREMEN seed's accounts worked — so one
--     seed had run and the other had not, with nothing on disk saying so.
-- Verify with the SELECTs at the bottom before acting on anything here.
--
-- ── WHY THIS FILE EXISTS SEPARATELY FROM THE 2026-08-25 CLEANUP ──────────
-- sql/sairnroofing_verify_accounts_cleanup.sql targets exactly three accounts:
-- rf-verify-admin, rf-verify-fmA, rf-verify-fmB. The live roster has FIVE.
-- Running that file alone would delete the three it names and LEAVE
-- rf-verify-owner and rf-verify-ui — both role `owner` — behind.
--
-- THAT IS NOT A COSMETIC GAP. It is precisely how this licence reached the
-- state found on 2026-08-28, where it had ZERO active owners and was
-- unrecoverable through the API: reactivating an owner needs an owner (403),
-- provisioning one needs an owner (403), and `bootstrap` refuses while ANY row
-- exists (409), because its existence probe deliberately does not filter on
-- `active`. All three exits were proven closed live. See the Platform row in
-- docs/SAIRN-OPEN-WORK-INDEX.md.
--
-- So this file deletes ALL FIVE. Deleting every credential row is what re-arms
-- `bootstrap`, and that is the correct end state for a demo licence: a real
-- customer creates their own Owner rather than inheriting a disposable one.
--
-- ── DELETE, NEVER DEACTIVATE ─────────────────────────────────────────────
-- Do not "clean up" by setting active = false. Deactivating the last owner is
-- what created the unrecoverable state above, and it is how SD-AUDIT-2026 was
-- lost (api/sd-auth.js:304-308). Delete, or leave them alone.
--
-- ── WHAT THE ROUND TRIP DID, so the rows are attributable ────────────────
-- All through the real deployed API as rf-verify-admin (promoted to `owner` by
-- Michael for this run; it is `admin` in its own seed file). Every leg passed:
--   reason required to deactivate (400) · self-deactivate refused (409
--   SELF_DEACTIVATE) · deactivate fmB (200, remaining_owners 2) · repeat is
--   unchanged:true · the deactivated foreman can no longer sign in (401) ·
--   deactivate the second owner (200, remaining_owners 1) · reactivate both
--   (200) · sign-in restored (200).
-- NO NEW ROWS WERE CREATED. Every account below predates this session.
--
-- LAST_OWNER WAS NOT REACHED, and that is the documented correct behaviour, not
-- a missed test. With exactly one active owner remaining, attempting to
-- deactivate it returned 409 SELF_DEACTIVATE, because the self-check runs
-- before the roster read. Reaching LAST_OWNER needs an active owner caller
-- deactivating a DIFFERENT active owner who is simultaneously the ONLY active
-- owner — self-contradictory. This is the "quarantined guard" recorded in
-- sairn-employee-auth-scaffold §7: unreachable by construction, kept because
-- reachability is a property of the CURRENT rule set and adding a second
-- provisioning role would make it live again.
--
-- ── PINS ─────────────────────────────────────────────────────────────────
-- No PIN is written here. Two are already committed in this repo from earlier
-- passes (sairnroofing_verify_admin_seed.sql and _foremen_seed.sql) and are a
-- reason to DELETE these accounts, not to keep them. rf-verify-owner's own PIN
-- was set live during Phase 1-2 and deliberately never recorded, so that
-- account is active-but-not-loggable-in and cannot be used by anyone.

begin;

-- All five disposable verification credentials. Deleting every row re-arms
-- action:bootstrap for this licence — the intended end state.
delete from public.sairnroofing_employee_auth
 where license_hash = encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in (
     'rf-verify-admin',
     'rf-verify-fmA',
     'rf-verify-fmB',
     'rf-verify-owner',
     'rf-verify-ui'
   );

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- Expect 0:
--   select count(*) from public.sairnroofing_employee_auth
--    where license_hash = encode(digest('RF-PINNACLE-2026','sha256'),'hex');
--
-- Expect 1 — the licence itself is NOT removed:
--   select count(*) from public.license_keys where key = 'RF-PINNACLE-2026';
--
-- Then confirm through the API, which is the real proof the rows are gone
-- rather than merely deactivated:
--   POST /api/rf-auth {"action":"bootstrap","employee_id":"...","pin":"12345678"}
--   with RF-PINNACLE-2026. A 200 means bootstrap is re-armed and the licence is
--   healthy. A 409 ALREADY_PROVISIONED means at least one credential row
--   survived and the licence is still in the trapdoor.
--
-- NOTE: no roofing table grants DELETE to service_role — all fourteen grant
-- lines are select/insert(/update) — so this must run in the SQL editor as the
-- owner role. The app cannot perform this teardown, by design.
