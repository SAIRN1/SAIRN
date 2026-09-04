-- sql/cl_rate_limit_consume_fn_2026-09-04.sql
-- Makes the CourtListener rate limiter ATOMIC. Run once in the Supabase SQL
-- editor, AFTER sql/sairnlaw_citator_schema.sql (which creates the table).
--
-- ── THE BUG THIS FIXES ──
-- api/_lib/courtlistener.js:37 checkAndLogRateLimit() counted and then
-- recorded in SEPARATE HTTP CALLS, once per window:
--
--     SELECT id FROM cl_rate_limit_log WHERE requested_at >= now() - 60s
--     SELECT id FROM cl_rate_limit_log WHERE requested_at >= now() - 3600s
--     SELECT id FROM cl_rate_limit_log WHERE requested_at >= now() - 86400s
--     INSERT INTO cl_rate_limit_log DEFAULT VALUES
--
-- Nothing coordinates them. Vercel runs these functions concurrently, so N
-- simultaneous callers all read the SAME counts, all decide they are under
-- every window, and all insert.
--
-- ── WHY THIS IS SHARPER THAN THE AI LIMITER'S VERSION OF THE SAME BUG ──
-- sql/sairn_ai_rate_limit_consume_fn.sql fixed this exact shape for
-- sairn_ai_rate_limit_log. Three things make the CourtListener case worse:
--
--   * THE CEILING IS 4 PER MINUTE, not 200 per day. Three concurrent callers
--     at a count of 3 is already an overshoot. The AI limiter needed 50
--     concurrent requests to demonstrate its race; this one needs two.
--   * THE TOKEN IS SHARED BY EVERY SAIRNlaw FIRM. api/courtlistener.js says so
--     in its header. The overshoot is not scoped to one tenant, and neither is
--     the consequence.
--   * THE PENALTY BELONGS TO A THIRD PARTY. Exceeding an internal counter is
--     an internal problem. Exceeding CourtListener's documented limit risks
--     them throttling or revoking the shared token, which takes the citator
--     down for every firm at once and cannot be undone from this side.
--
-- ── FAILS CLOSED, WHICH IS THE OPPOSITE OF THE AI LIMITER, ON PURPOSE ──
-- sairn_ai_rate_limit_consume's client deliberately ALLOWS the call when the
-- RPC fails: a counting outage must not take down every AI feature on the
-- platform. Copying that decision here would invert the meaning of this
-- limiter. If this function cannot answer, the honest state is "I do not know
-- whether we are within a third party's limit on a credential shared by every
-- firm", and the safe answer to that is to refuse -- which is what the
-- existing JS already does by throwing on a failed count. That behaviour is
-- preserved, not replaced.
--
-- ── ALL THREE WINDOWS INSIDE ONE LOCK ──
-- The three counts and the insert happen in one transaction under one
-- advisory lock, so a caller cannot pass the minute window, lose the lock, and
-- insert after another caller has filled it.
--
-- ── WHY AN ADVISORY LOCK RATHER THAN A ROW LOCK OR A COUNTER ROW ──
-- Same reasoning as the AI limiter's file, and it holds here for the same
-- reasons: there is no single row to lock because the quantity is an aggregate
-- over an append-only log, and SELECT ... FOR UPDATE cannot lock rows that do
-- not exist yet -- which is precisely the gap a concurrent INSERT drives
-- through. A counter row would need an UPDATE grant and could not express a
-- true sliding window without its own reset job.
--
-- THE LOCK KEY IS A SINGLE CONSTANT, not a per-tenant one. That is deliberate
-- and is the difference from the AI limiter, which keys on app_id: there is
-- one CourtListener token, so there is one budget, so there is one lock. A
-- per-firm key would let two firms pass the same window simultaneously and
-- would reintroduce exactly the bug this file exists to close.
--
-- ── SECURITY INVOKER, DELIBERATELY ──
-- Not SECURITY DEFINER. Only service_role can call it (see the GRANT), and
-- service_role already holds the SELECT and INSERT this needs. A DEFINER
-- function would run with the owner's rights for no benefit.
--
-- ── RECORDS EVEN WHEN OVER THE LIMIT? NO -- AND THAT DIFFERS TOO ──
-- The AI limiter inserts unconditionally so observe-mode data reflects real
-- demand rather than being clipped. This one must NOT: a request that is
-- refused never reaches CourtListener, so logging it would consume budget for
-- a call that never happened and would make the limiter progressively
-- over-tighten under load. The row is written ONLY when the call is permitted.

set search_path to public, extensions;

create or replace function public.cl_rate_limit_consume(
  p_minute_max integer,
  p_hour_max   integer,
  p_day_max    integer
)
returns jsonb
language plpgsql
as $$
declare
  v_minute bigint;
  v_hour   bigint;
  v_day    bigint;
begin
  if p_minute_max is null or p_hour_max is null or p_day_max is null then
    return jsonb_build_object('error', 'all three window maxima are required');
  end if;

  -- One budget, one token, one lock. Held to end of transaction; every
  -- PostgREST RPC call is its own transaction, so no caller can hold it after
  -- crashing.
  perform pg_advisory_xact_lock(hashtext('cl_rate_limit:shared'));

  select count(*) into v_minute from public.cl_rate_limit_log
   where requested_at >= now() - make_interval(secs => 60);
  select count(*) into v_hour from public.cl_rate_limit_log
   where requested_at >= now() - make_interval(secs => 3600);
  select count(*) into v_day from public.cl_rate_limit_log
   where requested_at >= now() - make_interval(secs => 86400);

  if v_minute >= p_minute_max then
    return jsonb_build_object('limited', true, 'window', 'minute',
                              'max', p_minute_max, 'prior_count', v_minute);
  end if;
  if v_hour >= p_hour_max then
    return jsonb_build_object('limited', true, 'window', 'hour',
                              'max', p_hour_max, 'prior_count', v_hour);
  end if;
  if v_day >= p_day_max then
    return jsonb_build_object('limited', true, 'window', 'day',
                              'max', p_day_max, 'prior_count', v_day);
  end if;

  -- Only now, and only inside the same lock, is the budget consumed.
  insert into public.cl_rate_limit_log default values;

  return jsonb_build_object('limited', false,
                            'minute', v_minute, 'hour', v_hour, 'day', v_day);
end;
$$;

revoke all on function public.cl_rate_limit_consume(integer, integer, integer)
  from public, anon, authenticated;
grant execute on function public.cl_rate_limit_consume(integer, integer, integer)
  to service_role;

-- ── Verify after running ───────────────────────────────────────────────────
--   select public.cl_rate_limit_consume(1000, 1000, 1000);
--     -> {"limited": false, "minute": N, ...}
--   select public.cl_rate_limit_consume(1000, 1000, 1000);
--     -> minute is N+1, proving the insert happened inside the same call
--   select public.cl_rate_limit_consume(0, 1000, 1000);
--     -> {"limited": true, "window": "minute", ...} and NO row written --
--        re-run the first form and confirm the count did not move.
--
-- Concurrency check, if you want to see the fix work rather than trust it.
-- Twenty parallel callers against a limit of 5: exactly 5 must come back
-- limited:false, and their `minute` values must be 0,1,2,3,4 with no repeats.
--   select x, public.cl_rate_limit_consume(5, 1000, 1000)
--     from generate_series(1,20) x;
-- A repeated `minute` value would mean the lock is not holding.
--
-- No DELETE is granted on this table platform-wide (deliberate). Verification
-- rows age out of every window on their own -- the day window is 24 hours, so
-- a burst of test rows suppresses real traffic for that long. Use small maxima
-- for the limited: true cases, which write nothing.
