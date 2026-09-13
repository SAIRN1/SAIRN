-- sql/sairnvet_employee_auth_schema.sql
-- SAIRNvet per-employee RBAC credentials -- Supabase schema. Run this once
-- before api/sv-auth.js's bootstrap/login/setup actions will work.
--
-- WHY THIS IS THE LAST ONE, AND WHY IT WAS BUILT OUT OF TURN.
-- SAIRNvet was the SIXTEENTH and final app to get per-employee auth. Fifteen
-- others already shipped api/*-auth.js; `sv` was not among them, and
-- `grep -rln "sv_employee_auth" sql/ api/` returned nothing. Until today the
-- app authenticated on the LICENCE KEY ONLY -- sairnvet.html says so in its
-- own words at :2011: "`role` is a self-selected dropdown, never
-- server-verified."
--
-- That mattered more here than anywhere else on the platform. SAIRNvet holds
-- `sv_controlled`, which api/_resources/sairnvet.js calls "the
-- controlled-substance register (DEA-relevant)", and `sv_audit_log`, its
-- dosing trail. `python tools/removal_path_check.py --burn-down` ranks
-- sv_controlled TIER A WITH NO REMOVAL PATH: a wrong row cannot be taken back
-- through the product at all. So the one app on the platform whose sharpest
-- record is legally permanent was the one that knew which PRACTICE was
-- writing and never which PERSON.
--
-- Found 2026-09-13 while scoping the irreversible-write witnessing lock
-- (docs/2026-09-13-irreversible-write-witnessing-scoping.md), where it is
-- named as the hard prerequisite rather than a detail: a lock that records
-- "the practice confirmed it" is theatre.
--
-- Modelled on sql/sairnroofing_employee_auth_schema.sql, which is the cleanest
-- of the family and the only one carrying the leading REVOKE ALL.
--
-- Role vocabulary: owner (Owner/DVM), dvm (Associate DVM), tech (Veterinary
-- Technician), assistant (Veterinary Assistant), manager (Practice Manager),
-- frontdesk -- READ OUT OF THE APP'S OWN staff roster dropdown
-- (sairnvet.html:1365 and :6887) rather than invented. See
-- api/_lib/auth.js's ROLES_BY_APP.sairnvet for the full note, including why
-- the roster's seventh option 'Other' is deliberately NOT a role.
--
-- THIS FILE CREATES A TABLE AND WRITES NO CREDENTIAL ROWS. There is no seed
-- here and there must never be one: a PIN committed to the repo is a PIN in
-- every clone's history forever. The first credential is minted through
-- api/sv-auth.js's `bootstrap` action, by whoever holds the licence key, and
-- that action refuses once ANY row exists for the licence.

create table if not exists public.sairnvet_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  -- The role list is duplicated here as a CHECK on purpose: the constraint is
  -- the database's own guarantee and does not depend on the API being the only
  -- writer. It must be kept in step with ROLES_BY_APP.sairnvet -- an
  -- unsynchronised pair would let signSessionToken mint a role the table
  -- refuses, which surfaces as an unexplained insert failure at first setup.
  role text not null check (role in ('owner','dvm','tech','assistant','manager','frontdesk')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnvet_employee_auth_license
  on public.sairnvet_employee_auth (license_hash);

alter table public.sairnvet_employee_auth enable row level security;
drop policy if exists "svc only sairnvet_employee_auth" on public.sairnvet_employee_auth;
create policy "svc only sairnvet_employee_auth" on public.sairnvet_employee_auth
  for all using (false) with check (false);

-- NO DELETE GRANT, matching every other employee_auth table on this platform.
-- Deactivation is active=false, never a row delete: the row preserves
-- created_at, role history, and -- here more than anywhere -- the identity any
-- sv_controlled or sv_audit_log entry was written under. Deleting a credential
-- row in this app would orphan the author of a DEA-relevant record.
--
-- REVOKE ALL FIRST. Without it the table inherits TRUNCATE/REFERENCES/TRIGGER
-- from the platform default ACL, and TRUNCATE on a credentials table wipes
-- every employee's access at once. Only sql/sairnroofing_employee_auth_schema.sql
-- had this before today; it is not optional here.
revoke all on public.sairnvet_employee_auth from service_role;
grant select, insert, update on public.sairnvet_employee_auth to service_role;
revoke all on public.sairnvet_employee_auth from anon, authenticated;

-- ── VERIFY AFTER RUNNING, one query per statement with its expected answer ──
-- A count at the end of the file cannot tell a full apply from a partial one.
--
--   select count(*) from public.sairnvet_employee_auth;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnvet_employee_auth' and grantee = 'service_role';
--     -- expect 3 (SELECT, INSERT, UPDATE). A 4th is a DELETE or TRUNCATE that
--     -- should not be there; 0 is the 42501 that looks like nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnvet_employee_auth' and grantee in ('anon','authenticated');
--     -- expect 0.
--
--   select rolname from pg_roles where rolname = 'service_role';
--     -- expect one row. If this is empty the grants above silently did nothing.
