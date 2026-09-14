-- sql/sairnlaw_citator_weight_freshness.sql
-- A freshness stamp on the one denormalised column in the citator.
--
-- ══ NOT RUN. ═══════════════════════════════════════════════════════════════
-- Nothing has executed this against the live database as of 2026-09-14.
-- Idempotent and safe to re-run once it has been.
--
-- ══ WHY ════════════════════════════════════════════════════════════════════
-- `cl_citations.court_hierarchy_weight` says so in its own comment:
--
--     court_hierarchy_weight numeric,   -- copied from cl_court_cache.position
--                                       -- at classification time
--
-- A copy with no stamp cannot be told from a current value. The SOURCE already
-- carries one -- `cl_court_cache.last_refreshed_at` -- so the copy is the only
-- half of the pair that cannot answer "as of when". Nothing re-syncs it, and
-- nothing could: there is no recorded moment to compare against.
--
-- The stamp makes staleness a SUBTRACTION rather than a guess, which is the
-- same move `db/schema_snapshot.json` already makes for the schema and
-- `gate_column_check.py` makes for its own snapshot age.
--
-- ══ DORMANT TODAY, AND THAT IS THE ARGUMENT FOR DOING IT NOW ═══════════════
-- api/legal-citator.js line 507 reads `const citingCourtId = null;` with a
-- comment explaining why, so the copy block never runs and EVERY
-- court_hierarchy_weight in the table is currently NULL. There is no stale data
-- to repair. **A defect that waits for its first real input is one nobody will
-- connect to the change that finally supplies it** -- the same reasoning as
-- item 50c, fixed the same day for the same reason.

-- ---------------------------------------------------------------------------
-- 1. Before: confirm the column really is unstamped and unpopulated.
-- ---------------------------------------------------------------------------
--   select count(*) as rows,
--          count(court_hierarchy_weight) as weights_set
--     from public.cl_citations;
--   -- EXPECT weights_set = 0 today. A non-zero answer means the copy path woke
--   -- up before this ran, and those rows have no recoverable as-of date --
--   -- record that rather than back-filling one, which would be inventing it.

-- ---------------------------------------------------------------------------
-- 2. The stamp.
-- ---------------------------------------------------------------------------
-- NULLABLE ON PURPOSE. A NOT NULL default of now() would stamp every existing
-- row with today's date and assert a freshness nobody measured -- the exact
-- fabrication this column exists to prevent. NULL means "copied before anyone
-- was recording", which is true and is different from "fresh".
alter table public.cl_citations
  add column if not exists court_hierarchy_weight_as_of timestamptz;

comment on column public.cl_citations.court_hierarchy_weight_as_of is
  'cl_court_cache.last_refreshed_at of the row court_hierarchy_weight was '
  'copied from. NULL means the weight predates this column, NOT that it is '
  'fresh. Written by api/legal-citator.js beside the weight itself.';

-- ---------------------------------------------------------------------------
-- 3. After: the two questions the stamp now makes answerable.
-- ---------------------------------------------------------------------------
-- HOW STALE IS THE COPIED HIERARCHY, per row:
--
--   select c.citing_court_id,
--          c.court_hierarchy_weight,
--          c.court_hierarchy_weight_as_of,
--          now() - c.court_hierarchy_weight_as_of as age
--     from public.cl_citations c
--    where c.court_hierarchy_weight is not null
--    order by c.court_hierarchy_weight_as_of nulls first
--    limit 50;
--
-- AND THE ONE THAT MATTERS -- has the source MOVED since the copy was taken:
--
--   select c.citing_court_id,
--          c.court_hierarchy_weight            as copied,
--          k.position                          as current_source,
--          c.court_hierarchy_weight_as_of      as copied_as_of,
--          k.last_refreshed_at                 as source_refreshed
--     from public.cl_citations c
--     join public.cl_court_cache k on k.id = c.citing_court_id
--    where c.court_hierarchy_weight is distinct from k.position;
--
-- EXPECT zero rows. Every row returned is a classification whose court-authority
-- ordering was computed from a weight the source no longer agrees with --
-- treatments are ordered by this column (api/legal-citator.js:348), so a
-- divergence changes WHICH citing case a lawyer is shown first.
--
-- THIS IS A DETECTOR, NOT A RESYNC. Rewriting the copy in place would silently
-- change the ordering of classifications that were already reviewed; whether a
-- historical classification should be re-ordered by a court ranking that moved
-- afterwards is a legal-product judgement, not a migration.
