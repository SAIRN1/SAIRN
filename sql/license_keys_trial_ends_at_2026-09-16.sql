-- sql/license_keys_trial_ends_at_2026-09-16.sql
--
-- Adds ONE nullable column to an existing public.license_keys. Nothing here
-- drops anything, nothing here writes a row, and every statement is guarded
-- with `if not exists`, so it is safe to re-run.
--
-- ── WHAT THIS CLOSES ──────────────────────────────────────────────────────
-- The trial-expiry gate has never refused anyone, on any licence, and the
-- reason was never a bug in the comparison. `trial_ends_at` IS NOT A COLUMN.
-- Three handlers carry an identical inline copy of the check --
-- api/sd-data.js, api/sd-render.js and api/_lib/sd-store.js -- and each reads
-- a field that does not exist, gets undefined, and falls through to allowed.
--
-- MEASURED, not recalled. db/schema_snapshot.json, capture 2026-09-13
-- 18:39:55+00, lists license_keys as exactly eleven columns:
--
--   id, key, app_id, shop_name, customer_email, stripe_customer_id,
--   stripe_subscription_id, plan, status, created_at, updated_at
--
-- The comment at the sd-data.js call site is what let it survive: "A
-- null/absent trial_ends_at (e.g. before the migration, or intentionally
-- unset) is treated as 'not expired' and allowed through." That reads as an
-- edge case being handled. It was not an edge case -- it was the only case.
--
-- ── THIS IS NOT THE SAIRNCASH TRIAL, AND THE DISTINCTION MATTERS ──────────
-- SAIRNcash is a consumer app with NO licence key. Its trial lives in
-- public.sairncash_trial, which already carries `expires_at`, and
-- api/sairncash/ai.js already compares it -- with its own comment saying "An
-- expired trial is not an active one. Compared here rather than trusted."
-- THAT GATE WORKS. This file touches the shared B2B licence table and changes
-- nothing about SAIRNcash.
--
-- ── NO BACKFILL, AND THAT IS THE DECISION RATHER THAN AN OMISSION ─────────
-- A backfill is the ONLY way this migration could refuse a real customer, and
-- there is nobody to expire: Stripe is not configured under the new LLC and no
-- licence is on a paid plan. So every row keeps a NULL trial_ends_at, which
-- reads as not-expired -- byte-for-byte the behaviour of today.
--
-- WHAT CHANGES IS CAPABILITY, NOT BEHAVIOUR. After this runs the gate is able
-- to fire; it still does not, because no row carries a date. THE FIRST ROW
-- THAT GETS ONE IS THE FIRST ROW THAT CAN BE REFUSED, and that is the moment
-- to be careful, not this one.
--
-- ── WHO BECOMES REFUSABLE, EXACTLY ────────────────────────────────────────
-- The gate refuses only a licence that is KNOWN NOT PAID and past its date.
-- license_keys has no `subscription_status` column either, so today:
--
--   * a licence WITH a stripe_subscription_id is a CANNOT-TELL and is never
--     refused, whatever its trial date -- that arm is what protects a real
--     subscriber, and api/license-trial-gate.test.js pins it;
--   * a licence with NO stripe_subscription_id is KNOWN NOT PAID, so a past
--     trial_ends_at on one of those WILL 402.
--
-- Before writing any trial_ends_at, list exactly who that is:
--
--   select key, app_id, customer_email, status, created_at
--     from public.license_keys
--    where stripe_subscription_id is null
--    order by created_at;
--
-- ── DELIBERATELY NOT BUNDLED: subscription_status ─────────────────────────
-- The same gate also reads `subscription_status`, which is likewise absent.
-- It is NOT added here, for a reason rather than an oversight: NOTHING IN
-- api/ WRITES IT (tools/entitlement_freshness_check.py). Adding it would
-- create a column that is NULL for ever, leave every subscribed licence a
-- cannot-tell exactly as it is now, change no outcome, and trip its own
-- tripwire in api/license-trial-gate.test.js for no gain. It needs a writer
-- first, and that is a Stripe-webhook decision, not a column.
--
-- ── AFTER RUNNING THIS ────────────────────────────────────────────────────
--   1. Re-capture the snapshot: run sql/schema_snapshot_query.sql, then
--      `python tools/load_schema_snapshot.py <pasted.json> --write`.
--   2. api/license-trial-gate.test.js's trial_ends_at tripwire WILL GO RED.
--      That is the arm working: it fires when the column becomes live, not
--      when this file is written, because it reads the snapshot rather than
--      this directory. Read its message before changing it -- it names the
--      three handlers that begin refusing.
--   3. Nothing else needs to change for the gate to be correct-but-inert.

alter table public.license_keys
  add column if not exists trial_ends_at timestamptz;

comment on column public.license_keys.trial_ends_at is
  'End of a non-Stripe trial. NULL means no trial is being enforced and the '
  'licence is never refused on this basis -- that is the state every row is in '
  'as of 2026-09-16. A date in the past refuses only a licence that is KNOWN '
  'NOT PAID (no stripe_subscription_id); one WITH a subscription id is a '
  'cannot-tell and is allowed through. See api/license-trial-gate.test.js.';

-- Verification, to be read rather than assumed. Expect one row, and
-- rows_with_a_date = 0 immediately after this migration.
select count(*)                                   as licences,
       count(trial_ends_at)                       as rows_with_a_date,
       count(*) filter (where stripe_subscription_id is null)
                                                  as refusable_if_a_date_is_set
  from public.license_keys;
