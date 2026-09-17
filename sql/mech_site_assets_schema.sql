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
-- ── THE SECOND RULE'S THREE COLUMNS (added 2026-09-17) ──────────────────────
-- 40 CFR 82.157 above is Section 608. The AIM Act's HFC rule is a DIFFERENT
-- regulation -- 40 CFR 84.106, Part 84 subpart C -- in force since 2026-01-01
-- at 15 lb for HFCs with GWP above 53, with a 30-day repair window. A 20 lb
-- R-410A unit is correctly `below` under 82.157 and in scope under 84.106, so
-- the two are computed and reported independently and are NEVER summed.
--
-- hfc_gwp_over_53 IS STATED BY THE CONTRACTOR AND IS NOT DERIVED, and that is
-- the same refusal refrigerant_charge_lb makes. Deciding whether R-410A is "an
-- HFC above GWP 53" needs a substance table, and seeding one here would be a
-- number this schema asserts that a contractor then acts on, with no source
-- behind it -- and GWP figures are revised, so a stale table reads as
-- authoritative. NULL means nobody has stated it. It must NOT collapse into
-- false, which means "stated, and it is out of scope": an asset at or above
-- 15 lb whose substance nobody has stated is reported `unknown_substance`, not
-- `below` and not in scope. Adding a DEFAULT false to this column would turn
-- every un-stated unit into one reported as out of scope under a federal rule.
--
-- leak_detected_on starts the 30-day clock and NOTHING ELSE DOES. NULL means
-- no clock is running, reported as such; the engine never substitutes the
-- install date or today, because a deadline on screen that no recorded fact
-- supports is worse than no deadline. leak_repair_verified_on records the
-- initial verification test and stops that clock -- recorded, never inferred
-- from the passage of time. The app still issues no compliance verdict and
-- still does not decide whether a leak exceeded the applicable rate: the rates
-- differ by appliance category, and that is the judgement the header above
-- already refuses to make.
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
  -- 40 CFR 84.106 (AIM Act), the SECOND rule -- see header. All three NULLABLE
  -- and none of them defaulted.
  hfc_gwp_over_53       boolean,              -- NULL = nobody stated it. NEVER default false.
  leak_detected_on      date,                 -- NULL = no repair clock running.
  leak_repair_verified_on date,               -- NULL = no initial verification recorded.
  status                text not null default 'active',   -- active | retired
  notes                 text,
  recorded_by           text,                 -- employee_id from the verified session
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, asset_id)
);

-- ── FOR AN INSTALL THAT ALREADY RAN THIS FILE BEFORE 2026-09-17 ─────────────
-- `create table if not exists` does NOTHING to a table that already exists, so
-- the three columns above would never arrive on a live registry and the AIM
-- Act board would read `unknown_substance` for every asset forever -- a check
-- that cannot fire, which is indistinguishable on screen from one that fires
-- and finds nothing. Re-running the whole file is safe and idempotent.
alter table public.mech_site_assets
  add column if not exists hfc_gwp_over_53         boolean,
  add column if not exists leak_detected_on        date,
  add column if not exists leak_repair_verified_on date;

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

-- And the AIM Act column with the same weight. hfc_gwp_over_53 MUST be
-- nullable with NO default. If this says NO, or shows `false`, every unit
-- nobody has stated a refrigerant for now reads as OUT OF SCOPE under 40 CFR
-- 84.106 -- the same class of unearned clearance as a defaulted charge:
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_site_assets'
   and column_name in ('hfc_gwp_over_53', 'leak_detected_on', 'leak_repair_verified_on')
 order by column_name;
-- Expect three rows, all is_nullable = YES, all column_default = NULL.
-- THREE ROWS. Fewer means the ALTER above did not run and the board's AIM Act
-- counts are being computed from columns that are not there.

-- And confirm the grant is select+insert+update, with NO delete:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'mech_site_assets'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT, UPDATE
