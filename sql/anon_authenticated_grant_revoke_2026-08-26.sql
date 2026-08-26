-- sql/anon_authenticated_grant_revoke_2026-08-26.sql
--
-- Platform-wide revoke of TRUNCATE / REFERENCES / TRIGGER from `anon` and
-- `authenticated`. Same six-part shape as the two service_role sweeps that
-- worked: R6 -> R4 -> Section 0 -> Section 1 -> Section 2 -> Section 3 -> 4.
--
-- ONLY SECTION 2 MUTATES, AND IT IS COMMENTED OUT. Everything else reads.
-- Run order: R6 -> R4 -> Section 0 -> 0b -> 0c -> Section 1 -> 1b -> (review)
--            -> Section 2 STAGE A (uncomment) -> 3a/3b/3c/3d/3e -> Section 4.
--
-- STAGE B (`revoke usage on schema public`) IS NOT IN THIS FILE. It runs
-- separately, after Stage A verifies clean. 3f records its before-state.
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
-- ══ SEVERITY -- CORRECTED 2026-08-26 BY SECTION 0b's OWN OUTPUT ════════════
-- This block previously said "`anon` is NOT unused, and assuming it was would
-- have been wrong", on the strength of browser code that calls PostgREST
-- directly as `anon`. That was right about the CODE and wrong about the
-- DATABASE, and the difference is the whole point.
--
-- What is true: the browsers do ship a Supabase publishable key
-- (`sb_publishable_...` at stonedesk.html:24668 and :34319, sairnbiz.html:835)
-- and the code does call `sb.from('intake_submissions').select/update/delete`
-- (stonedesk.html:31984, :32119, :32130).
--
-- What is ALSO true, and was not checked before that claim was made: those
-- calls FAIL. Section 0b returned `anon` holding only REFERENCES, TRIGGER and
-- TRUNCATE on `intake_submissions` -- no SELECT, UPDATE or DELETE -- and a
-- direct request with the real shipped key confirms it live:
--
--     GET /rest/v1/intake_submissions -> 401
--     {"code":"42501","message":"permission denied for table intake_submissions",
--      "hint":"Grant the required privileges to the current role with:
--              GRANT SELECT ON public.intake_submissions TO anon;"}
--
-- A 42501 is a Postgres AUTHORIZATION failure, which means the key
-- authenticated fine and resolved to `anon`; the role simply holds nothing.
-- The same probe returns 401 for `business_profiles`, `employees`, `sd_slabs`
-- and the PostgREST root itself. Corroborated from the repo side: there is
-- **no `grant ... to anon` statement anywhere in sql/**, on any table, ever.
--
-- So `anon` authenticates but is authorised for nothing reachable. It holds
-- only the default-ACL baseline this file removes. Two consequences:
--   * Severity DROPS further. There is no legitimate `anon` usage to protect,
--     so this sweep has no carve-out to get wrong.
--   * A REAL, SEPARATE BUG surfaces -- StoneDesk's intake panel. See below.
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
-- ══ THE CARVE-OUT -- RETIRED 2026-08-26. There is nothing to carve out. ════
-- This file was built expecting `intake_submissions` to be the one thing the
-- sweep could break: `anon` needed to keep SELECT/UPDATE/DELETE there or
-- StoneDesk's intake panel would stop working silently. Section 0b was written
-- specifically to assert that BEFORE the sweep rather than only after.
--
-- It asserted it, and the assertion FAILED -- which is the assertion doing its
-- job. `anon` holds no SELECT, UPDATE or DELETE on that table, so this sweep
-- cannot take them away. Removing the three baseline verbs leaves `anon` with
-- nothing on `intake_submissions`, which is already its effective state.
--
-- The 0b and 3a queries are KEPT, with their expectations inverted rather than
-- deleted. 0b now records the real before-state; 3a asserts the after-state is
-- empty. Deleting them would remove the only check that would catch this sweep
-- doing something unexpected on the one table anyone had a reason to watch.
--
-- The structural protection still stands and still matters for every OTHER
-- table: Section 2 revokes three named verbs, so nothing holding S/I/U/D loses
-- it, because nothing in this file touches those verbs. A `revoke all` +
-- selective re-grant would have put that at the mercy of a correctly written
-- re-grant list. This does not.
--
-- ══ SEPARATE, REAL BUG FOUND BY THAT FAILED ASSERTION -- NOT this sweep's ══
-- ══ to fix, and NOT caused by it ═══════════════════════════════════════════
-- StoneDesk's intake panel is broken in production right now, and has been
-- failing silently. `stonedesk.html:31984` reads `intake_submissions` through
-- the anon key inside a `try{}catch(e){}`; on failure it falls back to
-- `localStorage.getItem('sd_intake')` and renders that instead. The catch
-- swallows a 42501, so the panel shows device-local data with no error --
-- while the line directly above it comments *"Supabase is the real source of
-- truth here"*, which is exactly backwards in practice.
--
-- `intake_submissions` is also declared in NO schema file, so it is one of the
-- live-but-not-declared tables, and nothing in the repo has ever granted
-- `anon` anything on it. Whether it ever worked -- a hand-grant in the SQL
-- editor later removed, as happened to `sd_employee_auth` -- or never worked at
-- all is not answerable from the repo. Tracked as its own row in
-- docs/SAIRN-OPEN-WORK-INDEX.md. **Do not "fix" it by granting `anon` SELECT
-- while this sweep is in flight** -- decide the access path first; the proxy
-- (api/sd-data.js) is how every other table on the platform is reached.

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

-- ── SECTION 0b: BEFORE-STATE ON intake_submissions -- EXPECTATION ═══════
-- ──                CORRECTED 2026-08-26 AFTER IT RAN ────────────────────
-- This asked for `anon` holding at least SELECT, UPDATE and DELETE, and said
-- that if it did not come back, the intake panel was already broken for some
-- other reason. IT DID NOT COME BACK. Real output 2026-08-26:
--
--     anon | REFERENCES, TRIGGER, TRUNCATE
--
-- No SELECT, no UPDATE, no DELETE -- the default-ACL baseline and nothing
-- else. Confirmed independently against the live API with the real shipped
-- publishable key: 42501 permission denied. The panel IS already broken, and
-- this sweep did not cause it. See the SEPARATE, REAL BUG block above.
--
-- The query is kept, re-run it anyway: it is the before-half of the only pair
-- of assertions aimed at the one table anyone had reason to watch, and a
-- CHANGED answer here between now and Section 2 would mean someone granted
-- `anon` something in the window.
select grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name = 'intake_submissions'
  and grantee in ('anon', 'authenticated')
group by grantee
order by grantee;

-- ── SECTION 0c: BASELINE FOR THE NON-TABLE OBJECTS -- added for Stage A ──
-- Section 0 captures table grants only. Stage A also revokes on SEQUENCES and
-- ROUTINES, and a revoke you cannot diff is a revoke you cannot verify, so
-- those need their own before-state. 3e checks against this.
--
-- Sequences via aclexplode on pg_class rather than an information_schema view:
-- sequence privileges are USAGE/SELECT/UPDATE and no single IS view reports
-- all three cleanly per grantee. aclexplode reads the real ACL.
drop table if exists public._anon_nontable_baseline_2026_08_26;
create table public._anon_nontable_baseline_2026_08_26 as
select 'SEQUENCE'                  as obj_type,
       c.relname                   as obj_name,
       acl.grantee::regrole::text  as grantee,
       acl.privilege_type
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
cross join lateral aclexplode(c.relacl) as acl
where n.nspname = 'public'
  and c.relkind = 'S'
  and c.relacl is not null
  and acl.grantee::regrole::text in ('anon', 'authenticated')
union all
select 'ROUTINE',
       routine_name,
       grantee,
       privilege_type
from information_schema.role_routine_grants
where routine_schema = 'public'
  and grantee in ('anon', 'authenticated');

-- Record this. Zero rows is a perfectly good answer and would mean Stage A's
-- sequence and routine statements are no-ops -- which is worth KNOWING rather
-- than assuming, because "probably nothing there" is what left anon holding
-- TRUNCATE on 159 tables in the first place.
select obj_type, grantee, count(*) as rows_held
from public._anon_nontable_baseline_2026_08_26
group by obj_type, grantee
order by obj_type, grantee;

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

-- ── THE COUNT DRIFT IS THIS FILE'S OWN SCAFFOLDING -- read before Section 2 ──
-- Section 1 has now been read three times and climbed each time: ~158 at the
-- discovery query, 159, then 160. That is not tables appearing on the
-- platform. It is almost certainly THIS FILE.
--
-- Section 0 and Section 0c each `create table` in `public`, and by the very
-- default ACL this sweep exists to remove, each one acquires the
-- anon/authenticated baseline the moment it is created. Section 0 runs BEFORE
-- Section 1, so the baselines are inside the number Section 1 reports:
--
--     158 real + 1 baseline (_anon_grant_baseline)          = 159
--     158 real + 2 baselines (+ _anon_nontable_baseline)     = 160
--
-- The arithmetic fits exactly, which is suggestive and not proof -- it is a
-- PREDICTION, and it is falsifiable: after Section 4 drops both baseline
-- tables, the count must fall by exactly 2. If it does not, something else is
-- creating tables and that is worth knowing.
--
-- CONSEQUENCES FOR READING SECTION 3, so they are not mistaken for defects:
--   * 3b will report LOST rows for the two baseline tables themselves. That is
--     correct and expected -- 2a revokes on `all tables`, and they are tables.
--   * 3c's `live_tables` includes them, so it will not match a count taken
--     before Section 0 ran or after Section 4 drops them.
-- Neither is a problem. Both would look like one to a reader who did not know.

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

-- ══ SECTION 2 -- STAGE A. NOT RUN. Uncomment only after 1 and 1b reviewed ══
--
-- ── WHY THIS IS STAGE A AND NOT THE WHOLE THING ──────────────────────────
-- Approved 2026-08-26 as the first of two stages. Stage B -- the single
-- statement `revoke usage on schema public from anon, authenticated` -- is
-- NOT in this file and must be run separately, in its own window, after Stage
-- A verifies clean.
--
-- The split is not caution for its own sake. Every statement in Stage A is
-- verifiable from the catalog: 3b/3c/3e diff it against a captured baseline
-- and can say exactly what moved. Stage B's blast radius is NOT knowable from
-- this repo -- Supabase internals (Studio, Realtime, PostgREST schema-cache
-- reload) may touch `public` as these roles in ways no file here describes.
-- Run together, a failure would be unattributable: nobody could say which half
-- caused it. Run apart, the answer is free.
--
-- ── WHAT CHANGED FROM THE THREE-VERB DRAFT, AND WHY IT IS NOT BIGGER ─────
-- Section 1b came back EMPTY. TRUNCATE/REFERENCES/TRIGGER are ALL either role
-- holds on any table. So `revoke all on all tables` and
-- `revoke truncate, references, trigger on all tables` reach the SAME end
-- state today -- zero. The wider verb list is not a wider blast radius on
-- tables; it is the same change, stated so it stays correct if someone grants
-- one of these roles something before this runs.
--
-- The genuinely new surface in Stage A is SEQUENCES and ROUTINES, plus
-- widening ALTER DEFAULT PRIVILEGES past tables-only.
--
-- ── ONE STATEMENT WORTH READING TWICE: `ALL ROUTINES` ────────────────────
-- `public` is not only SAIRN's schema. Extensions install functions here too
-- -- `gen_random_uuid()`, which three migrations written tonight use as a
-- column default, lives in `public` via pgcrypto. `revoke all on all routines
-- in schema public` therefore touches extension functions, not just the five
-- SAIRN ones.
--
-- Checked before including it: this is safe, and here is the reasoning rather
-- than the conclusion. Revoking EXECUTE from `anon`/`authenticated` does not
-- touch `service_role`, which is the role that actually performs every insert
-- on this platform, so the `gen_random_uuid()` defaults keep working. The five
-- SAIRN functions already carry `revoke all ... from public` plus
-- `grant execute ... to service_role`, so they are unaffected either way.
-- Section 0c records the real before-state; if it comes back empty, both
-- routine and sequence statements are no-ops and 3e will say so.
--
-- The known cost, stated rather than discovered later: if `anon` is ever
-- legitimately granted INSERT on a table whose default calls a `public`
-- function, it will also need EXECUTE on that function. That is one extra
-- GRANT at that time, not a surprise.
--
-- All statements are list-free: `all tables` / `all sequences` / `all
-- routines in schema public` resolve from the catalog at execution time, so
-- they cannot drift from an enumerated list and cannot miss the
-- live-but-undeclared tables that started this whole thread.

-- ── 2a. STATE: existing objects ─────────────────────────────────────────
-- revoke all on all tables    in schema public from anon, authenticated;
-- revoke all on all sequences in schema public from anon, authenticated;
-- revoke all on all routines  in schema public from anon, authenticated;

-- ── 2b. SOURCE: objects created from here on ────────────────────────────
-- Without this, every new table re-acquires the baseline and this sweep has to
-- be re-run forever. It is the half that makes the fix durable, and it is the
-- half append_only_grant_audit.sql:192-193 got right for service_role and
-- omitted for these two roles -- which is the entire reason this file exists.
-- alter default privileges for role postgres in schema public
--   revoke all on tables    from anon, authenticated;
-- alter default privileges for role postgres in schema public
--   revoke all on sequences from anon, authenticated;
-- alter default privileges for role postgres in schema public
--   revoke all on routines  from anon, authenticated;

-- ── NOT IN STAGE A. Do not uncomment this here. ─────────────────────────
-- revoke usage on schema public from anon, authenticated;
--   ^ STAGE B. Separate run, separate window, separate verification, only
--     after Stage A's 3a/3b/3c/3d/3e all pass. Reversal is one GRANT, but the
--     failure mode may surface somewhere nobody is watching, which is exactly
--     why it does not share a run with statements that are fully verifiable.

-- ── SECTION 3: VERIFY -- only after Section 2 has actually run ───────────
-- 3a. AFTER-STATE ON intake_submissions -- EXPECTATION INVERTED 2026-08-26.
-- Originally: must still show anon holding SELECT/UPDATE/DELETE. That was
-- written before 0b revealed anon never had them.
--
-- NOW EXPECT: ZERO ROWS for `anon`. The three baseline verbs are what this
-- sweep removes, and they were all it had here.
--
-- STOP CONDITIONS, both of which mean something other than this sweep ran:
--   * a SELECT, UPDATE or DELETE row appears for `anon` -- this file grants
--     nothing, so someone else granted it in the window;
--   * REFERENCES, TRIGGER or TRUNCATE survives -- the revoke did not take on
--     this table, and 3b should be showing that too.
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
-- number written in this file. NOTE the two baseline tables are included in
-- `live_tables` here and are dropped by Section 4 -- see the count-drift note
-- above Section 1b. Take this reading BEFORE Section 4, and expect the number
-- to fall by exactly 2 afterwards. `remaining_rows` should equal
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

-- 3e. NON-TABLE OBJECTS -- the Stage A half Section 3b cannot see. 3b diffs
-- table grants only, so without this the sequence and routine statements would
-- be unverified and would still read as "swept".
--
-- EXPECT ZERO ROWS. Any row here is a sequence or routine privilege that
-- survived the revoke.
select 'SEQUENCE' as obj_type, c.relname as obj_name,
       acl.grantee::regrole::text as grantee, acl.privilege_type
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
cross join lateral aclexplode(c.relacl) as acl
where n.nspname = 'public'
  and c.relkind = 'S'
  and c.relacl is not null
  and acl.grantee::regrole::text in ('anon', 'authenticated')
union all
select 'ROUTINE', routine_name, grantee, privilege_type
from information_schema.role_routine_grants
where routine_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by 1, 2, 3;

-- 3f. STAGE B PRECONDITION, not a Stage A check. Records whether schema USAGE
-- is still held, so the Stage B decision starts from a measured state rather
-- than an assumed one. Stage A does NOT change this -- if it reads differently
-- after Stage A than before, something outside this file ran.
select n.nspname as schema, acl.grantee::regrole::text as grantee,
       acl.privilege_type
from pg_namespace n
cross join lateral aclexplode(n.nspacl) as acl
where n.nspname = 'public'
  and acl.grantee::regrole::text in ('anon', 'authenticated')
order by 2, 3;

-- ── SECTION 4: CLEANUP -- only after 3a/3b/3c/3d/3e all pass ───────────
-- Leave BOTH baseline tables in place if ANY of them did not. They are the
-- only record of the before-state, and dropping them on a failed run destroys
-- the evidence needed to work out what happened.
--
-- Keep them until STAGE B has also run and verified, not just Stage A -- Stage
-- B has no baseline of its own and 3f above is its only before-reading.
-- drop table if exists public._anon_grant_baseline_2026_08_26;
-- drop table if exists public._anon_nontable_baseline_2026_08_26;
