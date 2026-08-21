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
--   Canada   CanLII official REST API at api.canlii.org/v1 with a free key.
--            CanLII prohibits scraping -- the keyed API is the sanctioned
--            route, a distinction underlined by CanLII's own Nov-2024 claim
--            against an AI legal-research platform for systematic scraping.

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

create table if not exists public.canlii_rate_limit_log (
  id           bigserial primary key,
  requested_at timestamptz not null default now()
);
create index if not exists idx_canliiratelimit_time on public.canlii_rate_limit_log(requested_at);

-- ── RLS: service-role only, same posture as every other SAIRNlaw table ───
alter table public.wex_rate_limit_log    enable row level security;
alter table public.fcl_rate_limit_log    enable row level security;
alter table public.canlii_rate_limit_log enable row level security;

drop policy if exists "svc only wex_rate_limit_log"    on public.wex_rate_limit_log;
drop policy if exists "svc only fcl_rate_limit_log"    on public.fcl_rate_limit_log;
drop policy if exists "svc only canlii_rate_limit_log" on public.canlii_rate_limit_log;

create policy "svc only wex_rate_limit_log"    on public.wex_rate_limit_log    for all using (false) with check (false);
create policy "svc only fcl_rate_limit_log"    on public.fcl_rate_limit_log    for all using (false) with check (false);
create policy "svc only canlii_rate_limit_log" on public.canlii_rate_limit_log for all using (false) with check (false);

grant select, insert, delete on public.wex_rate_limit_log    to service_role;
grant select, insert, delete on public.fcl_rate_limit_log    to service_role;
grant select, insert, delete on public.canlii_rate_limit_log to service_role;
grant usage, select on sequence public.wex_rate_limit_log_id_seq    to service_role;
grant usage, select on sequence public.fcl_rate_limit_log_id_seq    to service_role;
grant usage, select on sequence public.canlii_rate_limit_log_id_seq to service_role;

revoke all on public.wex_rate_limit_log    from anon, authenticated;
revoke all on public.fcl_rate_limit_log    from anon, authenticated;
revoke all on public.canlii_rate_limit_log from anon, authenticated;

-- Verify after running (expect 0, 0, 0 and no error):
--   select
--     (select count(*) from wex_rate_limit_log)    as wex,
--     (select count(*) from fcl_rate_limit_log)    as fcl,
--     (select count(*) from canlii_rate_limit_log) as canlii;
