-- sql/sairndental_referrals_verify_cleanup.sql
-- Removes the ONE probe row written to production on 2026-08-25 while
-- verifying the dnt_referrals server path end to end.
--
-- NOT RUN by any session. Run it in the Supabase SQL editor as the owner.
--
-- ── WHY THIS FILE HAS TO EXIST AT ALL ────────────────────────────────────
-- The probe cannot be cleaned up through the API, and that is by design as
-- of tonight rather than an oversight. Confirmed live, not assumed:
--     POST /api/sd-data {"resource":"dnt_referrals","action":"delete",...}
--     -> HTTP 400 {"error":{"message":"action must be 'read' or 'write'"}}
-- api/sd-data.js's DNT_RESOURCES block implements only 'read' and 'write'
-- (:4854, :4862); the platform's single delete path is the SC_RESOURCES
-- (SAIRNcode) branch. On top of that, sql/unused_delete_grant_revoke
-- _2026-08-24.sql revoked service_role's DELETE on all 134 non-sc_* tables
-- on 2026-08-25, so even a new API branch could not delete this row until
-- the grant were deliberately re-added.
--
-- THIS IS THE SECOND TIME THE SAME THING HAS HAPPENED. The open-work index
-- records that the platform-wide "no delete capability" row was originally
-- found "while trying to clean up a verification probe from
-- dnt_appointments." Verifying a write path on production leaves a row that
-- the product itself has no way to remove. Worth deciding deliberately --
-- either a disposable verification license whose rows can be bulk-removed,
-- or accepting that every live write check needs a hand-written cleanup
-- file like this one.
--
-- ── SCOPE: ONE ROW, NAMED EXPLICITLY ─────────────────────────────────────
-- Keyed on the referral_id, not on a LIKE pattern and not on the license
-- alone -- DNT-PINNACLE-2026 is a shared demo licence and may carry real
-- demo data that must survive.

-- 1. LOOK FIRST. Expect exactly one row.
select referral_id, license_hash, data->>'patient_name' as patient_name,
       data->>'status' as status, updated_at
from public.dnt_referrals
where referral_id = 'RF-VERIFY-PROBE-20260825';

-- 2. DELETE, only after the row above is the probe and nothing else.
-- delete from public.dnt_referrals
-- where referral_id = 'RF-VERIFY-PROBE-20260825';

-- 3. VERIFY. Expect zero rows.
-- select count(*) as should_be_zero
-- from public.dnt_referrals
-- where referral_id = 'RF-VERIFY-PROBE-20260825';

-- ── WHAT THE PROBE PROVED, so it is not re-run needlessly ────────────────
-- Against https://sairn.vercel.app/api/sd-data on 2026-08-25, licence
-- DNT-PINNACLE-2026, all four legs:
--   read   -> {"ok":true,"data":[],"provisioned":true}   (was provisioned
--             false before the migration -- this is what changed)
--   write  -> 200, row created, and location_id "LOC-DEFAULT" stamped
--             SERVER-side; it was not sent in the payload, confirming
--             dntLocation.stampLocation() covers this path too
--   update -> 200, status Pending -> Completed via the same upsert the UI's
--             setReferralStatus() uses, and the read-back returned exactly
--             ONE row, proving on_conflict merged rather than inserting a
--             duplicate. That is a real UPDATE, which also confirms live
--             that tonight's DELETE sweep did not collaterally drop UPDATE
--             on this table -- the 134-LOST/0-GAINED result holding on a
--             table exercised by real traffic rather than only in a diff
--   delete -> 400 by design, as above
