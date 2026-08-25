-- sql/sairnlaw_wex_intl_schema.sql
-- Backing tables for SAIRNlaw Phase A (Wex legal-term lookup) and Phase B
-- (international case-law grounding). Run once in the Supabase SQL editor.
--
-- ── WHY THESE RATE-LIMIT TABLES EXIST ────────────────────────────────────
-- Same reasoning as cl_rate_limit_log in sairnlaw_citator_schema.sql: these
-- are stateless serverless functions and every SAIRNlaw firm shares the same
-- egress, so an in-process cooldown would be wrong the moment two instances
-- are warm. The published limit has to be enforced against shared state or it
-- is not really being enforced at all.
--
-- wex_rate_limit_log honours law.cornell.edu/robots.txt's `Crawl-delay: 10`.
-- That value was read from the live robots.txt before this was written, along
-- with confirming that /wex is NOT among the Disallow paths (only Drupal
-- infrastructure and /search/ are).
--
-- ── WHAT IS DELIBERATELY ABSENT, AND WHY ─────────────────────────────────
-- There are no BAILII or AustLII tables here, and there is no code anywhere in
-- SAIRNlaw that touches either. Both were researched against their own primary
-- terms before any design work:
--
--   BAILII  -- prohibits bulk downloading and scraping in its standard user
--             agreement, and restricts crawlers. Its stated concern is AI
--             software being built to predict case outcomes.
--   AustLII -- its usage policy prohibits "spidering, scraping, crawling,
--             mirroring, page framing, API access, bulk querying, automated
--             agents", and it blocks automated access for AI-related uses
--             across its entire collection. Even its educational-permission
--             carve-out is stated as excluding AI-related uses.
--
-- Neither is a bot-detection problem that better scraping tooling would solve.
-- They are permission problems, and the permission is explicitly refused. They
-- are therefore not covered, and SAIRNlaw states the gap in the UI rather than
-- quietly appearing to have worldwide coverage it does not have.
--
-- The jurisdictions that ARE covered are covered under terms that permit it:
--   US       CourtListener  (already live, see sairnlaw_citator_schema.sql)
--   UK E&W   Find Case Law (The National Archives), Open Justice Licence,
--            which expressly permits commercial use and incorporation into a
--            product. NOTE: bulk "computational analysis" needs a separate
--            licence, so this integration is on-demand lookup only.
--
-- CANADA WAS COVERED AND IS NO LONGER. Removed here 2026-08-25, and the
-- reason is a SCOPE decision, never a terms problem: CanLII's keyed REST API
-- was the sanctioned route and the implementation was correct. The feature
-- was deleted in b747ecb (live-verified), no CANLII_API_KEY was ever
-- provisioned, and Michael DROPPED public.canlii_rate_limit_log on
-- 2026-08-24. Its `create table if not exists`, index, RLS policy, grants
-- and verification line lived in this file until now -- meaning any routine
-- re-run of this schema would have RESURRECTED a deliberately dropped table.
-- That is why the table definition is gone rather than merely its grant.
-- api/_lib/intl-caselaw.js carries the full reasoning; the only remaining
-- CanLII references anywhere on the platform are explanatory comments in
-- that file, api/legal-citator.js and api/legal-reference.js -- confirmed by
-- grep, no live code path. If Canada is ever restored, re-read CanLII's
-- CURRENT API terms rather than reinstating this from history.

-- ── Phase A: Wex crawl-delay ledger ──────────────────────────────────────
create table if not exists public.wex_rate_limit_log (
  id           bigserial primary key,
  requested_at timestamptz not null default now()
);
create index if not exists idx_wexratelimit_time on public.wex_rate_limit_log(requested_at);

-- ── Phase B: per-source request ledgers ──────────────────────────────────
-- Separate tables rather than one shared ledger, because each source has its
-- own published limit and mixing them would make one source's traffic
-- throttle another's for no reason.
create table if not exists public.fcl_rate_limit_log (
  id           bigserial primary key,
  requested_at timestamptz not null default now()
);
create index if not exists idx_fclratelimit_time on public.fcl_rate_limit_log(requested_at);


-- ── RLS: service-role only, same posture as every other SAIRNlaw table ───
alter table public.wex_rate_limit_log    enable row level security;
alter table public.fcl_rate_limit_log    enable row level security;

drop policy if exists "svc only wex_rate_limit_log"    on public.wex_rate_limit_log;
drop policy if exists "svc only fcl_rate_limit_log"    on public.fcl_rate_limit_log;

create policy "svc only wex_rate_limit_log"    on public.wex_rate_limit_log    for all using (false) with check (false);
create policy "svc only fcl_rate_limit_log"    on public.fcl_rate_limit_log    for all using (false) with check (false);

-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert on public.wex_rate_limit_log    to service_role;
grant select, insert on public.fcl_rate_limit_log    to service_role;
grant usage, select on sequence public.wex_rate_limit_log_id_seq    to service_role;
grant usage, select on sequence public.fcl_rate_limit_log_id_seq    to service_role;

revoke all on public.wex_rate_limit_log    from anon, authenticated;
revoke all on public.fcl_rate_limit_log    from anon, authenticated;

-- Verify after running (expect 0, 0, 0 and no error):
--   select
--     (select count(*) from wex_rate_limit_log) as wex,
--     (select count(*) from fcl_rate_limit_log) as fcl;
