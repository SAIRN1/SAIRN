-- sql/sairndental_employee_auth_schema.sql
-- SAIRNdental per-employee RBAC credentials -- Supabase schema.
-- 2026-08-27.
--
-- Run this once in the Supabase SQL editor before api/dnt-auth.js's
-- bootstrap/login/setup actions will work. Until it runs they return a clear
-- 503 NOT_PROVISIONED rather than a generic 500.
--
-- ── WHY THIS EXISTS, AND WHY IT IS URGENT ────────────────────────────────
-- Found 2026-08-27 during a click-through audit, confirmed in source AND live:
-- SAIRNdental had NO authentication of any kind.
--
--   1. sairndental.html:678 carried
--      `var DEFAULT_PINS={owner:'1234',frontdesk:'2345',provider:'3456'};`
--      -- one shared, hardcoded, identical-for-every-customer PIN per role,
--      baked into a PUBLIC repo's client source. chkPin() compared the typed
--      digits in the BROWSER and flipped a CSS class. Role was stored in
--      localStorage and asserted client-side, so any role was self-assertable
--      by editing the DOM.
--   2. api/sd-data.js's DNT_RESOURCES read and write branches contained ZERO
--      verifySessionToken calls, while every other app on the platform gates
--      on it. The server had no idea which employee was acting.
--   3. Proven live, read-only: a POST carrying only the licence key as Bearer,
--      with no session token at all, returned 200 and 8 dnt_patients rows
--      including name and date of birth.
--
-- This is the SAME pattern sql/sairncode_employee_auth_schema.sql describes
-- itself as replacing, word for word. SAIRNcode was fixed. StoneDesk was
-- fixed. SAIRNdental -- the app holding PHI, with a real dentist prospect --
-- was not, and nothing had ever checked.
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN.
-- license_hash (not the raw licence key) scopes rows to a practice, matching
-- every other *_employee_auth table's convention.
--
-- Design note: no RLS policy beyond deny-all is needed -- read/write happens
-- exclusively via api/dnt-auth.js using SUPABASE_SERVICE_ROLE_KEY, which
-- bypasses RLS regardless. The anon key never touches this table.

create table if not exists public.sairndental_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','frontdesk','provider')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairndental_employee_auth_license
  on public.sairndental_employee_auth (license_hash);

alter table public.sairndental_employee_auth enable row level security;
drop policy if exists "svc only sairndental_employee_auth" on public.sairndental_employee_auth;
create policy "svc only sairndental_employee_auth" on public.sairndental_employee_auth
  for all using (false) with check (false);

-- Explicit grants. `revoke all` first, then grant, per
-- sql/append_only_grant_audit.sql -- Supabase's ALTER DEFAULT PRIVILEGES does
-- not reliably auto-grant to service_role for tables created in the SQL
-- editor, which is the real 502 StoneDesk hit in fe730e2.
--
-- NO DELETE, deliberately: nothing in api/dnt-auth.js deletes a credential
-- row -- deactivation is active=false -- so withholding it costs nothing and
-- removes a way to lose an audit subject. Do NOT re-add `delete` here when
-- fixing a missing grant.
--
-- UPDATE IS REQUIRED and is not optional padding: login PATCHes
-- failed_attempts and locked_until, and set_active flips active. A
-- select+insert grant would make every failed-login lockout silently fail --
-- exactly the ON CONFLICT DO UPDATE class of bug that broke
-- sairncash_waitlist on 2026-08-25.
revoke all on public.sairndental_employee_auth from service_role;
grant select, insert, update on public.sairndental_employee_auth to service_role;
revoke all on public.sairndental_employee_auth from anon, authenticated;

-- Verify after running:
--   select count(*) from public.sairndental_employee_auth;   -- expect 0
--
-- Confirm the grants (expect exactly INSERT, SELECT, UPDATE -- no DELETE):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'sairndental_employee_auth';
--
-- Then confirm LIVE, which is the real proof -- a clean SQL run is not
-- evidence the app can reach it:
--   POST /api/dnt-auth {"action":"bootstrap","employee_id":"...","pin":"123456"}
--   with a valid DNT- licence. 503 NOT_PROVISIONED means this file has not run.
