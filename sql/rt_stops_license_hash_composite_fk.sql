-- sql/rt_stops_license_hash_composite_fk.sql
-- Make `rt_stops.license_hash` STRUCTURALLY equal to its route's, instead of
-- equal by whoever writes the row remembering to make it so.
--
-- ── WHY THIS IS A MIGRATION AND NOT AN EDIT TO THE SCHEMA FILE ──────────────
-- `sql/rt_routes_schema.sql` HAS BEEN RUN -- 2026-10-19, by Michael, in the
-- Supabase SQL editor -- and its own header says what that changes: the tables
-- exist, `create table if not exists` makes a re-run a no-op, so editing a
-- constraint in that file CHANGES NOTHING IN THE DATABASE. It changes only
-- what a reader believes is there. An `alter table` in its own file, applied
-- separately, is the only thing that moves the real state.
--
-- ── THE DEFECT, from cc b24's Tier A review (docs/2026-10-19-cc-b24-notes.md,
-- ── FINDING 1, HIGH) ────────────────────────────────────────────────────────
-- `rt_stops` carries BOTH `license_hash text not null` AND
-- `route_id uuid references public.rt_routes(id)`. The tenancy key is stored
-- twice and NOTHING requires the two copies to agree -- no composite key, no
-- check, no trigger.
--
-- `idx_rtstops_license` exists precisely so a reader can scope by that column.
-- So a stop written with licence A's hash under a route belonging to licence B
-- IS VISIBLE IN A'S SCOPE WHILE BELONGING TO B'S ITINERARY. On a table that is
-- TIER A ON CONFIDENTIALITY because each row joins a NAMED assignee to a
-- STREET ADDRESS on a DATE -- a record of where an identifiable person was or
-- will be at a known time.
--
-- MEASURED, NOT INFERRED, and it is the reason this cannot wait for the
-- handler: `api/_lib/routes.js` never reads or writes `license_hash` at all --
-- the string does not appear in the file -- and neither wired consumer sends
-- one. The only thing that can get the column right is the handler, and
-- NOTHING ANYWHERE WOULD CATCH IT IF THE HANDLER GETS IT WRONG. A composite
-- foreign key makes the question unanswerable in the wrong direction: a stop
-- whose `license_hash` disagrees with its route's cannot be written at all,
-- whatever the handler intends.
--
-- ── WHAT THIS DOES NOT DO ───────────────────────────────────────────────────
-- It does not decide where the handler SHOULD get the value from. That is
-- cody's, and the deciding test was written down in b24 before it could be
-- run: does the handler derive `rt_stops.license_hash` from the ROUTE ROW it
-- is attaching to, or from the request? After this migration both answers
-- produce correct data when the request is honest, and only the first produces
-- a write at all when it is not. The FK is the floor, not the answer.
--
-- It does not drop the existing single-column `route_id` foreign key. See
-- section 5 for why that is a decision rather than an omission.
--
-- It does not touch grants, RLS, or any other table.
--
-- ── RUN IT IN ORDER AND READ EACH SECTION'S OUTPUT BEFORE THE NEXT ──────────
-- Sections 1 and 2 are READS and change nothing. Section 1 is the one that
-- decides whether section 3 can succeed, and it is first ON PURPOSE: a
-- migration whose first check is at the end tells you it failed only after it
-- has already half-run.


-- ════════════════════════════════════════════════════════════════════════════
-- 1. PRE-FLIGHT: ARE THERE ALREADY ROWS THAT VIOLATE THE INVARIANT?
--    THIS MUST RETURN 0. If it does not, STOP -- section 3 will fail, and the
--    rows it names are real cross-tenant stops that need a decision, not a
--    constraint. Do not "fix" them by copying the route's hash over the top:
--    a stop under the wrong route is as likely to be the ROUTE that is wrong,
--    and overwriting the evidence is how that becomes unanswerable.
-- ════════════════════════════════════════════════════════════════════════════
select
  count(*) as mismatched_stops
from public.rt_stops s
join public.rt_routes r on r.id = s.route_id
where s.license_hash is distinct from r.license_hash;

-- And the rows themselves, if the count above is not 0. Bounded at 50: a
-- larger number is a systemic write bug and the first 50 say so just as well.
select
  s.id            as stop_id,
  s.route_id,
  s.license_hash  as stop_license_hash,
  r.license_hash  as route_license_hash,
  r.app_id,
  r.route_date,
  s.seq
from public.rt_stops s
join public.rt_routes r on r.id = s.route_id
where s.license_hash is distinct from r.license_hash
order by s.route_id, s.seq
limit 50;

-- A STOP WHOSE ROUTE DOES NOT EXIST would not appear above, because the join
-- drops it -- and the existing `route_id` FK already makes that impossible.
-- Counted anyway, because "the join returned nothing" and "there is nothing
-- wrong" are the same screen and different facts.
select count(*) as orphaned_stops
from public.rt_stops s
where not exists (select 1 from public.rt_routes r where r.id = s.route_id);


-- ════════════════════════════════════════════════════════════════════════════
-- 2. PRE-FLIGHT: WHAT CONSTRAINTS EXIST NOW?
--    Read this before and after. Section 4 is the same query, and a migration
--    that reports its own success without a before-picture is reporting a
--    state, not a change.
-- ════════════════════════════════════════════════════════════════════════════
select
  c.conname,
  c.contype,
  c.convalidated,
  pg_get_constraintdef(c.oid) as definition
from pg_constraint c
where c.conrelid in ('public.rt_stops'::regclass, 'public.rt_routes'::regclass)
  and c.contype in ('f', 'u', 'p')
order by c.conrelid::regclass::text, c.conname;


-- ════════════════════════════════════════════════════════════════════════════
-- 3. THE PARENT KEY THE FOREIGN KEY NEEDS.
--
--    `rt_routes.id` is already the primary key, so `unique (id, license_hash)`
--    adds NO uniqueness that was not already guaranteed -- it is logically
--    redundant and it is REQUIRED anyway: Postgres will only let a foreign key
--    reference a column list covered by a unique constraint or unique index,
--    and the PK on `id` alone does not cover the pair.
--
--    Said out loud because a reader who sees a redundant unique constraint and
--    "tidies it up" silently breaks the foreign key below, and the error they
--    get back will be about a dependency rather than about tenancy.
-- ════════════════════════════════════════════════════════════════════════════
alter table public.rt_routes
  add constraint rtroutes_id_license_uniq unique (id, license_hash);


-- ════════════════════════════════════════════════════════════════════════════
-- 4. THE COMPOSITE FOREIGN KEY -- the whole point of this file.
--
--    VALIDATED, not `not valid`. `not valid` would let this land over existing
--    mismatched rows and enforce the invariant only for future writes, which
--    is the right tool when a table is too large to scan and the backlog is
--    known. Here the table is days old, section 1 establishes the backlog is
--    EMPTY, and a half-enforced tenancy constraint on a Tier A confidentiality
--    table is exactly the "it passed" that is not a pass. If section 1 was not
--    0, THIS STATEMENT FAILING IS THE CORRECT OUTCOME -- go read those rows.
--
--    `on delete cascade` matches the existing single-column FK, so deleting a
--    route still takes its stops with it and this migration does not quietly
--    change deletion behaviour.
--
--    NO `on update` clause, so the default NO ACTION applies and an UPDATE to
--    `rt_routes.license_hash` with stops attached is REFUSED. That is
--    deliberate: a route's tenancy key changing is not an operation this
--    schema supports -- a different licence is a different row, the hash being
--    sha256(license_key) -- and `on update cascade` would silently relabel a
--    named person's address history as belonging to another tenant.
-- ════════════════════════════════════════════════════════════════════════════
alter table public.rt_stops
  add constraint rtstops_license_matches_route
  foreign key (route_id, license_hash)
  references public.rt_routes (id, license_hash)
  on delete cascade;


-- ════════════════════════════════════════════════════════════════════════════
-- 5. READ IT BACK. Same query as section 2.
--
--    EXPECTED DELTA, and nothing else:
--      + rt_routes : rtroutes_id_license_uniq        UNIQUE (id, license_hash)
--      + rt_stops  : rtstops_license_matches_route   FOREIGN KEY
--                      (route_id, license_hash) REFERENCES rt_routes(id,
--                      license_hash) ON DELETE CASCADE
--    and `convalidated` TRUE on both. A present-but-unvalidated constraint
--    reads as done in a constraint list and enforces nothing about the rows
--    already there.
--
--    THE SINGLE-COLUMN `route_id` FOREIGN KEY IS STILL THERE AND IS LEFT
--    ALONE ON PURPOSE. The composite key subsumes it -- anything the
--    single-column key refuses, the composite refuses too -- so dropping it
--    would change no behaviour, and keeping it costs one redundant cascade
--    trigger on a route delete. Against that: its name is auto-generated, so
--    dropping it means introspecting `pg_constraint` to find the name, and a
--    DROP driven by a lookup that matched the wrong row leaves the table with
--    no route key at all. `sql/rt_routes_schema.sql` also documents that key
--    in words. One redundant constraint is cheaper than that risk, and this
--    paragraph is here so the redundancy reads as a choice.
-- ════════════════════════════════════════════════════════════════════════════
select
  c.conname,
  c.contype,
  c.convalidated,
  pg_get_constraintdef(c.oid) as definition
from pg_constraint c
where c.conrelid in ('public.rt_stops'::regclass, 'public.rt_routes'::regclass)
  and c.contype in ('f', 'u', 'p')
order by c.conrelid::regclass::text, c.conname;


-- ════════════════════════════════════════════════════════════════════════════
-- 6. PROVE IT REFUSES. A constraint that is present and does not fire is the
--    whole class this platform keeps paying for, and `convalidated = true`
--    above says the EXISTING rows were checked -- not that a NEW bad write is
--    stopped. These two statements are the negative control and the positive
--    control, in that order, and both roll back.
--
--    Run them as one transaction. The ROLLBACK is not optional: these write to
--    a Tier A table.
-- ════════════════════════════════════════════════════════════════════════════
begin;

  -- A route to hang the test on, under a hash that is obviously not a licence.
  insert into public.rt_routes (license_hash, app_id, assignee_id, route_date)
  values ('zz-fk-probe-route-hash', 'zz-fk-probe', 'zz-fk-probe', date '2026-01-01')
  returning id, license_hash;

  -- NEGATIVE CONTROL -- this MUST FAIL with
  -- "insert or update on table rt_stops violates foreign key constraint
  --  rtstops_license_matches_route". If it SUCCEEDS, the constraint is not
  --  doing the thing it was added for and section 4 reported a state rather
  --  than an effect.
  insert into public.rt_stops (route_id, license_hash, seq, address)
  select id, 'zz-fk-probe-SOMEONE-ELSES-HASH', 1, '1 Probe Street'
  from public.rt_routes
  where license_hash = 'zz-fk-probe-route-hash';

  -- POSITIVE CONTROL -- run this INSTEAD, in a second transaction, after the
  -- negative control has failed and aborted this one. It MUST SUCCEED: a
  -- constraint that refuses everything is not a tenancy guard, it is an
  -- outage, and the two look identical from a failed insert alone.
  --
  --   begin;
  --   insert into public.rt_routes (license_hash, app_id, assignee_id, route_date)
  --   values ('zz-fk-probe-route-hash', 'zz-fk-probe', 'zz-fk-probe', date '2026-01-01');
  --   insert into public.rt_stops (route_id, license_hash, seq, address)
  --   select id, license_hash, 1, '1 Probe Street'
  --   from public.rt_routes where license_hash = 'zz-fk-probe-route-hash';
  --   rollback;

rollback;

-- RESIDUE: none. Both controls are inside transactions that roll back, and
-- the licence hash they use -- 'zz-fk-probe-route-hash' -- is not sha256 of
-- anything, so it can never collide with a real tenant even if a rollback is
-- missed. If a `zz-fk-probe` row IS left behind, it is removable by
-- `delete from public.rt_routes where app_id = 'zz-fk-probe';` which cascades
-- to its stops. Confirm with the section 1 counts afterwards.


-- ════════════════════════════════════════════════════════════════════════════
-- 7. REVERSAL, if this has to come out.
--    In this order: the child key first, then the parent key it depends on.
-- ════════════════════════════════════════════════════════════════════════════
-- alter table public.rt_stops  drop constraint rtstops_license_matches_route;
-- alter table public.rt_routes drop constraint rtroutes_id_license_uniq;


-- ════════════════════════════════════════════════════════════════════════════
-- 8. OWED AFTER THIS RUNS, and it is owed to whoever holds the schema file.
--    `sql/rt_routes_schema.sql` is fourth's and its own header states the
--    rule: an `alter` applied separately must then be REFLECTED there. Until
--    that happens the schema file describes a table without this constraint,
--    which is the staleness class that header exists to name.
--    It is NOT reflected pre-emptively: writing it into the schema file before
--    Michael has run this would make that file claim a constraint the database
--    does not have, which is the same defect pointing the other way.
-- ════════════════════════════════════════════════════════════════════════════
