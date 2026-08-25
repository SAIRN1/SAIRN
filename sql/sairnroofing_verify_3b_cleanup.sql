-- sql/sairnroofing_verify_3b_cleanup.sql
-- Cleanup for the SAIRNroofing Phase 3b live round trip (2026-08-24). NOT RUN
-- by this session. Run once in the Supabase SQL editor AFTER the assignment-gate
-- portion has been run (it needs the foreman seed first).
--
-- SCOPE WIDENED AGAIN 2026-08-25 (second pass): this now also covers the
-- Phase 5 contingency-agreement round trip. Two more DELETEs at the bottom --
-- rf_claim_agreements is APPEND-ONLY with no delete verb through the API, so
-- like rf_claim_photos and rf_certifications its verification rows can only be
-- removed here.
--
-- SCOPE WIDENED 2026-08-25: this now also covers the Phase 3c live round trip.
-- The filename is deliberately NOT changed -- 3c wrote only VERIFY-tagged rows
-- that the LIKE patterns below already match, so a separate 3c file would issue
-- the identical DELETEs against the identical rows. One cleanup, not two.
--
-- license_hash = sha256('RF-PINNACLE-2026').
--
-- WHAT THE ROUND TRIPS WROTE, all disposable, all VERIFY-tagged:
--   rf_claim_photos : RFCPH-VERIFY-1        (append-only -- needs SQL to remove)
--   rf_claims       : RFCLM-VERIFY-1        (mutable)
--                     RFCLM-VERIFY-3C-NOMEAS      (3c: the unmeasured-job case)
--   rf_jobs         : RFJOB-VERIFY-3B       (the job the claim hung on; 3c also
--                     appended one measurement_correction entry to it, which
--                     goes away with the row)
--                     RFJOB-VERIFY-3C-NOMEAS      (3c: kept measurement-free on
--                     purpose, to prove has_measurement:false does not crash)
--   employee_auth   : rf-verify-admin, rf-verify-fmA, rf-verify-fmB (disposable)
--
-- PHASE 5 (2026-08-25) added, all matched by the SAME patterns below -- no new
-- delete was needed for the claims/jobs, only the two at the bottom:
--   rf_jobs             : RFJOB-VERIFY-P5
--   rf_claims           : RFCLM-VERIFY-P5-OH, -SHOP, -NORULE, -IND
--   rf_claim_agreements : RFAGR-VERIFY-P5-OH, -R2 (the rescission), -SHOP,
--                         -NR, -IND        (append-only -- needs SQL to remove)
--   rf_contingency_rules: RFCON-VERIFY-OH-HSSA
-- Three further ids appear in the harness and are NOT in the database because
-- the endpoint refused them, which was the point of those checks:
-- RFCON-VERIFY-BAD (no citation), RFCON-VERIFY-FM (foreman, 403),
-- RFAGR-VERIFY-P5-R0/R1 (rescission with no / a bogus supersedes),
-- RFAGR-VERIFY-P5-EVIL (wrong foreman, 403).
--
-- Phase 3c wrote NO new table and NO new resource: `reconcile` is compute-only
-- and was proven live to write nothing at all (claim and jobs rows byte-identical
-- across repeat calls). Everything above came from ordinary rf_jobs/rf_claims
-- writes used to set up the inputs.

delete from public.rf_claim_photos
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and photo_id like 'RFCPH-VERIFY-%';

delete from public.rf_claims
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and claim_id like 'RFCLM-VERIFY-%';

delete from public.rf_jobs
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and job_id like 'RFJOB-VERIFY-%';

-- Phase 5: the append-only agreement rows, and the disposable contingency rule.
-- The rule delete is scoped to the VERIFY prefix so a REAL Ohio rule a
-- contractor entered is never caught by it.
delete from public.rf_claim_agreements
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and agreement_id like 'RFAGR-VERIFY-%';

delete from public.rf_contingency_rules
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and rule_id like 'RFCON-VERIFY-%';

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
--   select count(*) from public.rf_claim_agreements where agreement_id like 'RFAGR-VERIFY-%';
--   select count(*) from public.rf_contingency_rules where rule_id like 'RFCON-VERIFY-%';
--
-- NOTE: the RFCERT-VERIFY-* rows and rf-verify-admin from the 3a round trip are
-- covered by sql/sairnroofing_verify_cleanup.sql. If that has not been run yet,
-- run it too (or run this one, which removes rf-verify-admin as well -- the
-- rf_certifications rows still need that other file).
