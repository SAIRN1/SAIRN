-- sql/sairngrounds_caddie_schema.sql
-- SAIRNgrounds On-Course Caddie -- Supabase schema (2026-09-02)
--
-- ADDITIVE, run after sql/sairngrounds_data_schema.sql and
-- sql/sairngrounds_data_schema_phase2.sql. Neither of those tables is
-- duplicated here. Idempotent (create table if not exists), safe to re-run.
--
-- WHAT THIS IS FOR. SAIRNGROUNDS-SCOPE.md section 5a's base layer, built on
-- the item 10 course-mapping foundation that was already shipped. Two tables:
--
--   grd_rounds       a round on a property: the player/group label, start and
--                    finish, and the holes walked with arrival/completion
--                    timestamps and any GPS-measured shots.
--   grd_cart_orders  an on-course order placed against a round, carrying the
--                    hole and the player's GPS position so the Pro Shop can
--                    find them. A REQUEST, not a sale -- no money moves here
--                    and no stock moves; the existing msb_sales till does both
--                    when the order is delivered.
--
-- WHY THESE ARE SERVER-SIDE at all, when several other SAIRNgrounds panels
-- were localStorage-only for a while: both are read by somebody other than the
-- device that wrote them. Pace of play is the loop back into operations
-- (section 5a item 5) and is worthless if it stays on a player's phone; a cart
-- order the shop cannot see is not an order. That is the line where
-- localStorage stops being enough, and it is the reason these got tables while
-- e.g. the plant database did not.
--
-- KEYING: license_hash = sha256(license_key), TYPE A (property-scoped list) in
-- the phase-2 file's own taxonomy -- each row carries its own <entity>_id plus
-- the property_id it belongs to.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- same as
-- every other grd_* table. api/sd-data.js is the only door in.
--
-- NO DELETE GRANT, deliberately. sql/unused_delete_grant_revoke_2026-08-24.sql
-- revoked it platform-wide across 134 tables, and the platform's only reachable
-- delete path is api/sd-data.js's SC_RESOURCES branch. Do not add `delete` here
-- when fixing a missing grant -- see the same warning in
-- sql/sairngrounds_data_schema_phase2.sql.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES. A round accumulates holes and shots as it is played, so
-- this is the one table here where the cap is a real ceiling rather than a
-- formality: at roughly 300 bytes per recorded shot it allows a few hundred
-- shots on one round, which is far beyond any real round, but a client that
-- looped and appended would hit it rather than growing without bound.

create extension if not exists pgcrypto;

create table if not exists public.grd_rounds (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  round_id     text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- player_label, started_at, finished_at, holes[{zone_id, zone_name, arrived_at, completed_at, shots[{from,to,meters,band_meters,at}]}]
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, round_id),
  constraint grdrnd_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdrnd_license on public.grd_rounds(license_hash);

create table if not exists public.grd_cart_orders (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairngrounds',
  order_id     text not null,
  property_id  text not null,
  data         jsonb not null default '{}'::jsonb,    -- round_id, player_label, zone_id, zone_name, lat, lng, accuracy_m, items[], total, status, placed_at, delivered_at
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, order_id),
  constraint grdco_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_grdco_license on public.grd_cart_orders(license_hash);

alter table public.grd_rounds      enable row level security;
alter table public.grd_cart_orders enable row level security;

drop policy if exists "svc only grd_rounds"      on public.grd_rounds;
drop policy if exists "svc only grd_cart_orders" on public.grd_cart_orders;

create policy "svc only grd_rounds" on public.grd_rounds
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only grd_cart_orders" on public.grd_cart_orders
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.grd_rounds      to service_role;
grant select, insert, update on public.grd_cart_orders to service_role;
