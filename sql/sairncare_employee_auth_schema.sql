-- sql/sairncare_employee_auth_schema.sql
-- SAIRNcare (assisted living) per-employee RBAC credentials -- Supabase
-- schema. Run this once before api/alf-auth.js's bootstrap/login/setup
-- actions will work.
--
-- Ground-up app, never had a shared-PIN scaffold to replace -- same
-- starting point as SAIRNlegacy/SAIRNlaw/SAIRNbuild/SAIRNsenior. Real
-- per-employee identity is the prerequisite for the resident privacy gate
-- this app is built around (api/sd-data.js's alf_clients branch): a Med
-- Aide or Caregiver must only ever see residents assigned to them.
--
-- Modelled directly on sql/sairnsenior_employee_auth_schema.sql -- same
-- shape, same explicit grants (StoneDesk's fe730e2 real 502 incident
-- taught this platform that ALTER DEFAULT PRIVILEGES does not reliably
-- auto-grant to service_role for tables created in the SQL editor).
--
-- Role vocabulary: owner (Administrator/Executive Director), nursing
-- (Resident Care Director / Director of Nursing), med_aide, caregiver,
-- billing (Business Office), activities (Activities Coordinator) -- see
-- api/_lib/auth.js's ROLES_BY_APP.sairncare for the full reasoning, and
-- docs/superpowers/specs/2026-08-20-sairncare-v1-scope.md for why this
-- role list is scoped from research, not a real signed SOP.

create table if not exists sairncare_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','nursing','med_aide','caregiver','billing','activities')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairncare_employee_auth_license
  on sairncare_employee_auth (license_hash);

alter table sairncare_employee_auth enable row level security;
drop policy if exists "svc only sairncare_employee_auth" on sairncare_employee_auth;
create policy "svc only sairncare_employee_auth" on sairncare_employee_auth
  for all using (false) with check (false);

-- No DELETE grant, matching every other employee_auth table on this
-- platform -- deactivation is active=false, not a row delete.
grant select, insert, update on sairncare_employee_auth to service_role;
revoke all on sairncare_employee_auth from anon, authenticated;

-- Verify after running (expect 0, no error):
--   select count(*) from sairncare_employee_auth;
