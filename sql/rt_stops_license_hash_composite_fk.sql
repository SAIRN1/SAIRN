-- sql/rt_stops_license_hash_composite_fk.sql
--
-- CONCEPT: APPLY THE CONSTRAINT, AND NOTHING ELSE. The read that tells you
-- whether it CAN be applied comes first, and it only reads.
--
-- ── WHY THIS FILE WAS REWRITTEN, 2026-10-20 (cc b28) ────────────────────────
-- The previous version of this file put the ADD CONSTRAINT, a probe INSERT and
-- a negative control in one file. Michael ran it in the Supabase SQL editor.
-- The negative control's insert raised `rtstops_license_matches_route`
-- violated -- WHICH IS THE CONTROL WORKING -- on route f38eb356 with
-- 'zz-fk-probe-SOMEONE-ELSES-HASH'. But the editor runs a multi-statement
-- script as ONE TRANSACTION, so the raised error aborted the whole run and
-- rolled back the ADD CONSTRAINT with it. `pg_constraint` shows no
-- `rtstops_license_matches_route`. THE FK IS NOT APPLIED and b24 FINDING 1
-- (HIGH) is still open.
--
-- The defect was mine and it is a design defect, not a typo: A FILE THAT
-- DELIBERATELY RAISES AN ERROR CANNOT ALSO BE A FILE THAT APPLIES A CHANGE.
-- The test and the migration are now separate files --
-- `sql/rt_stops_fk_probe.sql` is the control, and it catches its own expected
-- failure instead of letting it escape.
--
-- RUN ORDER: this file, then sql/rt_stops_fk_probe.sql.
--
-- ── WHAT IT DOES IF YOU RUN IT TWICE ───────────────────────────────────────
-- NOTHING, and it says so. Postgres has no `ADD CONSTRAINT IF NOT EXISTS`, so
-- each ADD is wrapped in a DO block that catches `duplicate_object` and
-- RAISES A NOTICE instead. A second run prints "already present" twice and
-- changes nothing. Section 1's reads are read-only on every run.
--
-- ── THE DEFECT THIS CLOSES: cc b24 FINDING 1, HIGH ─────────────────────────
-- `rt_stops` carries BOTH `license_hash text not null` AND
-- `route_id uuid references public.rt_routes(id)`. The tenancy key is stored
-- twice and NOTHING requires the two copies to agree -- no composite key, no
-- check, no trigger. `idx_rtstops_license` exists precisely so a reader can
-- scope by that column, so a stop written under licence A's hash on a route
-- belonging to licence B IS VISIBLE IN A'S SCOPE WHILE BELONGING TO B'S
-- ITINERARY -- on a table that is TIER A ON CONFIDENTIALITY because every row
-- joins a NAMED assignee to a STREET ADDRESS on a DATE.
--
-- MEASURED, and it is why this cannot wait for the handler:
-- `api/_lib/routes.js` never reads or writes `license_hash` at all -- the
-- string does not appear in the file -- and neither wired consumer sends one.
-- So only the handler can get the column right, and NOTHING ANYWHERE WOULD
-- CATCH IT IF THE HANDLER GOT IT WRONG. A composite foreign key makes the
-- question unanswerable in the wrong direction.
--
-- ── WHAT THIS FILE DOES NOT DO ─────────────────────────────────────────────
-- It does not decide where the handler SHOULD get the value from -- that is
-- cody's, and b24 wrote the deciding test down before it could be run: does
-- the handler derive `rt_stops.license_hash` from the ROUTE ROW it is
-- attaching to, or from the request? The FK is the floor, not the answer.
-- It does not test itself. It does not drop the existing single-column
-- `route_id` foreign key -- the composite subsumes it, so dropping it would
-- change no behaviour, and its name is auto-generated, which means a DROP
-- driven by an introspection lookup that matched the wrong row would leave the
-- table with no route key at all. One redundant constraint is cheaper.
-- It does not touch grants, RLS, or any other table.


-- ════════════════════════════════════════════════════════════════════════════
-- 1. READ FIRST. ALL THREE QUERIES ARE READ-ONLY AND CHANGE NOTHING.
--
--    1a MUST RETURN 0. If it does not, STOP -- section 2 will fail, and the
--    rows 1b lists are real cross-tenant stops that need a DECISION, not a
--    constraint. DO NOT "fix" them by copying the route's hash over the top:
--    a stop under the wrong route is as likely to be the ROUTE that is wrong,
--    and overwriting the evidence makes that unanswerable for ever. NOTHING
--    IN THIS FILE DELETES OR UPDATES A ROW.
-- ════════════════════════════════════════════════════════════════════════════

-- 1a. The count that decides whether section 2 can succeed.
select count(*) as mismatched_stops
from public.rt_stops s
join public.rt_routes r on r.id = s.route_id
where s.license_hash is distinct from r.license_hash;

-- 1b. The rows themselves, if 1a is not 0. Bounded at 50: a larger number is a
--     systemic write bug and the first 50 say so just as well.
select
  s.id            as stop_id,
  s.route_id,
  s.license_hash  as stop_license_hash,
  r.license_hash  as route_license_hash,
  r.app_id,
  r.route_date,
  s.seq,
  s.created_at
from public.rt_stops s
join public.rt_routes r on r.id = s.route_id
where s.license_hash is distinct from r.license_hash
order by s.route_id, s.seq
limit 50;

-- 1c. WHAT IS ALREADY THERE. Run this before AND after, because section 2's
--     notices tell you what it DID and this tells you what the database HAS.
--     The previous run of the old file rolled back, so expect NEITHER
--     constraint below to be present on a first successful run.
select
  c.conrelid::regclass::text as on_table,
  c.conname,
  c.contype,
  c.convalidated,
  pg_get_constraintdef(c.oid) as definition
from pg_constraint c
where c.conname in ('rtroutes_id_license_uniq', 'rtstops_license_matches_route')
order by on_table, c.conname;


-- ════════════════════════════════════════════════════════════════════════════
-- 2. APPLY IT. Two ADD CONSTRAINTs, and the first exists only to make the
--    second legal.
--
--    `rt_routes.id` is already the primary key, so `unique (id, license_hash)`
--    adds NO uniqueness that was not already guaranteed. It is logically
--    redundant AND REQUIRED: Postgres will only let a foreign key reference a
--    column list covered by a unique constraint or unique index, and the PK on
--    `id` alone does not cover the pair. Said out loud because a reader who
--    sees a redundant unique constraint and tidies it away silently breaks the
--    foreign key, and the error they get back will be about a dependency
--    rather than about tenancy.
--
--    VALIDATED, not `not valid`. `not valid` would let this land over existing
--    mismatched rows and enforce the invariant only for future writes -- the
--    right tool when a table is too large to scan and the backlog is known.
--    Here section 1a establishes the backlog is EMPTY, and a half-enforced
--    tenancy constraint on a Tier A confidentiality table is exactly the "it
--    passed" that is not a pass.
--
--    `on delete cascade` matches the existing single-column FK, so deleting a
--    route still takes its stops with it and this changes no deletion
--    behaviour.
--
--    NO `on update` clause, so the default NO ACTION applies and an UPDATE to
--    `rt_routes.license_hash` with stops attached is REFUSED. Deliberate: a
--    route's tenancy key changing is not an operation this schema supports --
--    the hash is sha256(license_key), so a different licence is a different
--    row -- and `on update cascade` would silently relabel a named person's
--    address history as belonging to another tenant.
-- ════════════════════════════════════════════════════════════════════════════

do $$
begin
  alter table public.rt_routes
    add constraint rtroutes_id_license_uniq unique (id, license_hash);
  raise notice 'ADDED rtroutes_id_license_uniq on rt_routes';
exception
  when duplicate_object or duplicate_table then
    raise notice 'rtroutes_id_license_uniq already present -- no change';
end
$$;

do $$
begin
  alter table public.rt_stops
    add constraint rtstops_license_matches_route
    foreign key (route_id, license_hash)
    references public.rt_routes (id, license_hash)
    on delete cascade;
  raise notice 'ADDED rtstops_license_matches_route on rt_stops';
exception
  when duplicate_object then
    raise notice 'rtstops_license_matches_route already present -- no change';
end
$$;


-- ════════════════════════════════════════════════════════════════════════════
-- 3. THE VERIFICATION QUERY. READ-ONLY.
--
--    EXPECTED: exactly TWO rows, both with convalidated = true.
--      rt_routes  rtroutes_id_license_uniq       u  UNIQUE (id, license_hash)
--      rt_stops   rtstops_license_matches_route  f  FOREIGN KEY (route_id,
--                   license_hash) REFERENCES rt_routes(id, license_hash)
--                   ON DELETE CASCADE
--
--    ONE ROW, OR TWO WITH convalidated = false, IS NOT A PASS. A
--    present-but-unvalidated constraint reads as done in a constraint list and
--    enforces nothing about the rows already there.
--
--    AND A CONSTRAINT THAT IS PRESENT IS NOT A CONSTRAINT THAT FIRES. This
--    query cannot tell you it refuses a bad write; `convalidated` is a
--    statement about the EXISTING rows. Run sql/rt_stops_fk_probe.sql next --
--    that is the only thing here that answers the question this constraint
--    was added for.
-- ════════════════════════════════════════════════════════════════════════════
select
  c.conrelid::regclass::text as on_table,
  c.conname,
  c.contype,
  c.convalidated,
  pg_get_constraintdef(c.oid) as definition
from pg_constraint c
where c.conname in ('rtroutes_id_license_uniq', 'rtstops_license_matches_route')
order by on_table, c.conname;


-- ════════════════════════════════════════════════════════════════════════════
-- 4. REVERSAL, if this has to come out. Child key first, then the parent key
--    it depends on. Not run by this file.
-- ════════════════════════════════════════════════════════════════════════════
-- alter table public.rt_stops  drop constraint if exists rtstops_license_matches_route;
-- alter table public.rt_routes drop constraint if exists rtroutes_id_license_uniq;


-- ════════════════════════════════════════════════════════════════════════════
-- 5. OWED AFTER THIS RUNS, and it is owed to whoever holds the schema file.
--    `sql/rt_routes_schema.sql` describes a pair of tables without this
--    constraint. Its own header states the rule: an `alter` applied separately
--    must then be REFLECTED there. NOT reflected pre-emptively -- writing it
--    in before this has run would make that file claim a constraint the
--    database does not have, which is the same defect the
--    `rtroutes_saved_sane` paragraph just cost us, pointing the other way.
-- ════════════════════════════════════════════════════════════════════════════
