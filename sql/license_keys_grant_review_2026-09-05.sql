-- sql/license_keys_grant_review_2026-09-05.sql
-- The dedicated `license_keys` grant review the open-work index has been
-- holding open since 2026-08-25. READ-ONLY THROUGH SECTION 3. Section 4 is the
-- only mutating statement and it ships COMMENTED OUT.
--
-- NOT RUN by any session. No SAIRN clone holds a credential that could: a
-- REVOKE needs the object owner, so this is a hand-off to the Supabase SQL
-- editor, run as `postgres`.
--
-- ── WHY THIS TABLE WAS EXCLUDED FROM BOTH PREVIOUS SWEEPS ─────────────────
-- `license_keys` has no tracked CREATE TABLE anywhere in this repo, so a
-- sweep's output could not be checked against an expected schema -- there was
-- nothing to diff against. Both sweeps exclude it BY NAME:
--   sql/full_crud_truncate_sweep_2026-08-24.sql   (TRUNCATE)
--   sql/unused_delete_grant_revoke_2026-08-24.sql (DELETE, Section 2)
-- and the second one's Section 3 therefore expects EXACTLY ONE ROW -- this
-- table -- not zero. A future session must not read that as a failed revoke
-- and "fix" it.
--
-- ── THE CODE HALF IS DONE, AND IT IS UNAMBIGUOUS ──────────────────────────
-- What does the platform actually DO to this table at run time?
--
--   EXACTLY ONE application code path touches it, and it is a GET:
--     api/_lib/license.js:71
--       GET /rest/v1/license_keys?key=eq.<key>&select=*&limit=1
--
-- That is the whole runtime surface. Measured, not assumed: every file in the
-- repo mentioning `license_keys` was enumerated with comment lines excluded --
-- 51 lines across 32 files -- and every one of them is either
--   * that single GET and its two error messages, or
--   * a TEST STUB intercepting the URL (13 files under api/_lib/*.test.js),
--     which never reaches a database, or
--   * a .sql file run BY THE OWNER in the SQL editor (14 licence seeds, 4
--     audits), which does not use service_role's grants at all, or
--   * tooling that GENERATES sql (tools/sairn_build_load_gates.py).
--
-- A separate scan for a non-GET fetch to this table anywhere under api/
-- returned NOTHING.
--
--   ==> service_role needs SELECT on public.license_keys. Nothing else.
--
-- The INSERTs live in licence-seed files and the one DELETE lives in
-- sql/license_seed_onconflict_verify_2026-08-28.sql cleaning up its own probe
-- row. Per the grant-sweep discipline, an owner-run maintenance script is NOT
-- a reason to grant a verb to service_role.
--
-- ── WHAT THIS FILE CANNOT DECIDE ──────────────────────────────────────────
-- Whether the live grants match that. This clone has no Supabase credential,
-- so Sections 1-3 are the measurement and they have NOT been run. Do not
-- record any outcome here that a run did not produce.

-- ══ SECTION 0 — WHO ARE YOU ═══════════════════════════════════════════════
-- Must print `postgres`. `role_table_grants` only shows grants where the
-- current user is grantor, grantee or a member, and REVOKE only removes what
-- the executing role has authority over -- so running this as anything less
-- iterates a SHORT LIST, changes less than it claims, and reports clean
-- through the same blind spot.
select current_user as must_be_postgres;

-- ══ SECTION 1 — THE BASELINE, IN A REAL TABLE ═════════════════════════════
-- A real table, not a temp table: the SQL editor does not guarantee two Run
-- clicks share a session, and a temp table that vanishes between them takes
-- the only proof with it.
drop table if exists license_keys_grant_baseline;
create table license_keys_grant_baseline as
select grantee, privilege_type, is_grantable
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'license_keys';

select * from license_keys_grant_baseline order by grantee, privilege_type;

-- ══ SECTION 2 — WHAT IS ACTUALLY THERE, AND WHAT IS EXCESS ════════════════
-- 2a. Every role holding anything on this table. Read this before Section 4.
--     ANY role other than service_role appearing here is its own finding --
--     the platform-wide sweeps covered service_role only, and `anon` /
--     `authenticated` have never been swept on any table (see the standing
--     index rows). On THIS table that would mean an unauthenticated client
--     could read customer emails and Stripe ids straight from PostgREST.
select grantee,
       string_agg(distinct privilege_type, ', ' order by privilege_type) as privs,
       bool_or(is_grantable = 'YES') as any_grantable
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'license_keys'
group by grantee
order by grantee;

-- 2b. Is RLS on, and is there a policy? service_role BYPASSES RLS entirely, so
--     this does not protect against a leaked service key -- but it is what
--     stands between `anon` and the table if 2a shows anon holding SELECT.
select c.relname, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'license_keys';

select polname, polcmd, pg_get_expr(polqual, polrelid) as using_expr
from pg_policy where polrelid = 'public.license_keys'::regclass;

-- 2c. COLUMN-LEVEL grants, which `REVOKE ALL` would silently destroy and the
--     re-GRANT would not restore. Queried through pg_attribute.attacl rather
--     than information_schema.role_column_grants, which echoes table-level
--     grants per column and can never return zero on any database.
--     EXPECT ZERO ROWS. If it does not, Section 4 is unsafe as written.
select a.attname, (aclexplode(a.attacl)).grantee::regrole as grantee,
       (aclexplode(a.attacl)).privilege_type
from pg_attribute a
where a.attrelid = 'public.license_keys'::regclass
  and a.attnum > 0 and a.attacl is not null;

-- 2d. WITH GRANT OPTION anywhere. EXPECT ZERO ROWS -- a re-GRANT does not
--     restore grantability either.
select grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and table_name = 'license_keys'
  and is_grantable = 'YES';

-- ══ SECTION 3 — THE REAL COLUMN LIST, RECORDED WHERE A SWEEP CAN SEE IT ═══
-- The reason this table was excluded is that nothing in the repo says what it
-- looks like. This prints it. Expected, from db/schema_snapshot.json captured
-- live on 2026-09-02 (11 columns):
--   id, key, app_id, shop_name, customer_email, stripe_customer_id,
--   stripe_subscription_id, plan, status, created_at, updated_at
-- IF THIS DIFFERS, the snapshot is stale and the difference is the finding.
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public' and table_name = 'license_keys'
order by ordinal_position;

-- NOTE, because it is already load-bearing elsewhere: `trial_ends_at` is NOT
-- expected in that list, and its absence is independently confirmed -- a first
-- run of sql/demo_license_keys_seed.sql failed 42703 on it, and that file
-- records a 23-candidate PostgREST column-existence probe. api/sd-render.js
-- reads it anyway. See the open-work row on that; it is a separate finding and
-- must not be "fixed" by adding the column here without deciding the billing
-- question first.

-- ══ SECTION 4 — THE NARROWING. COMMENTED OUT. DO NOT RUN BLIND ════════════
-- Uncomment ONLY after Sections 2a-2d have been read by a person and 2c/2d
-- returned zero rows.
--
-- Revoke-then-grant, so the default-ACL baseline is cleared: a bare GRANT is
-- additive and cannot remove a privilege the role already holds.
--
-- This is deliberately NOT the generic loop the other sweeps use. One table,
-- named explicitly, because the whole point of this file is that this table
-- must not be folded back into a bulk sweep.
--
-- do $$
-- begin
--   revoke all on public.license_keys from service_role;
--   grant select on public.license_keys to service_role;
--   raise notice 'license_keys: service_role now holds SELECT only';
-- end $$;

-- ══ SECTION 5 — VERIFY: LOST and GAINED, not "the target is gone" ═════════
-- Run AFTER Section 4. Expect exactly the rows you intended to remove on the
-- LOST side and ZERO on the GAINED side. A loop bug that dropped SELECT would
-- pass a check that only asked whether DELETE disappeared.
--
-- select coalesce(b.grantee, a.grantee) as grantee,
--        coalesce(b.privilege_type, a.privilege_type) as privilege_type,
--        case when a.grantee is null then 'LOST' else 'GAINED' end as delta
-- from license_keys_grant_baseline b
-- full outer join (
--   select grantee, privilege_type
--   from information_schema.role_table_grants
--   where table_schema = 'public' and table_name = 'license_keys'
-- ) a on a.grantee = b.grantee and a.privilege_type = b.privilege_type
-- where a.grantee is null or b.grantee is null
-- order by delta, grantee, privilege_type;
--
-- GUARD THE GUARD: if Section 1 under-read, the diff above passes vacuously.
-- select count(*) as baseline_rows from license_keys_grant_baseline;
--   -- must be > 0, and must match what Section 2a showed.
--
-- Then, and only then:
-- drop table license_keys_grant_baseline;

-- ══ WHAT THIS FILE DOES NOT COVER, SAID OUT LOUD ══════════════════════════
--   * Roles other than service_role are REPORTED (2a) but not changed. If anon
--     or authenticated hold anything here, that is a bigger decision than this
--     file and belongs in its own pass.
--   * ALTER DEFAULT PRIVILEGES. Check pg_default_acl before assuming a default
--     is what put a verb here; on this project the default ACL grants
--     TRUNCATE/REFERENCES/TRIGGER and NOT DELETE, so "widening the default to
--     include delete" would be a no-op that reads like a fix.
--   * The schema-ownership question. This file documents the columns; it does
--     not create the table, and deliberately so -- a `create table if not
--     exists` here would let a wrong shape be created if the real table were
--     ever absent, in the one place the platform cannot afford it.
