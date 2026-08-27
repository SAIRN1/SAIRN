-- sql/sairnmechanical_verify_auth_cleanup_2026-08-27.sql
-- Scoped cleanup for the SAIRNmechanical auth live-verification run,
-- 2026-08-27. NOT RUN by this session (no DB access). Targeted by exact
-- employee_id, never by license_hash alone.
--
-- ── RUN THIS PROMPTLY, NOT AT LEISURE ───────────────────────────────────
-- These are LIVE, WORKING credentials on MECH-PINNACLE-2026, and their PINs
-- are in a session transcript. Deliberately NOT written into this file: a
-- cleanup script that carries the very secrets it exists to retire is a worse
-- artifact than the debris. The two employee_ids are enough to target them.
--
--     mech-verify-owner   role owner
--     mech-verify-tech    role tech
--
-- Leaving them live would reintroduce a smaller version of what this whole
-- recovery closed: known-to-others credentials on an app that shipped with
-- four published passwords.
--
-- ── WHY DELETE, NOT DEACTIVATE, THIS ONCE ───────────────────────────────
-- The platform rule is deactivate-never-delete, and it is right: the row keeps
-- created_at, role history, and any audit reference to that employee_id, so a
-- departing employee stays auditable.
--
-- These two are the deliberate exception. They are not employees. They were
-- minted by a verification run, have no history worth preserving, and a
-- deactivated row still carries a scrypt hash of a PIN that is now effectively
-- public -- left on a customer-facing credential table indefinitely. Removing
-- them entirely is the smaller risk.
--
-- Do NOT generalise this. For a real person, deactivate.
--
-- ── ORDER MATTERS: TECH FIRST, OWNER LAST ───────────────────────────────
-- Deleting the only owner while another row remains leaves a licence whose
-- surviving credential cannot provision anything, and where bootstrap still
-- refuses -- it checks for ANY row, active or not (api/mech-auth.js's existence
-- probe deliberately does not filter on active). That is the permanent lockout
-- that lost SD-AUDIT-2026. Removing both, owner last, returns
-- MECH-PINNACLE-2026 to a clean unprovisioned state where bootstrap re-arms,
-- which is the right end state for a demo licence nobody has used.

-- 1. the tech
delete from public.sairnmechanical_employee_auth
 where license_hash = encode(digest('MECH-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'mech-verify-tech';

-- 2. the owner, last
delete from public.sairnmechanical_employee_auth
 where license_hash = encode(digest('MECH-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'mech-verify-owner';

-- NOTE ON THE license_hash EXPRESSION: computed in-query rather than pasted as
-- a literal so a mistyped hex character cannot silently delete nothing.
-- digest() needs pgcrypto; if the extension is unavailable, derive
-- sha256('MECH-PINNACLE-2026') yourself rather than trusting a paste, and
-- confirm the WHERE clause matches exactly two rows before running.

-- ── Confirm afterwards. Do not skip: a multi-statement paste into the SQL
-- editor can apply partway and still report success -- seen twice on
-- 2026-08-26, and again as a push that reported clean while nothing landed.
--   select employee_id, role, active from public.sairnmechanical_employee_auth
--    where employee_id like 'mech-verify-%';           -- expect 0 rows
--   select count(*) from public.sairnmechanical_employee_auth;  -- expect 0
--
-- Then confirm live, which is the real proof:
--   POST /api/mech-auth {"action":"login","employee_id":"mech-verify-owner","pin":"<the one from the run>"}
--   -> must be 401 INVALID_CREDENTIALS
--   POST /api/mech-auth {"action":"check_license"}
--   -> must remain 200, the licence itself is NOT being removed
