-- sql/license_seed_onconflict_verify_2026-08-28.sql
-- Closes Guardian v2 Check 29 for commit 4fd0297 (the 13 license seeds
-- converted from WHERE NOT EXISTS to ON CONFLICT (key) DO NOTHING).
--
-- WHY THIS FILE EXISTS: Check 29 says any change touching a schema
-- constraint or the shape of what gets persisted must be proven with a REAL
-- write against the REAL store -- not reasoned about, not unit-tested. The
-- session that wrote 4fd0297 has no DB access, so that commit shipped with
-- Check 29 explicitly unsatisfied and said so in its own message. This is
-- the file that closes it.
--
-- SAFE TO RUN. It touches ONE throwaway row (VERIFY-ONCONFLICT-2026-08-28)
-- and deletes it again in Step 5. It does not read, modify or delete any
-- real license. Nothing here depends on the 13 seeds having been run.
--
-- HOW TO RUN: paste into the Supabase SQL editor and run the steps ONE AT A
-- TIME, top to bottom. Send back the output of every numbered step.
--
-- RUN THE STEPS SEPARATELY, NOT AS ONE PASTE. A multi-statement paste in the
-- Supabase SQL editor can apply only partway and still report success -- that
-- has already happened twice on this platform (the SAIRNroofing cleanup,
-- 2026-08-26). A partial apply here would silently skip the idempotency test,
-- which is the only step that actually proves the DO NOTHING choice.

-- ─────────────────────────────────────────────────────────────────────────
-- STEP 1 -- Does the constraint this whole change rests on actually exist,
-- under the name claimed? Read-only.
-- ─────────────────────────────────────────────────────────────────────────
select conname, contype, pg_get_constraintdef(oid) as definition
from pg_constraint
where conrelid = 'public.license_keys'::regclass
  and contype in ('u','p')
order by conname;

-- EXPECT: a row `license_keys_key_key | u | UNIQUE (key)`.
-- If that row is ABSENT, STOP -- every statement in commit 4fd0297 will fail
-- with 42P10 and the commit must be reverted, not patched.
-- A PRIMARY KEY on `key` instead of a UNIQUE would also satisfy ON CONFLICT
-- (key); anything else does not.


-- ─────────────────────────────────────────────────────────────────────────
-- STEP 2 -- First insert of a throwaway key, using the EXACT statement shape
-- all 13 seed files now use. This is the real write Check 29 requires.
-- ─────────────────────────────────────────────────────────────────────────
insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('VERIFY-ONCONFLICT-2026-08-28', 'active', 'first@verify.example', 'stonedesk', 'demo', null)
on conflict (key) do nothing;

-- EXPECT: `INSERT 0 1` (one row inserted), no error.
-- A 42P10 here means Step 1 lied or was skipped.


-- ─────────────────────────────────────────────────────────────────────────
-- STEP 3 -- THE STEP THAT MATTERS. Same key, DIFFERENT customer_email and
-- status. This is what separates DO NOTHING from DO UPDATE, and it is the
-- reason DO NOTHING was chosen: a re-run must never overwrite or reactivate
-- a row that a human deliberately changed.
-- ─────────────────────────────────────────────────────────────────────────
insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('VERIFY-ONCONFLICT-2026-08-28', 'cancelled', 'SECOND-SHOULD-NOT-WIN@verify.example', 'sairnvet', 'enterprise', 'sub_should_not_appear')
on conflict (key) do nothing;

-- EXPECT: `INSERT 0 0` (zero rows inserted), no error.
-- `INSERT 0 1` would mean a duplicate was created -> the constraint is not on
-- `key` and Step 1 was misread.


-- ─────────────────────────────────────────────────────────────────────────
-- STEP 4 -- Read it back. Confirm exactly one row survived and that it still
-- holds STEP 2's values, not STEP 3's.
-- ─────────────────────────────────────────────────────────────────────────
select count(*) as row_count,
       max(customer_email) as customer_email,
       max(status)         as status,
       max(app_id)         as app_id,
       max(plan)           as plan
from public.license_keys
where key = 'VERIFY-ONCONFLICT-2026-08-28';

-- EXPECT EXACTLY:
--   row_count      = 1
--   customer_email = first@verify.example      (NOT the SECOND- one)
--   status         = active                    (NOT cancelled)
--   app_id         = stonedesk                 (NOT sairnvet)
--   plan           = demo                      (NOT enterprise)
--
-- Any Step 3 value appearing here means the seeds are behaving as DO UPDATE,
-- which is the exact failure mode DO NOTHING was chosen to prevent -- a
-- re-run would silently reactivate a suspended license. Report it and stop.


-- ─────────────────────────────────────────────────────────────────────────
-- STEP 5 -- Cleanup. Scoped to the single throwaway key by exact match.
-- ─────────────────────────────────────────────────────────────────────────
delete from public.license_keys
where key = 'VERIFY-ONCONFLICT-2026-08-28';

-- EXPECT: `DELETE 1`.

select count(*) as should_be_zero
from public.license_keys
where key = 'VERIFY-ONCONFLICT-2026-08-28';

-- EXPECT: 0. A non-zero here means cleanup did not apply -- say so rather
-- than re-running the delete blind.


-- ─────────────────────────────────────────────────────────────────────────
-- STEP 6 -- OPTIONAL, and a DIFFERENT question. Steps 1-5 prove the SQL is
-- correct. They do NOT prove any of the 13 real seeds has ever been run, or
-- that the live app can see the rows -- a select as owner reads fine even
-- when the app 502s for every real user (the sairncash_waitlist case,
-- 2026-08-25). Only the deployed endpoint proves that.
--
-- Run these from a shell with network access. 15 keys across 13 files:
-- ─────────────────────────────────────────────────────────────────────────
--
--   for K in SB-PINNACLE-2026 GRD-DEMO-2026 SCP-DEMO-2026 SB-TEST-2026 \
--            ALF-TEST-2026 DNT-PINNACLE-2026 SDN-PINNACLE-2026 \
--            LAW-PINNACLE-2026 LAW-TEST-2026 LEG-PINNACLE-2026 \
--            MECH-PINNACLE-2026 SEN-PINNACLE-2026 SV-PINNACLE-2026 \
--            SD-AUDIT-2026 SD-PARTNER-2026; do
--     printf '%-22s ' "$K"
--     curl -s -o /dev/null -w '%{http_code}\n' \
--       -X POST https://sairn.vercel.app/api/sd-data \
--       -H 'Content-Type: application/json' \
--       -H "Authorization: Bearer $K" \
--       -d '{"action":"read","resource":"profile"}'
--   done
--
--   200 -> row present and active
--   401 -> INVALID_LICENSE, that seed has never been run
--   403 -> LICENSE_INACTIVE, row exists but status is not 'active'
--
-- A 401 is NOT a failure of this change -- it means that app's seed file has
-- not been run yet, which was equally true before 4fd0297. Report the codes
-- as-is; do not re-run seeds to make them green without saying which ones
-- were missing first.
