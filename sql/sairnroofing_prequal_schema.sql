-- sql/sairnroofing_prequal_schema.sql
-- SAIRNroofing gap B7 -- the contractor's OWN prequalification packet and
-- bonding position.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHICH DIRECTION THIS FACES ═════════════════════════════════════════════
-- The audit's B7: prequalification and bonding, "a Tier-B-only category
-- (TradeTapp, Highwire, Constrafor) that exists because GCs and owners require
-- it of bonded subs. Absent."
--
-- Checked before building, because this is the third time a "new" build nearly
-- duplicated something already on the platform. SAIRNbuild HAS prequal_status,
-- financial_capacity, safety_record, references_checked, bonding_capacity and
-- current_backlog_pct -- but ON ITS SUBCONTRACTORS. SAIRNbuild is the general
-- contractor qualifying the trades it hires.
--
-- These tables face the other way. SAIRNroofing's customer IS the roofer, and
-- at Tier B the roofer is the SUB being qualified: what a GC asks THEM for.
-- Same vocabulary, opposite subject, nothing duplicated. Verified 2026-09-02:
-- sairnroofing.html had ZERO hits for bond, EMR, experience modification,
-- prequal or surety.
--
-- ══ NO EXPIRY WINDOW AND NO EMR THRESHOLD ARE SEEDED ═══════════════════════
-- A financial statement is "current" for as long as the GC asking for it says,
-- and that varies. An EMR of 0.87 is acceptable to one owner and not another;
-- "under 1.0" is each GC's own prequalification criterion and NOT a rule this
-- application may assert. So every document carries the expiry the contractor
-- entered, a document with none reads 'no_expiry_recorded' rather than being
-- assumed fine, and api/_lib/roofing-prequal.js carries EMR through UNJUDGED.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- See docs/2026-09-02-constraints-not-comparable.md.

-- ---------------------------------------------------------------------------
-- 1. The packet. One row per document a GC might ask for.
-- ---------------------------------------------------------------------------
-- `kind` is free text and NOT an enum, deliberately: every GC's form asks for
-- a slightly different set, and an enum here would mean a schema migration
-- every time a customer met a new one. The engine matches on whatever the
-- caller says was required, so the vocabulary is the contractor's.
--
-- `value` / `value_year` carry a numeric fact the document states -- an EMR
-- rate is the reason they exist. They are reported, never interpreted.
create table if not exists public.rf_prequal_documents (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  document_id   text not null,                  -- client-generated
  kind          text not null,                  -- emr_letter, financials, safety_program, references, bond_letter, w9, coi...
  issuer        text,
  effective_on  date,
  expires_on    date,                           -- nullable; absent reads 'no_expiry_recorded', never 'current'
  value         numeric(12,4),                  -- e.g. an EMR rate. NEVER judged by this platform.
  value_year    integer,
  reference     text,                           -- a file name, a portal reference, wherever the original lives
  source        text,                           -- who issued the figure; the engine flags a value without one
  notes         text,
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  updated_by    text,
  unique (license_hash, document_id),
  constraint rfpq_year_sane check (value_year is null or (value_year >= 1900 and value_year <= 2200)),
  constraint rfpq_source_size check (source is null or octet_length(source) <= 2048),
  constraint rfpq_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfpq_license on public.rf_prequal_documents(license_hash);
create index if not exists idx_rfpq_kind on public.rf_prequal_documents(license_hash, kind, expires_on);

-- ---------------------------------------------------------------------------
-- 2. Bonding. Kept as ROWS, not one editable record.
-- ---------------------------------------------------------------------------
-- A surety letter is reissued with new limits, and last year's letter is what
-- last year's bid was submitted under. Overwriting one row would erase the
-- record of what the contractor could bond when they signed something. So each
-- letter is its own row with its own effective and expiry dates, and the
-- engine is handed whichever one the caller considers in force.
--
-- committed_backlog is NOT a column. It is derived from real contract values
-- and what has been earned -- api/_lib/wip-accounting.js already computes
-- exactly that -- and storing it here would create a second figure that drifts
-- away from the WIP schedule the moment a draw is entered.
create table if not exists public.rf_bonding (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  bonding_id            text not null,           -- client-generated
  surety                text,
  agent                 text,
  single_project_limit  numeric(14,2),
  aggregate_limit       numeric(14,2),
  effective_on          date,
  expires_on            date,
  source                text,                    -- the surety letter or the agent who issued it
  notes                 text,
  data                  jsonb not null default '{}'::jsonb,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  updated_by            text,
  unique (license_hash, bonding_id),
  constraint rfbond_single_not_negative check (single_project_limit is null or single_project_limit >= 0),
  constraint rfbond_agg_not_negative check (aggregate_limit is null or aggregate_limit >= 0),
  constraint rfbond_source_size check (source is null or octet_length(source) <= 2048),
  constraint rfbond_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfbond_license on public.rf_bonding(license_hash, expires_on);

-- ---------------------------------------------------------------------------
-- 3. RLS and grants. Service-role only, SELECT/INSERT/UPDATE, no DELETE.
-- ---------------------------------------------------------------------------
-- No DELETE matters here for the same reason as the safety tables: a
-- prequalification packet and the bonding letters behind it are exactly what
-- gets asked for after something goes wrong.
alter table public.rf_prequal_documents enable row level security;
drop policy if exists "svc only rf_prequal_documents" on public.rf_prequal_documents;
create policy "svc only rf_prequal_documents" on public.rf_prequal_documents
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_prequal_documents from service_role;
grant select, insert, update on public.rf_prequal_documents to service_role;
revoke all on public.rf_prequal_documents from anon, authenticated;

alter table public.rf_bonding enable row level security;
drop policy if exists "svc only rf_bonding" on public.rf_bonding;
create policy "svc only rf_bonding" on public.rf_bonding
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_bonding from service_role;
grant select, insert, update on public.rf_bonding to service_role;
revoke all on public.rf_bonding from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_prequal_documents;  -- expect 0
--   select count(*) from rf_bonding;            -- expect 0
--
-- Grants (expect INSERT,SELECT,UPDATE on both; no DELETE, no TRUNCATE):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_prequal_documents','rf_bonding')
--    group by table_name;
--
-- Confirm a constraint bites (expect an ERROR, not a row):
--   insert into public.rf_bonding (license_hash, bonding_id, aggregate_limit)
--   values ('test', 'RFBOND-CHECK', -1);
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- these tables.
