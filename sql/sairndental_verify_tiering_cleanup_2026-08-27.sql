-- sql/sairndental_verify_tiering_cleanup_2026-08-27.sql
-- Scoped cleanup for the SAIRNdental minimum-necessary TIERING live-verification
-- run, 2026-08-27.
-- ⚠ STATUS CORRECTED 2026-08-28: THIS FILE HAS RUN, and its own header said
-- "NOT RUN by this session" for a day after it had. Michael ran it and
-- reported: credentials, providers and patients all cleaned successfully; the
-- appointments delete matched nothing because it targeted AP-VERIFY-1 while the
-- rows present were AP-VERIFY-A/D/E. The delete was CORRECT and the INVENTORY
-- was incomplete -- see sql/sairndental_appointment_residue_identify_2026-08-27.sql.
-- The trivial-PIN owner credential this file exists to remove IS gone; verified
-- live 2026-08-27 by bootstrap re-arming on a clean licence. Every statement is
-- targeted by exact id, never by license_hash alone.
--
-- NO PINs APPEAR IN THIS FILE, deliberately, unlike
-- sql/sairndental_verify_auth_cleanup_2026-08-27.sql which wrote two live PINs
-- into the repo. Michael's instruction this run was explicit. The credentials
-- below are identified by employee_id only; their PINs existed solely in the
-- verifying process and were never written anywhere.
--
-- ── RUN THIS PROMPTLY. ONE ROW IS A REAL MISTAKE OF MINE. ────────────────
-- `probe-only-not-created` is an OWNER credential on a PHI-holding licence with
-- a trivial six-digit PIN. I created it by accident: I sent a bootstrap call intending
-- it to be REFUSED (I expected the prior run's credentials to still exist and
-- for bootstrap to be disarmed), named the employee_id to say so, and bootstrap
-- was in fact armed -- the earlier cleanup had already been run. The call
-- succeeded and minted a working owner. I used it for the verification rather
-- than mint a second one, but it must not survive this session.
-- A trivial-PIN owner on a dental practice's credential table is exactly the
-- class of problem today's work existed to close.
--
-- ── WHY DELETE AND NOT DEACTIVATE, AGAIN THE EXCEPTION ───────────────────
-- The platform rule is deactivate, never delete, and it is right: the row keeps
-- created_at, role history and any audit rows referencing that employee_id, so
-- a departing employee stays auditable. These two rows are not employees. They
-- were minted by a verification run, have no history worth preserving, and a
-- deactivated row still carries a scrypt hash of a PIN that should not persist
-- on this licence. Removing them entirely is the smaller risk.
-- Do NOT generalise this. For a real person, deactivate.
--
-- ── ORDER MATTERS ───────────────────────────────────────────────────────
-- Delete the PROVIDER credential first and the OWNER last. Deleting the only
-- owner while another row remains leaves a licence whose surviving credential
-- can provision nothing and where bootstrap still refuses (it checks for ANY
-- row, active or not) -- the permanent lockout that lost SD-AUDIT-2026.
-- Removing both, owner last, returns DNT-PINNACLE-2026 to a clean
-- unprovisioned state where bootstrap re-arms.

-- ─────────────────────────────────────────────────────────────────────────
-- 1. CREDENTIALS -- provider first
-- ─────────────────────────────────────────────────────────────────────────
delete from public.sairndental_employee_auth
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'dnt-verify-provider';

-- 2. the owner, LAST
delete from public.sairndental_employee_auth
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id = 'probe-only-not-created';

-- ─────────────────────────────────────────────────────────────────────────
-- 3. TEST DATA created by the round trip, by exact id.
--    Enumerated from a live owner read after the run, not from memory:
--      dnt_patients     PT-VERIFY-1, PT-VERIFY-2
--      dnt_providers    PV-VERIFY-A
--      dnt_appointments AP-VERIFY-1
--    PV-VERIFY-B and PV-VERIFY-SELF were REFUSED (409 EMPLOYEE_ALREADY_LINKED
--    and 403 ROLE_NOT_PERMITTED) and confirmed absent from a live read -- the
--    refusals were real, not partial writes, so there is nothing to clean up
--    for either. They are named here only so a reader who finds them in the
--    transcript knows they were checked.
-- ─────────────────────────────────────────────────────────────────────────
delete from public.dnt_appointments
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and appointment_id = 'AP-VERIFY-1';

delete from public.dnt_providers
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and provider_id = 'PV-VERIFY-A';

delete from public.dnt_patients
 where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
   and patient_id in ('PT-VERIFY-1', 'PT-VERIFY-2');

-- ── DELIBERATELY NOT TOUCHED ─────────────────────────────────────────────
-- `PV-VERIFY-1` / "Dr. Verify Test" is residue from the EARLIER (auth)
-- verification run, not from this one, and seven pre-existing PT-<timestamp>
-- patient rows predate both. Left alone per the standing instruction not to
-- touch anything else on the licence. Flagged rather than silently removed --
-- if the demo licence is meant to be clean, PV-VERIFY-1 is a leftover somebody
-- should decide about, but it is not this file's to delete.
--
-- ── NOTE ON GRANTS ───────────────────────────────────────────────────────
-- The dnt_* tables carry NO delete grant for service_role (revoked
-- 2026-08-25, sql/unused_delete_grant_revoke_2026-08-24.sql), which is why the
-- API has no delete path and why this cleanup is SQL rather than an endpoint
-- call. Running it in the Supabase SQL editor is not affected -- that session is
-- not service_role. Do NOT "fix" a permission error here by re-granting delete.
--
-- ── NOTE ON THE license_hash EXPRESSION ──────────────────────────────────
-- Computed in-query rather than pasted as a literal so there is no chance of
-- transcribing the wrong 64 hex characters and silently deleting nothing.
-- `digest()` needs pgcrypto; if it is not enabled, derive the sha256 of
-- 'DNT-PINNACLE-2026' rather than trusting a pasted value, and confirm the
-- WHERE clause matches the expected row count before running.

-- ── CONFIRM AFTERWARDS. Do not skip: a multi-statement paste into the SQL
-- editor can apply partway and still report success (seen twice on 2026-08-26).
--   select employee_id, role, active from public.sairndental_employee_auth;
--     -- expect 0 rows
--   select provider_id from public.dnt_providers
--    where provider_id like 'PV-VERIFY-%';           -- expect only PV-VERIFY-1
--   select patient_id from public.dnt_patients
--    where patient_id like 'PT-VERIFY-%';            -- expect 0 rows
--   select appointment_id from public.dnt_appointments
--    where appointment_id like 'AP-VERIFY-%';        -- expect 0 rows
--
-- Then confirm LIVE. Deliberately WITHOUT a PIN -- a login probe would require
-- writing the credential's PIN down somewhere, which is the thing this file is
-- avoiding, and a wrong PIN returns INVALID_CREDENTIALS whether the row exists
-- or not, so it proves nothing anyway. These two do prove it:
--   POST /api/dnt-auth {"action":"roster"}    (licence only, no session)
--     -> 403 FORBIDDEN either way; NOT a proof, listed only so it is not mistaken for one
--   POST /api/sd-data  {"action":"read","resource":"dnt_patients"}   (licence only)
--     -> must remain 401 NO_SESSION
-- The real proof is the SELECT above returning 0 credential rows. If you want a
-- live one, a fresh `bootstrap` succeeding is conclusive (it refuses while ANY
-- row exists) -- but it mints a new owner, so only do that if you intend to keep
-- it, and never with a trivial PIN.
