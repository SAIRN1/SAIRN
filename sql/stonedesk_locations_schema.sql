-- sql/stonedesk_locations_schema.sql
-- StoneDesk multi-location (multi-yard) support -- Supabase schema (2026-09-03)
--
-- Competitive-gap audit GAP 7 ("no multi-location support"). The audit records
-- that Stone Profit Systems ships "Multiple Locations" and that the absence
-- "caps StoneDesk at single-yard shops and excludes exactly the consolidating
-- multi-branch fabricator that has the budget". Additive and idempotent.
-- Verified absent word-boundary before building: `sd_locations` 0,
-- `location_id` 0, `locationId` 0, `multiLocation` 0, `yard_id` 0.
--
-- WHAT THIS STORES. One table:
--
--   sd_locations   a yard the shop operates: its name, address and whether it
--                  is still open.
--
-- ── THE SLAB IS THE ONLY THING THAT CARRIES A LOCATION ──────────────────
-- A slab is a physical object and it is AT a yard. Everything else -- a quote,
-- a job, a purchase order, a remnant -- gets its location by looking at the
-- slab, and stores none of its own.
--
-- That is the same shape SAIRNsenior's branch rollup uses (B1) and it is not a
-- style preference. Stamping a location onto a job at creation FREEZES it:
-- move the work to the other yard and the history stays attributed to the old
-- one forever, and correcting it means rewriting historical rows. Deriving it
-- means the attribution follows the material.
--
-- ── `location_id` IS THE YARD. `yardLocation` IS THE BAY. ───────────────
-- A slab already carried `yardLocation`, a FREE-TEXT string the Add Slab prompt
-- asks for as "Bay/location" -- "Bay 3", "Rack B, row 2". That is a position
-- INSIDE a yard and it stays exactly as it is.
--
-- This is worth saying at length because the two are easy to conflate and the
-- conflation is what makes an audit read "partially there": grepping `location`
-- in stonedesk.html returns plenty of hits, none of which are a business
-- location. The audit's own word-boundary check found `location_id` zero times,
-- which is the number that mattered.
--
-- ── WHAT THIS DOES NOT DO, SAID ON THE PANEL AS WELL AS HERE ────────────
-- IT DOES NOT PARTITION ACCESS. A multi-yard shop usually also wants staff
-- scoped to their own yard -- a Cleveland salesperson seeing Cleveland slabs.
-- That is an authorisation change reaching every panel, every read gate and the
-- employee roster, and it is NOT in this table. Every employee still sees every
-- yard; what changes is that inventory is now ATTRIBUTED to one.
--
-- Shipping attribution while implying access control would be the more
-- expensive half-truth: a shop would believe its yards were separated when they
-- are not. So the Locations panel says so in the same words.
--
-- ── UNASSIGNED IS ALWAYS ITS OWN ROW ────────────────────────────────────
-- Every slab that exists today has no location, because the column is new. The
-- rollup therefore always carries an Unassigned bucket whenever anything lands
-- in it, and never folds those slabs into the first yard or drops them from a
-- total. A rollup that silently loses rows is worse than one that shows an
-- uncomfortable number.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- sd_slabs and every other sd_* table. Licence-scoped with no employee session,
-- the same gate as 'slabs': a yard's name and address is operational data, not
-- personnel or financial data.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A closed yard is `active:false`
-- and keeps its history -- deleting it would leave every slab ever held there
-- pointing at nothing, which is the same orphaning sen_branches refuses.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sd_locations (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'stonedesk',
  location_id   text not null,
  data          jsonb not null default '{}'::jsonb,   -- id, name, address, phone, active, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, location_id),
  constraint sdlocations_data_size check (octet_length(data::text) <= 16384)
);
create index if not exists idx_sd_locations_license on public.sd_locations(license_hash);

alter table public.sd_locations enable row level security;

drop policy if exists "svc only sd_locations" on public.sd_locations;

create policy "svc only sd_locations" on public.sd_locations
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sd_locations to service_role;
revoke all on public.sd_locations from anon, authenticated;

-- NOTE: no migration is needed for sd_slabs. `location_id` lives inside that
-- table's existing jsonb `data` blob, so an existing slab simply has no key --
-- which is exactly the Unassigned state the rollup is built to report, rather
-- than a null that has to be back-filled with a guess about which yard a slab
-- was in.

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sd_locations;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sd_locations';
