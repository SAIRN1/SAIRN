-- sql/sairnroofing_employee_auth_schema.sql
-- SAIRNroofing per-employee RBAC credentials -- Supabase schema. Run this
-- once before api/rf-auth.js's bootstrap/login/setup actions will work.
--
-- Ground-up app, never had a shared-PIN scaffold to replace -- same
-- starting point as SAIRNcare/SAIRNlegacy/SAIRNlaw/SAIRNbuild/SAIRNsenior.
-- Real per-employee identity is the prerequisite for the assignment-based
-- job privacy gate this app is built around (api/sd-data.js's rf_jobs
-- branch, when Phase 4 builds it): a foreman or crew member must only ever
-- see jobs assigned to them.
--
-- Modelled directly on sql/sairncare_employee_auth_schema.sql -- same
-- shape, same explicit grants (StoneDesk's fe730e2 real 502 incident
-- taught this platform that ALTER DEFAULT PRIVILEGES does not reliably
-- auto-grant to service_role for tables created in the SQL editor).
--
-- Role vocabulary: owner, admin (office manager), estimator (combined
-- sales-and-estimating, deliberately one role -- see api/rf-auth.js's
-- header), foreman, crew -- see api/_lib/auth.js's ROLES_BY_APP.sairnroofing
-- and docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md for the
-- full reasoning. Confirmed by Michael 2026-08-24, not invented.

create table if not exists sairnroofing_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','admin','estimator','foreman','crew')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnroofing_employee_auth_license
  on sairnroofing_employee_auth (license_hash);

alter table sairnroofing_employee_auth enable row level security;
drop policy if exists "svc only sairnroofing_employee_auth" on sairnroofing_employee_auth;
create policy "svc only sairnroofing_employee_auth" on sairnroofing_employee_auth
  for all using (false) with check (false);

-- No DELETE grant, matching every other employee_auth table on this
-- platform -- deactivation is active=false, not a row delete.
grant select, insert, update on sairnroofing_employee_auth to service_role;
revoke all on sairnroofing_employee_auth from anon, authenticated;

-- Verify after running (expect 0, no error):
--   select count(*) from sairnroofing_employee_auth;
