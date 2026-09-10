-- sql/sairndental_vendor_schema.sql
-- SAIRNdental vendor and supply data -- the last four collections this app
-- kept only on the device.
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run. Until it runs, every write
-- answers 503 NOT_PROVISIONED naming this file and every read answers
-- provisioned:false, so the app degrades honestly.
--
-- WHY, MEASURED. tools/local_only_collection_check.py reported sairndental.html
-- as 18 of 22 collections covered and FOUR with no route to a server:
-- dnt_supplies_list, dnt_vendor_contacts, dnt_vendor_order_history and
-- dnt_vendor_pricing_rules. The rest of this practice's record -- patients,
-- charges, payments, credentials -- has been server-backed since 2026-09-05,
-- so a browser-data clear left the clinical record intact and took the
-- purchasing history and the negotiated vendor discounts with it. That
-- selective shape is worse than a uniformly local app, for the same reason it
-- was worse in StoneDesk: what survives looks authoritative.
--
-- TWO OF THE FOUR RESOURCE NAMES ARE NOT THEIR STORAGE KEYS, and that is this
-- app's existing convention rather than a new one: DNT_SYNC_RESOURCES is a list
-- of [resource, storage-key] PAIRS (dnt_patients <-> dnt_patients_list). The
-- four pairs added are:
--   dnt_supplies             <-> dnt_supplies_list
--   dnt_vendor_orders        <-> dnt_vendor_order_history
--   dnt_vendor_contacts      <-> dnt_vendor_contacts          (same name)
--   dnt_vendor_pricing_rules <-> dnt_vendor_pricing_rules     (same name)
--
-- THE TWO THAT MATCH DO SO ON PURPOSE. tools/local_only_collection_check.py
-- resolves coverage by matching a resource name against a storage key, and a
-- DIFFERING pair is only visible to it inside a [resource, key] literal --
-- which these two have not got, because they are single objects hydrated in
-- their own block rather than through DNT_SYNC_RESOURCES. Naming them
-- identically is what makes their coverage MEASURABLE instead of a permanent
-- could-not-tell. The heading of this paragraph said "RESOURCE NAMES ARE NOT
-- THE STORAGE KEYS HERE" as though it covered all four; it covers two.
--
-- TWO OF THE FOUR ARE SINGLE OBJECTS, NOT LISTS. dnt_vendor_contacts is a map
-- keyed by vendor and dnt_vendor_pricing_rules is one settings object
-- ({vendorDiscounts, categoryDiscounts, productOverrides}). Both are stored as
-- ONE row with id 'default' and replaced wholesale on hydrate -- exactly the
-- treatment dnt_settings already gets in this app, and for the same reason: a
-- merge-by-id over something that has no per-record id would append the whole
-- object every sync.
--
-- SOFT DELETE IS INCLUDED BECAUSE ONE OF THESE CAN BE DELETED, and without it
-- the backup would be a bug. removeSupply() drops an item from
-- dnt_supplies_list; hydration merges the server's rows back in by id, so a
-- removed supply would REAPPEAR on the next sync. dnt_supplies is therefore
-- registered with the platform's existing `soft_delete` extra action (the read
-- filters `data->>_deleted_at is null`), and removeSupply() calls it. No new
-- database privilege: the marker lives inside the existing jsonb and the write
-- is an UPDATE.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name, the rule
-- every other app's schema documents.
--
-- SECURITY MODEL: licence key only, matching every other dnt_* resource in
-- api/_resources/sairndental.js. RLS enabled with no anon policy --
-- api/sd-data.js is the only door in. 64KB per row's data jsonb.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE. Soft delete is an UPDATE; the
-- platform's only reachable hard-delete path is sd-data.js's SC_RESOURCES
-- branch. `revoke all` precedes each grant because a bare grant is additive
-- and cannot remove what the default ACL already handed over.

create extension if not exists pgcrypto;

-- Supply inventory items. Records with an id, and the ONLY one of the four with a delete path -- see the soft-delete note in the header.
create table if not exists public.dnt_supplies (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairndental',
  supply_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, supply_id),
  constraint dnt_supplies_data_size check (octet_length(data::text) <= 65536)
);
alter table public.dnt_supplies enable row level security;
drop policy if exists "svc only dnt_supplies" on public.dnt_supplies;
create policy "svc only dnt_supplies" on public.dnt_supplies
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.dnt_supplies from service_role;
grant select, insert, update on public.dnt_supplies to service_role;

-- Purchase orders placed with a vendor. The client keeps the newest 200; the server keeps all of them, which is the point of a backup.
create table if not exists public.dnt_vendor_orders (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairndental',
  vendor_order_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vendor_order_id),
  constraint dnt_vendor_orders_data_size check (octet_length(data::text) <= 65536)
);
alter table public.dnt_vendor_orders enable row level security;
drop policy if exists "svc only dnt_vendor_orders" on public.dnt_vendor_orders;
create policy "svc only dnt_vendor_orders" on public.dnt_vendor_orders
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.dnt_vendor_orders from service_role;
grant select, insert, update on public.dnt_vendor_orders to service_role;

-- Rep contact per vendor. ONE row, id 'default', holding the whole map -- see the single-object note.
create table if not exists public.dnt_vendor_contacts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairndental',
  vendor_contact_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vendor_contact_id),
  constraint dnt_vendor_contacts_data_size check (octet_length(data::text) <= 65536)
);
alter table public.dnt_vendor_contacts enable row level security;
drop policy if exists "svc only dnt_vendor_contacts" on public.dnt_vendor_contacts;
create policy "svc only dnt_vendor_contacts" on public.dnt_vendor_contacts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.dnt_vendor_contacts from service_role;
grant select, insert, update on public.dnt_vendor_contacts to service_role;

-- Vendor/category/product discount rules. ONE row, id 'default' -- a single settings object, not a list.
create table if not exists public.dnt_vendor_pricing_rules (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairndental',
  vendor_pricing_rule_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vendor_pricing_rule_id),
  constraint dnt_vendor_pricing_rules_data_size check (octet_length(data::text) <= 65536)
);
alter table public.dnt_vendor_pricing_rules enable row level security;
drop policy if exists "svc only dnt_vendor_pricing_rules" on public.dnt_vendor_pricing_rules;
create policy "svc only dnt_vendor_pricing_rules" on public.dnt_vendor_pricing_rules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.dnt_vendor_pricing_rules from service_role;
grant select, insert, update on public.dnt_vendor_pricing_rules to service_role;

grant usage on schema public to service_role;
