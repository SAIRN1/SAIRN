-- sql/stonedesk_remnants_schema.sql
-- StoneDesk remnant yard -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit GAP 8 ("no remnant publishing to the shop's public
-- website"). Additive and idempotent; run after
-- sql/stonedesk_public_surface_schema.sql, whose sd_public_shop this reads
-- alongside. Nothing there is duplicated here.
--
-- WHAT THIS STORES. One table:
--
--   sd_remnants   a cut-off piece in the yard: what stone, how big, where it
--                 is, what it is being asked for, and whether the shop has
--                 published it to its public catalog.
--
-- ── THE GAP WAS HALF-CLOSED AND THAT IS WHY THIS EXISTS ─────────────────
-- The public catalog shipped on 2026-09-02 (GAP 1) and it publishes SLABS.
-- `stonedesk-catalog.html` contained the word "remnant" ZERO times. The
-- publishing mechanism arrived and the remnant half did not, which is a shape
-- that reads as done from a distance: the audit item says "publishing to the
-- public website", the machinery exists, and nothing on any screen said the
-- remnants were not in it.
--
-- Remnant sale is margin recovery on material the shop has already paid for.
-- Slabsmith publishes live slab AND remnant inventory to the customer's own
-- site; SlabWise auto-lists remnants straight out of nesting.
--
-- ── REMNANTS WERE localStorage-ONLY BEFORE THIS ────────────────────────
-- The remnant yard read and wrote `sd_remnant` (SINGULAR) in the browser and
-- had no server table at all, so a remnant existed on exactly one machine.
-- Nothing could publish it, because the public endpoint reads Supabase and not
-- somebody's laptop.
--
-- ── THE PRICE IS PUBLISHED, AND THAT IS THE OPPOSITE OF THE SLAB RULE ───
-- api/_lib/stonedesk-public.js refuses to publish a slab's cost, correctly:
-- that figure is what the SHOP PAID, and showing it would be commercially wrong
-- and factually misleading about what a customer would be charged.
--
-- A REMNANT'S `price` IS THE ASKING PRICE -- what a customer pays. It is the
-- entire point of publishing a remnant, since the piece is being cleared rather
-- than quoted. This is stated here at length precisely because the two rules
-- look contradictory side by side, and a later reader "fixing the
-- inconsistency" would delete the feature.
--
-- ── ONLY AN AVAILABLE REMNANT REACHES THE CATALOG ──────────────────────
-- Publication is an explicit per-remnant flag AND the piece must still be
-- Available. A Reserved or Sold remnant with the flag left on is dropped from
-- the public view, because a catalog offering a piece that is already gone is
-- the double-sale problem in miniature -- the same failure the slab
-- reservation compare-and-swap exists to stop. The shop's own panel SAYS the
-- piece is being withheld rather than silently omitting it, so a ticked box
-- that produces nothing on the web is explained rather than mysterious.
--
-- ── `age` IS NOT PUBLISHED, AND IT IS NOT AN OVERSIGHT ─────────────────
-- The remnant record carries `age` as a STORED DAY COUNT, set once and never
-- incremented by anything. It is usable internally as the number somebody last
-- wrote down. Published, it becomes a fact that decays: a piece shown as "12
-- days old" is still saying 12 a year later. The catalog omits it rather than
-- printing a number that gets more wrong every day, and this comment exists so
-- the omission is not read as a missing field.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- sd_slabs and every other sd_* table. The public endpoint reaches this table
-- with the service role after resolving a shop_slug, exactly as it does for
-- slabs; a visitor never holds a key of any kind.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A sold remnant becomes
-- status Sold and keeps its history, because it is the record of what the yard
-- recovered on material already paid for.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sd_remnants (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'stonedesk',
  remnant_id    text not null,
  data          jsonb not null default '{}'::jsonb,   -- id, stone, size, sqft, status ('Available'|'Reserved'|'Sold'), location, price, age, origin, notes, published, photo_base64
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, remnant_id),
  -- Same ceiling and same reason as sdslabs_data_size: a photo lives in this
  -- blob and an unbounded one would take the row past what PostgREST will
  -- return in a list read.
  constraint sdremnants_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sd_remnants_license on public.sd_remnants(license_hash);

alter table public.sd_remnants enable row level security;

drop policy if exists "svc only sd_remnants" on public.sd_remnants;

create policy "svc only sd_remnants" on public.sd_remnants
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sd_remnants to service_role;
revoke all on public.sd_remnants from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sd_remnants;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sd_remnants';
