-- sql/sairn_ai_usage_columns_2026-09-02.sql
--
-- Records how big AI requests actually are. Run in the Supabase SQL editor
-- AFTER sql/sairn_ai_rate_limit_schema.sql and
-- sql/sairn_ai_rate_limit_consume_fn.sql, both of which this replaces parts of.
--
-- ── WHY THIS EXISTS ─────────────────────────────────────────────────────────
-- [0039] was held for a day of production traffic so a token budget could be
-- set from real assembled prompt sizes. There were none, and there never had
-- been: api/claude.js receives Anthropic's own `usage` block on every
-- successful call and forwards it to the client WITHOUT EVER READING IT, and
-- this table stored only (app_id, requested_at). Vercel confirmed 97
-- /api/claude calls in 36 hours across nineteen apps with no size recorded on
-- any of them. Waiting longer would have produced the same nothing.
--
-- So SD_PROMPT_BUDGET_TOKENS in stonedesk.html is currently a labelled guess.
-- These two columns are what would let it become a measured number.
--
-- ── NO NEW TABLE, DELIBERATELY ──────────────────────────────────────────────
-- This table already gets a row per rate-limited AI call across every app. A
-- parallel usage table would be a second logging system to keep in step with
-- the first, and the first already has the app_id and the timestamp.
--
-- ── HONEST SCOPE: THIS DOES NOT SEE EVERY CALL ──────────────────────────────
-- api/claude.js only consults the rate limiter when `is_demo` is true. Ten of
-- eleven live apps send is_demo:true, so this covers most traffic and NOT all
-- of it, and a non-demo call will be entirely absent rather than present with
-- null tokens. Do not read counts off this table as total platform AI volume.
--
-- ── WHY AN RPC AND NOT A TABLE GRANT ────────────────────────────────────────
-- Writing the tokens means UPDATE, and service_role deliberately holds only
-- SELECT and INSERT here. sairn_ai_rate_limit_consume_fn.sql already made this
-- exact call and wrote down its reasoning: "GRANT EXECUTE on one function is
-- narrower" than widening a table grant, on a platform that has just been
-- through a deliberate grant-narrowing sweep. Same answer here, so no
-- `grant update` appears in this file.
--
-- The recorder below is the ONE thing in this schema that is SECURITY DEFINER,
-- and the consume function's own header argues against DEFINER. That argument
-- was about a function that needed no extra privilege; this one genuinely does,
-- since the whole point is an UPDATE service_role cannot perform. It is fenced
-- so that it can do nothing else:
--   * it writes only the two token columns, never app_id or requested_at;
--   * it refuses a row whose tokens are already set, so history cannot be
--     rewritten, only filled in once;
--   * it refuses a row older than one hour, so it cannot be walked backwards
--     over the table;
--   * it takes an id, so it can never touch more than one row;
--   * search_path is pinned, which is the standard DEFINER hardening.
--
-- ── FAILS OPEN, LIKE EVERYTHING ELSE ON THIS PATH ───────────────────────────
-- Recording a size is a measurement, never a control. api/claude.js calls the
-- recorder fire-and-forget after the reply is already on its way back; if this
-- migration has not been run, the RPC 404s and nothing happens. An AI feature
-- must never break because a statistic could not be written.

-- ── 1. THE COLUMNS ──────────────────────────────────────────────────────────
-- Nullable on purpose. NULL means "not recorded", which is a real and common
-- state: the request failed upstream, or the row predates this migration.
-- A zero would be a measurement, and these are not measurements.
alter table public.sairn_ai_rate_limit_log
  add column if not exists input_tokens  integer,
  add column if not exists output_tokens integer;

-- Only rows that HAVE a measurement are ever queried for sizing, and after a
-- backlog of null rows that is most of the table. Partial index, so it does
-- not carry the un-measured majority.
create index if not exists idx_sairn_ai_rl_usage
  on public.sairn_ai_rate_limit_log (app_id, requested_at desc)
  where input_tokens is not null;

-- ── 2. CONSUME NOW RETURNS THE ROW IT INSERTED ──────────────────────────────
-- Identical to sql/sairn_ai_rate_limit_consume_fn.sql except for `returning id`
-- and the extra `row_id` key. Additive: an older client that ignores the key
-- behaves exactly as before, so this file and that one can be run in either
-- order without a window where the limiter is broken.
create or replace function public.sairn_ai_rate_limit_consume(
  p_app_id         text,
  p_limit          integer,
  p_window_seconds integer
)
returns jsonb
language plpgsql
as $$
declare
  v_count  bigint;
  v_row_id bigint;
begin
  if p_app_id is null or p_app_id = '' then
    return jsonb_build_object('error', 'app_id required');
  end if;

  perform pg_advisory_xact_lock(hashtext('sairn_ai_rl:' || p_app_id));

  select count(*)
    into v_count
    from public.sairn_ai_rate_limit_log
   where app_id = p_app_id
     and requested_at >= now() - make_interval(secs => p_window_seconds);

  -- Recorded even when over the limit, so observe-mode data reflects real
  -- demand rather than being clipped at the threshold. Unchanged.
  insert into public.sairn_ai_rate_limit_log (app_id)
  values (p_app_id)
  returning id into v_row_id;

  return jsonb_build_object(
    'prior_count', v_count,
    'limited',     v_count >= p_limit,
    'limit',       p_limit,
    'row_id',      v_row_id
  );
end;
$$;

revoke all on function public.sairn_ai_rate_limit_consume(text, integer, integer) from public, anon, authenticated;
grant execute on function public.sairn_ai_rate_limit_consume(text, integer, integer) to service_role;

-- ── 3. THE RECORDER ─────────────────────────────────────────────────────────
-- Returns true only if it actually wrote. False is not an error and is not
-- retried -- a missed statistic costs nothing, and the caller ignores it.
create or replace function public.sairn_ai_record_usage(
  p_row_id        bigint,
  p_input_tokens  integer,
  p_output_tokens integer
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_hit integer;
begin
  if p_row_id is null then
    return false;
  end if;
  -- Negative or absurd values are refused rather than stored: a poisoned
  -- number in a table meant to SET a budget is worse than a missing one.
  if p_input_tokens is null or p_input_tokens < 0 or p_input_tokens > 10000000
     or p_output_tokens is null or p_output_tokens < 0 or p_output_tokens > 10000000 then
    return false;
  end if;

  update public.sairn_ai_rate_limit_log
     set input_tokens  = p_input_tokens,
         output_tokens = p_output_tokens
   where id = p_row_id
     and input_tokens is null            -- fill in once, never rewrite
     and requested_at >= now() - interval '1 hour';   -- and only what is current

  get diagnostics v_hit = row_count;
  return v_hit = 1;
end;
$$;

revoke all on function public.sairn_ai_record_usage(bigint, integer, integer) from public, anon, authenticated;
grant execute on function public.sairn_ai_record_usage(bigint, integer, integer) to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- 1. The columns exist and are nullable:
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'sairn_ai_rate_limit_log'
   and column_name in ('input_tokens', 'output_tokens');

-- 2. consume now returns a row_id (the key is what matters, not the value):
--   select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400);
--     -> {"limit":1000000,"limited":false,"prior_count":N,"row_id":12345}
--
-- 3. The recorder writes once and refuses the second time -- run these three
--    in order using the row_id from step 2:
--   select public.sairn_ai_record_usage(<row_id>, 1234, 567);   -> true
--   select public.sairn_ai_record_usage(<row_id>, 9999, 999);   -> false  (already set)
--   select public.sairn_ai_record_usage(-1,       1234, 567);   -> false  (no such row)
--   select input_tokens, output_tokens from public.sairn_ai_rate_limit_log
--    where id = <row_id>;                                       -> 1234, 567
--
-- 4. Once real traffic has accumulated, THIS is the query that replaces the
--    provisional SD_PROMPT_BUDGET_TOKENS = 20000 in stonedesk.html with a
--    measured number. Report the distribution, not just the mean -- a mean
--    hides exactly the runaway tail the budget exists to catch:
--   select app_id,
--          count(*)                                                     as calls,
--          min(input_tokens)                                            as min_in,
--          percentile_disc(0.50) within group (order by input_tokens)   as p50_in,
--          percentile_disc(0.95) within group (order by input_tokens)   as p95_in,
--          percentile_disc(0.99) within group (order by input_tokens)   as p99_in,
--          max(input_tokens)                                            as max_in
--     from public.sairn_ai_rate_limit_log
--    where input_tokens is not null
--    group by app_id
--    order by max_in desc;
