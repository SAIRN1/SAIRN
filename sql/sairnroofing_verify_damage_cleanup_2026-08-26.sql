-- sql/sairnroofing_verify_damage_cleanup_2026-08-26.sql
-- Scoped cleanup for the repair-vs-replace live round trip, 2026-08-26.
-- NOT RUN by this session (no DB access). Every row below was created by that
-- run and nothing else; each is targeted by exact id, never by license_hash
-- alone.
--
-- Needed for the same reason SAIRNsenior's cleanup was: none of these tables
-- has a delete path through the API. rf_jobs, rf_claims and rf_settings are all
-- granted `select, insert, update` with no delete, deliberately, so live
-- write-path verification can only be undone as owner in the SQL editor.
--
-- ALL DATA SYNTHETIC. Carrier "SYNTHETIC CARRIER", address "1 Test Way", photo
-- ids "RFCPH-SYNTH-*" that reference no real evidence rows.
--
-- ── WHAT THE RUN PROVED, so the value is not lost with the rows ──────────
-- 24/24 against production on RF-PINNACLE-2026. All three outcomes on real
-- data: North 9 hits over 1 test square met the configured 8; South 2 over 1
-- came back below; East, with nothing recorded, came back insufficient_evidence
-- carrying "This slope has not been assessed. It is not a finding of low
-- damage." West proved the density rule live -- 12 hits over 3 test squares is
-- 4 per square, which is BELOW 8, where a raw-total comparison would have
-- wrongly called the slope total.
--
-- Both refusal branches fired against real config: a claim with no peril
-- recorded refused with "no threshold can be selected", and a peril with no
-- configured threshold refused naming that peril rather than falling back to
-- the 8-hits trade convention. A threshold submitted without a source was
-- rejected at storage with INVALID_SETTING, not merely at compute time.
--
-- Confirmed live, not inferred: `updated_by` came from the verified session
-- and the forged payload value was discarded; assess_damage wrote NO snapshot
-- (compute-only) and the snapshot appeared only after an explicit save, then
-- read back carrying the threshold that was actually used; a per-claim override
-- won AND was reported as an override; wind read creased_or_missing against the
-- wind threshold while ignoring 40 hail hits on the same slope; and the whole
-- response was scanned for "totalled", "should_replace", "approved",
-- "entitled" and "owed" with no hit -- there is no whole-roof verdict.

-- ── 1. claims (both, including the no-peril refusal claim) ───────────────
delete from public.rf_claims
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and claim_id in ('RFCLM-DMGVERIFY-20260826', 'RFCLM-DMGVERIFY-20260826-NP');

-- ── 2. the job they hung off (delete AFTER the claims that reference it) ─
delete from public.rf_jobs
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and job_id = 'RFJOB-DMGVERIFY-20260826';

-- ── 3. THE THRESHOLD ROW IS CONFIG, NOT DEBRIS -- DECIDE, DO NOT REFLEX ──
-- rf_settings now holds a damage_threshold row for this licence:
--   hail 8 / wind 3, both sourced "SYNTHETIC verification 2026-08-26 -- ...".
--
-- Deleting it is NOT automatically right. The feature does not work without a
-- threshold -- an assessment refuses -- so removing it returns the app to the
-- state the refusal tests exercised. But the SOURCES are wrong for real use:
-- they say "SYNTHETIC verification", and a threshold citing a verification run
-- as its authority is exactly the unsourced-number problem the engine exists to
-- prevent. Two honest options:
--
--   (a) REPLACE with the company's real numbers and real citation (preferred --
--       there is no delete grant on rf_settings anyway, so this is an update):
--         update public.rf_settings
--            set data = '{"hail":{"hits_per_test_square":8,"source":"REPLACE ME"},
--                         "wind":{"hits_per_test_square":3,"source":"REPLACE ME"}}'::jsonb,
--                updated_at = now()
--          where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
--            and setting_key = 'damage_threshold';
--
--   (b) BLANK it, returning the app to "no threshold configured", which is the
--       honest state until a real one is decided:
--         update public.rf_settings set data = '{}'::jsonb, updated_at = now()
--          where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
--            and setting_key = 'damage_threshold';
--
-- Left commented deliberately. This is a product decision about a demo
-- licence, not cleanup.

-- ── SEPARATE, AND NOT THIS RUN'S DEBRIS ─────────────────────────────────
-- `rf-verify-admin` is STILL LIVE on RF-PINNACLE-2026 -- it authenticated this
-- round trip. sql/sairnroofing_verify_admin_seed.sql's own cleanup block says
-- to remove it after the Phase 3a round trip, and that was evidently never run.
-- Flagging rather than folding in: it is another session's row, its removal is
-- their call, and this file should not quietly delete a credential it did not
-- create. Its PIN is in a public repo, which is the argument for removing it.
--   delete from public.sairnroofing_employee_auth
--    where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
--      and employee_id  = 'rf-verify-admin';

-- ── Confirm afterwards (expect 0 from each of the first two) ─────────────
--   select count(*) from public.rf_claims where claim_id like 'RFCLM-DMGVERIFY-%';
--   select count(*) from public.rf_jobs   where job_id   = 'RFJOB-DMGVERIFY-20260826';
--   select setting_key, data from public.rf_settings
--    where setting_key = 'damage_threshold';   -- whatever you decided in 3
