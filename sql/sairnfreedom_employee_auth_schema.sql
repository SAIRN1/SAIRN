-- sql/sairnfreedom_employee_auth_schema.sql
-- SAIRNfreedom per-employee credentials -- Supabase schema. Run this ONCE
-- before api/sf-auth.js's bootstrap/login/setup actions will work, and before
-- the session gate on sf_accounts / sf_ledger / sf_vendor_prices is armed.
--
-- ── WHY THIS EXISTS AND WHY IT IS FIRST ───────────────────────────────────
-- SAIRNfreedom had NO employee auth at all. Measured 2026-09-21 while building
-- the cross-tenant isolation arms: api/sd-data.js's SF_RESOURCES dispatcher
-- serves 35 resources, THREE of them Tier A -- sf_accounts, sf_ledger,
-- sf_vendor_prices -- and neither its read nor its write branch carried a
-- session check of any kind. The LICENCE KEY was the entire authorisation, and
-- the licence key is shipped to the browser and readable by anyone who can open
-- the app. Same shape the platform already recorded for law_trusttx, which was
-- swept into SD_SESSION_GATED on 2026-09-16; SAIRNfreedom was not swept with it.
--
-- THE TENANT BOUNDARY WAS NEVER THE PROBLEM and is asserted:
-- api/sd-data-cross-tenant-dispatchers.test.js drives all three and they filter
-- by license_hash correctly. This is identity WITHIN a tenant -- who inside the
-- post may read the general ledger -- plus the audit half, which never shows up
-- as a refusal: a write with no session has no employee_id to record, so the
-- ledger cannot say who made an entry.
--
-- ── THE ROLE VOCABULARY IS THE APP'S OWN, LIFTED NOT INVENTED ─────────────
-- sairn-employee-auth-scaffold says the per-app role vocabulary is an explicit
-- judgment call every time and never a silent copy. Here the app had already
-- made that call and written down its reasoning, so this lifts it rather than
-- deciding again: sairnfreedom.html's CAPABILITIES array, with the comment
-- "Capabilities are the enum. Officer titles are display, mapped per org type."
--
-- The reasoning that comment records, and it is why a generic owner/admin/staff
-- list would have been WRONG here: a VFW finance officer is the Quartermaster,
-- an Elks one is the Treasurer, a Moose one is the Treasurer under a Governor
-- rather than a Commander. The app maps five org types (American Legion, VFW,
-- Elks, Moose, Eagles) onto ONE stable capability set, and its own words are
-- "hardcoding one vocabulary would be wrong for three of the five target
-- orders". The capability id is the stable thing; the title is display.
--
-- So the `role` column holds a CAPABILITY ID, and the ELEVEN values below are
-- sairnfreedom.html's CAPABILITIES list verbatim. If that array ever changes,
-- this check constraint and ROLES_BY_APP.sairnfreedom must change with it --
-- three copies of one list, which is a real drift risk.
--
-- NAMING THE RISK IS WHAT THIS PARAGRAPH USED TO DO, AND IT WAS NOT ENOUGH.
-- `trustee.audit` was added to sairnfreedom.html on 2026-09-27 and reached
-- neither of the other two copies for sixteen days, so a post could assign the
-- Trustee office and then could not give that trustee a sign-in. As of
-- 2026-10-13 the agreement is CHECKED: api/role-vocabulary-agreement.test.js
-- parses this CHECK out of this file and compares it to ROLES_BY_APP in both
-- directions, for every app with an employee_auth table, not just this one.
--
-- PROVISIONING: post.govern and post.govern.deputy, taken from the app's own
-- PROVISIONING_CAPS. post.govern carries `sole:true`, which is what the
-- last-admin refusal in api/sf-auth.js's set_active keys on.

create table if not exists sairnfreedom_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  -- ── trustee.audit ADDED 2026-10-13 ON MICHAEL'S DECISION ────────────────
  -- A VFW post trustee gets their own login, view-only on financial records.
  -- Eleven capabilities now, and this list is one of THREE copies -- the others
  -- are ROLES_BY_APP.sairnfreedom in api/_lib/auth.js and CAPABILITIES in
  -- sairnfreedom.html. api/role-vocabulary-agreement.test.js compares this
  -- CHECK against ROLES_BY_APP for EVERY app in both directions, so the drift
  -- this file used to only warn about now fails a test.
  --
  -- RE-RUNNING THIS FILE DOES NOT WIDEN AN EXISTING TABLE. `create table if not
  -- exists` skips it, constraint and all -- the same trap
  -- sql/audit_checkpoint_schema.sql contained until 2026-10-13. The ALTER that
  -- acts on a live table is the idempotent block at the FOOT OF THIS FILE, and
  -- it must be run.
  role text not null check (role in (
    'post.govern',
    'post.govern.deputy',
    'records.write',
    'finance.write',
    'trustee.audit',
    'member.admit',
    'services.refer',
    'legal.review',
    'history.write',
    'ceremonial.manage',
    'chaplain.pastoral'
  )),
  pin_hash text not null,
  pin_salt text not null,
  -- The column is `active`. Never `is_active` -- all twelve existing
  -- employee_auth tables agree and this is not the one to differ.
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_sairnfreedom_employee_auth_license
  on public.sairnfreedom_employee_auth (license_hash);

alter table public.sairnfreedom_employee_auth enable row level security;
drop policy if exists "svc only sairnfreedom_employee_auth" on public.sairnfreedom_employee_auth;
create policy "svc only sairnfreedom_employee_auth" on public.sairnfreedom_employee_auth
  for all using (false) with check (false);

-- ── THE GRANTS, AND THE LEADING REVOKE, WHICH IS NOT DECORATION ──────────
-- NO DELETE GRANT, EVER. Nothing on this platform deletes a credential row --
-- deactivation is active=false. Withholding it costs nothing and removes a way
-- to lose an audit subject. SAIRNscape once granted it by writing the full CRUD
-- verb list reflexively and had to walk it back.
--
-- THE LEADING `revoke all ... from service_role` MATTERS and only SAIRNroofing
-- had it before this file. Without it the table inherits TRUNCATE / REFERENCES
-- / TRIGGER from the platform default ACL, and TRUNCATE on a credentials table
-- wipes every employee's access at once. A GRANT only ever adds; it cannot take
-- that away.
--
-- AND THE GRANTS ARE WRITTEN INTO THE FILE rather than assumed from ALTER
-- DEFAULT PRIVILEGES. SAIRNbiz shipped without them and every employee login
-- broke in production with a 42501; SAIRNlaw hit the same thing live.
revoke all on public.sairnfreedom_employee_auth from service_role;
grant select, insert, update on public.sairnfreedom_employee_auth to service_role;
revoke all on public.sairnfreedom_employee_auth from anon, authenticated;

-- Verify after running (expect 0, no error):
--   select count(*) from public.sairnfreedom_employee_auth;
--
-- And confirm the grants landed -- a missing one is a 42501 that looks like
-- nothing else:
--   select privilege_type from information_schema.role_table_grants
--    where table_name = 'sairnfreedom_employee_auth' and grantee = 'service_role';
--   -- expect exactly SELECT, INSERT, UPDATE

-- ═══════════════════════════════════════════════════════════════════════════
-- THE trustee.audit WIDENING -- 2026-10-13, ONE IDEMPOTENT BLOCK, RUN IT
-- ═══════════════════════════════════════════════════════════════════════════
-- WHY THIS EXISTS SEPARATELY FROM THE `create table` ABOVE: `create table if
-- not exists` SKIPS AN EXISTING TABLE, CONSTRAINT AND ALL. So on a database
-- where this file has already been run, re-running it to pick up the eleventh
-- capability reports success and changes NOTHING -- a silent no-op that reads
-- exactly like a successful migration. That trap cost thirteen audit logs their
-- tamper-evidence until 2026-10-13; this is the same shape, caught at the point
-- of writing instead.
--
-- IDEMPOTENT BY CONSTRUCTION, not by convention: `drop constraint if exists`
-- makes the `add` safe on a second run, and the name is the one Postgres
-- generates for the inline CHECK above, so this acts on a table created by
-- either printing of this file.
--
-- SAFE AGAINST EXISTING ROWS: the new list is a strict SUPERSET of the old ten,
-- so every row already stored satisfies the new constraint and the validation
-- scan cannot fail.
--
-- NOT WRAPPED IN A DO BLOCK, deliberately: a constraint failure inside
-- PL/pgSQL can be caught and reported as a NOTICE, and a widening that silently
-- did nothing is the exact failure this block exists to end.
alter table public.sairnfreedom_employee_auth
  drop constraint if exists sairnfreedom_employee_auth_role_check;
alter table public.sairnfreedom_employee_auth
  add constraint sairnfreedom_employee_auth_role_check
  check (role in (
    'post.govern',
    'post.govern.deputy',
    'records.write',
    'finance.write',
    'trustee.audit',
    'member.admit',
    'services.refer',
    'legal.review',
    'history.write',
    'ceremonial.manage',
    'chaplain.pastoral'
  ));

-- ── VERIFY, with the answer each must give ────────────────────────────────
-- 1. ELEVEN capabilities are permitted. Expect: 11
select count(*)
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z.]+)''', 'g') m
 where c.conname = 'sairnfreedom_employee_auth_role_check';

-- 2. And NAME them, because a count of 11 over the wrong names passes query 1.
--    Expect the eleven above, one per row, INCLUDING trustee.audit.
select m[1] as role
  from pg_constraint c,
       lateral regexp_matches(pg_get_constraintdef(c.oid), '''([a-z.]+)''', 'g') m
 where c.conname = 'sairnfreedom_employee_auth_role_check'
 order by 1;

-- 3. THEN PROVISION A REAL TRUSTEE THROUGH THE API, which is the only thing
--    that proves the whole chain. With a post.govern session token:
--
--      curl -s -X POST https://sairn.vercel.app/api/sf-auth \
--        -H 'Content-Type: application/json' \
--        -H 'Authorization: Bearer SF-PINNACLE-2026' \
--        -H 'X-SD-Auth: <post.govern token>' \
--        -d '{"action":"setup","employee_id":"trustee-1",
--             "display_name":"Post Trustee","role":"trustee.audit","pin":"135790"}'
--
--    200                      -> both halves landed
--    400 with a check         -> this block has NOT been run; the server
--      constraint violation      accepted the role and the database rejected it,
--                                which is the 400 nobody can read
--    403 / UNKNOWN_ROLE       -> the api/_lib/auth.js half is missing instead
