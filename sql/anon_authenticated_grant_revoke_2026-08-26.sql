-- sql/anon_authenticated_grant_revoke_2026-08-26.sql
--
-- Platform-wide revoke of TRUNCATE / REFERENCES / TRIGGER from `anon` and
-- `authenticated`. Same six-part shape as the two service_role sweeps that
-- worked: R6 -> R4 -> Section 0 -> Section 1 -> Section 2 -> Section 3 -> 4.
--
-- ONLY SECTION 2 MUTATES, AND IT IS COMMENTED OUT. Everything else reads.
-- Run order: R6 -> R4 -> Section 0 -> Section 1 -> (review) -> Section 2
--            (uncomment) -> 3a/3b/3c/3d -> Section 4.
--
-- ══ WHY THIS EXISTS, AND WHY IT IS NOT A FOLLOW-ON TO ANYTHING ═════════════
-- Found 2026-08-26. `anon` and `authenticated` each hold
-- TRUNCATE/REFERENCES/TRIGGER on ~158 tables in `public` -- declared and
-- undeclared alike, including heavily-used tables like `dnt_appointments` and
-- `grd_jobs`.
--
-- It was found by a control that was written to falsify a hypothesis, and did.
-- The prediction was that this baseline would sit only on
-- live-but-not-declared tables, on the theory that a sweep driven off `sql/`
-- inherits `sql/`'s omissions. Section 3 of
-- sql/undeclared_table_acl_check_2026-08-26.sql checked DECLARED tables as the
-- control and came back dirty too. Declaration status is irrelevant.
--
-- REAL ROOT CAUSE: every grant-hardening pass on this platform targeted
-- `service_role` ONLY. sql/append_only_grant_audit.sql:192-193 reads
-- `revoke truncate, references, trigger, maintain on tables from service_role`
-- and names no other role. `anon` and `authenticated` were never in scope for
-- any of it, on any table.
--
-- ══ SEVERITY, ASSESSED BEFORE SCOPING -- read this before deciding urgency ══
-- `anon` is NOT unused, and assuming it was would have been wrong. The
-- browsers ship a Supabase publishable key (`sb_publishable_...` at
-- stonedesk.html:24668 and :34319, sairnbiz.html:835) and talk to PostgREST
-- directly as `anon`, reading, updating and DELETING `intake_submissions`
-- (stonedesk.html:31984, :32119, :32130). Recorded previously at
-- sql/full_crud_truncate_sweep_2026-08-24.sql:351 and :502. The
-- everything-goes-through-the-proxy model is not universal.
--
-- But the three verbs this file revokes have no invocation path today:
--   * PostgREST exposes no TRUNCATE verb and no DDL verb at all.
--   * There are ZERO `.rpc()` calls in any browser file on the platform.
--   * All five SQL functions are SECURITY INVOKER and carry
--     `revoke all ... from public` + `grant execute ... to service_role` only.
--
-- Two things worth being exact about, because both cut against the intuitive
-- reading:
--   * RLS IS NOT A CONTROL HERE. TRUNCATE bypasses row-level security
--     entirely. All 186 policies on this platform are
--     `auth.role() = 'service_role'`, and not one of them would stop a
--     TRUNCATE issued by a role holding the privilege.
--   * A PUBLISHABLE KEY IS PUBLIC BY DESIGN. Whatever `anon` holds is
--     effectively held by anyone who views source.
--
-- VERDICT: latent, not active. Medium. It is unreachable because no verb
-- exposes it, not because anything guards it -- and it becomes High the moment
-- any SECURITY DEFINER function is granted to `anon` or `public`, or any RPC
-- runs dynamic SQL. That is a thin margin to be relying on silently, which is
-- why this is being closed now rather than logged.
--
-- ══ `authenticated` IS UNREACHABLE, NOT MERELY UNUSED -- verified, not ══════
-- ══ assumed, across the whole codebase rather than the obvious paths ═══════
-- Checked 2026-08-26 before scoping, because "probably unused" is not a basis
-- for stripping a role:
--   * NO Supabase Auth anywhere. Zero hits for `supabase.auth`,
--     `signInWithPassword`, `signUp(`, `onAuthStateChange`, `setSession`,
--     `/auth/v1/`, `gotrue`, `admin.createUser`, `admin.generateLink` or
--     `@supabase` imports across every *.html, *.js and *.json in the repo,
--     including inside api/.
--   * THE ONLY Auth ON THE PLATFORM IS FIREBASE, and it is a different system
--     entirely: sairncash.html:402 imports `getAuth, signInWithCustomToken`
--     from `gstatic.com/firebasejs/10.12.0/firebase-auth.js`, backing Firebase
--     RTDB on project sarintype-6e070. It produces a Firebase `auth.uid`, NOT
--     a Supabase JWT, and cannot ever yield the `authenticated` role. A naive
--     grep for "auth" finds this and reads like Supabase Auth is in use. It is
--     not. This is the specific trap the whole-codebase check was for.
--   * SAIRN's own `*-auth.js` endpoints (sd-auth, sb-auth, rf-auth, ...) are
--     per-employee credential endpoints of SAIRN's own design. They issue
--     SAIRN session tokens verified by `verifySessionToken()`. They do not
--     touch Supabase Auth.
--   * ZERO RLS policies reference `auth.uid()`, `auth.jwt()` or `auth.email()`
--     -- all 186 are `auth.role() = 'service_role'`. A platform with real
--     signed-in Supabase users would have at least one.
-- Conclusion: no code path can mint a Supabase JWT carrying `authenticated`.
-- The role is unreachable. It should hold nothing, and this file's scope on it
-- is still deliberately limited to the three verbs -- see the next block.
--
-- ══ SCOPE -- what this file does NOT do, deliberately ══════════════════════
-- Verbs: TRUNCATE, REFERENCES, TRIGGER. NOT select/insert/update/delete.
-- Even though `authenticated` is unreachable and arguably should hold nothing
-- at all, stripping it to zero is a SEPARATE change with a separate blast
-- radius, and mixing the two would make Section 3 unable to distinguish an
-- intended removal from a collateral one. One sweep, one verb-set, one
-- assertion shape. Log the `authenticated`-to-zero question separately.
--
-- ══ THE CARVE-OUT -- the one thing this sweep could break silently ═════════
-- `intake_submissions` must keep `anon`'s SELECT, UPDATE and DELETE, or
-- StoneDesk's intake panel stops working WITHOUT AN ERROR -- the browser calls
-- are wrapped in `try{}catch(e){}` (stonedesk.html:32119, :32130), so a
-- permission failure is swallowed and the panel simply shows nothing.
--
-- The carve-out is protected STRUCTURALLY, not by a filter: Section 2 revokes
-- three named verbs, and `intake_submissions` keeps everything else because
-- nothing in this file touches S/I/U/D. That is deliberate -- a `revoke all`
-- + selective re-grant would put the carve-out at the mercy of a correctly
-- written re-grant list, and this does not.
--
-- It is still asserted BEFORE (Section 0b) and AFTER (Section 3a), because
-- "structurally safe" is a claim about the code and the assertion is a claim
-- about the database, and tonight has repeatedly shown those two diverging.

-- ── SECTION R6: PRECONDITION. Must print `postgres`. ─────────────────────
-- `role_table_grants` only shows grants where the current user is grantor,
-- grantee or a member, and REVOKE only removes what the executing role has
-- authority over. As anything less, Section 1 reads a SHORT list, Section 2
-- changes less than it claims, and Section 3 reports clean through the same
-- blind spot. Neither `anon` nor `authenticated` nor `service_role` can run
-- this sweep.
select current_user, session_user;

-- ── SECTION R4: PRE-FLIGHT. Both must return ZERO rows. ──────────────────
-- ADAPTED, NOT COPIED. In the service_role sweeps this check existed because
-- `REVOKE ALL` cascades to COLUMN-level privileges that the re-GRANT would not
-- restore. This file issues no `REVOKE ALL`, so most of that risk is absent --
-- but not all of it, and the part that remains is specific:
--
--   TRUNCATE and TRIGGER have NO column-level form. They cannot be affected.
--   REFERENCES DOES have a column-level form. A column-specific
--   `GRANT REFERENCES (col)` to anon/authenticated would not appear in
--   `role_table_grants`, and revoking the table-level privilege leaves it
--   behind -- so this sweep would report clean while a column-scoped
--   REFERENCES survived.
--
-- So R4a is run for REFERENCES specifically, not as ceremony.
--
-- USE THIS QUERY, NOT information_schema.role_column_grants. That view reports
-- a row per column whenever the privilege is held INCLUDING via a table-level
-- grant, so it can never return zero on any database -- it returned hundreds
-- during the truncate sweep and read as a false stop. `pg_attribute.attacl` is
-- NULL unless a genuine column-specific GRANT was issued.
select
  c.relname                   as table_name,
  a.attname                   as column_name,
  acl.grantee::regrole::text  as grantee,
  acl.privilege_type
from pg_attribute a
join pg_class c     on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
cross join lateral aclexplode(a.attacl) as acl
where n.nspname = 'public'
  and c.relkind in ('r', 'p')
  and a.attacl is not null
  and not a.attisdropped
  and acl.grantee::regrole::text in ('anon', 'authenticated')
order by 1, 2, 3;

-- R4b: WITH GRANT OPTION. If either role can re-grant, revoking from the role
-- does not remove the privilege from whoever it granted onward.
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and is_grantable = 'YES'
order by 1, 2, 3;

-- ── SECTION 0: BASELINE CAPTURE -- run BEFORE Section 2. ─────────────────
-- A REAL table, deliberately, not a temp one: the Supabase SQL editor does not
-- guarantee two Run clicks share a session, and a temp table that vanishes
-- between them takes the only proof with it, leaving a mutation applied and
-- nothing to check it against. Section 4 drops it.
--
-- Captures EVERY privilege both roles hold, not just the three being revoked.
-- That is what lets 3b detect collateral loss -- most importantly `anon`'s
-- SELECT/UPDATE/DELETE on `intake_submissions`, which is outside this sweep's
-- verb-set and must survive it.
drop table if exists public._anon_grant_baseline_2026_08_26;
create table public._anon_grant_baseline_2026_08_26 as
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated');

-- Record these numbers. DO NOT predict them -- the DELETE sweep predicted
-- 779/211 and the real baseline was 785/213, and the arithmetic fit of the
-- wrong number was itself convincing. Whatever this returns is the baseline;
-- 3c compares against it, not against a literal in this file.
select grantee,
       count(*)                   as baseline_rows,
       count(distinct table_name) as baseline_tables
from public._anon_grant_baseline_2026_08_26
group by grantee
order by grantee;

-- ── SECTION 0b: THE CARVE-OUT, ASSERTED BEFORE ──────────────────────────
-- Expect `anon` holding at least SELECT, UPDATE and DELETE on
-- `intake_submissions`. If this does NOT come back before the sweep, then the
-- browser intake panel is already broken for some other reason and 3a would
-- otherwise "confirm" a state this sweep did not cause. Record the output.
select grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name = 'intake_submissions'
  and grantee in ('anon', 'authenticated')
group by grantee
order by grantee;

-- ── SECTION 1: DISCOVER -- run this, review the real output ──────────────
-- List-free: the set is computed from the catalog, never pasted. Expect ~158
-- tables per role. Report the real numbers; do not carry the ~158 forward as
-- fact -- it is another session's figure, and this file's whole subject is a
-- privilege state nobody had actually enumerated.
select grantee,
       privilege_type,
       count(*) as tables_holding
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and privilege_type in ('TRUNCATE', 'REFERENCES', 'TRIGGER')
group by grantee, privilege_type
order by grantee, privilege_type;

-- 1b: anything OTHER than the three verbs -- i.e. what these roles legitimately
-- (or illegitimately) hold that this sweep will NOT touch. `intake_submissions`
-- should be the interesting row. Anything else here is worth a look before
-- Section 2, because it is a real anon-reachable surface nobody has reviewed.
select table_name,
       grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and privilege_type not in ('TRUNCATE', 'REFERENCES', 'TRIGGER')
group by table_name, grantee
order by table_name, grantee;

-- ── SECTION 2: THE FIX -- NOT RUN. Uncomment only after reviewing 1 and 1b ──
-- Two statements, both list-free.
--
-- The first fixes the STATE on tables that exist now. `on all tables in
-- schema public` resolves at execution time from the catalog, so it cannot
-- drift from a list the way an enumerated file would, and it cannot miss the
-- undeclared tables that started this whole thread.
--
-- The second fixes the SOURCE. Without it every table created from here on
-- re-acquires the baseline and this sweep has to be re-run forever. It mirrors
-- append_only_grant_audit.sql:192-193 exactly, for the two roles that line
-- omitted. NOTE: `maintain` is included there and is included here for
-- symmetry, even though Section 1 shows only three verbs actually held -- a
-- deliberate choice, flagged rather than silent, so the two default-privilege
-- lines cannot drift apart later.

-- revoke truncate, references, trigger
--   on all tables in schema public
--   from anon, authenticated;

-- alter default privileges for role postgres in schema public
--   revoke truncate, references, trigger, maintain on tables from anon, authenticated;

-- ── SECTION 3: VERIFY -- only after Section 2 has actually run ───────────
-- 3a. THE CARVE-OUT, ASSERTED AFTER. Must match Section 0b exactly: `anon`
-- still holding SELECT, UPDATE, DELETE on intake_submissions. If SELECT,
-- UPDATE or DELETE is missing here, STOP -- StoneDesk's intake panel is broken
-- and it will not report an error, because the browser calls are inside
-- `try{}catch(e){}`.
select grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name = 'intake_submissions'
  and grantee in ('anon', 'authenticated')
group by grantee
order by grantee;

-- 3b. THE DIFF -- INVERTED, as in the DELETE sweep. LOST is the objective
-- here, so "zero rows on both sides" is NOT the success condition; it would
-- mean the revoke did nothing.
--
-- Read it like this:
--   EVERY row must be LOST, and every LOST row must be TRUNCATE, REFERENCES
--   or TRIGGER. That is success.
--   ANY row marked GAINED is a failure -- this file grants nothing.
--   ANY LOST row whose privilege is NOT one of those three is collateral
--   damage. A LOST | anon | intake_submissions | SELECT row is the specific
--   catastrophe this sweep is shaped to prevent, and it would be invisible to
--   3a's summary if the row still showed the other two verbs.
select 'LOST' as direction, b.grantee, b.privilege_type,
       count(*) as tables_affected
from public._anon_grant_baseline_2026_08_26 b
left join information_schema.role_table_grants g
  on g.table_schema  = 'public'
 and g.table_name    = b.table_name
 and g.grantee       = b.grantee
 and g.privilege_type = b.privilege_type
where g.table_name is null
group by b.grantee, b.privilege_type
union all
select 'GAINED', g.grantee, g.privilege_type, count(*)
from information_schema.role_table_grants g
left join public._anon_grant_baseline_2026_08_26 b
  on b.table_name     = g.table_name
 and b.grantee        = g.grantee
 and b.privilege_type = g.privilege_type
where g.table_schema = 'public'
  and g.grantee in ('anon', 'authenticated')
  and b.table_name is null
group by g.grantee, g.privilege_type
order by 1 desc, 2, 3;

-- 3c. TOTALS. Compare against Section 0's recorded output, not against any
-- number written in this file. `remaining_rows` should equal
-- baseline_rows minus the LOST count from 3b, per role, and the table count in
-- `public` must be UNCHANGED -- a revoke cannot drop a table, so a changed
-- count means something else ran in the window.
select (select count(*) from public._anon_grant_baseline_2026_08_26)     as baseline_rows,
       (select count(*) from information_schema.role_table_grants
         where table_schema = 'public'
           and grantee in ('anon', 'authenticated'))                     as remaining_rows,
       (select count(*) from information_schema.tables
         where table_schema = 'public'
           and table_type = 'BASE TABLE')                                as live_tables;

-- 3d. THE SOURCE FIX. Confirms the ALTER DEFAULT PRIVILEGES landed, which is
-- the half that stops this recurring. Expect the anon/authenticated revokes to
-- appear alongside the existing service_role one. If this is empty, only the
-- state was fixed and the next migration re-creates the problem.
select d.defaclrole::regrole            as granting_role,
       d.defaclobjtype                  as obj_type,
       n.nspname                        as schema,
       d.defaclacl                      as default_acl
from pg_default_acl d
join pg_namespace n on n.oid = d.defaclnamespace
where n.nspname = 'public'
order by 1, 2;

-- ── SECTION 4: CLEANUP -- only after 3a/3b/3c/3d all pass ───────────────
-- Leave the baseline table in place if ANY of them did not. It is the only
-- record of the before-state, and dropping it on a failed run destroys the
-- evidence needed to work out what happened.
-- drop table if exists public._anon_grant_baseline_2026_08_26;
