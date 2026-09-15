-- sql/sairn_circuit_breaker_schema.sql
-- The SHARED state behind api/_lib/resilience.js's circuit breaker.
-- Run once in the Supabase SQL editor. Nothing else depends on it.
--
-- ══ WHY THIS TABLE HAS TO EXIST AT ALL ══════════════════════════════════════
-- A circuit breaker is a failure COUNTER with a THRESHOLD. Hystrix, Resilience4j
-- and Polly all keep that counter in process memory, which is correct for a
-- long-lived JVM or .NET host and is wrong here.
--
-- THIS PLATFORM HAS ALREADY MEASURED WHAT HAPPENS. api/_lib/anon-rate-limit.js
-- shipped a per-instance counter with a threshold; live on 2026-09-05, 40
-- concurrent requests against a limit of 20 produced not one trip, because a
-- dozen Vercel instances each counted the same subject from 1. Its header states
-- the general result: horizontal scale-out defeats a per-instance counter IN
-- PROPORTION TO LOAD. For a breaker that is worse than for a rate limiter --
-- load is exactly what makes a dependency degrade, so the counter is diluted
-- most at the moment the breaker is supposed to trip.
--
-- So the state is in Postgres, and the decision is one RPC under an advisory
-- lock, on the pattern sql/sairn_ai_rate_limit_consume_fn.sql already proved.
--
-- ══ WHAT THIS CANNOT BE USED FOR, BY CONSTRUCTION ═══════════════════════════
-- IT CANNOT BREAK ON SUPABASE ITSELF. Asking the database whether the database
-- is reachable returns the answer you already have, and a breaker whose store is
-- the failing dependency has no state to read when it matters. A Supabase
-- breaker is therefore instance-backed and OBSERVE-ONLY, and api/_lib/
-- resilience.js refuses to enforce one. The TIMEOUT and the BULKHEAD are what
-- protect a caller from a slow Supabase; both are per-instance and both work.
-- This is a real limit of the design, not a gap to close later.

create table if not exists public.sairn_circuit_breaker (
  -- One row per dependency key: 'stripe', 'claude-proxy', 'resend', ...
  -- NOT per licence. A dependency is down for everybody or for nobody, and a
  -- per-tenant key would need each tenant to independently discover the outage.
  key               text primary key,
  state             text not null default 'CLOSED'
                      check (state in ('CLOSED', 'OPEN', 'HALF_OPEN')),
  -- CONSECUTIVE failures, reset by any success. Lifetime failures would trip a
  -- long-lived key on unrelated noise spread over hours, which is an outage
  -- caused by the breaker rather than prevented by it.
  failures          integer not null default 0 check (failures >= 0),
  opened_at         timestamptz,
  half_open_probes  integer not null default 0 check (half_open_probes >= 0),
  -- Observability, not mechanism. Without these a breaker that opened at 3am is
  -- a mystery by morning: nothing records that it ever happened.
  last_failure_at   timestamptz,
  last_success_at   timestamptz,
  opened_count      integer not null default 0,
  updated_at        timestamptz not null default now()
);

comment on table public.sairn_circuit_breaker is
  'Shared circuit-breaker state. Per-instance memory cannot hold this on Vercel '
  '-- see api/_lib/anon-rate-limit.js, measured 2026-09-05.';

-- ── THE DECISION, IN ONE ROUND TRIP, UNDER A LOCK ──────────────────────────
-- p_outcome: 'probe'   -- may I call? (also performs the OPEN -> HALF_OPEN roll)
--            'failure' -- the call failed in a way that counts
--            'success' -- the call worked
--
-- SECURITY DEFINER with a pinned search_path, and EXECUTE granted to
-- service_role only. Same reasoning as the rate-limit RPC: a definer function
-- with a mutable search_path is a privilege-escalation surface if the grant is
-- ever widened.
create or replace function public.sairn_circuit_breaker_step(
  p_key              text,
  p_outcome          text,
  p_threshold        integer,
  p_open_ms          integer,
  p_half_open_probes integer
) returns public.sairn_circuit_breaker
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  r public.sairn_circuit_breaker;
begin
  if p_key is null or length(trim(p_key)) = 0 then
    raise exception 'p_key is required' using errcode = '22023';
  end if;
  if p_outcome not in ('probe', 'failure', 'success') then
    raise exception 'p_outcome must be probe, failure or success (got %)', p_outcome
      using errcode = '22023';
  end if;
  -- REFUSE A THRESHOLD OF ZERO OR LESS rather than treating it as "open
  -- immediately". A caller that passes 0 by accident -- an unset env var read as
  -- a number is the usual way -- would otherwise take a healthy dependency
  -- offline on its first hiccup, and the breaker would look like it was working.
  if p_threshold is null or p_threshold < 1 then
    raise exception 'p_threshold must be >= 1 (got %); a threshold of zero opens '
                    'the circuit on the first failure and is almost always an '
                    'unset configuration value', p_threshold using errcode = '22023';
  end if;
  if p_open_ms is null or p_open_ms < 1 then
    raise exception 'p_open_ms must be >= 1 (got %)', p_open_ms using errcode = '22023';
  end if;

  -- Serialises the read-modify-write for THIS key. Two different dependencies
  -- never wait on each other, which matters because this is now on the path of
  -- every guarded call.
  perform pg_advisory_xact_lock(hashtext('sairn_cb:' || p_key));

  insert into public.sairn_circuit_breaker (key) values (p_key)
    on conflict (key) do nothing;
  select * into r from public.sairn_circuit_breaker where key = p_key for update;

  -- The OPEN -> HALF_OPEN roll happens on a PROBE, not on a timer. There is no
  -- background job here and there must not be one: state that only advances
  -- when somebody asks cannot drift while nobody is looking.
  if r.state = 'OPEN'
     and r.opened_at is not null
     and now() - r.opened_at >= make_interval(secs => p_open_ms / 1000.0) then
    r.state := 'HALF_OPEN';
    r.half_open_probes := 0;
  end if;

  if p_outcome = 'probe' then
    if r.state = 'HALF_OPEN' then
      if r.half_open_probes >= greatest(coalesce(p_half_open_probes, 1), 1) then
        -- Already probing. Report OPEN to this caller so it is refused, without
        -- disturbing the probe that is in flight.
        r.state := 'OPEN';
      else
        r.half_open_probes := r.half_open_probes + 1;
      end if;
    end if;

  elsif p_outcome = 'success' then
    r.state := 'CLOSED';
    r.failures := 0;
    r.opened_at := null;
    r.half_open_probes := 0;
    r.last_success_at := now();

  else  -- 'failure'
    r.failures := r.failures + 1;
    r.last_failure_at := now();
    -- A failed probe re-opens at once. Giving a still-broken dependency another
    -- full threshold of traffic is the thing HALF_OPEN exists to avoid.
    if r.state = 'HALF_OPEN' or r.failures >= p_threshold then
      if r.state <> 'OPEN' then
        r.opened_count := r.opened_count + 1;
      end if;
      r.state := 'OPEN';
      r.opened_at := now();
      r.half_open_probes := 0;
    end if;
  end if;

  r.updated_at := now();
  update public.sairn_circuit_breaker set
    state = r.state, failures = r.failures, opened_at = r.opened_at,
    half_open_probes = r.half_open_probes, last_failure_at = r.last_failure_at,
    last_success_at = r.last_success_at, opened_count = r.opened_count,
    updated_at = r.updated_at
  where key = p_key;

  return r;
end;
$$;

-- ── GRANTS: REVOKE FIRST, THEN THE MINIMUM ────────────────────────────────
-- No DELETE and no TRUNCATE. A breaker row is the record that a dependency was
-- failing, and TRUNCATE here would silently close every open circuit at once --
-- re-admitting full traffic to everything that was failing, in one statement,
-- with nothing logged.
revoke all on public.sairn_circuit_breaker from public, anon, authenticated;
grant select, insert, update on public.sairn_circuit_breaker to service_role;

revoke all on function public.sairn_circuit_breaker_step(text, text, integer, integer, integer)
  from public, anon, authenticated;
grant execute on function public.sairn_circuit_breaker_step(text, text, integer, integer, integer)
  to service_role;

alter table public.sairn_circuit_breaker enable row level security;
-- No policy is created on purpose: service_role bypasses RLS, and nothing else
-- is allowed to read this table at all. A policy would imply a caller that does
-- not exist.

-- ══ VERIFY BLOCK -- run each statement and compare to its expectation ════════
-- One query per statement with the answer written beside it. A single check at
-- the end cannot tell a full apply from a partial one, and the Supabase SQL
-- editor reports success for the statements it DID run.

select count(*) from information_schema.tables
  where table_schema = 'public' and table_name = 'sairn_circuit_breaker';
-- expect 1

select count(*) from information_schema.routines
  where routine_schema = 'public' and routine_name = 'sairn_circuit_breaker_step';
-- expect 1

select count(*) from information_schema.role_table_grants
  where table_name = 'sairn_circuit_breaker' and privilege_type in ('DELETE', 'TRUNCATE');
-- expect 0

select count(*) from information_schema.role_table_grants
  where table_name = 'sairn_circuit_breaker' and grantee in ('anon', 'authenticated');
-- expect 0

select relrowsecurity from pg_class where relname = 'sairn_circuit_breaker';
-- expect t

-- A REAL ROUND TRIP, not just a schema check. Three failures at a threshold of
-- 3 must open it; a success must close it. If the schema is right and the logic
-- is wrong, only this catches it.
select state from public.sairn_circuit_breaker_step('__verify__', 'failure', 3, 30000, 1);
-- expect CLOSED
select state from public.sairn_circuit_breaker_step('__verify__', 'failure', 3, 30000, 1);
-- expect CLOSED
select state from public.sairn_circuit_breaker_step('__verify__', 'failure', 3, 30000, 1);
-- expect OPEN
select state from public.sairn_circuit_breaker_step('__verify__', 'probe', 3, 30000, 1);
-- expect OPEN   (the open window has not elapsed)
select state from public.sairn_circuit_breaker_step('__verify__', 'success', 3, 30000, 1);
-- expect CLOSED

-- And the guard against a zero threshold, which is the configuration mistake
-- most likely to reach production:
-- select * from public.sairn_circuit_breaker_step('__verify__', 'failure', 0, 30000, 1);
-- expect ERROR 22023 -- commented out so the block runs clean; uncomment to see it

delete from public.sairn_circuit_breaker where key = '__verify__';
-- expect DELETE 1  -- as the table owner in the SQL editor, NOT via service_role,
--                     which deliberately has no DELETE grant
