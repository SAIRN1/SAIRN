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
begin
  if p_app_id is null or p_app_id = '' then
    return jsonb_build_object('error', 'app_id required');
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
