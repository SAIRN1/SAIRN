-- sql/scp_employee_auth_schema.sql
-- SAIRNscape per-employee credentials — Supabase schema
--
-- Run this once in the Supabase SQL editor before api/scp-auth.js's
-- login/setup/bootstrap actions will work.
--
-- Mirrors sql/grd_employee_auth_schema.sql exactly (same design, separate
-- table + separate role vocabulary) — a DELIBERATELY separate identity
-- system from every other app, not a merge, per the platform's standing
-- cross-app-collision discipline (api/_lib/auth.js's ROLES_BY_APP + the
-- signed `app` claim inside each token).
--
-- Roles match SAIRNscape's Phase 1 role picker (Owner/Crew Lead/Office)
-- plus 'owner' already being the bootstrap role, so no separate addition
-- needed there.
--
-- GRANT statements included explicitly this session (2026-08-06) — a
-- known recurring gap flagged after the SAIRNgrounds license-row issue.
-- service_role bypasses RLS by default in Supabase, but being explicit
-- here removes any ambiguity rather than relying on that default silently.

create table if not exists scp_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','crew_lead','office')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_scp_employee_auth_license
  on scp_employee_auth (license_hash);

-- No RLS policy needed for anon/authenticated (service-role only, reached
-- exclusively through api/scp-auth.js and api/sd-data.js) — but grant
-- explicitly to service_role so access never silently depends on the
-- default-bypass behavior alone.
alter table scp_employee_auth enable row level security;
grant usage on schema public to service_role;
grant select, insert, update, delete on scp_employee_auth to service_role;
