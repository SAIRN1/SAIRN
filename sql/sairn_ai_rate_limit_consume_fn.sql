-- sql/sairn_ai_rate_limit_consume_fn.sql
-- Makes the AI rate limiter ATOMIC. Run once in the Supabase SQL editor,
-- AFTER sql/sairn_ai_rate_limit_schema.sql.
--
-- ── THE BUG THIS FIXES ──
-- api/_lib/ai-rate-limit.js counted and then recorded in TWO SEPARATE HTTP
-- CALLS:
--
--     SELECT count(*) ... WHERE app_id = $1 AND requested_at >= now() - 24h
--     INSERT INTO sairn_ai_rate_limit_log (app_id) VALUES ($1)
--
-- Nothing coordinates them. Vercel runs these functions concurrently across
-- however many instances traffic demands, so N simultaneous requests all read
-- the SAME count, all decide they are under the limit, and all insert. At a
-- limit of 200 with 50 concurrent requests arriving at count 199, every one of
-- the 50 is permitted -- 249 calls against a 200 cap. The limit was therefore
-- approximate, never enforced, and would have stayed approximate the moment
-- SAIRN_AI_RATE_LIMIT_MODE=enforce was switched on. Worse in enforce mode than
-- in observe mode, because it would look like a real cap.
--
-- ── WHY AN ADVISORY LOCK RATHER THAN A ROW LOCK OR A COUNTER ROW ──
-- There is no single row to lock: this is an append-only log, and the quantity
-- being protected is an aggregate over many rows. SELECT ... FOR UPDATE cannot
-- lock rows that do not exist yet, which is exactly the gap a concurrent
-- INSERT drives through.
--
-- A single counter row with UPDATE ... RETURNING would also be atomic, and was
-- rejected for two reasons. It needs an UPDATE grant on a table that today has
-- only SELECT and INSERT -- and this platform has just been through a
-- deliberate grant-narrowing sweep (see sql/unused_delete_grant_revoke_
-- 2026-08-24.sql), so widening a table grant is the more expensive privilege.
-- GRANT EXECUTE on one function is narrower. And a counter row cannot express
-- a true sliding window without its own reset job; the log table already can.
--
-- pg_advisory_xact_lock is keyed on the app_id, so two different apps never
-- block each other, and the lock is released automatically when the
-- transaction ends. Each PostgREST RPC call is its own transaction, so there
-- is no path where a crashed caller holds it.
--
-- ── SECURITY INVOKER, DELIBERATELY ──
-- Not SECURITY DEFINER. Only service_role can call this (see the GRANT below),
-- and service_role already holds exactly the SELECT and INSERT this needs. A
-- DEFINER function would run with the owner's rights for no benefit and would
-- be a privilege-escalation surface if the EXECUTE grant were ever widened.
--
-- ── STILL FAILS OPEN ──
-- The client treats an RPC failure exactly as it treats a count failure today:
-- allow the call and log loudly. A counting outage must never take down every
-- AI feature on the platform. That decision is unchanged by this file.
--
-- ══ SUPERSEDED 2026-09-15. DO NOT RE-RUN AFTER THE TENANT MIGRATION. ═══════
-- THIS FILE DEFINES THE THREE-ARGUMENT FORM, AND THAT SIGNATURE WAS
-- DELIBERATELY DROPPED. sql/sairn_ai_tenant_subbudget_2026-09-15.sql:91 does
-- `drop function if exists public.sairn_ai_rate_limit_consume(text, integer,
-- integer)` before creating a SIX-argument form whose last three parameters
-- have DEFAULTS -- and its own comment says why it drops rather than
-- overloads: with both present, a three-argument call matches BOTH and
-- Postgres refuses the whole call with "function is not unique". That is a
-- HARD OUTAGE on every AI call on the platform, not a degradation.
--
-- SO RE-RUNNING THIS FILE IS THE OUTAGE. It is not "reverting a guard" -- this
-- file's definition IS guarded, which is exactly why the hazard is easy to
-- miss and why tools/advisory_lock_isolation_check.py now keys its SUPERSEDED
-- class on an explicit `drop function` rather than on a missing guard. The
-- first version of that checker looked for an unguarded duplicate and walked
-- straight past this file.
--
-- The block below ABORTS the script rather than leaving that as a sentence. A
-- comment saying "do not run this" is the same class of control as the prose
-- that documented the REPEATABLE READ hazard in sairnlaw_trusttx_functions.sql
-- and protected nothing. On a database where the six-argument form is NOT
-- installed this raises nothing, because a fresh database legitimately needs
-- one of the two files to run.
do $$
begin
  if exists (
    select 1 from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname = 'sairn_ai_rate_limit_consume'
       and p.pronargs = 6
  ) then
    raise exception
      'REFUSING: the CURRENT 6-argument sairn_ai_rate_limit_consume is already '
      'installed, and sql/sairn_ai_tenant_subbudget_2026-09-15.sql dropped the '
      '3-argument form on purpose. Creating it again would make every 3-arg '
      'call ambiguous ("function is not unique") and take every AI call down. '
      'Run sql/sairn_ai_tenant_subbudget_2026-09-15.sql instead.'
      using errcode = 'invalid_table_definition';
  end if;
end;
$$;

create or replace function public.sairn_ai_rate_limit_consume(
  p_app_id         text,
  p_limit          integer,
  p_window_seconds integer
)
returns jsonb
language plpgsql
as $$
declare
  v_count bigint;
  v_iso   text;
begin
  if p_app_id is null or p_app_id = '' then
    return jsonb_build_object('error', 'app_id required');
  end if;

  -- ── THE PRECONDITION THIS FUNCTION'S CORRECTNESS RESTS ON ────────────────
  -- Added 2026-09-14 after the formal model was extended to stop ASSUMING it.
  --
  -- pg_advisory_xact_lock serialises ACQUISITION. It does not move the
  -- transaction's SNAPSHOT. Under read committed the `select count(*)` below
  -- takes a fresh snapshot, so it sees every row committed by the caller that
  -- just released the lock, and count-then-insert is genuinely atomic.
  --
  -- Under REPEATABLE READ or SERIALIZABLE the snapshot is taken once, at the
  -- transaction's first data statement, and a caller that WAITED on the lock
  -- still counts against a snapshot from before the holder committed. It then
  -- inserts. The cap over-runs with the lock working perfectly the whole time
  -- -- `node tools/rate_limit_race_model.js` enumerates it and prints the
  -- schedule: S0, L0(rows=1), S1, S2, L1(counts 1), L2(counts 1, rows=3).
  --
  -- Nothing on this deployment sets a non-default isolation level today. That
  -- is exactly why this guard exists: `alter role service_role set
  -- default_transaction_isolation = 'repeatable read'` is one statement, would
  -- be made for an unrelated reason, and would silently turn this function back
  -- into the bug it was written to fix. There would be no error and no symptom
  -- until the cap over-ran.
  --
  -- RAISES rather than returning an error object, deliberately. The client
  -- treats an RPC failure as fail-open (allow and log loudly), which is the
  -- right behaviour for a counting outage -- but an error OBJECT would be read
  -- as a real answer and the caller would believe a count it must not believe.
  -- "Could not run" is a third state and is never folded into an answer.
  v_iso := current_setting('transaction_isolation');
  if v_iso <> 'read committed' then
    raise exception
      'sairn_ai_rate_limit_consume requires READ COMMITTED; this transaction '
      'is %. The advisory lock serialises acquisition but does not move the '
      'snapshot, so under % the count is read from before the previous caller '
      'committed and the cap over-runs while the lock appears to work. '
      'Refusing rather than returning a count that cannot be trusted.',
      v_iso, v_iso
      using errcode = 'invalid_transaction_state';
  end if;

  -- Serialise concurrent callers for THIS app only. Held to end of
  -- transaction; every RPC call is its own transaction.
  perform pg_advisory_xact_lock(hashtext('sairn_ai_rl:' || p_app_id));

  select count(*)
    into v_count
    from public.sairn_ai_rate_limit_log
   where app_id = p_app_id
     and requested_at >= now() - make_interval(secs => p_window_seconds);

  -- Recorded even when over the limit, so observe-mode data reflects real
  -- demand rather than being clipped at the threshold. Same reasoning the
  -- JS had, preserved.
  insert into public.sairn_ai_rate_limit_log (app_id) values (p_app_id);

  return jsonb_build_object(
    'prior_count', v_count,
    'limited',     v_count >= p_limit,
    'limit',       p_limit
  );
end;
$$;

revoke all on function public.sairn_ai_rate_limit_consume(text, integer, integer) from public, anon, authenticated;
grant execute on function public.sairn_ai_rate_limit_consume(text, integer, integer) to service_role;

-- Verify after running:
--   select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400);
--     -> {"limit": 1000000, "limited": false, "prior_count": 0}
--   select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400);
--     -> prior_count 1, proving the insert happened inside the same call
--   delete is NOT granted on this table platform-wide (deliberate, see the
--   schema file) -- the two __verify__ rows are harmless and age out of every
--   24-hour window on their own.
--
-- Concurrency check, if you want to see the fix work rather than trust it.
-- In one psql session, with a limit of 5 and 20 parallel callers, the highest
-- prior_count returned must be exactly 19 with no value repeated:
--   select x, (public.sairn_ai_rate_limit_consume('__concurrency__', 5, 86400)->>'prior_count')::int
--     from generate_series(1,20) x;
-- Repeated prior_count values would mean the lock is not holding.
--
-- ── AND VERIFY THE ISOLATION GUARD ITSELF, because a guard nobody has seen
--    refuse is indistinguishable from one that cannot ──────────────────────
--   begin;
--     set transaction isolation level repeatable read;
--     select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400);
--     -- EXPECTED: ERROR 25000 "requires READ COMMITTED; this transaction is
--     --           repeatable read". If it returns a jsonb row instead, the
--     --           guard is not firing and the model's precondition is not
--     --           being enforced -- report that, do not work around it.
--   rollback;
--
-- The paired positive is the first __verify__ call above, which must still
-- succeed under the default isolation level. One arm proving refusal and one
-- proving it still permits: either alone is half a control.
