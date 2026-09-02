-- sql/stonedesk_public_surface_schema.sql
-- StoneDesk public catalog, quote requests and order tracking (2026-09-02)
--
-- Competitive-gap audit GAP 1 (no customer-facing portal) and the narrow
-- order-tracking slice of GAP 8. Additive and idempotent; run after
-- sql/sd_slabs_schema.sql. Nothing in that file is duplicated here.
--
-- ── THE DECISION THAT SHAPES EVERY TABLE BELOW ──
-- The public surface is served by its own file, stonedesk-catalog.html, and
-- reads its own tables. It is NOT a mode of stonedesk.html and it does NOT read
-- the employee profile blob. That is not a style preference:
-- `stonedesk.html` carries SAIRN's own chart of accounts, its price book and a
-- patent deadline as literal strings in the HTML -- the residual the
-- competitive audit explicitly left open at §4.1, where gating the Executive
-- Suite panel stopped UI access and did nothing about View Source. Serving that
-- file to an anonymous visitor would publish all of it. A public surface
-- therefore gets its own file and its own tables, and the only data that can
-- reach it is data a shop deliberately put in a table built for publication.
--
--   sd_public_shop      one row per license: the shop's public slug, display
--                       name and contact details, and whether the catalog is
--                       published at all. The slug is a real indexed column,
--                       not a jsonb-buried value, and is globally unique --
--                       same shape and same reasoning as dnt_settings'
--                       booking_slug.
--   sd_quote_requests   inbound leads from the public form. A SEPARATE table
--                       from sd_crm, deliberately -- see below.
--   sd_order_links      revocable, scoped order-tracking tokens.
--   sd_public_rate_limits  per-IP-hash counters for the unauthenticated
--                       endpoints, mirroring dnt_booking_rate_limits.
--
-- ── WHY QUOTE REQUESTS DO NOT LAND IN sd_crm ──
-- sd_crm is the shop's real customer list, and api/sd-data.js gates read AND
-- write on a genuine StoneDesk session. An anonymous, unauthenticated submitter
-- must not be able to insert rows into it. Requests land here as `pending` and
-- a member of staff promotes them. Same rule, same reason, as
-- api/sairndental/public-book.js's "new bookings always land as Pending --
-- never auto-confirmed": an anonymous submitter must never write directly into
-- the record the business runs on.
--
-- ── WHY A TOKEN AND NOT A CUSTOMER PASSWORD ──
-- sd_order_links follows sql/sairnsenior_portal_links_schema.sql exactly. A
-- customer is a DIFFERENT ACTOR CLASS from an employee: every credential on
-- this platform lives in a *_employee_auth table with a PIN, a lockout and a
-- provisioning role, and a customer has none of those. The token IS the
-- credential, like a calendar-share link -- 256-bit crypto-random, revocable,
-- scoped to exactly one job, and the job_id it resolves to is never supplied by
-- the caller. Inventing a customer password store would add a credential
-- database with no recovery path and no provisioning model, to solve a problem
-- this platform already solved once.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- the public
-- API functions hold the service key server-side and are the only door in. A
-- browser never talks to PostgREST directly.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide across 134 tables; the only reachable delete path anywhere is
-- api/sd-data.js's SC_RESOURCES branch. Revocation here is a flag, not a
-- delete, so a revoked link stays auditable -- the same reason a deactivated
-- credential row is kept rather than removed.
--
-- SIZE CAP: 64KB of jsonb per row, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES and sd_slabs' own CHECK.

create extension if not exists pgcrypto;

-- ── PUBLIC SHOP PROFILE ─────────────────────────────────────────────────────
create table if not exists public.sd_public_shop (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  shop_slug    text,
  published    boolean not null default false,
  data         jsonb not null default '{}'::jsonb,   -- shop_name, phone, email, address, blurb, updated_by
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash),
  constraint sdps_data_size check (octet_length(data::text) <= 65536)
);
-- Globally unique, and only where a slug is actually set -- two shops cannot
-- claim the same public URL, and any number may have none. Same partial-unique
-- shape as dnt_settings' booking_slug.
create unique index if not exists idx_sdps_slug on public.sd_public_shop(shop_slug) where shop_slug is not null;

-- ── QUOTE REQUESTS (inbound leads) ──────────────────────────────────────────
create table if not exists public.sd_quote_requests (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  request_id   text not null,
  status       text not null default 'pending',
  data         jsonb not null default '{}'::jsonb,   -- name, phone, email, project_type, material, sqft, budget, timeline, message, slab_id, slab_label, submitted_at, promoted_at, promoted_by, declined_reason
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, request_id),
  constraint sdqr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdqr_license on public.sd_quote_requests(license_hash);

-- ── CUSTOMER RECORDS ────────────────────────────────────────────────────────
-- Added in the same file as the tracking links because tracking cannot be
-- honest without it. sd_customers was localStorage-only -- the shop's actual
-- customer list lived in one browser and died with its cache, the same state
-- sd_crm was in before it got a real sync. An order-tracking link has to
-- resolve to the REAL record; the alternative was a status snapshot stored on
-- the link itself, which drifts the moment anyone updates the job and would
-- have shown a customer "in fabrication" after their kitchen shipped.
create table if not exists public.sd_customers (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'stonedesk',
  customer_id  text not null,
  data         jsonb not null default '{}'::jsonb,   -- name, phone, email, project, material, quote, status, referral, rating, createdAt
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, customer_id),
  constraint sdcust_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_sdcust_license on public.sd_customers(license_hash);

-- ── ORDER TRACKING LINKS ────────────────────────────────────────────────────
create table if not exists public.sd_order_links (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  app_id           text not null default 'stonedesk',
  link_id          text not null,
  link_token       text not null,
  job_id           text not null,
  label            text,
  active           boolean not null default true,
  created_at       timestamptz not null default now(),
  last_accessed_at timestamptz,
  revoked_at       timestamptz,
  unique (license_hash, link_id)
);
-- The token is looked up directly on every anonymous view, so it is unique
-- across the whole table and indexed for it.
create unique index if not exists idx_sdol_token on public.sd_order_links(link_token);
create index if not exists idx_sdol_license on public.sd_order_links(license_hash);

-- ── RATE LIMITS ─────────────────────────────────────────────────────────────
-- Mirrors dnt_booking_rate_limits. HONEST LIMITATION, carried over from
-- api/_lib/dental-public.js's own header: the increment is read-then-write, not
-- a single atomic statement, so a very tight concurrent burst can undercount by
-- a request or two inside one window. Acceptable for abuse deterrence on a
-- public form, and self-correcting every new window. NOT acceptable to reuse
-- this shape where a hard security or financial boundary is needed.
create table if not exists public.sd_public_rate_limits (
  id           uuid primary key default gen_random_uuid(),
  ip_hash      text not null,
  window_start timestamptz not null,
  count        integer not null default 0,
  created_at   timestamptz not null default now(),
  unique (ip_hash, window_start)
);
create index if not exists idx_sdprl_window on public.sd_public_rate_limits(window_start);

alter table public.sd_customers          enable row level security;
alter table public.sd_public_shop        enable row level security;
alter table public.sd_quote_requests     enable row level security;
alter table public.sd_order_links        enable row level security;
alter table public.sd_public_rate_limits enable row level security;

drop policy if exists "svc only sd_customers"          on public.sd_customers;
drop policy if exists "svc only sd_public_shop"        on public.sd_public_shop;
drop policy if exists "svc only sd_quote_requests"     on public.sd_quote_requests;
drop policy if exists "svc only sd_order_links"        on public.sd_order_links;
drop policy if exists "svc only sd_public_rate_limits" on public.sd_public_rate_limits;

create policy "svc only sd_customers" on public.sd_customers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sd_public_shop" on public.sd_public_shop
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sd_quote_requests" on public.sd_quote_requests
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sd_order_links" on public.sd_order_links
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only sd_public_rate_limits" on public.sd_public_rate_limits
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sd_customers          to service_role;
grant select, insert, update on public.sd_public_shop        to service_role;
grant select, insert, update on public.sd_quote_requests     to service_role;
grant select, insert, update on public.sd_order_links        to service_role;
grant select, insert, update on public.sd_public_rate_limits to service_role;
