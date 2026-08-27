-- sql/sairnmechanical_employee_auth_schema.sql
-- SAIRNmechanical per-employee RBAC credentials -- Supabase schema.
-- 2026-08-27.
--
-- Run this once in the Supabase SQL editor before api/mech-auth.js's
-- bootstrap/login/setup actions will work. Until it runs they return a clear
-- 503 NOT_PROVISIONED rather than a generic 500.
--
-- ── WHY THIS EXISTS ────────────────────────────────────────────────────
-- SAIRNmechanical was written 2026-06-14 on branch
-- origin/claude/lucid-ptolemy-b73vu0 and NEVER MERGED to main. The app route
-- returned 404 correctly for two months because the file was not in the tree;
-- Guardian's App File Map claimed otherwise and was corrected 2026-08-27.
--
-- It is being recovered now, and it is NOT being landed in its June state at
-- any point. As written it carried
--     var DEFAULT_PINS = {"owner":"1234","tech":"2345","sales":"3456","admin":"4567"};
-- compared in the BROWSER, with the role kept in a local variable -- the same
-- client-only pattern StoneDesk, SAIRNcode and SAIRNdental were each
-- remediated for, the last of them earlier the same day this file was written.
-- Committing the file first and fixing auth afterwards was explicitly refused:
-- vercel.json builds with `cp *.html dist/`, so ANY root .html is served the
-- moment it lands, route or no route. There is no safe intermediate state.
--
-- NOTE ON SCOPE, stated rather than implied: SAIRNmechanical has no
-- server-side data layer yet -- no MECH_RESOURCES branch in api/sd-data.js,
-- and its only server writes go to api/bridge.js's unauthenticated push. So
-- this table gates the APP'S OWN LOGIN, and there is not yet protected data
-- behind it. That is still worth doing -- it removes four published passwords
-- and gives a real identity for when a data layer lands -- but it should not
-- be described as securing data it does not yet touch.
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw licence key) scopes rows to a practice, matching
-- every other *_employee_auth table's convention.
--
-- Design note: no RLS policy beyond deny-all is needed -- read/write happens
-- exclusively via api/mech-auth.js using SUPABASE_SERVICE_ROLE_KEY, which
-- bypasses RLS regardless. The anon key never touches this table.

create table if not exists public.sairnmechanical_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','admin','sales','tech')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnmechanical_employee_auth_license
  on public.sairnmechanical_employee_auth (license_hash);

alter table public.sairnmechanical_employee_auth enable row level security;
drop policy if exists "svc only sairnmechanical_employee_auth" on public.sairnmechanical_employee_auth;
create policy "svc only sairnmechanical_employee_auth" on public.sairnmechanical_employee_auth
  for all using (false) with check (false);

-- Explicit grants. `revoke all` first, then grant, per
-- sql/append_only_grant_audit.sql -- Supabase's ALTER DEFAULT PRIVILEGES does
-- not reliably auto-grant to service_role for tables created in the SQL
-- editor, which is the real 502 StoneDesk hit in fe730e2.
--
-- NO DELETE, deliberately: nothing in api/mech-auth.js deletes a credential
-- row -- deactivation is active=false -- so withholding it costs nothing and
-- removes a way to lose an audit subject. Do NOT re-add `delete` here when
-- fixing a missing grant.
--
-- UPDATE IS REQUIRED and is not optional padding: login PATCHes
-- failed_attempts and locked_until, and set_active flips active. A
-- select+insert grant would make every failed-login lockout silently fail --
-- exactly the ON CONFLICT DO UPDATE class of bug that broke
-- sairncash_waitlist on 2026-08-25.
revoke all on public.sairnmechanical_employee_auth from service_role;
grant select, insert, update on public.sairnmechanical_employee_auth to service_role;
revoke all on public.sairnmechanical_employee_auth from anon, authenticated;

-- Verify after running:
--   select count(*) from public.sairnmechanical_employee_auth;   -- expect 0
--
-- Confirm the grants (expect exactly INSERT, SELECT, UPDATE -- no DELETE):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'sairnmechanical_employee_auth';
--
-- Then confirm LIVE, which is the real proof -- a clean SQL run is not
-- evidence the app can reach it:
--   POST /api/mech-auth {"action":"bootstrap","employee_id":"...","pin":"123456"}
--   with a valid MECH- licence. 503 NOT_PROVISIONED means this file has not run.
