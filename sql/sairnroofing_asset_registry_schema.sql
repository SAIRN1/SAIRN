-- sql/sairnroofing_asset_registry_schema.sql
-- SAIRNroofing gap B1 -- the commercial roof asset registry.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHY THIS IS NOT A BIGGER rf_jobs ═══════════════════════════════════════
-- The 2026-08-26 competitive-gap audit calls B1 "the single largest Tier B
-- structural gap" and gives the reason: the shape is MANY ROOFS PER CUSTOMER
-- and one contractor servicing hundreds of buildings, while rf_jobs is one job
-- at a time. An entire product category exists for it (Garland RAMP, Tecta
-- TectaTracker, Nations Roof AM, RoofManager, Roof Hoss RoofTrack) and it is
-- absent from every Tier A product surveyed. The audit's B2 is the commercial
-- half: those tools are all commercial-owner / large-contractor products, so
-- there is no starter version a growing roofer can adopt when it wins its
-- first maintenance-contract commercial customer.
--
-- Bolting a portfolio onto rf_jobs would have made every job row pretend to be
-- a building. Two tables instead, one dependency, no change to rf_jobs.
--
-- ══ NO SERVICE LIFE IS SEEDED, AND THERE IS NO DEFAULT ═════════════════════
-- "TPO lasts 20 years" is real industry data and it is also wrong for a
-- specific roof at a specific thickness in a specific climate. A capital plan
-- built on a number nobody entered is a budget handed to a building owner on
-- the strength of a blog post. Same 2026-08-25 decision as
-- sairnroofing_programs_schema.sql and sairnroofing_warranties_schema.sql:
-- expected_life_years is NULLABLE with no default, it carries a life_source,
-- and api/_lib/roofing-asset-registry.js refuses to produce a replacement year
-- without both -- reporting 'no_service_life_recorded' instead of guessing.
--
-- ══ CONDITION IS STORED BESIDE THE DATES, NOT FOLDED INTO THEM ═════════════
-- Every commercial product in this category quotes one condition-adjusted
-- "remaining service life". That adjustment is a MODEL relating a walk-over
-- score to years, this platform does not have one, and inventing one here
-- would put a fabricated curve underneath somebody's capital budget. The score
-- and its date are stored; the engine reports them beside the calendar life and
-- flags where the two DISAGREE, which is the actionable fact.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- tools/sairn_sql_preflight.py can only compare CHECK constraints where both
-- sides state a numeric bound. Plain octet_length(...) <= N stays inside what
-- it can verify. See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. Buildings. The level rf_jobs does not have.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_buildings (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  building_id   text not null,                    -- client-generated
  name          text not null,
  customer      text,
  address       text,
  location_id   text,                             -- which branch services it, same free reference as rf_jobs
  active        boolean not null default true,
  notes         text,
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  updated_by    text,
  unique (license_hash, building_id),
  constraint rfbld_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfbld_license on public.rf_buildings(license_hash);

-- ---------------------------------------------------------------------------
-- 2. Roof sections. Many per building -- this is the whole point.
-- ---------------------------------------------------------------------------
-- `building_id` and `warranty_id` are plain text references and NOT foreign
-- keys, matching how every other rf_ table references its siblings here. The
-- cost is stated rather than hidden: nothing at the database level stops a
-- section naming a building or a warranty that does not exist, and the engine
-- is what catches it -- which it does, as 'warranty_not_found', never as
-- 'covered'. A wrong match here would tell a building owner a roof is under
-- warranty when it is not.
create table if not exists public.rf_roof_sections (
  id                  uuid primary key default gen_random_uuid(),
  license_hash        text not null,
  section_id          text not null,              -- client-generated
  building_id         text not null,
  name                text not null,              -- 'Main roof', 'North wing'
  system_type         text,                       -- the contractor's own vocabulary, not an enum
  area_sqft           numeric(12,2),
  installed_on        date,
  -- NULLABLE, NO DEFAULT. See the header: a default here would be this file
  -- inventing the number a capital plan is spent against.
  expected_life_years integer,
  life_source         text,                       -- where that figure came from; the engine requires it
  condition_score     integer,                    -- 1..5, 1 worst
  condition_on        date,
  warranty_id         text,                       -- explicit link into rf_job_warranties, never inferred
  status              text not null default 'active',
  notes               text,
  data                jsonb not null default '{}'::jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  updated_by          text,
  unique (license_hash, section_id),
  constraint rfsec_status_check check (status in ('active','replaced','removed')),
  constraint rfsec_life_sane check (expected_life_years is null or (expected_life_years > 0 and expected_life_years <= 100)),
  constraint rfsec_condition_sane check (condition_score is null or (condition_score >= 1 and condition_score <= 5)),
  constraint rfsec_area_not_negative check (area_sqft is null or area_sqft >= 0),
  constraint rfsec_data_size check (octet_length(data::text) <= 65536),
  constraint rfsec_life_source_size check (life_source is null or octet_length(life_source) <= 2048)
);

create index if not exists idx_rfsec_license on public.rf_roof_sections(license_hash);
create index if not exists idx_rfsec_building on public.rf_roof_sections(license_hash, building_id);
-- The query this table exists to answer: what is coming due across the whole
-- portfolio, in what year.
create index if not exists idx_rfsec_life on public.rf_roof_sections(license_hash, status, installed_on);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants.
-- ---------------------------------------------------------------------------
-- Service-role only, matching every other rf_ table. SELECT/INSERT/UPDATE and
-- no DELETE: a section that is torn off is marked 'replaced', which the next
-- capital plan needs to see, not deleted.
alter table public.rf_buildings enable row level security;
drop policy if exists "svc only rf_buildings" on public.rf_buildings;
create policy "svc only rf_buildings" on public.rf_buildings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_buildings from service_role;
grant select, insert, update on public.rf_buildings to service_role;
revoke all on public.rf_buildings from anon, authenticated;

alter table public.rf_roof_sections enable row level security;
drop policy if exists "svc only rf_roof_sections" on public.rf_roof_sections;
create policy "svc only rf_roof_sections" on public.rf_roof_sections
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_roof_sections from service_role;
grant select, insert, update on public.rf_roof_sections to service_role;
revoke all on public.rf_roof_sections from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_buildings;      -- expect 0, nothing is seeded
--   select count(*) from rf_roof_sections;  -- expect 0
--
-- Grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_buildings','rf_roof_sections')
--    group by table_name;
--
-- Confirm the condition-range constraint bites (expect an ERROR, not a row):
--   insert into public.rf_roof_sections
--     (license_hash, section_id, building_id, name, condition_score)
--   values ('test', 'RFSEC-CHECK', 'B', 'N', 9);
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables. Until that happens the preflight reports them as undeclared
-- against live, which is correct and not a failure.
