-- sql/bridge_schema.sql
-- SAIRN Bridge (api/bridge.js) — Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as
-- sql/agent_schema.sql) before api/bridge.js's "push"/"pull" actions will
-- work. Until this runs, push/pull return a clear 503 NOT_PROVISIONED
-- rather than a generic 500 — that error message points back here.
--
-- Only push/pull need this table. api/bridge.js's third action, proxy_get
-- (the FRED/homebuyer.com relay used by StoneDesk's and SAIRNbuild's Market
-- Intelligence panels), is stateless and works with no schema at all.
--
-- Design note: no RLS policy is defined here on purpose. The row is written/
-- read exclusively via api/bridge.js using SUPABASE_SERVICE_ROLE_KEY, which
-- bypasses RLS regardless — the browser anon key is never used against this
-- table (same model as business_profiles/ai_memories/sd_slabs in
-- api/sd-data.js). If a future change adds direct anon-key access to this
-- table, add RLS at that point, not before it's actually needed.
--
-- shop_id is a plain text tenant key (matches what StoneDesk's sdShopId()
-- already sends), not license_hash — the two live callers (syncToSAIRNBridge,
-- the Field Map/Check-Register expense push) send no Authorization header at
-- all, so there is no license to hash. This intentionally does not carry the
-- same auth/tenancy guarantee api/sd-data.js's tables do.

create table if not exists bridge_pushes (
  id uuid primary key default gen_random_uuid(),
  shop_id text not null,
  jobs jsonb,
  invoices jsonb,
  employees jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_bridge_pushes_shop_id_created_at
  on bridge_pushes (shop_id, created_at desc);
