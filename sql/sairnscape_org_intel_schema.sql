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

-- ── b29 (2026-10-20), BEFORE THIS FILE HAS EVER BEEN RUN ─────────────────────
-- "Unauthenticated by design" above is about the APP. It was never meant to
-- extend to the DATABASE, and as first written it did: no RLS, no revoke, so
-- the table would have been created holding whatever the project's default ACL
-- gives anon and authenticated -- readable and writable straight through
-- PostgREST with the public anon key, around api/org-intel.js entirely. RLS is
-- now on with no policy (service_role bypasses RLS, so the endpoint is
-- unaffected), anon/authenticated lose every privilege, and service_role is
-- reset to exactly the two verbs the endpoint calls (insert at org-intel.js:94,
-- select at :124 and :131). The table name is schema-qualified so the CREATE
-- and the GRANT cannot land in different schemas on an unusual search_path.
-- Safe to re-run: every statement is idempotent.

create table if not exists public.sairnscape_org_intel (
  id uuid primary key default gen_random_uuid(),
  org_id text not null,
  app_id text not null default 'sairnscape',
  location_id text,
  location_name text default 'Main Office',
  insight text not null,
  category text default 'general',
  created_at timestamptz not null default now()
);
create index if not exists idx_org_intel_org_app on public.sairnscape_org_intel (org_id, app_id, created_at desc);

alter table public.sairnscape_org_intel enable row level security;
revoke all on public.sairnscape_org_intel from anon, authenticated;
revoke all on public.sairnscape_org_intel from service_role;
grant select, insert on public.sairnscape_org_intel to service_role;

-- ── VERIFY (read-only) ─────────────────────────────────────────────────────
-- Expect exactly three rows: rls_enabled = true, then service_role INSERT and
-- service_role SELECT. Any anon or authenticated row, or rls_enabled = false,
-- is a failed run, not a pass.
select 'rls_enabled' as what, relrowsecurity::text as value
  from pg_class where oid = 'public.sairnscape_org_intel'::regclass
union all
select grantee || ' ' || privilege_type, 'granted'
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'sairnscape_org_intel'
   and grantee in ('anon', 'authenticated', 'service_role')
 order by 1;
