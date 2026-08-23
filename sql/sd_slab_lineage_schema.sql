-- sql/sd_slab_lineage_schema.sql
-- StoneDesk Phase 1b (2026-08-22): block / bundle / slab-history lineage.
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sd_blocks / sd_bundles / sd_slab_history branches will work.
--
-- Design: docs/superpowers/specs/2026-08-22-stonedesk-phase1-slab-unification-design.md
--
-- WHY THESE ARE SIBLING TABLES AND NOT FIELDS ON THE SLAB BLOB.
-- sd_slabs.data is capped at 65536 bytes by its own sdslabs_data_size CHECK,
-- and stonedesk.html compresses each slab photo to BSU_PHOTO_BUDGET_BYTES =
-- 55KB before upload. That leaves roughly 9KB of real headroom per slab, and
-- the cap is not raisable locally: a slabs-specific 500KB override was tried
-- on 2026-08-04, passed the API layer, and was rejected by Postgres with a
-- much less clear error (recorded in api/sd-data.js's own header). Three
-- consequences decided this shape:
--
--   1. HISTORY IS UNBOUNDED. A slab that is received, moved between bays a
--      few times, reserved, released, reserved again, consumed, and spawns
--      two remnants accumulates a dozen-plus events. In the blob that makes a
--      record MORE likely to fail the longer it is used -- failing first on
--      the busiest, highest-value slabs, which are exactly the ones whose
--      provenance someone is auditing when it breaks.
--   2. BLOCK FACTS ARE SHARED. Quarry, origin, PO, arrival date and a block
--      photo denormalised into every slab cut from that block multiplies a
--      fixed-ceiling problem by slab count, and one correction to a block
--      fact means rewriting every slab in it.
--   3. VEIN-MATCHING NEEDS A QUERY. "Give me every slab from block X" is the
--      actual product requirement. Answerable against an indexed sibling row;
--      not answerable against block ids buried in per-row jsonb.
--
-- WHAT GOES IN THE SLAB BLOB INSTEAD: exactly two optional short strings,
-- blockId and bundleId, roughly 60 bytes total. Both optional -- a slab with
-- neither is a valid slab, which is what every pre-1b row is and what a
-- directly-purchased remnant always will be.
--
-- REVERSAL. These tables are new and referenced by nothing else. The slab ->
-- block link is a plain string, NOT a database foreign key, deliberately: a
-- dangling blockId after a table drop degrades to "no block info", never to a
-- constraint error or an orphaned row. Rollback tiers, cheapest first:
--   (a) stop writing -- revert the client; the two keys are simply not read;
--   (b) strip the keys -- one client-side sweep, safe because both are optional;
--   (c) drop these three tables -- cannot orphan or break a single slab.
-- At no point does a slab record stop being a valid pre-1b slab record.
--
-- Same row shape as every other sd_* resource: license_hash-scoped, one row
-- per entry, a jsonb data column, unique on (license_hash, <entry>_id).

-- ── BLOCKS: one row per quarry block ─────────────────────────────────────
create table if not exists public.sd_blocks (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  block_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, block_id),
  constraint sd_blocks_data_size check (octet_length(data::text) <= 65536)
);

-- ── BUNDLES: one row per bundle, carrying its parent block id in data ────
create table if not exists public.sd_bundles (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  bundle_id    text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, bundle_id),
  constraint sd_bundles_data_size check (octet_length(data::text) <= 65536)
);

-- ── SLAB HISTORY: one row per event, append-only in practice ─────────────
-- Deliberately NOT an array on the slab -- see reason 1 in the header. The
-- slab_id here is the client-generated slab id string, matching sd_slabs.slab_id.
create table if not exists public.sd_slab_history (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  event_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, event_id),
  constraint sd_slab_history_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sd_blocks_license        on public.sd_blocks(license_hash);
create index if not exists idx_sd_bundles_license       on public.sd_bundles(license_hash);
create index if not exists idx_sd_slab_history_license  on public.sd_slab_history(license_hash);

alter table public.sd_blocks       enable row level security;
alter table public.sd_bundles      enable row level security;
alter table public.sd_slab_history enable row level security;

drop policy if exists "svc only sd_blocks" on public.sd_blocks;
create policy "svc only sd_blocks" on public.sd_blocks for all using (false) with check (false);
drop policy if exists "svc only sd_bundles" on public.sd_bundles;
create policy "svc only sd_bundles" on public.sd_bundles for all using (false) with check (false);
drop policy if exists "svc only sd_slab_history" on public.sd_slab_history;
create policy "svc only sd_slab_history" on public.sd_slab_history for all using (false) with check (false);

grant select, insert, update, delete on public.sd_blocks       to service_role;
grant select, insert, update, delete on public.sd_bundles      to service_role;
grant select, insert, update, delete on public.sd_slab_history to service_role;

revoke all on public.sd_blocks       from anon, authenticated;
revoke all on public.sd_bundles      from anon, authenticated;
revoke all on public.sd_slab_history from anon, authenticated;

-- Verify after running (expect 0 rows, no error, for each):
--   select count(*) from sd_blocks;
--   select count(*) from sd_bundles;
--   select count(*) from sd_slab_history;
