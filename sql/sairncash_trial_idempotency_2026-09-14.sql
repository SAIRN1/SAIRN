-- sql/sairncash_trial_idempotency_2026-09-14.sql
-- ---------------------------------------------------------------------------
-- MAKES trial-start IDEMPOTENT AGAINST A LOST RESPONSE, without turning it
-- into a way to steal somebody else's trial.
--
-- ── THE DEFECT ─────────────────────────────────────────────────────────────
-- `sairncash_trial.email` is UNIQUE, so the ROW cannot duplicate: a retry gets
-- 409 and api/sairncash/trial-start.js answers ALREADY_EXISTS. The row is safe.
--
-- THE REQUEST IS NOT. `trial_token` is minted per request and returned ONLY on
-- the 200 path. If the insert commits and the response is lost -- a client
-- timeout, a dropped connection, a phone changing network -- the caller retries,
-- gets ALREADY_EXISTS, and NEVER RECEIVES THE TOKEN THAT WAS MINTED. The trial
-- exists on the server and is unreachable by the person it belongs to. The
-- handler's own message already anticipates the support ticket: "Contact
-- support if you need help accessing it."
--
-- ── WHY NOT "JUST RETURN THE EXISTING TOKEN ON 409" ────────────────────────
-- That is the fix api/sairndental/public-complaint-submit.js uses and it is
-- WRONG HERE, which is worth stating because the two look alike.
--
-- trial-start is PUBLIC and unauthenticated: `Access-Control-Allow-Origin: *`,
-- no bearer, no session, and the only input is an email address. Returning the
-- existing trial_token to anybody who posts that email would let a stranger who
-- knows an email take over its trial. That is a credential disclosure, and it
-- would be strictly worse than the 409 it replaced.
--
-- The complaint handler can do it because its key is a hash of the patient
-- name AND the message body -- content only the original submitter had. An
-- email address is not that.
--
-- ── SO THE RETRY HAS TO PROVE IT IS THE SAME REQUEST ───────────────────────
-- The client generates a high-entropy idempotency key, sends it with the first
-- attempt and with every retry of that attempt. Only a request carrying the
-- MATCHING key gets the token back. Somebody who knows the email and not the
-- key gets exactly what they get today.
--
-- STORED AS A SHA-256, never in the clear, for the same reason
-- sairnvet_witness_tokens stores token_hash: this column is a credential in its
-- own right -- anyone holding it can retrieve the trial token -- and a database
-- copy or a support query should not hand it over.
--
-- ── NOT UNIQUE, AND THAT IS DELIBERATE ─────────────────────────────────────
-- `email` already carries the uniqueness that stops a second trial. A unique
-- constraint on the key would add nothing and would refuse a legitimate second
-- trial for a different email that happened to reuse a key. An INDEX, because
-- it is looked up; not a constraint, because it constrains nothing.
-- ---------------------------------------------------------------------------

alter table public.sairncash_trial
  add column if not exists idempotency_key_hash text;

comment on column public.sairncash_trial.idempotency_key_hash is
  'sha256 of the client-supplied idempotency key for the request that created '
  'this trial. Lets a retry after a lost response receive the SAME trial_token '
  'instead of ALREADY_EXISTS. Hashed because holding it retrieves the token. '
  'Null for rows created before 2026-09-14 -- those retries still get 409, '
  'which is the old behaviour and not a regression.';

create index if not exists idx_sairncash_trial_idem
  on public.sairncash_trial (idempotency_key_hash)
  where idempotency_key_hash is not null;

-- The grant is unchanged: service_role already holds select and insert on this
-- table and this adds no verb. Stated rather than assumed, because a new column
-- is exactly where a silent privilege gap would sit.

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. The column exists and is nullable. Expect: idempotency_key_hash | text | YES
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sairncash_trial'
   and column_name = 'idempotency_key_hash';

-- 2. The index exists and is PARTIAL. Expect one row whose indexdef contains
--    `WHERE (idempotency_key_hash IS NOT NULL)` -- a full index over a column
--    that is null for every pre-existing row is wasted, and the partial
--    predicate is the thing worth confirming took.
select indexname, indexdef
  from pg_indexes
 where schemaname = 'public' and tablename = 'sairncash_trial'
   and indexname = 'idx_sairncash_trial_idem';

-- 3. No row leaks a key in the clear. Expect: 0
--    A value that is not 64 hex characters is not a sha256 digest, which would
--    mean something wrote the raw key. This is cheap and it is the one mistake
--    that turns the column from a guard into a disclosure.
select count(*) from public.sairncash_trial
 where idempotency_key_hash is not null
   and idempotency_key_hash !~ '^[0-9a-f]{64}$';

-- 4. Existing rows are untouched. Expect: every pre-2026-09-14 row null.
select count(*) filter (where idempotency_key_hash is null)  as legacy_rows,
       count(*)                                              as total_rows
  from public.sairncash_trial;
