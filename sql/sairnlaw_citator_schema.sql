-- sql/sairnlaw_citator_schema.sql
-- SAIRNlaw legal-research citator -- Supabase schema
--
-- DELIBERATELY GLOBAL, NOT license_hash-scoped (unlike every other table in
-- this repo's sd-data.js-pattern schemas). Whether a case has been followed,
-- distinguished, questioned, or overruled is a fact about public case law --
-- identical regardless of which firm on the platform is asking. Scoping this
-- cache per-license would mean every firm separately burns CourtListener's
-- real (and very small -- 5/min, 50/hr, 125/day on the free authenticated
-- tier, confirmed live 2026-08-08) rate limit re-discovering the same public
-- facts. A shared cache means the FIRST firm to look up a popular case pays
-- the CourtListener/Claude cost once; every other firm on the platform gets
-- it free from cache after that. This is the correct architecture given the
-- real rate-limit constraint, not a shortcut.
--
-- The one thing that IS per-firm/per-attorney is the feedback log (who
-- confirmed/corrected which classification) -- that table alone carries
-- license_hash, for attribution, while still feeding into a GLOBAL
-- confidence signal (see cl_citing_treatments.feedback_confirm_count /
-- feedback_correct_count below).
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- same as
-- every other table in this repo. api/courtlistener.js and
-- api/legal-citator.js are the only doors in.

create extension if not exists pgcrypto;

-- One row per CourtListener opinion cluster (a "case") that's ever been
-- looked up through the citator, caching the case-identifying metadata so
-- repeat lookups don't re-hit CourtListener's search/cluster endpoints.
create table if not exists public.cl_case_cache (
  id                uuid primary key default gen_random_uuid(),
  cl_cluster_id     bigint not null,               -- CourtListener cluster_id
  case_name         text not null,
  citation          text,                          -- primary reporter citation string, e.g. "384 U.S. 436"
  court_id          text,                           -- CourtListener court_id, e.g. "scotus"
  court_name        text,
  date_filed        date,
  cite_count        integer,                        -- CourtListener's own reported citeCount at last refresh
  last_refreshed_at timestamptz not null default now(),
  created_at        timestamptz not null default now(),
  unique (cl_cluster_id),
  constraint clcache_data_size check (octet_length(case_name) <= 2000)
);
create index if not exists idx_clcache_cluster on public.cl_case_cache(cl_cluster_id);

-- CourtListener's own court table, mirrored locally for hierarchy weighting
-- (position/jurisdiction/appeals_to are real fields on CourtListener's
-- /courts/ endpoint, confirmed live 2026-08-08 -- not invented here).
-- Refreshed periodically, not per-request -- court structure changes rarely.
create table if not exists public.cl_court_cache (
  id             text primary key,                 -- CourtListener court_id, e.g. "scotus", "ohioctapp"
  full_name      text not null,
  jurisdiction   text,                              -- CourtListener's jurisdiction code, e.g. "F", "SA"
  position       numeric,                           -- CourtListener's own ordinal ranking -- lower = higher authority
  parent_court   text,
  appeals_to     jsonb default '[]'::jsonb,
  last_refreshed_at timestamptz not null default now()
);

-- The core citator record: one row per (cited case, citing opinion) pair --
-- i.e. one row per "how does opinion Y treat case X." This is what item 2
-- and item 3 of the brief are actually built on.
create table if not exists public.cl_citing_treatments (
  id                    uuid primary key default gen_random_uuid(),
  cited_cluster_id      bigint not null,             -- the case being researched
  citing_opinion_id     bigint not null,             -- the CourtListener opinion doing the citing
  citing_case_name      text,
  citing_court_id       text,
  citing_date_filed     date,
  court_hierarchy_weight numeric,                    -- copied from cl_court_cache.position at classification time
  -- Multi-pass classification results -- run_results is the raw per-pass
  -- output (never fewer than 2 passes, see api/legal-citator.js), so
  -- agreement/disagreement is inspectable after the fact, not just
  -- collapsed into a single number.
  run_results           jsonb not null default '[]'::jsonb,
  -- one of: followed / distinguished / questioned / overruled / criticized /
  -- unclear -- "unclear" exists specifically so a low-agreement result has
  -- somewhere honest to land instead of being forced into a confident-
  -- looking label it didn't earn.
  final_treatment        text not null,
  agreement_pct           numeric,                    -- fraction of passes that agreed with final_treatment
  -- Asymmetric caution (brief item 4): the LOWER threshold required to flag
  -- something as questioned/overruled/criticized than to affirmatively call
  -- it still-good-law. Recorded per-row so the actual threshold applied is
  -- auditable, not just described in code comments that can drift from
  -- what shipped.
  caution_threshold_applied numeric,
  -- The real evidence -- brief item 3 requires the actual supporting
  -- sentence and a link, not a bare label.
  supporting_sentence    text not null,
  supporting_sentence_context text,                   -- a bit more surrounding text, for real verification
  source_url             text not null,                -- real CourtListener link to the citing opinion
  -- Feedback loop (brief item 6) -- aggregate counts only here; the
  -- individual feedback events themselves live in cl_feedback_log below.
  -- These are what a future confidence-weighting pass would actually read.
  feedback_confirm_count integer not null default 0,
  feedback_correct_count integer not null default 0,
  classified_at           timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (cited_cluster_id, citing_opinion_id),
  constraint cltreat_evidence_size check (octet_length(supporting_sentence) <= 4000 and octet_length(coalesce(supporting_sentence_context,'')) <= 8000)
);
create index if not exists idx_cltreat_cited on public.cl_citing_treatments(cited_cluster_id);
create index if not exists idx_cltreat_treatment on public.cl_citing_treatments(cited_cluster_id, final_treatment);

-- Coverage tracking per cited case -- brief item 5 requires an HONEST
-- statement of what's actually been processed, not an implied full-parity
-- claim. This is what that statement is computed from: real counts, not a
-- percentage pulled from nowhere.
create table if not exists public.cl_coverage (
  cited_cluster_id       bigint primary key,
  total_citing_reported  integer,                    -- CourtListener's own citeCount for this case
  total_citing_processed integer not null default 0, -- how many of those this system has actually fetched+classified
  jurisdiction_filter     text,                        -- if processing was scoped to a jurisdiction, record it honestly
  date_filter_from        date,                        -- if processing was scoped to "cases after YYYY", record it honestly
  last_processed_at       timestamptz,
  processing_status       text not null default 'not_started', -- not_started / in_progress / complete_within_filter
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

-- Feedback loop (brief item 6): one row per attorney confirm/correct action.
-- license_hash-scoped for real attribution (who said what), but the
-- SIGNAL this produces (confirm vs. correct rates) is meant to inform the
-- GLOBAL cl_citing_treatments row via feedback_confirm_count/
-- feedback_correct_count above -- individual feedback stays attributable,
-- its effect on confidence is shared.
create table if not exists public.cl_feedback_log (
  id                  uuid primary key default gen_random_uuid(),
  license_hash        text not null,
  app_id              text not null default 'sairnlaw',
  treatment_id         uuid not null references public.cl_citing_treatments(id) on delete cascade,
  action               text not null,                -- 'confirmed' or 'corrected'
  corrected_to         text,                          -- new treatment label, only set when action='corrected'
  note                 text,
  created_at           timestamptz not null default now(),
  constraint clfeed_note_size check (octet_length(coalesce(note,'')) <= 2000)
);
create index if not exists idx_clfeed_treatment on public.cl_feedback_log(treatment_id);
create index if not exists idx_clfeed_license on public.cl_feedback_log(license_hash);

-- Real, Supabase-backed sliding-window rate-limit log for outbound calls to
-- CourtListener. Necessary because: (1) CourtListener's authenticated free
-- tier is genuinely small -- 5 requests/minute, 50/hour, 125/day, confirmed
-- against their live docs 2026-08-08 -- and (2) that budget is shared by
-- EVERY SAIRNlaw firm through one server-side token, so an in-memory
-- counter in a stateless Vercel function (resets on cold start, not shared
-- across concurrent invocations) would systematically undercount and blow
-- through the real limit. One row per outbound CourtListener request;
-- api/courtlistener.js checks recent row counts before each call and
-- refuses with 429 if within an unsafe margin of the real limit. Pruned
-- periodically (rows older than 25 hours have no further use for any of
-- the three windows this checks).
create table if not exists public.cl_rate_limit_log (
  id           bigserial primary key,
  requested_at timestamptz not null default now()
);
create index if not exists idx_clratelimit_time on public.cl_rate_limit_log(requested_at);

-- ── RLS: service-role only ────────────────────────────────────────────────
alter table public.cl_case_cache        enable row level security;
alter table public.cl_court_cache       enable row level security;
alter table public.cl_citing_treatments enable row level security;
alter table public.cl_coverage          enable row level security;
alter table public.cl_feedback_log      enable row level security;
alter table public.cl_rate_limit_log    enable row level security;

drop policy if exists "svc only cl_case_cache"        on public.cl_case_cache;
drop policy if exists "svc only cl_court_cache"       on public.cl_court_cache;
drop policy if exists "svc only cl_citing_treatments" on public.cl_citing_treatments;
drop policy if exists "svc only cl_coverage"          on public.cl_coverage;
drop policy if exists "svc only cl_feedback_log"      on public.cl_feedback_log;
drop policy if exists "svc only cl_rate_limit_log"    on public.cl_rate_limit_log;

create policy "svc only cl_case_cache" on public.cl_case_cache
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only cl_court_cache" on public.cl_court_cache
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only cl_citing_treatments" on public.cl_citing_treatments
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only cl_coverage" on public.cl_coverage
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only cl_feedback_log" on public.cl_feedback_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only cl_rate_limit_log" on public.cl_rate_limit_log
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update, delete on public.cl_case_cache        to service_role;
grant select, insert, update, delete on public.cl_court_cache       to service_role;
grant select, insert, update, delete on public.cl_citing_treatments to service_role;
grant select, insert, update, delete on public.cl_coverage          to service_role;
grant select, insert, update, delete on public.cl_feedback_log      to service_role;
grant select, insert, update, delete on public.cl_rate_limit_log    to service_role;
