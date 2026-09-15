-- sql/sairn_ai_tenant_subbudget_2026-09-15.sql
-- PER-TENANT SUB-BUDGET INSIDE THE EXISTING PER-APP AI CEILING.
-- Run once in the Supabase SQL editor. Safe to re-run.
--
-- ── THE DECISION THIS IMPLEMENTS ──────────────────────────────────────────
-- docs/2026-09-15-item93-shared-backend-tenancy-scoping.md measured what this
-- platform actually shares and found three sharing scopes -- global, per-app,
-- per-instance -- chosen independently, of which two were reasoned about
-- explicitly and one was not.
--
-- The one that was not is this limiter. It keys on `app_id`, and every line of
-- justification in api/_lib/ai-rate-limit.js is about ATOMICITY -- the
-- count-then-insert race, the advisory lock, the exact-count header. All of it
-- correct, none of it about tenancy. The consequence was that "should two
-- customers of the same app share one daily quota?" had been answered by a
-- COLUMN NAME rather than by anybody.
--
-- Michael decided it 2026-09-15: each client gets its own sub-budget inside the
-- existing per-app ceiling. Not a second limiter, not a bigger ceiling.
-- CourtListener's global "one token, one budget, one lock" design is NOT part
-- of this change and stays exactly as it is -- that one was reasoned correctly
-- (sql/cl_rate_limit_consume_fn_2026-09-04.sql), for the reason that there is
-- one upstream token and therefore genuinely one budget.
--
-- ── THE GUARANTEE, STATED AS A PROPERTY RATHER THAN AS A MECHANISM ────────
-- Once an app is past its contention floor, NO SINGLE TENANT MAY HOLD MORE
-- THAN ITS SHARE OF THE DAILY CEILING, so the remainder stays reachable by
-- every other tenant of that app. Below the floor nobody is capped.
--
-- ── WHY THE CAP BINDS ONLY UNDER CONTENTION, WHICH IS THE WHOLE DESIGN ────
-- A hard per-tenant cap would be a REGRESSION on this platform today. Ten of
-- the fourteen apps with seeded licences have exactly ONE tenant; capping that
-- tenant at a fraction of its own app's ceiling would take capacity away from
-- somebody who is contending with nobody, to protect tenants who do not exist.
--
-- So the sub-budget is a FAIR-SHARE cap, not a quota: it does nothing until the
-- app is genuinely busy, and then it stops one tenant taking the rest. That is
-- the same reasoning shuffle sharding rests on -- bound the blast radius of one
-- bad neighbour without charging the cost to everyone who has no neighbours.
--
-- ── A NULL TENANT KEY IS NOT A REFUSAL, AND IT IS NOT INVISIBLE EITHER ────
-- SAIRN_CLAUDE_AUTH_MODE is `observe` in production (live-verified 2026-09-13
-- and again 2026-09-15), so a large share of real traffic arrives with NO
-- licence at all and therefore no tenant identity. Refusing those would take
-- the platform down to enforce an accounting rule.
--
-- They are counted against the APP as they always were, are never sub-budgeted,
-- and `tenant_scoped: false` comes back in the answer so observe-mode data
-- shows HOW MUCH traffic is currently unattributable. That number is the real
-- precondition for turning enforcement on, and it did not exist before.
--
-- ── THE 3-ARG FUNCTION IS DROPPED, NOT OVERLOADED ────────────────────────
-- Adding a defaulted 4th parameter alongside the existing 3-arg function would
-- make a 3-arg call AMBIGUOUS -- Postgres would refuse it with "function is not
-- unique", which is a hard outage on every AI call rather than a degradation.
-- So the old signature is dropped and replaced by one with a defaulted
-- p_tenant_key, which still accepts an old-shaped 3-arg call.
--
-- Wrapped in a single transaction so there is no window in which neither
-- exists. If it is run statement-by-statement anyway, the gap is survivable:
-- api/_lib/ai-rate-limit.js treats a 404 as "migration not run" and falls back
-- to its racy count-then-insert, which allows and logs. That is a counting
-- degradation, never a refusal.

begin;

-- ── 1. THE COLUMN ────────────────────────────────────────────────────────
-- NULLABLE ON PURPOSE. Every row written before this migration has no tenant,
-- and back-filling one would invent an attribution nobody recorded -- the same
-- rule api/_lib/dnt-location.js states for location stamping and for the same
-- reason: a call attributed to the wrong tenant is worse than one attributed to
-- none.
alter table public.sairn_ai_rate_limit_log
  add column if not exists tenant_key text;

-- The window query filters app_id + tenant_key + requested_at. The existing
-- (app_id, requested_at desc) index still serves the app-total query; this one
-- serves the tenant-total query. Partial, because a NULL tenant is never
-- counted per-tenant and indexing those rows would be dead weight on the
-- majority of the table today.
create index if not exists idx_sairn_ai_ratelimit_tenant_time
  on public.sairn_ai_rate_limit_log (app_id, tenant_key, requested_at desc)
  where tenant_key is not null;

comment on column public.sairn_ai_rate_limit_log.tenant_key is
  'sha256 license_hash of the calling licence, or NULL when the call arrived '
  'with no licence (SAIRN_CLAUDE_AUTH_MODE=observe). NEVER the raw licence '
  'key -- that is a bearer secret and must not sit in a log table.';

-- ── 2. THE FUNCTION ──────────────────────────────────────────────────────
drop function if exists public.sairn_ai_rate_limit_consume(text, integer, integer);

create or replace function public.sairn_ai_rate_limit_consume(
  p_app_id           text,
  p_limit            integer,
  p_window_seconds   integer,
  p_tenant_key       text    default null,
  p_tenant_limit     integer default null,
  p_contention_floor integer default null
) returns jsonb
language plpgsql
security invoker
as $$
declare
  v_iso            text;
  v_count          integer;
  v_tenant_count   integer := null;
  v_tenant_limit   integer;
  v_floor          integer;
  v_app_limited    boolean;
  v_tenant_limited boolean := false;
begin
  if p_app_id is null or p_app_id = '' then
    raise exception 'sairn_ai_rate_limit_consume: p_app_id is required'
      using errcode = 'invalid_parameter_value';
  end if;

  -- ── THE ISOLATION GUARD IS UNCHANGED AND IS NOT NEGOTIABLE ─────────────
  -- Carried verbatim from the 3-arg function. The advisory lock serialises
  -- acquisition but does not move the snapshot, so under REPEATABLE READ the
  -- count is read from before the previous caller committed and the cap
  -- over-runs while the lock appears to work perfectly. `alter role
  -- service_role set default_transaction_isolation = 'repeatable read'` is one
  -- statement, would be made for an unrelated reason, and would silently turn
  -- this function back into the bug it was written to fix.
  --
  -- RAISES rather than returning an error object: the client treats an RPC
  -- failure as fail-open, which is right for a counting outage, but an error
  -- OBJECT would be read as a real answer and a count would be believed that
  -- must not be. "Could not run" is a third state and is never folded in.
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

  -- Defaults are derived HERE as well as in the client, so a direct SQL caller
  -- and the endpoint cannot disagree about what the sub-budget is. Half the
  -- ceiling for both: past the floor, a single tenant may hold at most half, so
  -- at least half stays reachable by everybody else. Stated as the property it
  -- buys rather than as a number somebody has to reverse-engineer.
  v_tenant_limit := coalesce(p_tenant_limit, greatest(1, p_limit / 2));
  v_floor        := coalesce(p_contention_floor, greatest(1, p_limit / 2));

  -- THE LOCK KEY IS STILL THE APP, DELIBERATELY. Locking per tenant would let
  -- two tenants of the same app pass the APP ceiling simultaneously, which is
  -- exactly the race the 2026-09-02 fix closed. The app lock is the wider one
  -- and it serialises both counts together.
  perform pg_advisory_xact_lock(hashtext('sairn_ai_rl:' || p_app_id));

  select count(*)
    into v_count
    from public.sairn_ai_rate_limit_log
   where app_id = p_app_id
     and requested_at >= now() - make_interval(secs => p_window_seconds);

  if p_tenant_key is not null and p_tenant_key <> '' then
    select count(*)
      into v_tenant_count
      from public.sairn_ai_rate_limit_log
     where app_id = p_app_id
       and tenant_key = p_tenant_key
       and requested_at >= now() - make_interval(secs => p_window_seconds);

    -- The cap binds ONLY under contention. See the header: ten of fourteen
    -- seeded apps have one tenant, and capping a tenant contending with nobody
    -- would take capacity away to protect tenants who do not exist.
    v_tenant_limited := (v_count >= v_floor) and (v_tenant_count >= v_tenant_limit);
  end if;

  v_app_limited := v_count >= p_limit;

  -- Recorded even when over the limit, so observe-mode data reflects real
  -- demand rather than being clipped at the threshold. Unchanged, and it is
  -- what makes the tenant counts usable for the enforcement decision.
  insert into public.sairn_ai_rate_limit_log (app_id, tenant_key)
  values (p_app_id, nullif(p_tenant_key, ''));

  -- `limited` keeps its old meaning -- "this call is over a limit" -- so an
  -- un-migrated client reading only that key behaves correctly. WHICH limit is
  -- a separate field, because "your practice has used its share" and "the whole
  -- app is out" need different words in front of a customer.
  return jsonb_build_object(
    'prior_count',       v_count,
    'limited',           v_app_limited or v_tenant_limited,
    'limited_by',        case when v_app_limited then 'app'
                              when v_tenant_limited then 'tenant'
                              else null end,
    'limit',             p_limit,
    'tenant_scoped',     (p_tenant_key is not null and p_tenant_key <> ''),
    'tenant_prior_count', v_tenant_count,
    'tenant_limit',      v_tenant_limit,
    'contention_floor',  v_floor
  );
end;
$$;

revoke all on function public.sairn_ai_rate_limit_consume(text, integer, integer, text, integer, integer)
  from public, anon, authenticated;
grant execute on function public.sairn_ai_rate_limit_consume(text, integer, integer, text, integer, integer)
  to service_role;

commit;

-- ── VERIFY AFTER RUNNING ─────────────────────────────────────────────────
-- 1. The old 3-arg shape still resolves (defaults fill the rest), and a call
--    with no tenant is NOT sub-budgeted:
--      select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400);
--      -> tenant_scoped false, tenant_prior_count null, limited false
--
-- 2. A tenant-scoped call reports its own count:
--      select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400, 'tenant_a');
--      -> tenant_scoped true, tenant_prior_count 0
--      select public.sairn_ai_rate_limit_consume('__verify__', 1000000, 86400, 'tenant_a');
--      -> tenant_prior_count 1
--
-- 3. THE PROPERTY, and this is the one worth actually running -- a tenant is
--    capped only once the app is past the floor. limit 4 -> floor 2, share 2:
--      select public.sairn_ai_rate_limit_consume('__verify2__', 4, 86400, 'a');  -- app 0  -> false
--      select public.sairn_ai_rate_limit_consume('__verify2__', 4, 86400, 'a');  -- app 1  -> false (below floor)
--      select public.sairn_ai_rate_limit_consume('__verify2__', 4, 86400, 'a');  -- app 2, tenant 2 -> limited_by 'tenant'
--      select public.sairn_ai_rate_limit_consume('__verify2__', 4, 86400, 'b');  -- app 3, tenant 0 -> false, b is NOT starved
--
-- 4. Clean up the verification rows:
--      delete from public.sairn_ai_rate_limit_log where app_id in ('__verify__','__verify2__');
