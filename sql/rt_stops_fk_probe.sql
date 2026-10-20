-- sql/rt_stops_fk_probe.sql
--
-- CONCEPT: A NEGATIVE CONTROL MUST FAIL, BE SEEN TO FAIL, AND LEAVE NOTHING
-- BEHIND. An expected failure that escapes as a raw error is not a test
-- result -- it is an aborted script, and it takes the migration with it.
--
-- ── THE INCIDENT THIS FILE EXISTS BECAUSE OF ───────────────────────────────
-- 2026-10-20. The old sql/rt_stops_license_hash_composite_fk.sql carried both
-- the ADD CONSTRAINT and this control. Michael ran it. The control's insert
-- raised `rtstops_license_matches_route` violated -- THE CONTROL WORKING
-- EXACTLY AS DESIGNED, on route f38eb356 with
-- 'zz-fk-probe-SOMEONE-ELSES-HASH'. The Supabase SQL editor runs a
-- multi-statement script as ONE TRANSACTION, so that error aborted the run
-- and rolled the ADD CONSTRAINT back with it. The constraint was never
-- applied, the editor showed an error, and the only honest reading of the
-- screen was "the migration failed" when in fact the migration had worked and
-- the test had worked and the two had destroyed each other.
--
-- So: the test is its own file, and it CATCHES its expected failure in a
-- PL/pgSQL EXCEPTION handler. The failure becomes a NOTICE that says PASS.
-- Nothing escapes, nothing aborts, and there is no migration here to lose.
--
-- RUN ORDER: sql/rt_stops_license_hash_composite_fk.sql FIRST, then this.
--
-- ── WHAT IT DOES IF YOU RUN IT TWICE ───────────────────────────────────────
-- EXACTLY THE SAME THING, and leaves the database exactly as it found it.
-- Three reasons, because "idempotent" on a file that writes needs more than a
-- word. (1) Section 2 begins by deleting any `zz-fk-probe` route left by a
-- previous run, so a half-finished earlier attempt cannot collide with
-- rt_routes' `unique (license_hash, app_id, assignee_id, route_date)`.
-- (2) The whole body is ONE `do $$ ... $$` statement, which is atomic: if any
-- path raises, the fixture route rolls back with it. (3) The success path
-- deletes the fixture itself, and the delete cascades to its stops.
--
-- ── RESIDUE, STATED RATHER THAN CLAIMED ABSENT ─────────────────────────────
-- The licence hash this uses is 'zz-fk-probe-route-hash', which is NOT
-- sha256 of anything, so it can never collide with a real tenant even if a
-- rollback were somehow missed. If a row IS ever left behind, section 3's
-- read finds it and this removes it:
--     delete from public.rt_routes where app_id = 'zz-fk-probe';
-- That cascades to its stops. Section 3 is the check, not an assumption.
--
-- ── WHAT THIS CANNOT TELL YOU ──────────────────────────────────────────────
-- It proves the constraint refuses a stop whose `license_hash` disagrees with
-- its route's, and accepts one that agrees. It says NOTHING about whether the
-- unlanded handler sends the right value -- b24's deciding question, which is
-- cody's -- and nothing about rows that already existed before the constraint
-- landed. The migration file's section 1 answers that one.


-- ════════════════════════════════════════════════════════════════════════════
-- 1. PRECONDITION. READ-ONLY. MUST RETURN ONE ROW.
--
--    If this returns NOTHING, the constraint is not applied and section 2
--    would report a FAIL that is really a COULD-NOT-RUN. Section 2 checks this
--    itself and refuses with that wording rather than blaming the constraint;
--    this query is so you can see it before you start.
-- ════════════════════════════════════════════════════════════════════════════
select
  c.conname,
  c.convalidated,
  pg_get_constraintdef(c.oid) as definition
from pg_constraint c
where c.conrelid = 'public.rt_stops'::regclass
  and c.conname = 'rtstops_license_matches_route';


-- ════════════════════════════════════════════════════════════════════════════
-- 2. THE PROBE. One atomic statement. Reads its own verdicts out as NOTICEs.
--
--    READ THE "NOTICE" LINES IN THE OUTPUT PANEL -- that is where the result
--    is. A clean run with no error raised and no NOTICE visible means the
--    notices were suppressed by the client, NOT that the probe passed; set
--    `client_min_messages = notice` and run it again.
--
--    THREE OUTCOMES AND EACH IS DISTINCT, which is the whole point:
--      * every NOTICE says PASS            -> the constraint fires correctly
--      * an exception naming COULD NOT RUN -> the constraint is absent; run
--                                             the migration file first
--      * an exception naming FAIL          -> the constraint exists and did
--                                             NOT refuse the bad write, or
--                                             refused the good one
--    In all three the database is left as it was found.
-- ════════════════════════════════════════════════════════════════════════════
do $$
declare
  v_route   uuid;
  v_hash    text := 'zz-fk-probe-route-hash';
  v_present boolean;
  v_left    integer;
begin
  -- ── 2.0 The constraint has to EXIST before its behaviour can be tested.
  -- COULD NOT RUN IS A THIRD STATE and is never folded into a FAIL: a missing
  -- constraint is a fact about the migration, not about the constraint.
  select exists (
    select 1 from pg_constraint
    where conrelid = 'public.rt_stops'::regclass
      and conname = 'rtstops_license_matches_route'
  ) into v_present;
  if not v_present then
    raise exception
      'COULD NOT RUN: rtstops_license_matches_route does not exist on '
      'public.rt_stops, so nothing was tested. This is NOT a failure of the '
      'constraint. Run sql/rt_stops_license_hash_composite_fk.sql first, '
      'confirm its section 3 returns TWO rows, then re-run this file.';
  end if;

  -- ── 2.1 Clear any fixture a previous half-run left, so this file cannot
  -- collide with itself on rt_routes' unique(license_hash, app_id,
  -- assignee_id, route_date). Scoped to the probe's own app_id and nothing
  -- else; cascades to its stops.
  delete from public.rt_routes where app_id = 'zz-fk-probe';

  -- ── 2.2 The fixture. A route under a hash that is not sha256 of anything.
  insert into public.rt_routes (license_hash, app_id, assignee_id, route_date)
  values (v_hash, 'zz-fk-probe', 'zz-fk-probe', date '2026-01-01')
  returning id into v_route;
  raise notice 'fixture route % created under %', v_route, v_hash;

  -- ── 2.3 NEGATIVE CONTROL. This insert MUST be refused. The expected
  -- failure is CAUGHT here rather than allowed to escape -- that escape is
  -- what destroyed the migration on 2026-10-20.
  begin
    insert into public.rt_stops (route_id, license_hash, seq, address)
    values (v_route, 'zz-fk-probe-SOMEONE-ELSES-HASH', 1, '1 Probe Street');
    -- Reached ONLY if the bad insert SUCCEEDED, which is the defect.
    raise exception
      'FAIL (negative control): a stop whose license_hash disagrees with its '
      'route was ACCEPTED. rtstops_license_matches_route exists and is not '
      'refusing. A stop under licence A on a route of licence B is visible in '
      'A''s scope -- the exact cross-tenant read b24 FINDING 1 names.';
  exception
    when foreign_key_violation then
      raise notice
        'PASS (negative control): a mismatched license_hash was REFUSED by '
        'rtstops_license_matches_route.';
  end;

  -- ── 2.4 POSITIVE CONTROL. A constraint that refuses EVERYTHING is not a
  -- tenancy guard, it is an outage -- and from a single failed insert the two
  -- look identical. The hash comes from the route row, which is also the
  -- shape b24 says the handler should use.
  insert into public.rt_stops (route_id, license_hash, seq, address)
  select r.id, r.license_hash, 1, '1 Probe Street'
  from public.rt_routes r where r.id = v_route;
  raise notice
    'PASS (positive control): a stop whose license_hash matches its route was '
    'ACCEPTED, so the refusal above is selective and not an outage.';

  -- ── 2.5 Clean up. The route delete cascades to the stop.
  delete from public.rt_routes where id = v_route;
  select count(*) into v_left from public.rt_routes where app_id = 'zz-fk-probe';
  if v_left <> 0 then
    raise exception
      'FAIL (teardown): % zz-fk-probe route(s) survived the delete. The probe '
      'passed and left residue, which is not a clean run.', v_left;
  end if;
  raise notice 'teardown clean: 0 zz-fk-probe routes remain.';
  raise notice 'PROBE RESULT: PASS -- negative refused, positive accepted, no residue.';
end
$$;


-- ════════════════════════════════════════════════════════════════════════════
-- 3. THE VERIFICATION QUERY. READ-ONLY. MUST RETURN 0 AND 0.
--
--    `routes_left` and `stops_left` are the residue check, read AFTER the
--    probe rather than asserted by it -- a teardown that reports success is a
--    reply, not a state. Anything other than 0 and 0 means a run was
--    interrupted between 2.2 and 2.5; remove it with
--    `delete from public.rt_routes where app_id = 'zz-fk-probe';`
-- ════════════════════════════════════════════════════════════════════════════
select
  (select count(*) from public.rt_routes where app_id = 'zz-fk-probe') as routes_left,
  (select count(*) from public.rt_stops s
     join public.rt_routes r on r.id = s.route_id
    where r.app_id = 'zz-fk-probe')                                    as stops_left;
