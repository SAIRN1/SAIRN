-- sql/sairncash_trial_renew_idempotency_2026-09-14.sql
-- ---------------------------------------------------------------------------
-- STOPS ONE ADMIN APPROVAL FROM EXTENDING A TRIAL TWICE.
--
-- ── THE DEFECT, AND IT IS A READ-MODIFY-WRITE ──────────────────────────────
-- api/sairncash/trial-renew.js SELECTs renewal_count, computes `(count || 0)+1`
-- in JavaScript, and PATCHes that value back together with a fresh expires_at
-- computed from NOW. Two separate round trips with nothing between them.
--
-- TWO FAILURES, AND THEY ARE NOT THE SAME ONE:
--
--   1. LOST UPDATE. Two renewals in flight both read N and both write N+1, so
--      one approval vanishes from the count. The count is the only record of
--      how many times a trial has been extended.
--   2. DOUBLE EXTENSION ON RETRY, which is worse. If the PATCH commits and the
--      response is lost -- a browser timeout, a dropped connection -- the admin
--      retries, the retry reads N+1, and it writes N+2 AND A NEW expires_at 30
--      DAYS FROM THE RETRY. The trial is extended twice from ONE approval, on
--      the only write path that can extend expires_at at all.
--
-- ── ONE FIX DOES NOT COVER BOTH, WHICH IS WHY THERE ARE TWO ────────────────
-- A COMPARE-AND-SET (`&renewal_count=eq.<N>` in the PATCH filter) closes the
-- lost update: the loser of a race matches zero rows and finds out. It does
-- NOT close the retry, because a sequential retry reads the already-incremented
-- value and its CAS succeeds honestly.
--
-- An IDEMPOTENCY KEY closes the retry: the second call recognises itself and
-- returns the ORIGINAL expiry instead of computing a new one. It does not close
-- the concurrent case, because two genuinely different approvals carry
-- different keys and both are legitimate.
--
-- The CAS needs no migration. This file is the key.
--
-- ── NOT HASHED, UNLIKE sairncash_trial.idempotency_key_hash ────────────────
-- That one is on a PUBLIC endpoint where holding the key retrieves a trial
-- token, so it is a credential. This endpoint is behind
-- `Authorization: Bearer SAIRNCASH_ADMIN_SECRET` and the key retrieves only
-- the expiry of a renewal the caller just performed. Copying the hash because
-- the neighbouring column has one would be cargo-culting the shape without the
-- reason -- and it would make the retry lookup impossible to debug from the
-- SQL editor for no gain.
--
-- ── NOT UNIQUE ─────────────────────────────────────────────────────────────
-- One row per email, so the key identifies the LAST renewal of that trial, not
-- a row of its own. A unique constraint would be asserting something this
-- column does not mean.
-- ---------------------------------------------------------------------------

alter table public.sairncash_trial
  add column if not exists renew_idempotency_key text;

comment on column public.sairncash_trial.renew_idempotency_key is
  'Caller-supplied key for the renewal that produced the current expires_at. A '
  'retry carrying the same key gets that SAME expiry back instead of extending '
  'the trial a second time from one approval. Null for rows renewed before '
  '2026-09-14 and for callers that send no key -- those keep the old '
  'double-extend-on-retry behaviour, which is not a regression.';

create index if not exists idx_sairncash_trial_renew_idem
  on public.sairncash_trial (renew_idempotency_key)
  where renew_idempotency_key is not null;

-- No new verb. service_role already holds select and update here; stated
-- rather than assumed, because a new column is where a silent privilege gap
-- would sit.

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. The column exists and is nullable. Expect: renew_idempotency_key|text|YES
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sairncash_trial'
   and column_name = 'renew_idempotency_key';

-- 2. The index exists and is PARTIAL. Expect an indexdef containing
--    `WHERE (renew_idempotency_key IS NOT NULL)`.
select indexname, indexdef
  from pg_indexes
 where schemaname = 'public' and tablename = 'sairncash_trial'
   and indexname = 'idx_sairncash_trial_renew_idem';

-- 3. THE COMPARE-AND-SET REALLY REFUSES A STALE WRITER. This is the only query
--    that proves the lost-update half, and it needs no application code.
--    Expect: the first UPDATE reports 1 row, the second reports 0.
-- begin;
--   insert into public.sairncash_trial (email, trial_token, started_at, expires_at, renewal_count)
--     values ('cas-probe@example.invalid', 'probe-token-2026-09-14',
--             now(), now() + interval '30 days', 0);
--   -- Two writers that both read renewal_count = 0:
--   update public.sairncash_trial set renewal_count = 1
--    where email = 'cas-probe@example.invalid' and renewal_count = 0;   -- 1 row
--   update public.sairncash_trial set renewal_count = 1
--    where email = 'cas-probe@example.invalid' and renewal_count = 0;   -- 0 rows
--   -- ZERO ROWS on the second is the whole mechanism. If it reports 1, the
--   -- filter is not being sent and the lost update is still live.
-- rollback;   -- nothing above is kept

-- 4. Existing rows are untouched. Expect legacy_rows = total_rows today.
select count(*) filter (where renew_idempotency_key is null) as legacy_rows,
       count(*)                                              as total_rows
  from public.sairncash_trial;
