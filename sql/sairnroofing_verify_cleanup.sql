-- sql/sairnroofing_verify_cleanup.sql
-- Cleanup for the SAIRNroofing Phase 3a live round trip (2026-08-24). NOT RUN
-- by this session (no DB access). Run once in the Supabase SQL editor.
--
-- Same situation as the SAIRNdental DCRED-VERIFY cleanup: rf_certifications has
-- no delete verb through the API by design (append-only -- a certification row
-- asserts a named worker held a real credential on a real date), so the six
-- verification rows cannot be removed from outside the database. That is the
-- design working, not a gap.
--
-- THREE THINGS GOT WRITTEN during the round trip, all disposable:
--
--   1. Six rf_certifications rows under employee rf-verify-admin, all prefixed
--      RFCERT-VERIFY- and all carrying VERIFY / disposable labels:
--        RFCERT-VERIFY-FALL     safety_training  (expires 2026-09-23)
--        RFCERT-VERIFY-FALL2    safety_training  (supersedes FALL, 2028-09-23)
--        RFCERT-VERIFY-LADDER   safety_training  (expires 2026-09-24)
--        RFCERT-VERIFY-OSHA     osha_card        (has_expiry:false)
--        RFCERT-VERIFY-TESLA    installer_cert   (expires 2027-06-01)
--        RFCERT-VERIFY-LOCAL    local_license    (Columbus, 2026-12-31)
--
--   2. The rf-verify-admin employee row itself (seeded by
--      sql/sairnroofing_verify_admin_seed.sql).
--
--   3. THREE rf_cert_rules rows: the real Ohio + federal requirements. These
--      are NOT deleted below -- they are genuine, sourced production data the
--      prospect's app needs (Ohio's no-state-licence answer and the two OSHA
--      rules), loaded with their citations. Leaving them is the correct call,
--      the same way the SAIRNdental dnt_cred_rules were kept.
--
-- license_hash below is sha256('RF-PINNACLE-2026').

-- 1. The six verification certification rows. Scoped to BOTH the prefix and the
--    disposable admin, so no real record can be caught even if a prefix were
--    reused by accident later.
delete from public.rf_certifications
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and employee_id  = 'rf-verify-admin'
   and entry_id like 'RFCERT-VERIFY-%';

-- 2. The disposable admin account.
delete from public.sairnroofing_employee_auth
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and employee_id  = 'rf-verify-admin';

-- Verify after (expect 0 for both):
--   select count(*) from public.rf_certifications
--    where entry_id like 'RFCERT-VERIFY-%';
--   select count(*) from public.sairnroofing_employee_auth
--    where employee_id = 'rf-verify-admin';
-- And confirm the real rules survived (expect 3):
--   select count(*) from public.rf_cert_rules;
