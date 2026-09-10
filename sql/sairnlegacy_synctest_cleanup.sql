-- sql/sairnlegacy_synctest_cleanup.sql
-- Removes the live write-then-read round-trip test rows created 2026-08-07
-- to verify sql/sairnlegacy_data_schema.sql + sql/sairnlegacy_license_seed.sql
-- work end-to-end (not just resource-name validation) -- same pattern as
-- sql/sairndesign_synctest_cleanup.sql and sql/rbac_test_artifact_cleanup.sql.
--
-- Test performed: wrote one record each to leg_cases, leg_vehicles, and
-- leg_monuments via LEG-PINNACLE-2026 in one request, then read each back
-- in a completely separate request (no shared connection/session) and
-- confirmed the written record was present. All three passed.
--
-- Safe to run once; matches on the exact test ids only, nothing else in
-- any of these tables is touched.

delete from public.leg_cases     where case_id     = 'SYNCTEST-CS-1786145858';
delete from public.leg_vehicles  where vehicle_id   = 'SYNCTEST-FV-1786145858';
delete from public.leg_monuments where monument_id  = 'SYNCTEST-MN-1786145858';

-- ── CONFIRM AFTERWARDS -- ONE QUERY PER STATEMENT (added 2026-09-10) ──────
-- Added because this file had none, which `CLAUDE.md`'s Verification
-- Discipline has required since 2026-08-26: "one per statement, not one for
-- the file: a single count at the end cannot tell a full apply from a partial
-- one." The Supabase SQL editor returns SUCCESS for the statements it DID run,
-- so a multi-statement paste that stops halfway is indistinguishable from a
-- complete one -- that is a real 2026-08-26 failure, not a hypothetical.
--
-- Run each and compare against the expected answer written beside it:
--   select count(*) from public.leg_cases     where case_id     = 'SYNCTEST-CS-1786145858';  -- expect 0
--   select count(*) from public.leg_vehicles  where vehicle_id  = 'SYNCTEST-FV-1786145858';  -- expect 0
--   select count(*) from public.leg_monuments where monument_id = 'SYNCTEST-MN-1786145858';  -- expect 0
--
-- ── AND A CONTROL, so an empty result cannot be a bad predicate ───────────
-- All three coming back 0 proves nothing on its own if the rows were never
-- reachable by that predicate to begin with. Confirm the tables are not simply
-- empty under this licence:
--   select count(*) from public.leg_dispatches;    -- expect > 0 under LEG-PINNACLE-2026
--   select count(*) from public.leg_merch_units;   -- expect > 0 under LEG-PINNACLE-2026
--
-- ── THE "NOT RUN" LABEL ON THIS FILE IS UNVERIFIED, NOT TRUE ──────────────
-- A live probe recorded in docs/SAIRN-OPEN-WORK-INDEX.md on 2026-08-25 found
-- the leg_cases, leg_vehicles and leg_monuments rows named above ALREADY GONE,
-- with working controls alongside (leg_dispatches 1 row, leg_merch_units 3) so
-- an empty result could not be a bad hash. That is another session's
-- observation and it is cited, not re-verified here -- this session had no
-- licence key. Do not read "NOT RUN" on this file as a fact about the
-- database. Run the queries above; they are the only thing that can answer it.
