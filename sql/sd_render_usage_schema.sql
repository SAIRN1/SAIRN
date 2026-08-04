-- sql/sd_render_usage_schema.sql
-- StoneDesk "Visualize on Your Kitchen" render-cap usage tracking -- Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as sql/sd_employee_auth_schema.sql)
-- before api/sd-render.js's cap check/increment or api/sd-data.js's 'render_usage' resource
-- will work. Until this runs, both return a clear 503 NOT_PROVISIONED rather than a generic 500
-- -- same convention sd_employee_auth_schema.sql established for the same situation.
--
-- WHY THIS EXISTS: "Visualize on Your Kitchen" (photo upload -> AI material-swap render using
-- real in-stock slab inventory) calls a paid third-party image-edit vendor per render. Per
-- decision (2026-08-04): no usage-based passthrough billing, no Stripe metering, no per-shop
-- invoicing -- instead a generous free-render cap (75/month per shop, see api/sd-render.js's
-- RENDER_CAP constant for the full reasoning) baked into the existing flat subscription. This
-- table is ONLY the counter that makes that cap enforceable and gives visibility into volume --
-- it does not gate access to the app itself the way sd_employee_auth does.
--
-- One row per (license_hash, month). "month" is the shop's render month in 'YYYY-MM' form
-- (UTC-based, same convention as api/claude.js's per-day demo counter). count increments by 1
-- per successful render (a render that fails validation or gets refused by the cap itself does
-- not increment -- see api/sd-render.js).
--
-- KNOWN LIMITATION (disclosed, not hidden -- same honesty standard as api/claude.js's own
-- demoCallCounts comment): the increment in api/sd-render.js is read-current-count-then-write,
-- not a single atomic UPDATE ... SET count = count + 1. Two renders landing on the same shop in
-- the same instant could under-count by one. Acceptable at this feature's real volume (a stone
-- shop doing at most ~75/month, essentially never truly concurrent) -- if usage ever grows to
-- where that matters, replace with a Postgres function (e.g. an UPSERT ... ON CONFLICT DO UPDATE
-- SET count = sd_render_usage.count + 1) for a real atomic increment.
--
-- Design note: no RLS policy defined, on purpose -- same reasoning as sd_employee_auth and
-- bridge_data/network_insights: read/write exclusively via api/sd-render.js and api/sd-data.js
-- using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The anon key is never used
-- against this table.

create table if not exists sd_render_usage (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  month text not null,          -- 'YYYY-MM', UTC
  count integer not null default 0,
  updated_at timestamptz not null default now(),
  unique (license_hash, month)
);

create index if not exists sd_render_usage_license_month_idx
  on sd_render_usage (license_hash, month);
