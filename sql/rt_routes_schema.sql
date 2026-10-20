-- sql/rt_routes_schema.sql
-- The shared routing primitive — Supabase schema for `rt_routes` + `rt_stops`.
--
-- ── THIS HAS BEEN RUN. 2026-10-19, by Michael, in the Supabase SQL editor ───
-- IT IS NO LONGER A PRE-FLIGHT SCRIPT, AND THAT CHANGES WHAT AN EDIT TO THIS
-- FILE MEANS. The tables exist. `create table if not exists` makes a re-run a
-- no-op, so FROM NOW ON editing a column, a check or a key HERE CHANGES
-- NOTHING IN THE DATABASE -- it only changes what a reader believes is there.
-- Any further change needs an `ALTER TABLE` in its own `sql/` file, applied
-- separately, and then reflected here. A schema file that silently stops being
-- the source of truth is the staleness class this platform keeps paying for.
--
-- ── CORRECTED 2026-10-20 (cc b28). THIS FILE WAS WRONG FOR A DAY. ──────────
-- It said: "`constraint rtroutes_saved_sane` was REMOVED before the run,
-- deliberately", recorded on 2026-10-19 (fourth b38) as a reconciliation to
-- what Michael actually ran. **IT WAS NOT REMOVED.** It was live on the
-- database the whole time -- read out of the 2026-10-20 07:55:45 capture in
-- `db/schema_snapshot.json`, where `_constraints.rt_routes` carries four
-- entries and `rtroutes_saved_sane` is one of them.
--
-- THE COST OF THAT SENTENCE, because this is not a documentation nit. The
-- paragraph on `saved_seconds` below states what the constraint WOULD do:
-- "Postgres would have rejected the ENTIRE upsert and the route write would
-- have failed." The constraint was in place, so that was not a hypothetical --
-- the first negative saving to reach the live database would have failed the
-- whole upsert, while this file told every reader it could not happen.
-- Nobody re-checks a schema file after reading a paragraph that confident.
--
-- RESOLVED BY DROPPING IT, which is Michael's decision of 2026-10-20:
-- `api/_lib/routes.js` stays un-clamped and the constraint goes.
-- `sql/rt_routes_drop_saved_sane.sql` is the migration. The code was right and
-- the database was wrong.
--
-- THE WINDOW WAS A DAY, NOT HOURS, and the lesson is about how it closed: not
-- by anybody re-reading this file, but because an unrelated push gate demanded
-- a fresh live capture and the capture disagreed with the prose. A reconciled
-- claim is only as good as the read behind it -- b38's read was of what it
-- believed had been run, and this one was of the database.
--
-- Scope and the reasoning behind every column:
-- docs/2026-10-19-fourth-b33-routing-primitive-scope.md.
--
-- WHY THIS IS NOT PER-APP. StoneDesk, SAIRNgrounds, SAIRNscape, SAIRNroofing
-- and SAIRNmechanical all order a day's stops for one person. Five copies of
-- that would be five places to fix the same bug, which is why
-- api/_lib/routes.js is one module and these are one pair of tables. `app_id`
-- distinguishes the tenant's app, not the schema.
--
-- WHY `rt_` AND NOT `sd_`: the prefix on this platform marks the OWNING app,
-- and no app owns these. A `sd_` prefix would have made StoneDesk the owner of
-- a table SAIRNgrounds writes to, which is the naming the rest of the register
-- uses to decide who may change what.
--
-- KEYING: license_hash = sha256(license_key), the same key every other
-- server-side SAIRN table uses. `assignee_id` is the APP'S OWN employee or
-- crew identifier, carried verbatim and never re-keyed here — this module does
-- not own the roster and must not invent a second identity for a person who
-- already has one.
--
-- ── CRITICALITY, STATED HERE BECAUSE THE SCHEMA IS WHERE IT IS DECIDED ──────
-- Both rows are TIER A ON CONFIDENTIALITY. docs/CRITICALITY-TIERS.md carries
-- the row and the argument; the short form is that `rt_stops` joins a street
-- address to a NAMED assignee and a DATE, which is a record of where an
-- identifiable person was or will be at a known time. That is the same class
-- that took `grd_cart_orders` and `leg_processions` from B to A. It is not
-- incidental to the feature — an ordering with no addresses is not an
-- ordering — so it cannot be designed away, only protected.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy.
-- The application layer requires a LICENCE **and** A SESSION for every verb.
-- Not licence-only: a licence proves the shop, and an address list joined to a
-- named employee is not shop metadata. api/bridge.js's `push` was licence-only
-- for months while carrying expense invoices, and the comment at the top of
-- that file is the record of what that cost.

-- ── rt_routes: one planned run of stops, for one assignee, on one date ──────
create table if not exists public.rt_routes (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null,
  assignee_id   text not null,
  route_date    date not null,
  status        text not null default 'planned'
                  check (status in ('planned','active','closed')),

  -- NULL MEANS NEVER OPTIMISED. Not 0, not now(). A route that has only ever
  -- been hand-ordered must be able to say so, and `source` says which.
  optimized_at  timestamptz,

  -- NULL MEANS NOT COMPUTED, AND THAT IS THE POINT OF THE COLUMN.
  -- The 2026-06-18 implementation this design was recovered from floored its
  -- saving at `Math.max(0, ...)`, which renders "we could not tell" and "we
  -- saved nothing" as the same figure on screen. They are different facts.
  -- A NULL here MUST render as no claim at all, never as "saves ~0 min".
  saved_seconds integer,

  -- Which basis produced the CURRENT order. 'manual' = a human ordered it.
  -- 'drive-matrix' = a real drive-time matrix answered. 'great-circle' = a
  -- straight-line fallback, which is a legitimate second basis ONLY while it
  -- is labelled as one and never allowed to pass as drive time.
  source        text not null default 'manual'
                  check (source in ('manual','drive-matrix','great-circle')),

  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  -- One route per assignee per app per day. The upsert key.
  unique (license_hash, app_id, assignee_id, route_date),

  -- ── THERE IS NO NON-NEGATIVE CHECK ON `saved_seconds`, DELIBERATELY ──────
  -- CORRECTED 2026-10-20: these lines previously said the constraint "WAS
  -- REMOVED BEFORE THIS FILE WAS EVER RUN". That was false -- `constraint
  -- rtroutes_saved_sane check (saved_seconds is null or saved_seconds >= 0)`
  -- WAS LIVE ON THE DATABASE from the run on 2026-10-19 until
  -- `sql/rt_routes_drop_saved_sane.sql` removed it. Michael's decision of
  -- 2026-10-20: the module stays un-clamped and the constraint goes. The
  -- argument below is why, and it is unchanged -- it was correct all along
  -- about what the constraint would do and wrong only about whether it was
  -- there. It contradicted the module it exists to store for:
  -- api/_lib/routes.js returns a NEGATIVE saving UN-CLAMPED on purpose -- "a
  -- caller that stores a negative saving has learned something true" -- a test
  -- arm asserts it is negative, and all four wired consumers render it as
  -- "this order is about N min LONGER than the one you had". With the
  -- constraint in place Postgres rejects the ENTIRE upsert and the route write
  -- fails -- the user loses the ORDERING, not just the figure -- so the only
  -- way to satisfy it was to clamp in the module, which re-introduces the
  -- exact 2026-06-18 defect the `saved_seconds` comment above exists to
  -- prevent: "we could not tell" and "we saved nothing" rendering as the same
  -- figure.
  --
  -- A NEGATIVE SAVING IS A REAL MEASUREMENT, NOT BAD DATA. The three states
  -- this column must keep distinct are NULL (not computed), negative (the
  -- optimised order is worse than the human's, which happens and is worth
  -- knowing) and positive. Only NULL is special, and
  -- `rtroutes_saving_has_a_basis` below is the constraint that guards it.
  --
  -- Do not re-add a non-negative check. If a future reader believes one is
  -- needed, the thing to change is the module's contract first, and that
  -- contract is the reason this line is a comment instead of a constraint.

  -- A computed saving with no basis and no timestamp is a number from nowhere.
  constraint rtroutes_saving_has_a_basis
    check (saved_seconds is null
           or (optimized_at is not null and source <> 'manual'))
);
create index if not exists idx_rtroutes_license
  on public.rt_routes(license_hash, app_id, route_date);

-- ── rt_stops: one stop on that run. Address in, ORDER out ───────────────────
create table if not exists public.rt_stops (
  id            uuid primary key default gen_random_uuid(),
  route_id      uuid not null references public.rt_routes(id) on delete cascade,
  license_hash  text not null,

  -- 1-based position in the CURRENT order.
  seq           integer not null check (seq >= 1),

  -- The app's own job identifier, free-form and nullable. This module does not
  -- own the job and does not validate it.
  job_ref       text,

  address       text not null,

  -- NULL WHEN NOT GEOCODED. NEVER 0,0 — Null Island is a real failure mode and
  -- a stop at (0,0) is indistinguishable from a stop in the Gulf of Guinea.
  -- sairnsenior.html already has this instinct for its EVV clock-in: the
  -- coordinates are left null and the absence disclosed, never faked.
  lat           double precision check (lat is null or (lat between -90 and 90)),
  lng           double precision check (lng is null or (lng between -180 and 180)),

  -- Carried when the point came from a device fix, so a consumer that computes
  -- distance can honour the error band rather than discard it. SAIRNgrounds'
  -- gcdHaversineM() is the model: bands are ADDED, never averaged.
  accuracy_m    double precision check (accuracy_m is null or accuracy_m >= 0),

  status        text not null default 'pending'
                  check (status in ('pending','done','skipped')),

  -- TRUE = the optimiser must not move this stop. A real day has fixed
  -- appointments, and an optimiser that reorders a 9 AM commitment to save
  -- four minutes of driving is worse than no optimiser.
  locked        boolean not null default false,

  created_at    timestamptz not null default now(),

  unique (route_id, seq),
  -- lat and lng are meaningless alone; a stop has both or neither.
  constraint rtstops_coords_are_a_pair
    check ((lat is null) = (lng is null)),
  -- An accuracy with no fix to attach to is a number about nothing.
  constraint rtstops_accuracy_needs_a_fix
    check (accuracy_m is null or lat is not null),
  constraint rtstops_address_size
    check (char_length(address) between 1 and 500)
);
create index if not exists idx_rtstops_route on public.rt_stops(route_id, seq);
create index if not exists idx_rtstops_license on public.rt_stops(license_hash);

-- ── RLS ─────────────────────────────────────────────────────────────────────
alter table public.rt_routes enable row level security;
alter table public.rt_stops  enable row level security;

drop policy if exists "svc only rt_routes" on public.rt_routes;
create policy "svc only rt_routes" on public.rt_routes
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only rt_stops" on public.rt_stops;
create policy "svc only rt_stops" on public.rt_stops
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- ── GRANTS ──────────────────────────────────────────────────────────────────
-- NO `truncate`, NO `references`, NO `trigger`. Read docs/ and the
-- sairn-grant-sweep skill before widening this line; the platform-wide revoke
-- of 2026-08-24 took `delete` off 134 tables and this file is
-- `create table if not exists`, so a stray verb here would silently restore it
-- on the next re-run.
--
-- `delete` IS granted here and it is the only verb that needs an argument.
-- `upsert` replaces a route's stop set, which means removing the stops that
-- are no longer on it. The alternative — a soft-delete flag on every stop —
-- would make `seq` uniqueness unenforceable at the database, and `seq` is the
-- one thing this table exists to get right. The blast radius is bounded by the
-- `route_id` foreign key: a delete can only ever reach stops of one route of
-- one licence.
grant usage on schema public to service_role;
grant select, insert, update on public.rt_routes to service_role;
grant select, insert, update, delete on public.rt_stops to service_role;
