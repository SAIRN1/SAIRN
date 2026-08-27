-- sql/sairnsenior_evv_readiness_verify_cleanup_2026-08-27.sql
-- Cleanup for the EVV submission-readiness live round trip, 2026-08-27.
--
-- NOT RUN by the session that wrote this file -- it has no DB access. Every row
-- named below was created through the real deployed API against
-- SEN-PINNACLE-2026 during verification, and is real production data until this
-- runs.
--
-- ── READ THIS BEFORE TRUSTING THE "NOT RUN" LABEL ────────────────────────
-- On 2026-08-26 a spot-check of eight named probe rows across five other
-- cleanup files found six of the eight measurable ones GONE despite their files
-- still being labelled NOT RUN. "NOT RUN" is a claim about the FILE, and it
-- stops describing the database the moment anyone runs part of it by hand.
-- Verify with the SELECTs at the bottom before assuming anything here is still
-- present. See docs/SAIRN-OPEN-WORK-INDEX.md.
--
-- ── WHAT WAS CREATED AND WHY ─────────────────────────────────────────────
-- The readiness engine had nothing to prove against: the previous SAIRNsenior
-- verification's rows were already gone (its own cleanup had evidently run --
-- bootstrap succeeded, which it could not have done had any credential
-- survived). So a minimal, deliberately-shaped set was seeded:
--
--   sen_clients      CL-EVVRDY-1   -- no member_id, which is the point
--   sen_caregivers   CG-EVVRDY-1   -- no state_caregiver_id, same
--   sen_visits       VS-EVVRDY-A   -- completed, full GPS both ends
--                    VS-EVVRDY-B   -- completed, NO GPS (the live denial case)
--                    VS-EVVRDY-C   -- still scheduled (proves not-checkable)
--   sen_settings     evv_config    -- state OH / aggregator sandata
--                    agency_profile
--   *_employee_auth  sen-evvready-verify-20260827  (owner)
--                    CG-EVVRDY-1                   (caregiver)
--
-- TWO CREDENTIALS, and the second one is the interesting part. An OWNER's write
-- of clock_in_at/clock_out_at/GPS/status was SILENTLY STRIPPED by the server --
-- correctly, because sen_visits enforces a field-level split where EVV fields
-- are writable only by the ASSIGNED caregiver. A manager cannot forge an EVV
-- clock-in. So a caregiver credential matching the visit's assignee had to be
-- provisioned to produce a genuinely completed visit. That is the app working,
-- not a workaround.
--
-- ── PINS ARE DELIBERATELY NOT IN THIS FILE ───────────────────────────────
-- Both PINs were generated randomly at verification time and were never written
-- to the repository. The previous SAIRNsenior cleanup file recorded its PIN in
-- the repo and then had to warn readers about it (see its own lines 79-83).
-- Not repeating that. Neither credential is loggable-in by anyone reading this,
-- which is a reason to remove them, not a reason to keep them.
--
-- ── THE ORDER MATTERS, AND SO DOES THE TRAPDOOR ──────────────────────────
-- Removing BOTH credential rows re-arms action:bootstrap for this licence,
-- because the bootstrap existence probe deliberately does NOT filter on
-- `active` (api/sen-auth.js). That is the right end state for a demo licence: a
-- real customer should create their own owner rather than inherit a throwaway.
--
-- DO NOT instead "clean up" by deactivating them. Deactivating the last owner
-- leaves a licence where nobody can log in, nobody can run setup, and bootstrap
-- still 409s -- permanently unusable through the API and recoverable only by
-- direct database access. That is exactly how SD-AUDIT-2026 was lost. Delete,
-- or leave them alone; do not deactivate.
--
-- The public.license_keys row for SEN-PINNACLE-2026 STAYS. It is a real demo
-- licence in the same class as SB-PINNACLE-2026 and GRD-DEMO-2026.

begin;

-- 1. Visits first (they reference the client and the caregiver).
delete from public.sen_visits
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and visit_id in ('VS-EVVRDY-A', 'VS-EVVRDY-B', 'VS-EVVRDY-C');

-- 2. The client and caregiver records.
delete from public.sen_clients
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and client_id = 'CL-EVVRDY-1';

delete from public.sen_caregivers
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and caregiver_id = 'CG-EVVRDY-1';

-- 3. The two settings rows.
--    JUDGMENT CALL, FLAGGED RATHER THAN DECIDED HERE: if SEN-PINNACLE-2026 is
--    kept as a live demo, leaving evv_config (OH / sandata) is arguably better
--    than removing it -- it makes the Settings panel show a configured agency
--    instead of an empty one. Both rows are real configuration, not probe data.
--    Remove them if you want the licence back to a true blank slate.
delete from public.sen_settings
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and setting_key in ('evv_config', 'agency_profile');

-- 4. Both credentials. See the trapdoor note above -- delete, never deactivate.
delete from public.sairnsenior_employee_auth
 where license_hash = encode(digest('SEN-PINNACLE-2026', 'sha256'), 'hex')
   and employee_id in ('sen-evvready-verify-20260827', 'CG-EVVRDY-1');

commit;

-- ── VERIFY AFTER RUNNING (each should return 0) ──────────────────────────
--   select count(*) from public.sen_visits     where visit_id like 'VS-EVVRDY-%';
--   select count(*) from public.sen_clients    where client_id = 'CL-EVVRDY-1';
--   select count(*) from public.sen_caregivers where caregiver_id = 'CG-EVVRDY-1';
--   select count(*) from public.sairnsenior_employee_auth
--     where employee_id in ('sen-evvready-verify-20260827','CG-EVVRDY-1');
--
-- And this should still return 1 -- the licence itself is NOT being removed:
--   select count(*) from public.license_keys where key = 'SEN-PINNACLE-2026';
--
-- Then confirm bootstrap is re-armed, which is the real proof the credential
-- rows are gone rather than merely deactivated:
--   POST /api/sen-auth {"action":"bootstrap", ...} with SEN-PINNACLE-2026
--   -- a 409 ALREADY_PROVISIONED means a credential row survived.
