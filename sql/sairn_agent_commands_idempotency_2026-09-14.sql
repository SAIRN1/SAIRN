-- sql/sairn_agent_commands_idempotency_2026-09-14.sql
-- ---------------------------------------------------------------------------
-- STOPS A RETRIED enqueue FROM MAKING AN AGENT DO THE SAME THING TWICE.
--
-- ── THE DEFECT ─────────────────────────────────────────────────────────────
-- api/agent/enqueue.js inserts into sairn_agent_commands with no key, no unique
-- constraint and no read-before-write. If the insert commits and the response
-- is lost -- a client timeout, a dropped connection -- the caller retries and a
-- SECOND command row is queued. api/agent/poll.js hands it to the agent and the
-- agent executes it again.
--
-- WHAT IS DUPLICATED IS AN ARBITRARY OPERATION, not a log line. That is what
-- separates this from the other unguarded writes triaged on 2026-09-14: the
-- effect is whatever the agent does, and the queue cannot tell a deliberate
-- second request from a retry of the first.
--
-- ── WHY A PARTIAL UNIQUE INDEX AND NOT A CONSTRAINT ────────────────────────
-- Every row written before today has no key. A plain unique constraint over
-- (agent_id, idempotency_key) would treat those NULLs as distinct in Postgres
-- and so would work -- but a PARTIAL index states the intent outright: the
-- uniqueness applies to keyed rows only, and rows without a key are
-- deliberately outside it. A reader should not have to know Postgres's NULL
-- rule to know that legacy rows are not constrained.
--
-- ── SCOPED TO THE AGENT, NOT GLOBAL ────────────────────────────────────────
-- (agent_id, idempotency_key). Two different customers' apps generating the
-- same key must not collide, and a key is only ever meaningful within the
-- agent it was addressed to.
--
-- ── NOT HASHED, AND THAT IS A DIFFERENT CALL FROM trial-start ──────────────
-- sairncash_trial stores a HASH of its key, because holding that key retrieves
-- a trial token -- the key is a credential. This key retrieves nothing: the
-- worst a holder can do is collide with a command they already knew about, and
-- enqueue already authorises on agent_id alone (see that file's own security
-- note). Hashing here would add a step and protect nothing, and pretending
-- otherwise would be cargo-culting the shape without the reason.
-- ---------------------------------------------------------------------------

alter table public.sairn_agent_commands
  add column if not exists idempotency_key text;

comment on column public.sairn_agent_commands.idempotency_key is
  'Caller-supplied key for the enqueue request that created this command. A '
  'retry carrying the same key returns the ORIGINAL command_id instead of '
  'queueing a second command the agent would execute again. Null for rows '
  'created before 2026-09-14 and for callers that send no key -- those retain '
  'the old duplicate-on-retry behaviour, which is not a regression.';

create unique index if not exists uq_sairn_agent_commands_idem
  on public.sairn_agent_commands (agent_id, idempotency_key)
  where idempotency_key is not null;

-- No new verb. service_role already holds select and insert here; stated
-- rather than assumed, because a new column is exactly where a silent
-- privilege gap would sit.

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. The column exists and is nullable. Expect: idempotency_key | text | YES
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sairn_agent_commands'
   and column_name = 'idempotency_key';

-- 2. The index exists, is UNIQUE and is PARTIAL. Expect one row whose indexdef
--    contains both `UNIQUE` and `WHERE (idempotency_key IS NOT NULL)`.
--    A non-partial index here would still work by Postgres's NULL rule and
--    would say something different to a reader, so the predicate is the half
--    worth confirming took.
select indexname, indexdef
  from pg_indexes
 where schemaname = 'public' and tablename = 'sairn_agent_commands'
   and indexname = 'uq_sairn_agent_commands_idem';

-- 3. THE CONSTRAINT ACTUALLY REFUSES. This is the only query that proves the
--    index does its job rather than merely existing.
--    Expect: the second insert ERRORS with a unique-violation (23505).
-- begin;
--   insert into public.sairn_agent_commands (agent_id, operation, idempotency_key)
--     select id, 'probe', 'probe-key-2026-09-14' from public.sairn_agents limit 1;
--   insert into public.sairn_agent_commands (agent_id, operation, idempotency_key)
--     select id, 'probe', 'probe-key-2026-09-14' from public.sairn_agents limit 1;
--     -- EXPECTED HERE: ERROR 23505 duplicate key value violates unique
--     -- constraint "uq_sairn_agent_commands_idem". If BOTH inserts succeed,
--     -- the index is not doing anything and enqueue is still duplicating.
-- rollback;   -- nothing above is kept

-- 4. AND THE PAIRED POSITIVE: two keyless rows must still both land, or this
--    migration has broken every existing caller.
--    Expect: both inserts succeed.
-- begin;
--   insert into public.sairn_agent_commands (agent_id, operation)
--     select id, 'probe' from public.sairn_agents limit 1;
--   insert into public.sairn_agent_commands (agent_id, operation)
--     select id, 'probe' from public.sairn_agents limit 1;
-- rollback;

-- 5. Existing rows are untouched. Expect legacy_rows = total_rows today.
select count(*) filter (where idempotency_key is null) as legacy_rows,
       count(*)                                        as total_rows
  from public.sairn_agent_commands;
