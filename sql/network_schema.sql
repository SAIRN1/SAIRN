-- sql/network_schema.sql
-- SAIRN Intelligence Network (api/network.js) — Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as
-- sql/agent_schema.sql / bridge_data) before api/network.js's GET/POST
-- actions will work. Until this runs, both return a clear 503
-- NOT_PROVISIONED rather than a generic 500.
--
-- Check 0e (searched before creating this): probed 8 plausible existing
-- table names via the project's public anon/publishable key (already
-- shipped client-side, not a secret). None matched. Two unrelated-sounding
-- tables surfaced via PostgREST's "perhaps you meant" error hints --
-- webhook_events, demo_calls -- neither reused: no safe service-role
-- access from this session to confirm their actual schema/purpose, and
-- guessing wrong risks writing into an unrelated system. Worth a human
-- check in the Supabase dashboard, but this migration does not assume
-- either is a fit.
--
-- Design: one row per anonymized signal (an append-only event log, not a
-- per-tenant snapshot like bridge_data) -- app_id + a short type/pattern
-- pair + optional score. api/network.js's own POST handler enforces that
-- type/pattern can only be short bare identifiers (no free text at all),
-- which is what actually keeps PII/prices/names out -- structurally, not
-- via a scrub step here. No shop/customer identity is ever stored: app is
-- the app_id (e.g. 'stonedesk'), not a per-shop key, matching the client
-- comment's own framing ("anonymized patterns from other stonedesk
-- installs" -- cross-shop aggregate, not per-shop).
--
-- Design note: no RLS policy defined on purpose, same reasoning as
-- bridge_data -- read/write exclusively via api/network.js using
-- SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless. The anon key
-- is never used against this table.

create table if not exists network_insights (
  id uuid primary key default gen_random_uuid(),
  app text not null,
  type text not null,
  pattern text not null,
  score numeric,
  created_at timestamptz not null default now()
);

create index if not exists idx_network_insights_app_created_at
  on network_insights (app, created_at desc);

create index if not exists idx_network_insights_type_pattern
  on network_insights (type, pattern);
