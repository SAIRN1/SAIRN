-- sql/sairnroofing_verify_3b_cleanup.sql
-- Cleanup for the SAIRNroofing Phase 3b live round trip (2026-08-24). NOT RUN
-- by this session. Run once in the Supabase SQL editor AFTER the assignment-gate
-- portion has been run (it needs the foreman seed first).
--
-- license_hash = sha256('RF-PINNACLE-2026').
--
-- WHAT THE ROUND TRIP WROTE, all disposable, all VERIFY-tagged:
--   rf_claim_photos : RFCPH-VERIFY-1        (append-only -- needs SQL to remove)
--   rf_claims       : RFCLM-VERIFY-1        (mutable)
--   rf_jobs         : RFJOB-VERIFY-3B       (the job the claim hung on)
--   employee_auth   : rf-verify-admin, rf-verify-fmA, rf-verify-fmB (disposable)

delete from public.rf_claim_photos
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and photo_id like 'RFCPH-VERIFY-%';

delete from public.rf_claims
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and claim_id like 'RFCLM-VERIFY-%';

delete from public.rf_jobs
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and job_id like 'RFJOB-VERIFY-%';

-- The three disposable accounts (the 3a admin + the 3b foremen). This also
-- supersedes the cleanup line in sql/sairnroofing_verify_admin_seed.sql --
-- delete all three here in one pass.
delete from public.sairnroofing_employee_auth
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and employee_id in ('rf-verify-admin', 'rf-verify-fmA', 'rf-verify-fmB');

-- Verify after (expect 0 for all four):
--   select count(*) from public.rf_claim_photos where photo_id like 'RFCPH-VERIFY-%';
--   select count(*) from public.rf_claims where claim_id like 'RFCLM-VERIFY-%';
--   select count(*) from public.rf_jobs where job_id like 'RFJOB-VERIFY-%';
--   select count(*) from public.sairnroofing_employee_auth
--    where employee_id in ('rf-verify-admin','rf-verify-fmA','rf-verify-fmB');
--
-- NOTE: the RFCERT-VERIFY-* rows and rf-verify-admin from the 3a round trip are
-- covered by sql/sairnroofing_verify_cleanup.sql. If that has not been run yet,
-- run it too (or run this one, which removes rf-verify-admin as well -- the
-- rf_certifications rows still need that other file).
