-- sql/rt_routes_drop_saved_sane.sql
--
-- CONCEPT: REMOVE THE ONE CONSTRAINT THE MODULE WAS WRITTEN AGAINST, AND
-- NOTHING ELSE.
--
-- MICHAEL'S DECISION, 2026-10-20: `api/_lib/routes.js` STAYS UN-CLAMPED and
-- the constraint goes.
--
-- ── WHY ────────────────────────────────────────────────────────────────────
-- `rtroutes_saved_sane CHECK ((saved_seconds IS NULL) OR (saved_seconds >= 0))`
-- is LIVE on `public.rt_routes` -- read out of the 2026-10-20 07:55:45 capture
-- in `db/schema_snapshot.json`. `sql/rt_routes_schema.sql` said it "was
-- REMOVED before the run, deliberately", which was wrong; that line is
-- corrected in the same batch as this file.
--
-- The constraint contradicts the module it exists to store for.
-- `api/_lib/routes.js` returns a NEGATIVE saving UN-CLAMPED on purpose -- "a
-- caller that stores a negative saving has learned something true" -- a test
-- arm asserts it is negative, and all four wired consumers render it as "this
-- order is about N min LONGER than the one you had". With the constraint in
-- place Postgres rejects the ENTIRE upsert on the first negative saving, so
-- the route write fails and the user loses the ordering, not just the figure.
--
-- The only way to satisfy the constraint is to clamp in the module, which
-- re-introduces the 2026-06-18 defect the `saved_seconds` column comment
-- exists to prevent: `Math.max(0, ...)` renders "we could not tell" and "we
-- saved nothing" as the same number on screen. They are different facts.
--
-- ── WHAT STAYS, AND WHY THIS IS A DROP OF ONE CONSTRAINT AND NOT TWO ───────
-- `rtroutes_saving_has_a_basis CHECK ((saved_seconds IS NULL) OR
-- ((optimized_at IS NOT NULL) AND (source <> 'manual')))` is also live and
-- IS NOT TOUCHED. It is a different claim and a correct one: a saving must
-- have a basis. It says nothing about the SIGN of the number, so it does not
-- block a negative saving and nothing about this decision reaches it.
--
-- ── WHAT IT DOES IF YOU RUN IT TWICE ───────────────────────────────────────
-- NOTHING. `drop constraint if exists` is a no-op the second time and does not
-- error. Section 2 reads the same either way.
--
-- ── WHAT THIS DOES NOT DO ──────────────────────────────────────────────────
-- It does not change a column, a grant, an index, RLS, or any other
-- constraint. It does not touch `rt_stops`. It does not alter
-- `api/_lib/routes.js`, which is the point: the code was right and the
-- database was wrong.
--
-- ── AFTER IT RUNS ──────────────────────────────────────────────────────────
-- `db/schema_snapshot.json` will claim a constraint the database no longer
-- has, until somebody re-runs `sql/schema_snapshot_query.sql`. That is
-- expected and is stated rather than left to be discovered: a snapshot is only
-- as current as its last capture, and this file is a migration applied after
-- the newest one.


-- ════════════════════════════════════════════════════════════════════════════
-- 1. DROP IT. One statement.
-- ════════════════════════════════════════════════════════════════════════════
alter table public.rt_routes
  drop constraint if exists rtroutes_saved_sane;


-- ════════════════════════════════════════════════════════════════════════════
-- 2. THE VERIFICATION QUERY. READ-ONLY.
--
--    EXPECTED, exactly:
--      rtroutes_saved_sane          present = false
--      rtroutes_saving_has_a_basis  present = true    <- UNTOUCHED, and this
--                                                        row is why the query
--                                                        reads both
--
--    A `false` on the second row means this file removed something it was not
--    meant to; a `true` on the first means the drop did not take.
-- ════════════════════════════════════════════════════════════════════════════
select
  want.conname,
  exists (
    select 1 from pg_constraint c
    where c.conrelid = 'public.rt_routes'::regclass
      and c.conname = want.conname
  ) as present
from (values
  ('rtroutes_saved_sane'),
  ('rtroutes_saving_has_a_basis')
) as want(conname)
order by want.conname;


-- ════════════════════════════════════════════════════════════════════════════
-- 3. REVERSAL, if this has to come back. NOT run by this file, and read the
--    note: re-adding it would break the next negative saving, which is the
--    reason it was dropped.
-- ════════════════════════════════════════════════════════════════════════════
-- alter table public.rt_routes
--   add constraint rtroutes_saved_sane
--   check ((saved_seconds is null) or (saved_seconds >= 0));
