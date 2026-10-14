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
  role text not null check (role in ('owner','nursing','med_aide','caregiver','billing','activities','office_manager')),
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

-- ═══════════════════════════════════════════════════════════════════════════
-- THE office_manager WIDENING -- 2026-10-14, ONE IDEMPOTENT BLOCK
-- ═══════════════════════════════════════════════════════════════════════════
-- RUN THIS. The `create table if not exists` above does NOT amend an existing
-- table -- it skips it, constraint and all -- so on the live database
-- 'office_manager' is REJECTED until these two statements run, even though the
-- inline list above now carries it. A re-run of the file alone reports success
-- and changes nothing: the same silent no-op that cost thirteen audit logs
-- their tamper-evidence until 2026-10-13.
--
-- WHAT IS BROKEN UNTIL IT RUNS: api/_lib/auth.js mints the role, api/alf-auth.js
-- accepts it at `setup`, and the INSERT is then refused 23514 by the database.
-- The app believes the role exists and credential creation fails at the last
-- step.
--
-- IDEMPOTENT BY CONSTRUCTION: `drop constraint if exists` makes the `add` safe
-- on a second run, and the name is the one Postgres generates for the inline
-- CHECK above (<table>_<column>_check).
--
-- SAFE AGAINST EXISTING ROWS: the new list is a strict SUPERSET of the old six,
-- so every stored row satisfies it and the validation scan cannot fail.
--
-- THE FULL LIST IS RESTATED rather than appended to, because `add constraint`
-- replaces the whole predicate. Dropping a value here would REVOKE it, so the
-- six already permitted are all present below -- checked against the inline
-- CHECK above, not retyped from memory.
--
-- sql/sairncare_all_remaining_migrations.sql DECLARES THE SAME TABLE and
-- carries the same widened inline list. This ALTER is NOT duplicated there: it
-- acts on the table by name and running it once is enough whichever file built
-- it.
alter table public.sairncare_employee_auth
  drop constraint if exists sairncare_employee_auth_role_check;
alter table public.sairncare_employee_auth
  add constraint sairncare_employee_auth_role_check
  check (role in ('owner','nursing','med_aide','caregiver','billing',
                  'activities','office_manager'));

-- VERIFY. Expect exactly 1 row, and the definition must contain
-- 'office_manager'.
select pg_get_constraintdef(c.oid) as role_check
  from pg_constraint c
 where c.conname = 'sairncare_employee_auth_role_check';
