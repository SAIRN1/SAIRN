-- sql/sairndental_verify_auth_cleanup_2026-08-27.sql
-- Scoped cleanup for the SAIRNdental auth live-verification run, 2026-08-27.
-- ⚠ STATUS CORRECTED 2026-08-28 by a later session (CC): THIS FILE HAS RUN.
-- The line here said "NOT RUN by this session", accurate about the session that
-- wrote it and wrong about the database ever since. Proven live 2026-08-27, not
-- inferred: a login as dnt-verify-owner with the PIN this file itself printed
-- returned 401 INVALID_CREDENTIALS, and bootstrap on DNT-PINNACLE-2026 SUCCEEDED
-- -- which it can only do when zero credential rows exist. Both rows are gone.
-- (Its own bottom-of-file confirmation step predicted exactly that 401.)
-- Targeted by exact employee_id, never
-- by license_hash alone.
--
-- ── THIS ONE IS MORE THAN TIDINESS ──────────────────────────────────────
-- ⚠ NO LONGER TRUE, as of the status correction above: both rows are DELETED and
-- both PINs below are DEAD. The paragraph is kept rather than scrubbed because
-- it records why the file was urgent, and because deleting the two PIN literals
-- now would not un-publish them -- they are already in the repo's history. What
-- it should NOT be read as is a live exposure. Two lessons stand: a "these are
-- live credentials" warning goes stale the moment someone acts on it, exactly
-- like a NOT RUN label; and writing PIN literals into a repo file is the
-- practice that made this paragraph necessary at all. Later verification files
-- identify credentials by employee_id only, and print no PINs.
--
-- The original text, as written 2026-08-27:
-- These are LIVE, WORKING CREDENTIALS on DNT-PINNACLE-2026, and their PINs are
-- in a session transcript:
--     dnt-verify-owner       role owner       PIN 714205
--     dnt-verify-frontdesk   role frontdesk   PIN 336891
-- Leaving them in place would reintroduce a smaller version of the exact
-- problem the day's work closed: known-to-others credentials on an app that
-- holds PHI. Run this promptly rather than at leisure.
--
-- ── WHY A DELETE AND NOT A DEACTIVATION, THIS ONCE ──────────────────────
-- The platform rule is deactivate, never delete, and it is right: the row
-- preserves created_at, role history, and any audit entries referencing that
-- employee_id. It exists so a departing employee stays auditable.
--
-- These two rows are the exception on purpose. They are not employees. They
-- were minted by a verification run, they have no history worth preserving,
-- and a deactivated row still carries a scrypt hash of a PIN that is now
-- public. Deactivation would leave that hash on a PHI-holding practice's
-- credential table forever. Removing them entirely is the smaller risk.
--
-- Do NOT generalise this into a habit. For a real person, deactivate.
--
-- ── ORDER MATTERS ───────────────────────────────────────────────────────
-- Delete the frontdesk row FIRST. Deleting the only owner while another row
-- exists would leave a licence whose remaining credential cannot provision
-- anything and where bootstrap still refuses (it checks for ANY row, active or
-- not) -- the permanent lockout that lost SD-AUDIT-2026. Removing both, owner
-- last, returns DNT-PINNACLE-2026 to a clean unprovisioned state where
-- bootstrap re-arms, which is the right end state for a demo licence.

-- 1. the second employee
delete from public.sairndental_employee_auth
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'dnt-verify-frontdesk';

-- 2. the owner, last
delete from public.sairndental_employee_auth
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'dnt-verify-owner';

-- NOTE ON THE license_hash EXPRESSION: computed in-query rather than pasted as
-- a literal so there is no chance of transcribing the wrong 64 hex characters
-- and silently deleting nothing. `digest()` needs pgcrypto; if the extension is
-- not enabled, substitute the literal
--   'f1d2...'  -- sha256('DNT-PINNACLE-2026'), derive it rather than trust a paste
-- and re-check the WHERE clause matches exactly two rows before running.

-- ── Confirm afterwards. Do not skip: a multi-statement paste into the SQL
-- editor can apply partway and still report success (seen twice on 2026-08-26).
--   select employee_id, role, active from public.sairndental_employee_auth
--    where employee_id like 'dnt-verify-%';          -- expect 0 rows
--   select count(*) from public.sairndental_employee_auth;   -- expect 0
--
-- Then confirm live, which is the real proof:
--   POST /api/dnt-auth {"action":"login","employee_id":"dnt-verify-owner","pin":"714205"}
--   -> must be 401 INVALID_CREDENTIALS
--   POST /api/sd-data {"action":"read","resource":"dnt_patients"}  (licence only)
--   -> must remain 401 NO_SESSION
