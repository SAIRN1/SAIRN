-- sql/sairnlaw_rate_limit_consume_fn_2026-09-14.sql
-- ---------------------------------------------------------------------------
-- THE ITEM 78 RACE, SWEPT TO THE TWO RATE LIMITERS THAT NEVER GOT IT.
--
-- ── FOUR RATE LIMITERS, TWO FIXED ──────────────────────────────────────────
-- The count-then-insert race was found and fixed for the AI limiter
-- (sql/sairn_ai_rate_limit_consume_fn.sql) and for CourtListener
-- (sql/cl_rate_limit_consume_fn_2026-09-04.sql). Nobody swept the other two.
-- Found 2026-09-14 by reading them during the item 6 triage:
--
--     api/_lib/wex.js          checkLimit()  -- count, decide, POST
--     api/_lib/intl-caselaw.js checkLimit()  -- count, decide, POST
--
-- Both read the window in ONE HTTP call and insert in ANOTHER, with nothing
-- coordinating them. That is verbatim the shape docs/spec/RateLimitConsume.tla
-- models and tools/rate_limit_race_model.js proves violates the cap: N
-- concurrent lookups all see the same window and all proceed.
--
-- ── WHAT IS DIFFERENT HERE, BECAUSE COPYING THE PATTERN IS NOT THE JOB ─────
-- docs/2026-09-13-cross-domain-disciplines.md item 7: byte-identical is not
-- safe-in-context. Ariane 5 flew correct, faithfully-copied software into the
-- ground. So the three ways this differs from the two existing functions are
-- named rather than inherited:
--
--   1. IT TAKES A TABLE. The AI and CL functions each hardcode one ledger.
--      intl-caselaw's checkLimit is generic over its tables, so this one has to
--      be too -- and a table name reaching dynamic SQL is an injection surface
--      that neither of those functions has. It is ALLOWLISTED, not escaped:
--      api/_lib/audit.js faced exactly this for audit table names and chose an
--      allowlist over free interpolation, and its reasoning holds here. A name
--      outside the list RAISES; quote_ident alone would be safe against
--      injection and would still let a caller consume against any table.
--   2. THE LIMIT IS A PARAMETER AND SO IS THE WINDOW. wex is a CRAWL-DELAY --
--      at most ONE row in a 10-second window -- and fcl is an N-per-window cap.
--      The same function serves both because the comparison is the same; the
--      values are the caller's.
--   3. IT IS NOT OUR QUOTA. The AI limit protects our own spend. These honour
--      SOMEBODY ELSE'S published rate (law.cornell.edu's robots.txt says
--      `Crawl-delay: 10`). Over-running it is an access and politeness failure
--      whose cost lands on every customer if the source blocks the IP.
--
-- ── THE READ COMMITTED PRECONDITION TRAVELS WITH THE PATTERN ───────────────
-- pg_advisory_xact_lock serialises ACQUISITION and does not move the
-- transaction's SNAPSHOT. Under repeatable read or serializable a caller that
-- waited on the lock still counts against a world in which the holder had not
-- committed, and the cap over-runs WITH THE LOCK WORKING PERFECTLY -- the
-- stale-snapshot enumerator in tools/rate_limit_race_model.js exhibits it.
--
-- That precondition was discovered for the AI function on 2026-09-14 and it is
-- carried here DELIBERATELY rather than left to be rediscovered. Propagating a
-- pattern without its preconditions is how a correct fix becomes a wrong one
-- somewhere else.
--
-- ── SECURITY INVOKER, and STILL FAILS OPEN AT THE CLIENT ───────────────────
-- Not SECURITY DEFINER: only service_role may call it and service_role already
-- holds the SELECT and INSERT this needs. The CLIENTS keep their existing
-- behaviour on failure, which is NOT fail-open here and is worth stating: both
-- callers refuse the lookup when the ledger is unreachable, because a limit
-- that exists to be respected must not be skipped when its bookkeeping is
-- missing. This file does not change that.
-- ---------------------------------------------------------------------------

create or replace function public.sairnlaw_rate_limit_consume(
  p_table          text,
  p_window_seconds integer,
  p_max            integer
)
returns jsonb
language plpgsql
as $$
declare
  v_count bigint;
  v_iso   text;
begin
  -- THE ALLOWLIST. A table name becomes part of a dynamic statement below, and
  -- an unvalidated one from a caller is the injection vector even when every
  -- caller today passes a constant. Same decision, same reason, as
  -- api/_lib/audit.js's AUDIT_TABLES.
  if p_table is null or p_table not in ('wex_rate_limit_log', 'fcl_rate_limit_log') then
    return jsonb_build_object('error', 'unknown ledger: ' || coalesce(p_table, '(null)'));
  end if;
  if p_window_seconds is null or p_window_seconds <= 0
     or p_max is null or p_max < 1 then
    return jsonb_build_object('error', 'window_seconds must be > 0 and max >= 1');
  end if;

  -- THE PRECONDITION, CHECKED RATHER THAN ASSUMED. See the header: the lock
  -- serialises acquisition and not the snapshot, so outside read committed this
  -- function returns a count it cannot stand behind. RAISING rather than
  -- returning an error object is deliberate and matches
  -- sairn_ai_rate_limit_consume: the callers treat a failure as "could not
  -- check" and refuse, while an error OBJECT would be read as a real answer.
  v_iso := current_setting('transaction_isolation');
  if v_iso <> 'read committed' then
    raise exception
      'sairnlaw_rate_limit_consume requires READ COMMITTED; this transaction '
      'is %. The advisory lock serialises acquisition but does not move the '
      'snapshot, so under % the count is read from before the previous caller '
      'committed and the published rate is over-run while the lock appears to '
      'work.', v_iso, v_iso
      using errcode = 'invalid_transaction_state';
  end if;

  -- Per-ledger, so wex and fcl never block each other.
  perform pg_advisory_xact_lock(hashtext('sairnlaw_rl:' || p_table));

  execute format(
    'select count(*) from public.%I where requested_at >= now() - make_interval(secs => $1)',
    p_table) into v_count using p_window_seconds;

  if v_count >= p_max then
    -- NOT RECORDED WHEN REFUSED, and this differs from the AI limiter on
    -- purpose. That one records over-limit calls so observe-mode data reflects
    -- real demand. Here a recorded refusal would EXTEND the very crawl-delay
    -- window it was refused by -- a caller polling every second would hold
    -- itself out indefinitely. The limit is a promise to a third party about
    -- requests we SEND, so only a request we are about to send is recorded.
    return jsonb_build_object('limited', true, 'prior_count', v_count,
                              'max', p_max, 'window_seconds', p_window_seconds);
  end if;

  execute format('insert into public.%I default values', p_table);

  return jsonb_build_object('limited', false, 'prior_count', v_count,
                            'max', p_max, 'window_seconds', p_window_seconds);
end;
$$;

revoke all on function public.sairnlaw_rate_limit_consume(text, integer, integer)
  from public, anon, authenticated;
grant execute on function public.sairnlaw_rate_limit_consume(text, integer, integer)
  to service_role;

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. It exists and only service_role may execute it. Expect ONE row:
--    service_role | EXECUTE
select grantee, privilege_type
  from information_schema.routine_privileges
 where routine_schema = 'public'
   and routine_name = 'sairnlaw_rate_limit_consume'
 order by grantee;

-- 2. THE ALLOWLIST REFUSES. Expect: {"error": "unknown ledger: pg_authid"}
--    A function that happily counted pg_authid would be an information leak
--    dressed as a rate limiter, so this is the arm worth running first.
select public.sairnlaw_rate_limit_consume('pg_authid', 10, 1);

-- 3. THE PAIRED POSITIVE: a real ledger answers. Expect limited false on a
--    quiet window, and a prior_count.
select public.sairnlaw_rate_limit_consume('fcl_rate_limit_log', 1, 1000000);

-- 4. IT ACTUALLY REFUSES AT THE LIMIT. Expect the second call limited true.
--    A max of 1 over a long window means the row written by the first call
--    holds the second out, which is the crawl-delay shape wex depends on.
-- select public.sairnlaw_rate_limit_consume('fcl_rate_limit_log', 3600, 1);
-- select public.sairnlaw_rate_limit_consume('fcl_rate_limit_log', 3600, 1);
--   -> the SECOND must be {"limited": true}. If both say false the lock or the
--      count is not doing its job. (These write two real rows; they age out of
--      their own window and DELETE is not granted platform-wide.)

-- 5. THE ISOLATION GUARD REFUSES, because a guard nobody has watched refuse is
--    indistinguishable from one that cannot.
-- begin;
--   set transaction isolation level repeatable read;
--   select public.sairnlaw_rate_limit_consume('fcl_rate_limit_log', 10, 1);
--   -- EXPECTED: ERROR 25000 "requires READ COMMITTED". A jsonb row here means
--   -- the guard is not firing; report that rather than working around it.
-- rollback;

-- 6. THE CONCURRENCY CHECK, if you want to see the fix rather than trust it.
--    Twenty parallel callers with a max of 5: the highest prior_count returned
--    must be exactly 4 with no value repeated, because only the first five
--    insert. A repeated prior_count means the lock is not holding.
-- select x, (public.sairnlaw_rate_limit_consume('fcl_rate_limit_log', 3600, 5)->>'prior_count')::int
--   from generate_series(1, 20) x;
