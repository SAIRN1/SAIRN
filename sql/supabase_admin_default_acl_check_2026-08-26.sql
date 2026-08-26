-- sql/supabase_admin_default_acl_check_2026-08-26.sql
-- READ-ONLY. Four SELECTs. Nothing here writes, grants, revokes or alters.
--
-- ══ THE FINDING THIS EXISTS TO SETTLE ═════════════════════════════════════
-- Stage A's 3d verified that `postgres`'s default ACL in schema `public` no
-- longer grants `anon`/`authenticated` anything. It also revealed a SECOND
-- granting role that was never in scope: **`supabase_admin`**, whose own
-- default ACL still grants both roles
--
--     tables     arwdDxtm   -- INSERT, SELECT, UPDATE, DELETE, TRUNCATE,
--                              REFERENCES, TRIGGER, MAINTAIN. Everything.
--     sequences  rwU
--     functions  X
--
-- That is materially WORSE than what Stage A just removed. `postgres`'s
-- default ACL handed out three verbs; `supabase_admin`'s hands out full CRUD.
-- A table created by `supabase_admin` in `public` would arrive with `anon`
-- holding SELECT, INSERT, UPDATE and DELETE on it.
--
-- ══ THIS IS THE SAME BUG CLASS, ONE DOOR OVER -- WHICH IS THE POINT ════════
-- append_only_grant_audit.sql:192-193 fixed the default ACL `for role
-- postgres` and named only `service_role`, which is how `anon`/`authenticated`
-- survived on 159 tables. Stage A fixed `for role postgres` for both roles --
-- and named only `postgres`. Each fix was correct and each was scoped to what
-- the person writing it had looked at. Finding this one from 3d's output, one
-- step after the last one, is the argument for keeping the verification step
-- that prints the WHOLE picture rather than just asserting the thing you
-- changed.
--
-- ══ IS IT INERT? DO NOT ASSUME EITHER WAY -- THAT IS WHAT SECTION 1 IS FOR ══
-- The reason to think it may be inert: R6 printed `current_user = postgres`
-- and `session_user = postgres`, so the Supabase SQL editor -- the only way
-- any migration in sql/ has ever been run on this platform -- runs as
-- `postgres`, and a default ACL only applies to objects created BY the role it
-- names. On that path, `supabase_admin`'s entry never fires.
--
-- The reasons not to rely on that:
--   * It is a claim about how migrations are run TODAY, by one person, through
--     one UI. It is not a property of the database.
--   * Supabase's own machinery (extension installs and upgrades, dashboard
--     tooling, managed features being enabled) does act as `supabase_admin`,
--     and `public` is not off-limits to it -- pgcrypto's `gen_random_uuid()`
--     already lives in `public`.
--   * The failure is silent and delayed: nothing errors, a table simply
--     arrives with `anon` holding full CRUD, and nothing on this platform
--     watches for that between sweeps.
--
-- Section 1 below settles it with evidence instead of reasoning.
--
-- ══ AND A CAVEAT ON THE FIX, BEFORE ANYONE WRITES IT ══════════════════════
-- `ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin` requires membership in
-- that role. On Supabase, `postgres` is NOT a superuser, and it may or may not
-- be a member of `supabase_admin` -- Section 3 checks. If it is not, the fix
-- is not executable from the SQL editor at all and the options are a support
-- request or accepting the risk deliberately with a monitoring check instead.
-- Better to know that before writing a statement that cannot run.

-- ── 1. THE ANSWER: does anything in `public` actually get created by ──────
-- ──    `supabase_admin`? ─────────────────────────────────────────────────
-- Ownership is the evidence. The role that creates an object owns it unless
-- ownership was reassigned afterwards, so a population that is 100% `postgres`
-- is strong evidence the `supabase_admin` default ACL has never fired here.
-- Any row owned by `supabase_admin` is proof it does.
select c.relowner::regrole::text as owner,
       case c.relkind when 'r' then 'table'
                      when 'p' then 'partitioned table'
                      when 'S' then 'sequence'
                      when 'v' then 'view'
                      when 'm' then 'matview'
                      else c.relkind::text end as kind,
       count(*) as objects
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind in ('r', 'p', 'S', 'v', 'm')
group by 1, 2
order by 1, 2;

-- 1b. FUNCTIONS separately -- this is where an extension is most likely to
-- have left something owned by `supabase_admin`, and `revoke all on all
-- routines` in Stage A only covered what existed at that moment.
select p.proowner::regrole::text as owner,
       count(*) as functions
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
group by 1
order by 1;

-- ── 2. THE EXPOSURE, if it is not inert: name the objects ────────────────
-- Anything in `public` NOT owned by `postgres`. Expect zero rows. Every row is
-- an object whose future siblings would arrive with anon holding full CRUD.
select c.relowner::regrole::text as owner,
       c.relkind,
       c.relname
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind in ('r', 'p', 'S', 'v', 'm')
  and c.relowner::regrole::text <> 'postgres'
order by 1, 2, 3;

-- ── 3. CAN THE FIX EVEN BE RUN? ──────────────────────────────────────────
-- `ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin` needs membership in that
-- role. If `is_member` is false, do NOT write that statement -- it will fail,
-- and the decision becomes support-request-or-accept-and-monitor instead.
select current_user,
       pg_has_role(current_user, 'supabase_admin', 'MEMBER') as is_member_of_supabase_admin,
       (select rolsuper from pg_roles where rolname = current_user) as is_superuser;

-- ── 4. THE FULL DEFAULT-ACL PICTURE, for the record ──────────────────────
-- Same query as Stage A's 3d, repeated here so this file stands alone. Print
-- it whatever Section 1 says: it is the before-state for any future fix, and
-- it is how this finding surfaced in the first place.
select d.defaclrole::regrole  as granting_role,
       d.defaclobjtype        as obj_type,
       n.nspname              as schema,
       d.defaclacl            as default_acl
from pg_default_acl d
join pg_namespace n on n.oid = d.defaclnamespace
where n.nspname = 'public'
order by 1, 2;
