-- sql/sd_supplier_lead_times_schema.sql
--
-- [0072] Supplier lead time per (supplier, material). The data gap that had to
-- be closed before any risk arithmetic could be honest.
--
-- Design: docs/2026-09-02-0072-material-job-risk-design.md
--
-- ── THE GAP THIS FILLS ──────────────────────────────────────────────────────
-- Read from the app before writing this, not assumed: a slab record carries
-- `id, material, colorName, status, usableSqft, vendor, photo_base64, addedAt`
-- and a job carries `material, templateDate, targetDate, stage, sqft,
-- reservedSlabId, installedAt`. Neither has a lead time, and neither does the
-- in-file VENDORS constant. There was nowhere for the number to live.
--
-- ── KEYED ON THE PAIR, NOT ON THE SUPPLIER ──────────────────────────────────
-- (license_hash, supplier, material). Both halves matter: the same supplier is
-- faster on quartz they stock than on quartzite they import, and the same
-- material is faster from a local distributor than from an importer. A
-- supplier-only lead time would be an average across those and wrong for both.
--
-- `supplier` is stored as the free-text vendor string the slab record already
-- uses, NOT a VENDORS key. The app writes free text there today
-- (bsu-vendor-* is a text input), and forcing a key here would either drop
-- every slab whose vendor was typed by hand or silently mis-attribute it.
-- Normalisation is a real problem and it is left visible rather than papered
-- over: lower(trim()) is applied on write so "MSI " and "msi" agree, and
-- nothing beyond that is guessed.
--
-- ── QUOTED AND OBSERVED ARE SEPARATE COLUMNS AND ARE NEVER MERGED ───────────
-- quoted_days is what a supplier SAYS. The observed_* columns are what actually
-- happened, folded in one receipt at a time as a running sum and count so an
-- average is derivable without keeping an event table. They are stored apart
-- because a shop needs to know which one a projection used -- "the supplier
-- quotes 14 days but the last four took 31" is the single most useful thing
-- this table can tell anyone, and merging them into one number destroys it.
--
-- min and max are kept alongside the average because an average of 10 and 40 is
-- not a 25-day lead time in any sense a scheduler can use.
--
-- ── NO SEED DATA. NOT ONE ROW. ──────────────────────────────────────────────
-- This table ships EMPTY and that is the point. A projected completion date
-- built on an invented lead time is worse than no date, because it is a number
-- a shop would schedule a customer against. Until a shop enters a quoted value
-- or the system observes a real receipt, every job needing that material is
-- reported as risk "unknown" with a named reason -- never as "ok", and never
-- against a default. Same three-state discipline as the subcontractor
-- compliance gate: known / unknown / stale, and untracked is never a green tick.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, api/sd-data.js the only door.
-- Lead times are commercially sensitive -- they expose which suppliers a shop
-- depends on and how badly -- so this is licence-scoped like everything else.

create table if not exists public.sd_supplier_lead_times (
  id                  uuid primary key default gen_random_uuid(),
  license_hash        text not null,
  supplier            text not null,          -- lower(trim()) of the slab's vendor string
  material            text not null,          -- lower(trim()) of the material string
  quoted_days         integer,                -- what the supplier says. NULL = never stated.
  observed_total_days integer not null default 0,
  observed_n          integer not null default 0,
  observed_min_days   integer,
  observed_max_days   integer,
  last_observed_at    timestamptz,
  notes               text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (license_hash, supplier, material)
);

create index if not exists idx_sdslt_license
  on public.sd_supplier_lead_times (license_hash);
-- The engine's hot path is "lead time for THIS material from THIS supplier".
create index if not exists idx_sdslt_lookup
  on public.sd_supplier_lead_times (license_hash, material, supplier);

alter table public.sd_supplier_lead_times enable row level security;

grant select, insert, update on public.sd_supplier_lead_times to service_role;

-- No DELETE grant, deliberately, matching sd_subs and sd_sub_jobs. A lead-time
-- row is evidence about a supplier's behaviour over time; retiring one is
-- setting quoted_days to null and letting the observations stand, not erasing
-- the history that produced them.

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows. If this returns rows, something
-- seeded it and that needs explaining before any projection is trusted.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sd_supplier_lead_times'
 order by ordinal_position;

select count(*) as should_be_zero from public.sd_supplier_lead_times;
