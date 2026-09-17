-- sql/sairncash_verification_trial_cleanup.sql
-- Removes the throwaway trial rows created by verification runs.
--
-- ⚠ NOT RUN. Flagged for Michael.
--
-- WHY THIS FILE EXISTS INSTEAD OF AN API CALL: api/sairncash/ exposes
-- trial-start, trial-verify, trial-renew, checkout, verify, waitlist and
-- firebase-config. NONE of them can delete a trial. trial-renew is
-- admin-secret-gated but only extends a window; there is no delete verb and
-- no deactivate flag on a trial row, so a verification signup cannot be
-- cleaned up from outside the database.
--
-- This is the same structural gap that was just closed for employee
-- credentials on StoneDesk and SAIRNcode (api/sd-auth.js and api/sc-auth.js
-- gained set_active on 2026-08-23/24). SAIRNcash's trial table has the same
-- shape of problem and has NOT been given the same treatment -- flagged
-- here rather than fixed, because a trial lifecycle is a product decision
-- (does a cancelled trial disappear, or stay recorded as cancelled?) and
-- not a like-for-like port.
--
-- ROWS TO REMOVE -- all use the reserved .example TLD (RFC 2606), so none
-- can belong to a real person:
--   audit-probe-20260824@sairncash-verification.example
--     Created 2026-08-24 during the ground-truth audit, probing whether
--     trial-start reached a real table. It did.
--   cc-returning-20260824@sairncash-verification.example
--     Created 2026-08-24 for the returning-user click-through that verified
--     the showPage('app') -> initApp() lockout fix.
--
-- Earlier verification signups from 2026-08-18/19 (cc-test-*, cc-test2-*,
-- cc-test3-*, cc-test10-*@sairncash-verification.example) may also still be
-- present; the pattern below catches every address on that domain in one go.

-- Optional: see exactly what is about to be removed before removing it.
-- select id, email, created_at, expires_at
--   from public.sairncash_trial
--  where email like '%@sairncash-verification.example'
--  order by created_at;

delete from public.sairncash_trial
 where email like '%@sairncash-verification.example';

-- ── ONE MORE ROW, AND IT IS OFF-CONVENTION BECAUSE I CREATED IT BY ─────────
-- ── MISTAKE (2026-09-17, CC) ──────────────────────────────────────────────
-- Disclosed with its exact identifiers rather than folded into the pattern
-- above, because the pattern above DOES NOT MATCH IT and a reader who ran only
-- that delete would reasonably believe the table was clean.
--
-- WHAT HAPPENED. Asked to verify whether SAIRNcash's Stripe test mode is live
-- before building against it, I probed the endpoints against PRODUCTION. Three
-- of the four are read-only. `trial-start` IS NOT -- it mints a customer and a
-- 30-day trial -- and I sent it a request shaped to succeed, which it did:
--
--   email       probe@example.test
--   customerId  4026f5a7-3a6a-485a-9acb-da479281d4e3
--   expiresAt   2026-10-17T13:28:28.774Z
--   confirmed real by trial-verify -> {"valid":true,"daysLeft":30}
--
-- THE MISTAKE WAS NOT THE PROBE, IT WAS NOT READING THE VERB FIRST. Checking
-- whether a payment integration is configured needs the guard's answer, which
-- `checkout` and `verify` both give without writing anything. `trial-start`
-- was probed to establish what still worked WITHOUT Stripe, and that question
-- did not require a real signup -- a malformed request already answers it, and
-- the malformed one I sent first (400 "Valid email required") had answered it.
--
-- `probe@example.test` uses the reserved .test TLD (RFC 2606), so it cannot
-- belong to a real person, but it is NOT the `@sairncash-verification.example`
-- domain this file's pattern was built around. The next verification signup
-- should use that domain; this one did not and is named here instead.

delete from public.sairncash_trial
 where email = 'probe@example.test';

-- Scoped to the verification domain on purpose. Do NOT broaden this to
-- "delete expired trials" or similar: an expired trial row is the evidence
-- that a real person signed up and when, which is exactly what a renewal
-- request is checked against -- api/sairncash/trial-renew.js reads these
-- rows to grant a fresh window.
--
-- Verify after running (expect 0):
--   select count(*) from public.sairncash_trial
--    where email like '%@sairncash-verification.example';
--
-- TABLE NAME VERIFIED, not assumed: api/sairncash/trial-start.js line 40
-- posts to /rest/v1/sairncash_trial (singular), and its own 503 names
-- sql/sairncash_trial_schema.sql. An earlier draft of this file said
-- sairncash_trials (plural) and would have failed with "relation does not
-- exist" -- corrected by reading the endpoint rather than guessing.
