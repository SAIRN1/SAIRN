-- sql/mech_site_assets_schema.sql
--
-- SAIRNmechanical site asset registry: customer -> site -> asset.
-- Run once in the Supabase SQL editor. Second table this app has ever had.
--
-- ── WHY THIS SECOND ─────────────────────────────────────────────────────────
-- docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md
-- §9d ranks it second of ten: "Prerequisite for A3, A5, A7, B8, G13. Table
-- stakes -- every incumbent has it." §3 A2 records that the named fields are
-- identical across HVAC, electrical and plumbing and that only the asset
-- TAXONOMY differs by trade -- so the schema is shared and the type vocabulary
-- is the trade-gated part. That is why asset_type is a plain text column
-- validated in api/_lib/mech-assets.js rather than a Postgres enum: a second
-- trade adds vocabulary, not a migration.
--
-- Verified before building: the Equipment page was an honest empty state and
-- its "+ Add Equipment" button had no handler.
--
-- ── NOT APPEND-ONLY, UNLIKE mech_credentials, AND THAT IS DELIBERATE ────────
-- A credential is EVIDENCE: a renewal must never overwrite what somebody held
-- on a given day, so that table has no UPDATE grant. An asset is not evidence,
-- it is a description of a physical thing -- a serial gets corrected, a unit
-- gets relocated, a nameplate is re-read. Copying the append-only shape here
-- by reflex would force a new row for every typo and make "which row is the
-- unit" ambiguous.
--
-- So this table DOES carry an UPDATE grant, and that is a considered exception
-- to the platform's grant-narrowing default rather than an oversight. There is
-- still NO DELETE: retiring a unit is a status, not an erasure, because an
-- asset that has been serviced is referenced by history that must not orphan.
--
-- The SERVICE HISTORY chain the research names is genuinely append-only and is
-- NOT built in this pass. Called out rather than half-built.
--
-- ── THE COLUMN WITH LEGAL WEIGHT ────────────────────────────────────────────
-- refrigerant_charge_lb is NULLABLE ON PURPOSE, and null means "nobody has
-- weighed this unit" -- never zero. EPA keys its leak-repair provisions to a
-- full charge at or above 50 lb (40 CFR 82.157), and api/_lib/mech-assets.js
-- answers `unknown_charge` rather than `below` when the column is null.
-- Defaulting it to 0 would turn every un-surveyed chiller into a unit reported
-- as under threshold, which is a compliance claim with no evidence behind it.
--
-- The app does NOT store or compute a compliance verdict. It reports whether
-- the recorded charge is at or above a stated, cited threshold, and says the
-- rule must be confirmed. Leak-rate percentages differ by appliance category
-- and the HFC picture has moved since 2016; encoding one would be this app
-- asserting current federal law from a hardcoded number.
--
-- refrigerant_type = 'none' is a REAL answer for a boiler or a pump and is
-- stored, distinctly from null. The two must never render the same.
--
-- ── NO SEED DATA. NOT ONE ROW. ──────────────────────────────────────────────
-- This app's Equipment panel carried three invented customers, addresses and
-- units presented as a live board until 2026-08-27. It ships empty.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, api/sd-data.js the only door,
-- and every action requires a verified employee session. Writes are NOT
-- restricted to management, unlike mech_credentials: a field technician
-- recording the unit in front of them is the intended workflow, and there is
-- no self-dealing risk in describing a machine. The credential restriction
-- exists because nobody should record their own licence; that reasoning does
-- not transfer here, and copying it would have blocked the primary use.

create table if not exists public.mech_site_assets (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  asset_id              text not null,        -- client-generated, stable, unique per licence
  customer_name         text not null,
  site_name             text,
  site_address          text,
  asset_type            text not null,        -- validated in api/_lib/mech-assets.js (ASSET_TYPES)
  make                  text,
  model                 text,
  serial_no             text,
  location_on_site      text,
  installed_on          date,
  has_warranty          boolean,              -- true/false stated, NULL = nobody checked
  warranty_expires_on   date,
  refrigerant_type      text,                 -- 'none' is a real answer; NULL is not
  refrigerant_charge_lb numeric(10,2),        -- NULL = never weighed. NEVER default 0.
  status                text not null default 'active',   -- active | retired
  notes                 text,
  recorded_by           text,                 -- employee_id from the verified session
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, asset_id)
);

create index if not exists idx_mech_asset_license
  on public.mech_site_assets (license_hash, created_at desc);
-- "what is at this customer's site" is the question this table is asked.
create index if not exists idx_mech_asset_site
  on public.mech_site_assets (license_hash, customer_name, site_name);
-- And the compliance-adjacent one: which units are at or above the threshold,
-- and which have never been weighed at all.
create index if not exists idx_mech_asset_charge
  on public.mech_site_assets (license_hash, refrigerant_charge_lb);

alter table public.mech_site_assets enable row level security;

-- SELECT, INSERT and UPDATE. The UPDATE is the considered exception explained
-- in the header -- an asset is a description, not evidence. Still NO DELETE.
grant select, insert, update on public.mech_site_assets to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_site_assets'
 order by ordinal_position;

select count(*) as should_be_zero from public.mech_site_assets;

-- refrigerant_charge_lb MUST be nullable. If this says NO, something has given
-- it a default and every un-surveyed unit now reads as a measured zero:
select is_nullable as charge_is_nullable, column_default as charge_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_site_assets'
   and column_name = 'refrigerant_charge_lb';
-- Expect: YES, and no default.

-- And confirm the grant is select+insert+update, with NO delete:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'mech_site_assets'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT, UPDATE
