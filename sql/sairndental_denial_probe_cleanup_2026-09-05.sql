-- sql/sairndental_denial_probe_cleanup_2026-09-05.sql
-- Removes the ONE probe row written to production on 2026-09-05 while
-- live-verifying the dnt_denial write validation.
--
-- NOT RUN by any session. Run it in the Supabase SQL editor as the owner.
--
-- ── HOW IT GOT THERE, stated plainly because it was MY error ─────────────
-- The first live probe ran roughly a minute after the push, against a build
-- that did not yet carry the fix. All six deliberately-bad denials returned
-- 200 -- and the last one to land created this row. A second probe 100
-- seconds later returned 400 INVALID_DENIAL on the same payload, so the 200s
-- were a stale deploy and not a broken validator.
--
-- That is the push protocol's own point, arriving the hard way: a clean
-- `git push` is not proof the live app reflects the change, and a live
-- verification run too early reports the OLD build's behaviour with complete
-- confidence. The lesson worth keeping is narrower than "wait longer" --
-- it is that a probe which WRITES must not be the thing you use to find out
-- whether the deploy has landed. A read-only probe answers that question and
-- leaves nothing behind.
--
-- All eight refusals were re-verified live afterwards and every one returned
-- 400 INVALID_DENIAL. Every one of those re-runs deliberately reused this
-- same id, so a regression could only overwrite the row already needing
-- cleanup and never create a second one.
--
-- ── WHY THIS FILE HAS TO EXIST AT ALL ───────────────────────────────────
-- Unchanged from sql/sairndental_referrals_verify_cleanup.sql, and this is
-- now the third recorded instance of the same thing: api/sd-data.js
-- implements only 'read' and 'write' for DNT_RESOURCES, the platform's one
-- delete path is the SC_RESOURCES (SAIRNcode) branch, and
-- sql/unused_delete_grant_revoke_2026-08-24.sql revoked service_role's
-- DELETE on the non-sc_* tables anyway. Verifying a write path on production
-- leaves a row the product itself cannot remove. See the open-work index row
-- "Live write-path verification leaves rows the product cannot delete".
--
-- ── SCOPE: ONE ROW, NAMED EXPLICITLY ────────────────────────────────────
-- Keyed on the denial_id, not on a LIKE pattern and not on the licence alone
-- -- DNT-PINNACLE-2026 is a shared demo licence and may carry real demo data
-- that must survive.
--
-- The row as it stands is a denial with NO patient_id, which is precisely
-- the shape the fix now refuses: it is attached to no account, so nothing in
-- the app can show it against a patient, and dnAtStake() still counts its
-- 250 toward the amount at stake because its stage is 'none'.

-- 1. LOOK FIRST. Expect exactly one row.
select denial_id, license_hash,
       data->>'patient_id' as patient_id,
       data->>'amount'     as amount,
       data->>'denied_on'  as denied_on,
       data->>'stage'      as stage,
       updated_at
from public.dnt_denial
where denial_id = 'DN-PROBE-1';

-- 2. DELETE, only after the row above is the probe and nothing else.
-- delete from public.dnt_denial
-- where denial_id = 'DN-PROBE-1';

-- 3. VERIFY. Expect zero rows.
-- select count(*) as should_be_zero
-- from public.dnt_denial
-- where denial_id = 'DN-PROBE-1';

-- ── WHAT THE PROBE PROVED, so it is not re-run needlessly ───────────────
-- Against https://sairn.vercel.app/api/sd-data on 2026-09-05, licence
-- DNT-PINNACLE-2026, owner session, resource dnt_denial, action write.
-- All eight bad shapes returned 400 INVALID_DENIAL:
--   denied_on 'last tuesday'   -- unparseable, would leave the closing-soon warning
--   denied_on '2026-02-31'     -- JavaScript rolls it to 3 March, so the
--                                 appeal deadline would be real-looking and
--                                 counted from a day that never existed
--   denied_on '2026-02-29'     -- non-leap year, same rollover class
--   amount -250                -- reduces the at-stake total below the others
--   amount 'lots'              -- dnAtStake() reads Number(x) || 0, so zero
--   stage 'appealed'           -- absent from DN_DECIDED, counts as open forever
--   recovered 400 of 250       -- the panel prints "recovered of denied"
--   patient_id ''              -- orphan row
-- The ACCEPT side was deliberately NOT probed live: proving it would mean
-- writing a real denial into the demo practice, which is the cost this file
-- exists to clean up. It is covered by 112/112 assertions in
-- api/sd-data-dental-ledger-validation.test.js, including all seven stages
-- the form's own <select> can produce and a real leap day.
