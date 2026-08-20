-- sql/sairnbuild_visual_review_cleanup.sql
-- Leftover test data from live visual-review verification (2026-08-20) --
-- needs a direct Supabase run, no delete action exists for bld_bids via
-- the API (same limitation as every other sdn_/leg_ resource's cleanup
-- files this session).
--
-- 1. A real employee credential 'visual-test-owner' was bootstrapped on
--    BLD-PINNACLE-2026 to confirm login/bootstrap actually works in
--    production (it does -- sql/sairnbuild_employee_auth_schema.sql was
--    already live). Same low-risk precedent as every other app's
--    demo-license test accounts this session -- safe to leave, or remove
--    with the statement below if Michael wants BLD-PINNACLE-2026 clean.
-- 2. A real bid "Visual Review Test Client" was saved to confirm the
--    bld_bids write path (privacy gate, Assign-To/reassign UI) actually
--    works in production (it does -- sql/sairnbuild_bids_schema.sql was
--    already live too).
--
-- Run only the statements Michael actually wants -- both are safe,
-- narrowly scoped to this one test row/account, nothing else touched.

-- Remove the test bid:
-- delete from public.bld_bids where license_hash = (select license_hash from license_keys where license_key = 'BLD-PINNACLE-2026') and bid_id in (select bid_id from public.bld_bids b join license_keys lk on true where lk.license_key='BLD-PINNACLE-2026' and (b.data->>'client') = 'Visual Review Test Client');

-- Simpler, if bid_id is known directly (check the app's Bids table for the exact id first):
-- delete from public.bld_bids where license_hash = (select license_hash from license_keys where license_key = 'BLD-PINNACLE-2026') and (data->>'client') = 'Visual Review Test Client';

-- Remove the test employee credential:
-- delete from public.sairnbuild_employee_auth where license_hash = (select license_hash from license_keys where license_key = 'BLD-PINNACLE-2026') and employee_id = 'visual-test-owner';
