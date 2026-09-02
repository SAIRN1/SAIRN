-- sql/sairnroofing_entities_schema.sql
-- SAIRNroofing gap B5 -- multi-entity financial consolidation.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THIS EXISTS, AND WHY rf_locations DID NOT COVER IT ═════════════════
-- The 2026-08-26 competitive-gap audit's Tier-B item B5, whose own note is the
-- diagnosis: "rf_locations is attribution-only by design. Branch != entity."
-- A PE rollup owns several LEGAL ENTITIES, each operating one or more
-- BRANCHES. Roofing already had branches and nothing above them, so there was
-- no way to total the book by the thing that files a tax return.
--
-- ══ entity_id GOES ON THE LOCATION AND NOWHERE ELSE ════════════════════════
-- THE decision, and the reason there is no ALTER on rf_jobs, rf_invoices,
-- rf_draws or rf_schedule in this file.
--
-- Attribution is DERIVED ON READ by joining a financial row to its location
-- and then to that location's CURRENT entity. So moving a branch between
-- entities moves its ENTIRE HISTORY -- which is what a divestiture or an
-- internal reorganisation actually means.
--
-- Stamping entity_id on each financial row at write would freeze every row to
-- whichever entity owned the branch that day. A branch sold in March would
-- leave last year's revenue permanently attributed to a company that no longer
-- operates it, and the only remedy would be a backfill migration across every
-- financial table. That is the mistake this file exists to not make.
--
-- The invariant, checkable rather than asserted: reassigning a location
-- changes the BUCKETS and must NOT change the GRAND TOTAL.
-- api/_lib/roofing-consolidation.js returns `input_total`, `grand_total` and
-- `reconciles` on every call so a caller or a test can verify it.
--
-- ══ NULL entity_id IS A REAL STATE, NOT A DEFAULT TO PAPER OVER ════════════
-- A location with no entity lands in an UNASSIGNED bucket that is shown,
-- totalled and kept OUT of the entity list, so nobody can add up the entities
-- and believe they have the whole book. Defaulting new branches into the first
-- entity would silently attribute revenue to a company that may not own it.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. The entities.
-- ---------------------------------------------------------------------------
-- `tax_id` is deliberately free text and deliberately optional. It is a label
-- for the operator's own reference; nothing in this platform validates it,
-- looks it up, or files anything with it, and a schema that implied otherwise
-- would be claiming a capability that does not exist.
create table if not exists public.rf_entities (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  entity_id     text not null,                     -- client-generated (ENT-<slug>)
  legal_name    text not null,
  trading_name  text,
  tax_id        text,                              -- operator's own reference; never validated here
  jurisdiction  text,
  active        boolean not null default true,     -- deactivate, never delete: history points at it
  notes         text,
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  updated_by    text,
  unique (license_hash, entity_id),
  constraint rfent_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfent_license on public.rf_entities(license_hash);

-- ---------------------------------------------------------------------------
-- 2. The ONE column this feature adds to existing data.
-- ---------------------------------------------------------------------------
-- NULLABLE with NO DEFAULT and NO foreign key.
--
-- Nullable and undefaulted because a branch nobody has assigned must read as
-- unassigned, not as belonging to whichever entity happened to be created
-- first. Compare rf_jobs.location_id, which IS defaulted ('LOC-DEFAULT') --
-- correct there, because every job genuinely happens somewhere and the default
-- is the implicit single branch. There is no implicit single ENTITY: a shop
-- that has never entered one has zero, not one.
--
-- No foreign key, matching how every other rf_ table references its siblings.
-- The cost is stated rather than hidden: nothing at the database level stops a
-- location naming an entity that does not exist, and the engine is what
-- catches it -- which it does, by flagging the dangling reference and putting
-- the branch in Unassigned rather than silently inventing an entity for it.
alter table public.rf_locations
  add column if not exists entity_id text;

create index if not exists idx_rfloc_entity
  on public.rf_locations(license_hash, entity_id);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
alter table public.rf_entities enable row level security;
drop policy if exists "svc only rf_entities" on public.rf_entities;
create policy "svc only rf_entities" on public.rf_entities
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_entities from service_role;
grant select, insert, update on public.rf_entities to service_role;
revoke all on public.rf_entities from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_entities;   -- expect 0, nothing is seeded
--
-- The new column exists and is NULL everywhere (every branch unassigned):
--   select entity_id, count(*) from rf_locations group by entity_id;
--
-- Grants (expect INSERT,SELECT,UPDATE; no DELETE, no TRUNCATE):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'rf_entities';
--
-- THE INVARIANT, checked against live data rather than trusted. Note the
-- consolidated total before and after reassigning one branch; the per-entity
-- figures must move and this number must not:
--   select sum((data->>'total')::numeric) from rf_invoices where license_hash = '<hash>';
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- rf_entities and rf_locations' new column.
