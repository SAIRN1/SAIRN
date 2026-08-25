-- sql/sairnroofing_verify_accounts_cleanup.sql
-- The three disposable SAIRNroofing verification accounts. NOT RUN by any
-- session that writes it -- this is a deliberate, one-time act.
--
-- ── WHY THIS IS ITS OWN FILE (2026-08-25) ────────────────────────────────
-- These deletes used to live at the bottom of
-- sql/sairnroofing_verify_3b_cleanup.sql, in the same pass as the verification
-- ROWS. That coupling cost real time twice in one session: cleaning up after a
-- phase also destroyed the only credentials the NEXT phase's live round trip
-- could use, so it opened with three 401s and a re-seed before any
-- verification could begin.
--
-- The two concerns have genuinely different schedules:
--   ROWS     -- clean after EVERY phase. RF-PINNACLE-2026 may be shown to a
--               prospect at any time and must not carry visible test junk.
--               See sql/sairnroofing_verify_3b_cleanup.sql.
--   ACCOUNTS -- clean ONCE, when the whole of Phase 4 (4a/4d/4b/4c) is done.
--               They are invisible in any demo (they appear only in the
--               employee roster, which a prospect is not being shown), they are
--               scoped to this single license, and re-seeding them before every
--               phase is churn with no benefit.
--
-- RUN THIS WHEN: Phase 4c is finished and live-verified, or whenever
-- SAIRNroofing verification work stops for good.
--
-- license_hash = sha256('RF-PINNACLE-2026').
--
-- THE THREE ACCOUNTS, all disposable, none belonging to a real person:
--   rf-verify-admin  role admin    (seeded by sairnroofing_verify_admin_seed.sql)
--   rf-verify-fmA    role foreman  (seeded by sairnroofing_verify_foremen_seed.sql)
--   rf-verify-fmB    role foreman  (same file)
--
-- NOT AFFECTED: the real 'owner' account provisioned during Phase 1-2
-- verification. Its PIN is not known to any session and it is the license's
-- only non-disposable credential -- deleting it would lock the license out of
-- its own app, which is why this file names its three targets explicitly
-- rather than deleting by a prefix or a NOT IN.

delete from public.sairnroofing_employee_auth
 where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b'
   and employee_id in ('rf-verify-admin', 'rf-verify-fmA', 'rf-verify-fmB');

-- Verify after (expect 0):
--   select count(*) from public.sairnroofing_employee_auth
--    where employee_id in ('rf-verify-admin','rf-verify-fmA','rf-verify-fmB');
--
-- And confirm the real account survived (expect 1 or more, and NOT zero --
-- zero here means the license has no way back in):
--   select employee_id, role, active from public.sairnroofing_employee_auth
--    where license_hash = '47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b';
