-- sql/sairnscape_org_intel_schema.sql
-- SAIRNscape Organization Intelligence Layer -- Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as the other
-- *_schema.sql files) before api/org-intel.js's query/save actions will
-- work. Until this runs, action:query returns an empty insights list
-- (not an error) and action:save returns a clear NOT_PROVISIONED error
-- rather than a generic 500.
--
-- WHY THIS EXISTS: the client-side getOrgIntelligence()/saveOrgIntelligence()
-- functions and their "Organization Intelligence Layer" UI (location-switcher
-- modal, org badge) were already present in sairnscape.html before this
-- session touched it -- built, never wired into sendMessage(), and calling
-- a /api/org-intel URL that had never actually been committed (confirmed:
-- no api/org-intel.js existed in the repo). Rolling out this app's shared-
-- knowledge capability meant completing an already-designed, already-half-
-- built feature, not inventing new scope -- see api/org-intel.js's header
-- for the full reasoning, including why this is genuinely different
-- backend work than every other app in this AI-advancement rollout (which
-- all reused StoneDesk's existing sd_shared_knowledge table/endpoint;
-- SAIRNscape has no license-key system for that table's scoping model to
-- attach to, and the pre-existing client contract here expects a readable
-- insight string, not a word-frequency map).
--
-- SCOPE: org_id is a plain user-typed string (no cryptographic validation --
-- SAIRNscape has no license/auth system at all), so this is unauthenticated
-- by design, matching the app's actual security posture rather than
-- pretending a boundary exists where none does -- same stance as
-- bridge_data (api/bridge.js). One row per insight (append-only log, not
-- one row per org) -- unlike sd_shared_knowledge's single-row-per-license
-- aggregate, "what has each location learned over time" is inherently a
-- list, not a single mergeable blob.

create table if not exists sairnscape_org_intel (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,
  app_id text not null default 'sairnscape',
  location_id text,
  location_name text default 'Main Office',
  insight text not null,
  category text default 'general',
  created_at timestamptz not null default now()
);
create index if not exists idx_org_intel_org_app on sairnscape_org_intel (org_id, app_id, created_at desc);
grant select, insert on public.sairnscape_org_intel to service_role;
