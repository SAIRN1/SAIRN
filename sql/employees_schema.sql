-- sql/employees_schema.sql
-- The migration file for public.employees, written 2026-08-26.
--
-- ══ THIS TABLE HAS BEEN LIVE IN PRODUCTION SINCE LONG BEFORE THIS FILE ═════
-- Not a new table. `employees` is the cross-app roster the SAIRN Data Bridge
-- actually runs on -- the shared resource ten apps read, per Guardian v2's
-- corrected Bridge rule -- and it has had no migration file anywhere in the
-- repo. Found 2026-08-25 from two directions: from the code side (a registered
-- resource whose real table has no `create table` in sql/), and as one of the
-- 25 `live_but_not_declared` rows returned by
-- sql/provisioning_gap_check_2026-08-25.sql.
--
-- Of the three tables found that way, this is the one whose absence mattered
-- most structurally: it is shared infrastructure, not one app's storage, so a
-- rebuild from sql/ would have taken the roster out from under every app that
-- reads it.
--
-- EVERY COLUMN, CONSTRAINT AND INDEX BELOW WAS READ OUT OF THE LIVE DATABASE
-- via sql/introspect_undeclared_tables_2026-08-26.sql on 2026-08-26, not
-- inferred. The code-side prediction named customer_email, employee_id,
-- source_app, status, data and updated_at and correctly derived
-- UNIQUE(customer_email, employee_id) from `?on_conflict=` at
-- api/sd-data.js:432 -- but could not see `id`, the defaults, the size CHECK,
-- or the three-column index.
--
-- Safe to re-run. See DISCLOSED FINDINGS for what this file does not change.
--
-- ══ DISCLOSED FINDING 1 -- this table is scoped by customer_email, NOT ══════
-- ══ license_hash. Confirmed live. It is the only one on the platform. ══════
-- Every other data-carrying table on this platform keys on `license_hash`,
-- a sha256 of the licence key that never leaves the server. This one keys on
-- `customer_email`, and `UNIQUE(customer_email, employee_id)` makes that the
-- real tenancy boundary -- it is what decides which roster a write lands in.
--
-- This was predicted from the code and is now confirmed against the database,
-- so it is not an accident of one call site. Two consequences worth stating
-- plainly before anyone copies the pattern:
--   * The tenancy key is a mutable, human-facing identifier. Two licences
--     sharing a customer_email share a roster; a customer_email that changes
--     orphans one.
--   * It is a different trust class from license_hash. `license_hash` is
--     derived server-side from a bearer secret; `customer_email` is an
--     attribute read from the licence row (api/sd-data.js:419 takes it from
--     `lic`, not from the request body -- that part is correct and should stay
--     that way).
--
-- THIS FILE DOES NOT CHANGE THE KEY. Re-keying a live shared table used by ten
-- apps is not a migration-file decision, and writing it down is the point:
-- this file makes the choice visible instead of leaving it implicit in a table
-- nobody had declared. Decide deliberately, then change it deliberately.
--
-- ══ DISCLOSED FINDING 2 -- anon/authenticated hold TRUNCATE, and the revoke ══
-- ══ line below is the ONLY statement in this file that changes live state ══
-- Live grants as introspected 2026-08-26:
--     service_role   INSERT, SELECT, UPDATE          <- correct, no DELETE
--     anon           TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--     authenticated  TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--
-- service_role is already correct, so this table was NOT missed by the
-- 2026-08-25 DELETE sweep. The anon/authenticated verbs are the Supabase
-- default-ACL baseline removed elsewhere by sql/append_only_grant_audit.sql
-- and the 2026-08-24 TRUNCATE sweep; this table was never in scope for either,
-- because neither could see a table with no schema file. On a SHARED table
-- this one is worth weighing on its own terms -- a stray TRUNCATE here empties
-- the roster for every app at once.
--
-- The revoke line is written in because it is the house idiom
-- (sql/sairnroofing_billing_schema.sql) and a table re-provisioned from this
-- file should not inherit the problem. On the EXISTING live table it is not
-- inert. Running it is the platform-privilege work's call, not this file's.

--
-- ══ TWO SMALL THINGS THAT ARE INFERRED, NOT REPORTED -- stated so they can be ══
-- ══ checked rather than trusted ════════════════════════════════════════════
-- 1. `default gen_random_uuid()` on the primary key. The introspection summary
--    gave the column as `id uuid pk` without quoting its default. The default
--    is inferred, and inferred on solid ground: no writer on any path sends
--    `id`, and every insert succeeds, which cannot both be true unless the
--    column defaults server-side. Confirm against section 1's `column_default`
--    and correct this line if it differs -- the database wins.
-- 2. The CHECK constraint NAME below is this file's own, since the summary
--    reported the constraint's definition rather than its identifier. That is
--    harmless by construction: the guard around it matches on the definition,
--    not the name, so re-running cannot duplicate an existing differently-named
--    constraint. A fresh provision simply gets this name.

-- ---------------------------------------------------------------------------
-- 1. Table
-- ---------------------------------------------------------------------------
create table if not exists public.employees (
  id             uuid        primary key default gen_random_uuid(),
  employee_id    text        not null,   -- client-supplied; the app's own id
  source_app     text        not null,   -- which app wrote the row ('sairnbiz')
  -- Nullable live, and the writer always supplies it, defaulting to 'Active'
  -- in JS rather than in the column (api/sd-data.js:423). Left nullable to
  -- match the database exactly; adding a default here would mask a writer that
  -- stopped sending it.
  status         text,
  -- The tenancy key. See DISCLOSED FINDING 1 before touching this.
  customer_email text        not null,
  data           jsonb       not null default '{}'::jsonb,
  updated_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------
-- UNIQUE(customer_email, employee_id) is load-bearing: the roster write at
-- api/sd-data.js:432 posts `?on_conflict=customer_email,employee_id` with
-- `Prefer: resolution=merge-duplicates` to upsert a whole roster in one
-- request. Without this constraint that request fails outright rather than
-- silently duplicating -- which is the safer failure, but it is a failure.
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.employees'::regclass
       and contype  = 'u'
       and pg_get_constraintdef(oid) = 'UNIQUE (customer_email, employee_id)'
  ) then
    alter table public.employees
      add constraint employees_customer_email_employee_id_key
      unique (customer_email, employee_id);
  end if;
end $$;

-- 64 KB ceiling on the JSON payload, matching every other data-carrying table.
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.employees'::regclass
       and contype  = 'c'
       and pg_get_constraintdef(oid) like '%65536%'
  ) then
    alter table public.employees
      add constraint employees_data_size
      check (octet_length(data::text) <= 65536);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Indexes
-- ---------------------------------------------------------------------------
-- The pkey and the unique constraint bring their own. This three-column index
-- exists live and would be lost in a rebuild. It is wider than the unique
-- constraint's index and covers the shape the readers actually use: scoped to
-- a customer, narrowed by which app wrote the row and whether the employee is
-- still active -- the "active roster for this app" query the auth endpoints
-- run (api/sb-auth.js, api/rf-auth.js:340, api/bld-auth.js:274,
-- api/alf-auth.js:253).
create index if not exists idx_emp_scope
  on public.employees (customer_email, source_app, status);

-- ---------------------------------------------------------------------------
-- 4. RLS -- service-role only
-- ---------------------------------------------------------------------------
alter table public.employees enable row level security;
drop policy if exists "svc only employees" on public.employees;
create policy "svc only employees" on public.employees
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- 5. Grants -- revoke first, then grant only the verbs the code uses
-- ---------------------------------------------------------------------------
-- `revoke all` before `grant`: ALTER DEFAULT PRIVILEGES in this project grants
-- service_role a baseline on every new relation in public, so a bare grant
-- never describes the real end state. See sql/append_only_grant_audit.sql.
--
-- Verbs: SELECT, INSERT, UPDATE. No DELETE. Note what that means on a shared
-- roster -- an employee is deactivated by status, never removed, which is also
-- what the credential-deactivation lifecycle in `sairn-app-scaffold` requires
-- (set_active with a last-admin refusal and an audit row on every outcome).
-- Do NOT re-add `delete` here when fixing a missing grant.
--
-- The read side of this resource is gated in code as well as by grant:
-- api/sd-data.js checks `verifySessionToken(token, license_hash, expectedApp)`
-- WITH the third argument, which is Guardian Check 28 and exists because
-- 'owner' is a valid role in more than one app's vocabulary. The grant is the
-- floor, not the gate.
revoke all on public.employees from service_role;
grant select, insert, update on public.employees to service_role;

-- THE ONE NON-INERT STATEMENT IN THIS FILE. See DISCLOSED FINDING 2.
-- No-op on a fresh provision; on the existing live table it removes
-- TRUNCATE/REFERENCES/TRIGGER that anon and authenticated hold right now.
-- On a table ten apps share, that TRUNCATE is worth removing on its own
-- merits -- but it is still a live change. Comment it out to declare only.
revoke all on public.employees from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 6. Verify after running
-- ---------------------------------------------------------------------------
--   select count(*) from public.employees;
--     -- expect the real row count, NOT 0. Live shared data.
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid = 'public.employees'::regclass order by contype;
--     -- expect PRIMARY KEY (id), UNIQUE (customer_email, employee_id),
--     -- and the 65536 CHECK
--
--   select indexname from pg_indexes
--    where schemaname = 'public' and tablename = 'employees' order by 1;
--     -- expect 3: the pkey, the unique constraint's index, and idx_emp_scope
