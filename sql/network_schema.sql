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

-- GRANTS -- ADDED 2026-09-01 (Cody). This file shipped 2026-08-01 with no
-- grant statement at all, so re-running it on a fresh project produces a
-- table api/network.js cannot read or write. Source and production have
-- disagreed since creation; this closes that, and it is the reason the
-- disagreement was invisible -- the live table works, so nothing failed.
--
-- WHY IT WORKS LIVE ANYWAY: the table was created through Supabase's Table
-- Editor, which auto-grants, unlike a raw SQL migration. That mechanism is
-- recorded as a hypothesis in sql/full_crud_truncate_sweep_2026-08-24.sql
-- and is not upgraded to a finding here -- what IS verified is the access
-- itself, both halves, below.
--
-- VERIFIED LIVE 2026-09-01 BEFORE WRITING THIS, not inferred from the
-- grant table alone. api/network.js turns a missing grant into a NAMED 503
-- PERMISSION_DENIED (:121 / :211) and a missing table into 503
-- NOT_PROVISIONED (:115 / :207), so a 200 is positive evidence:
--   SELECT: GET  /api/network?app=stonedesk       -> 200 {"ok":true,...}
--   INSERT: POST /api/network {app:sairn_selftest,
--           type:selftest, pattern:insert_path_verification}
--                                                 -> 200 {"ok":true}
-- THE INSERT CALL CLOSES A NAMED OPEN ITEM. full_crud_truncate_sweep's
-- Correction A ends "SELECT confirmed present, INSERT unknown. Do not
-- upgrade that to 'the table is fine' without checking the write path."
-- The write path is now checked. It works. One throwaway row exists under
-- app='sairn_selftest' -- invisible to every real caller, since GET filters
-- app=eq.<app> and suppresses anything under MIN_OCCURRENCES=3.
--
-- WHY select, insert AND NOT THE FULL LIVE SET. The real grant-table
-- export in full_crud_truncate_sweep_2026-08-24.sql:506 reads
-- "INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE". TRUNCATE/REFERENCES/
-- TRIGGER are the create-time default baseline, are used by nothing, and
-- are precisely what that sweep's Section 2 exists to strip platform-wide.
-- Writing them here would re-arm, from source, the excess a pending sweep
-- is meant to remove -- so this grants the intersection of what is live
-- and what api/network.js actually does: SELECT (handleGet) and INSERT
-- (handlePost). There is no UPDATE or DELETE path in the endpoint, and an
-- append-only signal log should not have one. Matches the closest existing
-- analogue, alf_signals, which is also an append-only log granted exactly
-- select, insert.
--
-- CONSEQUENCE, STATED PLAINLY: running this file against the LIVE table
-- today does not revoke anything -- grant only adds. The three excess
-- privileges stay until the sweep runs. This file simply stops being the
-- thing that would put them back.
grant usage on schema public to service_role;
grant select, insert on public.network_insights to service_role;
