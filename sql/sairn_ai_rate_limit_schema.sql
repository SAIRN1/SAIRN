-- sql/sairn_ai_rate_limit_schema.sql
-- Platform-wide persistent rate-limit log for AI calls through api/claude.js
-- and api/sc-ai.js. Run once in the Supabase SQL editor.
--
-- WHY THIS EXISTS: api/claude.js's own header has documented this exact fix
-- as needed since it was written -- its `demoCallCounts` object is an
-- in-memory, per-instance counter that resets on cold start and is not shared
-- across concurrent Vercel invocations, so it "does NOT reliably cap usage or
-- cost across real traffic." The 2026-08-20 firewall audit (layer 22)
-- confirmed that is still true. This is the persistent counter that header
-- asked for, built on the same Supabase-backed sliding-window pattern already
-- proven in api/_lib/courtlistener.js (see cl_rate_limit_log in
-- sql/sairnlaw_citator_schema.sql).
--
-- READ THIS BEFORE ENABLING ENFORCEMENT -- 10 of 11 live apps send
-- is_demo:true, so a limit that has effectively NEVER been enforced (because
-- the in-memory counter kept resetting) would suddenly become real across
-- almost the whole platform. Blindly switching that on risks a platform-wide
-- outage on a threshold nobody has ever measured against real traffic.
--
-- For that reason the limiter ships in OBSERVE mode by default: it records
-- every call and logs when a limit WOULD have been exceeded, but does not
-- block. Flip it on deliberately, after looking at real numbers, by setting
-- the Vercel env var:
--     SAIRN_AI_RATE_LIMIT_MODE=enforce
-- The threshold itself is env-tunable without a redeploy:
--     SAIRN_AI_DAILY_LIMIT=200        (default 200, matching the old constant)
--
-- One row per AI call. app_id is recorded so limits are per-app, exactly as
-- the original DEMO_DAILY_LIMIT intended.

create table if not exists public.sairn_ai_rate_limit_log (
  id           bigserial primary key,
  app_id       text not null,
  requested_at timestamptz not null default now()
);

create index if not exists idx_sairn_ai_ratelimit_app_time
  on public.sairn_ai_rate_limit_log (app_id, requested_at desc);

alter table public.sairn_ai_rate_limit_log enable row level security;
drop policy if exists "svc only sairn_ai_rate_limit_log" on public.sairn_ai_rate_limit_log;
create policy "svc only sairn_ai_rate_limit_log" on public.sairn_ai_rate_limit_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant select, insert, delete on public.sairn_ai_rate_limit_log to service_role;
revoke all on public.sairn_ai_rate_limit_log from anon, authenticated;

-- Rows older than ~25 hours have no further use for a daily window. Prune
-- periodically (the limiter itself does not prune on every call -- that would
-- add a write to every request for no benefit):
--   delete from sairn_ai_rate_limit_log where requested_at < now() - interval '25 hours';

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sairn_ai_rate_limit_log;
