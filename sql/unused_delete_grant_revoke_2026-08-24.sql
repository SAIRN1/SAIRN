-- sql/unused_delete_grant_revoke_2026-08-24.sql
-- Revokes service_role's DELETE on every public table EXCEPT the SAIRNcode
-- sc_* family, which is the only app with a real, reachable delete path.
--
-- Same three-section shape as sql/full_crud_truncate_sweep_2026-08-24.sql:
-- discover live, review, then fix. The table list is NEVER hand-written --
-- it is pulled from information_schema at run time, so a table added after
-- this file was written is still covered.
--
-- ── COUNT CORRECTION 2026-08-25: THE "~107 / ~78" FIGURE WAS WRONG ────────
-- A live count on 2026-08-25 returned 135 non-sc_* tables holding DELETE,
-- not the ~78 this file's first revision implied. Reconciled before any
-- revoke runs, because a 57-table gap is not a rounding difference.
--
-- CAUSE: the original figure came from a TRUNCATED EXPORT, and was then
-- written into docs/SAIRN-OPEN-WORK-INDEX.md as though it described the
-- database. sql/full_crud_truncate_sweep_2026-08-24.sql records the same
-- root cause in its own header, found independently by the SAIRN-cc
-- session: "Michael's SQL client had a row limit; the first export
-- (100 rows) was confirmed truncated by cross-checking against tables
-- already known to exist (SAIRNlegacy alone continues well past where
-- that export stopped)." The real export is 227 tables. Any count near
-- 100 taken during that window is capped, not measured.
--
-- NOT THE CAUSE -- checked, not assumed: new tables created since. origin
-- has no schema commit after the original count; the only unpushed work in
-- any sibling clone (SAIRN-cc dd5327b) adds documentation and zero tables.
-- New tables account for approximately none of the 57.
--
-- WHERE THE 135 COMES FROM -- predicted from repo grant lines, then
-- CHECKED against Section 1's real output on 2026-08-25:
--   131  non-sc_* tables this repo grants anything on to service_role
--    83    of those carry an explicit `grant ... delete` line  <- the
--          original count, i.e. it counted GRANT LINES IN THIS REPO and
--          reported them as live rows. scp_employee_auth is one of these.
--    48    of those are granted only SELECT/INSERT/UPDATE here -- 10 of
--          which explicitly REVOKE delete, leaving 38 candidates.
--          *** ALL 38 CAME BACK CLEAN. Zero hold DELETE. ***
--   ~52  the real remainder: tables with NO grant-delete line in this repo
--          at all, consistent with 227 live tables vs 131 granted here.
--          This is where the 57-table gap actually lived -- untracked
--          schema, not a default privilege.
--
-- MY FIRST EXPLANATION WAS WRONG AND IS RECORDED AS WRONG: I predicted the
-- 48 (later 38) would be "granted only SELECT/INSERT/UPDATE here yet hold
-- DELETE live anyway", and proposed that as evidence the grant arrives by
-- default privilege. The live result is the exact opposite. The arithmetic
-- 83 + 48 + 4 = 135 fitted well enough to look like confirmation and was
-- coincidence. Flagged as unverified at the time, which is the only reason
-- it did not become a fact in this file.
--
-- ── AUDIT-LOG CHECK CAME BACK CLEAN, AND MY TEST WAS A BAD TEST ──────────
-- Confirmed live 2026-08-25: sairncode_audit_log, stonedesk_audit_log and
-- sairnlaw_audit_log all show INSERT/SELECT only, no DELETE. The
-- `revoke all ... from service_role` pattern does what it is supposed to.
-- It is not broken -- it is just not universal (9 tables use it; see
-- `grep -l "revoke all.*from service_role" sql/*.sql`).
--
-- But I proposed those three as the DISCRIMINATING test, and they are not.
-- All three are EXPLICITLY protected in their own schema files --
-- sairncode_audit_log and stonedesk_audit_log by `revoke all` first,
-- sairnlaw_audit_log by an explicit `revoke update, delete ... from
-- service_role` at sql/sairnlaw_audit_log*.sql:87. A table that explicitly
-- revokes DELETE showing no DELETE is consistent with BOTH hypotheses and
-- therefore separates neither. Recording this because the wrong test
-- passing is easy to mistake for the question being answered.
--
-- CANDIDATE SET NARROWED 48 -> 38. The first pass counted only `grant`
-- lines and ignored `revoke` lines, so it wrongly listed all 10 explicitly
-- protected tables as candidates. Re-parsed for both verbs: 38 non-sc_*
-- tables are granted SELECT/INSERT/UPDATE with NO delete granted AND no
-- revoke protecting them. Those 38 -- alf_* (13), sen_* (5), sd_sub*/sd_subs
-- (3), the eight *_employee_auth tables, bld_bids, bld_tna_assessments,
-- dnt_cred_rules, dnt_credentials, sairncash_trial, sairncash_waitlist,
-- sairnscape_org_intel, sd_render_usage, sd_shared_knowledge -- are the
-- real discriminator. RESOLVED BELOW: they came back clean, so the second
-- branch is what happened -- the 135 is 83 explicit grants plus ~52 tables
-- with no tracked schema, and the default-ACL question is moot.
--
-- ── SECTION 1 RAN 2026-08-25. 135 ROWS. RESULT: 0 OF THE 38 HOLD DELETE ──
-- The candidate hypothesis is DEAD, and cleanly so. All 38 tables that are
-- granted SELECT/INSERT/UPDATE with no delete granted and no revoke
-- protecting them came back CLEAN. Nothing is arriving by default.
--
-- ONE CORRECTION TO HOW THIS WAS REPORTED BACK: the single table found
-- holding DELETE, scp_employee_auth, was NOT one of the 38. It was in the
-- 83 -- the set with an EXPLICIT `grant ... delete` line in this repo. So
-- the score is 0 of 38, not 1 of 38, which makes the result stronger, not
-- weaker: no unprotected table anywhere acquired DELETE without being
-- explicitly granted it.
--
-- ── WHY scp_employee_auth DIFFERS FROM THE OTHER SEVEN: IT JUST SAYS SO ──
-- Not a missing revoke, not grant order, not a stray `grant all`, and not
-- a fix applied to the others but never to it. sql/scp_employee_auth_schema.sql:47
-- literally reads:
--     grant select, insert, update, delete on scp_employee_auth to service_role;
-- It is the ONLY *_employee_auth file on the platform whose grant line
-- contains `delete` -- confirmed by
-- `grep -niE "^\s*grant[^;]*delete[^;]*employee_auth" sql/*.sql`, one hit.
-- Every sibling (sb_, sairncode_, sairnlaw_, sairnbuild_, sairncare_,
-- sairndesign_, sairnlegacy_, sairnsenior_) grants `select, insert, update`
-- and stops.
--
-- The file's own header says why, and the reason is an OVERCORRECTION, not
-- an oversight: "GRANT statements included explicitly this session
-- (2026-08-06) -- a known recurring gap flagged after the SAIRNgrounds
-- license-row issue. service_role bypasses RLS by default in Supabase, but
-- being explicit here removes any ambiguity rather than relying on that
-- default silently." The author was fixing a pattern of MISSING grants and,
-- being explicit, wrote the full CRUD verb list instead of the verbs the
-- app actually uses. SAIRNscape has no delete path -- the platform's only
-- DELETE is the SAIRNcode branch -- so it has never been used.
--
-- That makes it exactly what this sweep is for, and it should still be
-- revoked. Root cause understood, not revoked blind.
--
-- ── WHAT THE REMAINING ~52 ROWS ARE ──────────────────────────────────────
-- 135 live, minus the 83 with an explicit repo grant-delete line, leaves
-- ~52 unaccounted for by any grant line in sql/*.sql. That is the
-- untracked-schema bucket, and it is consistent in size with the gap
-- already known: 227 live tables against 131 this repo grants anything on.
-- Some of the 83 may also never have been run (commit 6776f99 found two
-- audited tables that do not exist), so ~52 is a floor, not a fixed number.
-- EXACT BUCKETING NEEDS THE 135-ROW LIST ITSELF, which this session has not
-- seen -- only the 38-candidate verdict was reported back. Section 2 acts
-- correctly on all of them regardless, since it is list-free and preserves
-- whatever SELECT/INSERT/UPDATE each table already holds.
--
-- ── DOES THE DEFAULT-ACL FIX NEED WIDENING TO INCLUDE DELETE? NO ─────────
-- ANSWERED 2026-08-25 by the result above, ahead of the pg_default_acl
-- query: 37 of 38 -- now 38 of 38 -- tables with NO revoke protecting them
-- hold no DELETE. If any default privilege granted DELETE, those tables
-- would have it. They do not. Widening Section 4 of
-- sql/append_only_grant_audit.sql to include `delete` would be a no-op that
-- reads like a fix. DO NOT WIDEN IT.
--
-- The pg_default_acl query (every row, not just postgres's) is still worth
-- running, but it is now CONFIRMATORY rather than decisive. If it somehow
-- shows a second defaclrole granting DELETE, that would CONTRADICT the live
-- table evidence and the contradiction itself would be the finding -- do
-- not quietly reconcile it in favour of either side.
--
-- ── SUPERSEDED REASONING, KEPT SO IT IS NOT RE-DERIVED ───────────────────
-- sql/append_only_grant_audit.sql Section 4 revokes only
-- `truncate, references, trigger, maintain` from the default privileges,
-- not delete. Whether that needs widening depends entirely on the answer
-- above -- and there is already evidence in hand that it does NOT:
--
--   * Section 1a of that file confirmed live what postgres's default ACL
--     actually grants service_role: TRUNCATE, REFERENCES, TRIGGER,
--     MAINTAIN. DELETE is NOT in that list. If DELETE is not in the
--     default ACL, revoking it from the default ACL changes nothing.
--   * Section 1b of that file records dnt_credentials -- which IS one of
--     the 38 -- reading `del=f` before the fix. That is a table with no
--     delete grant, no revoke, and no DELETE. Exactly what the "default
--     privilege is not the source" answer predicts.
--
-- Both bullets above turned out to be right, and Section 1's real output
-- settled it directly rather than by inference. dnt_credentials was one of
-- the 38 and came back clean, matching its recorded `del=f`.
--
-- STATUS OF THIS BLOCK: superseded, not wrong. Kept because the reasoning
-- is what made the 38 the right thing to ask about, and because a later
-- session finding the pg_default_acl output should know this question was
-- already answered from the table side first.
--
-- ── WHY ───────────────────────────────────────────────────────────────────
-- Exactly ONE piece of code in the entire repo issues a DELETE:
-- api/sd-data.js, inside the SC_RESOURCES branch (line 5029 as of
-- 2026-08-25 -- the line number drifts as that file grows, the branch
-- does not; it was 4980 when this file was first written), gated by a
-- server-side re-check that the caller holds a valid SAIRNcode *admin*
-- session (a forged client claim of admin-ness is rejected there). Verified
-- by grepping every .js/.cjs/.mjs/.ts/.html in the repo, not just api/ --
-- one hit, no others.
--
-- Every other table's DELETE grant is a default copied forward through
-- schema files. Nothing built or planned needs it:
--   * erroneous-entry correction -> upsert on (license_hash, <entry>_id),
--     which is how every sd_*/grd_*/msb_* resource already works
--   * job/appointment cancellation -> a status ('Cancelled', 'INACTIVE'),
--     because a cancelled job you cannot see is indistinguishable from one
--     that never existed
--   * GDPR erasure -> the platform's own design (SAIRNcare) KEEPS the
--     identifier plus a suppression flag and reason code and deletes the
--     surrounding personal data. That is field-level redaction inside a
--     retained row -- an UPDATE, not a DELETE. These tables hold stone
--     inventory, landscaping jobs and beverage sales, not the personal-data
--     surface an erasure request targets anyway.
--
-- The grant is also the ONLY layer here. Every one of these tables has RLS
-- `for all using (false) with check (false)`, and service_role bypasses RLS
-- entirely -- so the grant is the sole thing between a leaked service key,
-- or a future coding mistake, and irreversible row loss.
--
-- One table makes the contradiction explicit: sd_slab_history is documented
-- in sql/sd_slab_lineage_schema.sql as "one row per event, append-only in
-- practice" and is granted DELETE. That is the provenance trail someone
-- reads when auditing a high-value slab.
--
-- ── NOTHING INTERNAL RELIES ON THIS, CHECKED NOT ASSUMED ──────────────────
-- The cleanup scripts that DO issue real deletes against in-scope tables
-- (sql/rbac_test_artifact_cleanup.sql -> msb_sales, grd_progress_photos;
-- sairndesign_*_cleanup.sql; sairncash_verification_trial_cleanup.sql;
-- sairndental_credentials_verify_cleanup.sql) run in the Supabase SQL
-- editor as the owner role, NOT as service_role. rbac_test_artifact_cleanup
-- says so in its own header: "This needs direct Supabase access -- same
-- hand-off as every other provisioning/schema step." Revoking service_role's
-- DELETE does not affect them. Neither Vercel cron
-- (/api/sairndental/send-reminder, /api/alf-alerts) deletes anything.
--
-- ── REVERSAL ──────────────────────────────────────────────────────────────
-- One line per table: GRANT DELETE ON public.<t> TO service_role.
-- This does NOT foreclose the deferred test/demo-data cleanup capability in
-- SAIRN-BACKLOG.md -- that item is explicitly undecided between soft- and
-- hard-delete. Revoking forces the decision to be made deliberately rather
-- than inherited from a copied grant.

-- ══ HARDENING PASS 2026-08-25 -- R1/R4/R6 ADDED, SECTION 3 REBUILT ══════
-- Same pass applied to sql/full_crud_truncate_sweep_2026-08-24.sql, which
-- has since run clean (923a31c). What this file already had, kept: the
-- revoke-then-grant loop preserving SELECT/INSERT/UPDATE exactly, both
-- exclusions with real reasons and a do-not-fold-back warning, and the
-- source-line reintroduction vector (scp_employee_auth fixed separately,
-- sairnscape_data_schema.sql's six flagged and deliberately left).
--
-- WHAT WAS MISSING, checked against the file rather than assumed:
--   R1  NO BASELINE OF ANY KIND. Before this pass the only executable
--       statement in all 358 lines was Section 1's discovery query.
--       Section 3 was prose plus a commented sc_* check plus manual app
--       smoke tests -- nothing to diff against, so a loop bug that dropped
--       UPDATE would have passed every check it had.
--   R4  No column-ACL or WITH GRANT OPTION pre-flight, though this file
--       uses REVOKE ALL and carries the identical hazard.
--   R6  No owner gate.
--   R5  No quiet-window note.
--   R2  NOT APPLICABLE, and checked rather than skipped: this file targets
--       ONE privilege and filters on that same privilege, so there is no
--       un-co-occurring sibling for the filter to miss. `not like 'sc\_%'`
--       was also verified -- it escapes to a literal `sc_` prefix and does
--       NOT exclude scp_* (SAIRNscape), which is the intended behaviour.
--   R3  ALREADY SATISFIED, better than the truncate file's first draft.
--       One addition: license_keys' real current row was re-read as R3
--       requires. Post-truncate-sweep it holds DELETE, INSERT, REFERENCES,
--       SELECT, TRIGGER, TRUNCATE, UPDATE -- and is now the ONLY table in
--       public still holding TRUNCATE/REFERENCES/TRIGGER, because it was
--       excluded from that sweep too. Its exclusion here stands.
--
-- ══ THE VERIFICATION SHAPE IS INVERTED. DO NOT COPY THE TRUNCATE FILE. ══
-- That sweep stripped a privilege NOTHING was allowed to lose, so its
-- Section 3b expected ZERO rows on both sides and any LOST row was a bug.
-- THIS sweep exists to remove DELETE, so LOST rows are the whole point.
-- Copying "expect zero on both sides" here would fail 134 times on
-- success. The assertion is instead:
--     EXACTLY 134 LOST, every one privilege_type = 'DELETE',
--     ZERO GAINED, and ZERO LOST of any other privilege type.
-- The last clause is the one doing real work -- it is what catches a loop
-- bug that dropped SELECT or UPDATE along the way, which is invisible to
-- "the DELETE grants are gone".
--
-- ══ EXPECTED NUMBERS, DERIVED NOT GUESSED ══════════════════════════════
-- All from the real 214-row truncate-sweep export cross-checked against
-- that sweep's confirmed run, so 3c is a genuine guard rather than a
-- plausible-looking number:
--   161 tables in public hold DELETE; 135 of them are non-sc_*, which
--       MATCHES this file's live Section 1 count of 135 exactly. The
--       export therefore fully contains this sweep's scope -- no untracked
--       table is hiding outside it.
--   134 in scope = 135 minus license_keys.
--     0 tables hold DELETE without also holding SELECT/INSERT/UPDATE, so
--       Section 2's "held ONLY DELETE" branch never fires and NO table is
--       left with zero grants. The loop anticipates the case; it does not
--       occur.
--   779 rows / 211 tables is the expected fresh baseline: the truncate
--       sweep captured 774/209, lost nothing (zero LOST), and the two
--       Phase 5 tables added 5 rows / 2 tables after it.
--   645 rows / 211 tables expected after Section 2 -- 779 minus 134 DELETE
--       rows, with the TABLE count unchanged because none is emptied.
--
-- ══ PRECONDITIONS THAT ARE NOT QUERY RESULTS ═══════════════════════════
-- (P1) SEQUENCING -- CLEAR. The truncate sweep is fully closed: run,
-- verified 3a/3b/3c, baseline table _grant_baseline_2026_08_25 DROPPED.
-- No other grant change is open. This sweep may take the window.
-- IT MUST STILL TAKE IT ALONE: capture, fix and verify with no other
-- grant script running in between, or this file's own 3b starts reporting
-- another script's intended changes as its failures.
-- (P2) THIS SWEEP CANNOT REUSE _grant_baseline_2026_08_25. It is dropped,
-- and it predated both the truncate run and the Phase 5 tables. Section 0
-- below captures its own, under its own name.
-- (P5) QUIET WINDOW, UNSCHEDULED. 134 tables, one DO block, one
-- transaction: GRANT/REVOKE takes an AccessExclusiveLock per relation and
-- the FIRST table locked stays locked until the whole loop commits.
-- Catalog-only work should be fast; "should be" is not a measurement.
--
-- ══ RUN ORDER ══════════════════════════════════════════════════════════
--   R6 -> R4 -> Section 0 -> Section 1 -> Section 2 (uncomment) -> 3a/3b/3c -> Section 4

-- ── SECTION R6: PRECONDITION. Must print `postgres`. ─────────────────────
-- role_table_grants only shows grants where the current user is grantor,
-- grantee or a member, and REVOKE only removes what the executing role has
-- authority over. As anything less, the loop iterates a SHORT list, changes
-- less than it claims, and Section 3 reports clean through the same blind
-- spot. service_role cannot run this sweep at all.
select current_user, session_user;

-- ── SECTION R4: PRE-FLIGHT. Both must return ZERO rows. ──────────────────
-- REVOKE ALL on a table cascades to that table's COLUMN-level privileges,
-- while Section 2's re-GRANT restores table-level ones only; WITH GRANT
-- OPTION is likewise not carried across. Neither is visible in
-- role_table_grants.
--
-- USE THIS QUERY, NOT information_schema.role_column_grants. That view
-- reports a row per column whenever the privilege is held INCLUDING via a
-- table-level grant, so it can never return zero on any database -- it
-- returned hundreds during the truncate sweep and read as a false stop.
-- pg_attribute.attacl is NULL unless a genuine column-specific GRANT was
-- issued, and has no table-level echo. Zero rows = pass in substance.
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
order by 1, 2, 3;

select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and grantee = 'service_role'
  and is_grantable = 'YES';

-- ── SECTION 0: BASELINE CAPTURE -- closes R1. Run BEFORE Section 2. ──────
-- A REAL table, deliberately, not a temp one: the Supabase SQL editor does
-- not guarantee two Run clicks share a session, and a temp table that
-- vanishes between them takes the only proof with it, leaving a mutation
-- applied and nothing to check it against.
--
-- Its own name, NOT the truncate sweep's. Captures every table
-- service_role holds CRUD on -- not just the DELETE holders -- which is
-- what lets 3b detect collateral loss on a table outside this sweep's
-- scope. Section 4 drops it.
drop table if exists public._delete_grant_baseline_2026_08_25;
create table public._delete_grant_baseline_2026_08_25 as
select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee = 'service_role'
  and privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE');

-- Expect 779 rows / 211 tables (see derivation above). More is possible if
-- a migration ran since; ANY LOWER means Section 0 under-read and 3b would
-- pass vacuously -- treat that as a failed capture, not a pass.
select count(*) as baseline_rows,
       count(distinct table_name) as baseline_tables
from public._delete_grant_baseline_2026_08_25;

-- ── SECTION 1: DISCOVER -- run this first, review the real output ─────────
-- Every table service_role can DELETE from that is NOT SAIRNcode's.
-- These are the rows Section 2 will change.
-- Expect 135 rows: the 134 in scope plus license_keys, which Section 2
-- excludes. Anything else means the picture moved -- stop and re-report.

select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as current_privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public'
  and g.grantee = 'service_role'
  and t.table_name not like 'sc\_%'
group by t.table_name
having bool_or(g.privilege_type = 'DELETE')
order by t.table_name;

-- Sanity counterpart -- the sc_* tables that must be LEFT ALONE.
-- Expect the SAIRNcode family here, and expect Section 2 not to touch them.
--
-- select t.table_name
-- from information_schema.tables t
-- join information_schema.role_table_grants g
--   on g.table_name = t.table_name and g.table_schema = t.table_schema
-- where t.table_schema = 'public' and g.grantee = 'service_role'
--   and t.table_name like 'sc\_%'
-- group by t.table_name
-- having bool_or(g.privilege_type = 'DELETE')
-- order by t.table_name;

-- ── SECTION 2: DRAFT FIX -- NOT RUN. Review Section 1's real output first. ──
-- Revoke-then-grant, so nothing regresses: strips ALL of service_role's
-- privileges on the table, then re-grants exactly whichever of
-- SELECT/INSERT/UPDATE it already held -- never more, never fewer, and
-- never DELETE. A table that somehow held only DELETE ends with no grant,
-- which is reported rather than silently done.
--
-- Excludes sc_* by the same pattern Section 1 uses, so the 29 SAIRNcode
-- grants are untouched. Idempotent and safe to re-run. Touches no row data.
--
-- DO $$
-- DECLARE
--   r RECORD;
--   keep_privs TEXT;
-- BEGIN
--   FOR r IN
--     SELECT t.table_name,
--            string_agg(DISTINCT g.privilege_type, ', ') AS all_privs
--     FROM information_schema.tables t
--     JOIN information_schema.role_table_grants g
--       ON g.table_name = t.table_name AND g.table_schema = t.table_schema
--     WHERE t.table_schema = 'public'
--       AND g.grantee = 'service_role'
--       AND t.table_name NOT LIKE 'sc\_%'
--       -- EXCLUDED ON MICHAEL'S DECISION 2026-08-25. Not a judgement call
--       -- left open any more: license_keys has no tracked CREATE TABLE
--       -- anywhere in this repo, so Section 2's output cannot be checked
--       -- against an expected schema, and every license check on the
--       -- platform depends on it. Real risk, not worth carrying in the same
--       -- pass as the rest. The truncate sweep excluded it for the same
--       -- reason. It gets its own dedicated review -- see the license_keys
--       -- row in docs/SAIRN-OPEN-WORK-INDEX.md. Do NOT quietly fold it back
--       -- into a later sweep.
--       AND t.table_name <> 'license_keys'
--     GROUP BY t.table_name
--     HAVING bool_or(g.privilege_type = 'DELETE')
--   LOOP
--     SELECT string_agg(priv, ', ') INTO keep_privs
--     FROM unnest(string_to_array(r.all_privs, ', ')) AS priv
--     WHERE priv IN ('SELECT', 'INSERT', 'UPDATE');
--
--     EXECUTE format('REVOKE ALL ON public.%I FROM service_role', r.table_name);
--     IF keep_privs IS NOT NULL THEN
--       EXECUTE format('GRANT %s ON public.%I TO service_role', keep_privs, r.table_name);
--     END IF;
--
--     RAISE NOTICE 'Revoked DELETE on %: kept %', r.table_name,
--       coalesce(keep_privs, '(nothing -- this table held ONLY DELETE, check it)');
--   END LOOP;
-- END $$;

-- ── SECTION 3: VERIFY, after Section 2 is actually run ───────────────────
-- FOUR checks, ALL must pass. The old Section 3 was 3a alone, in prose,
-- and 3a on its own proves only that a privilege went away -- it says
-- nothing about whether the others survived, which is the property the
-- revoke-then-grant loop actually rests on. 3b is the one that matters.

-- 3a. DELETE IS GONE OUTSIDE SAIRNcode. Expect EXACTLY ONE row:
--     license_keys, still holding DELETE, because Section 2 deliberately
--     excludes it. NOT "expect zero" -- that wording predates the
--     exclusion and would make a deliberate decision look like a failed
--     revoke. Any OTHER row is a real miss.
select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as current_privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public'
  and g.grantee = 'service_role'
  and t.table_name not like 'sc\_%'
group by t.table_name
having bool_or(g.privilege_type = 'DELETE')
order by t.table_name;

-- 3b. NOTHING BUT DELETE CHANGED. THE INVERTED CHECK -- read the shape
--     note at the top of this file before interpreting it. Unlike the
--     truncate sweep, LOST rows here are the OBJECTIVE, not a failure.
--     EXPECT EXACTLY ONE SUMMARY ROW:
--         delta = 'LOST' | privilege_type = 'DELETE' | n = 134
--     ANY other row fails the sweep:
--       * a LOST row with any other privilege_type -> the loop dropped a
--         privilege it was supposed to re-grant. This is the failure that
--         3a cannot see and that this whole section exists for.
--       * ANY GAINED row -> either something outside this script created
--         grants inside the window (check the table name against recent
--         migrations before assuming a bug -- that is exactly what the
--         truncate sweep's five GAINED rows turned out to be), or the loop
--         granted something it should not have. Note Section 2 is
--         structurally incapable of the latter: its GRANT list is
--         keep_privs, filtered from that same table's existing grants, so
--         it can only ever restore a subset.
--       * n <> 134 with delta/privilege otherwise correct -> scope moved
--         between Section 0 and Section 2. Reconcile before proceeding.
select
  case when a.table_name is null then 'LOST' else 'GAINED' end as delta,
  coalesce(b.privilege_type, a.privilege_type) as privilege_type,
  count(*) as n
from public._delete_grant_baseline_2026_08_25 b
full outer join (
  select table_name, privilege_type
  from information_schema.role_table_grants
  where table_schema = 'public'
    and grantee = 'service_role'
    and privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
) a
  on a.table_name = b.table_name and a.privilege_type = b.privilege_type
where a.table_name is null or b.table_name is null
group by 1, 2
order by 1, 2;

--     Detail query -- run ONLY if the summary above is not the single
--     expected row. Names every discrepancy individually.
-- select
--   coalesce(b.table_name, a.table_name) as table_name,
--   coalesce(b.privilege_type, a.privilege_type) as privilege_type,
--   case when a.table_name is null then 'LOST' else 'GAINED' end as delta
-- from public._delete_grant_baseline_2026_08_25 b
-- full outer join (
--   select table_name, privilege_type
--   from information_schema.role_table_grants
--   where table_schema = 'public' and grantee = 'service_role'
--     and privilege_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE')
-- ) a on a.table_name = b.table_name and a.privilege_type = b.privilege_type
-- where a.table_name is null or b.table_name is null
-- order by 3, 1, 2;

-- 3c. THE ARITHMETIC CLOSES, AND THE BASELINE WAS REAL. If Section 0
--     under-read, 3b compares against a short baseline and passes
--     vacuously -- the one way 3b can lie. Expect:
--       baseline_rows   779   (or higher if a migration ran since)
--       baseline_tables 211
--       live_rows       baseline_rows - 134
--       live_tables     baseline_tables  (UNCHANGED -- no table is emptied,
--                       because zero tables hold DELETE without also
--                       holding SELECT/INSERT/UPDATE)
--     baseline_rows at or below 774 means the capture predates the Phase 5
--     tables or under-read; do not trust 3b in that case.
select
  (select count(*) from public._delete_grant_baseline_2026_08_25)                    as baseline_rows,
  (select count(distinct table_name) from public._delete_grant_baseline_2026_08_25)  as baseline_tables,
  (select count(*) from information_schema.role_table_grants
     where table_schema = 'public' and grantee = 'service_role'
       and privilege_type in ('SELECT','INSERT','UPDATE','DELETE'))                  as live_rows,
  (select count(distinct table_name) from information_schema.role_table_grants
     where table_schema = 'public' and grantee = 'service_role'
       and privilege_type in ('SELECT','INSERT','UPDATE','DELETE'))                  as live_tables;

-- 3d. SAIRNcode UNTOUCHED. Expect the full sc_* family back, every row
--     still showing DELETE -- this is the one place DELETE is reachable by
--     real code (api/sd-data.js, SC_RESOURCES branch, admin-session gated).
select
  t.table_name,
  string_agg(distinct g.privilege_type, ', ' order by g.privilege_type) as privs
from information_schema.tables t
join information_schema.role_table_grants g
  on g.table_name = t.table_name and g.table_schema = t.table_schema
where t.table_schema = 'public' and g.grantee = 'service_role'
  and t.table_name like 'sc\_%'
group by t.table_name
having bool_or(g.privilege_type = 'DELETE')
order by t.table_name;

-- ── SECTION 4: CLEANUP -- only after 3a/3b/3c/3d all pass ────────────────
-- drop table public._delete_grant_baseline_2026_08_25;
--
-- Then confirm the app still works where it must: SAIRNcode's delete path
-- (api/sd-data.js SC_RESOURCES branch, admin session) must still succeed,
-- and a normal read/write round-trip on any sd_*/grd_*/dnt_* resource must
-- still succeed. A 403 from PostgREST on a WRITE would mean the re-grant
-- dropped a privilege -- that is what Section 2's keep_privs exists to
-- prevent, and what this check exists to catch if it failed anyway.

-- ── WHAT THIS DOES NOT COVER ──────────────────────────────────────────────
-- * The `anon` and `authenticated` roles. This file only touches
--   service_role. Those roles are locked out by RLS on these tables, but
--   their grants were not audited here.
-- * Schemas other than public.
-- * scp_employee_auth's source line -- FIXED 2026-08-25 in its own commit,
--   separately from this sweep. sql/scp_employee_auth_schema.sql now grants
--   `select, insert, update`. Verified afterwards: zero *_employee_auth
--   files on the platform still grant delete.
-- * THE SAME OVERCORRECTION IN sairnscape_data_schema.sql -- STILL OPEN.
--   The one-off check that fix required found it is NOT a one-off:
--   sql/sairnscape_data_schema.sql:24 carries the same rationale sentence
--   and same 2026-08-06 date, and grants delete on six more SAIRNscape
--   tables at lines 147-152 (scp_customers, scp_jobs, scp_quotes,
--   scp_schedule, scp_invoices, scp_progress_photos). Section 2 will revoke
--   all six live, after which that file and the database disagree and a
--   re-run of it restores them -- the exact failure mode the
--   scp_employee_auth fix just closed. Not fixed here: it is a schema edit,
--   it is six lines not one, and it deserves its own decision rather than
--   riding along in a grant sweep. Tracked in docs/SAIRN-OPEN-WORK-INDEX.md.
--   For scale, so this is not mistaken for the whole problem: 83 non-sc_*
--   `grant ... delete` lines exist across 35 files. Explicit delete grants
--   are common and are what this sweep is for. The overcorrection SIGNATURE
--   is what is narrow -- 2 files, both SAIRNscape, 7 grants.
-- * The DEFAULT PRIVILEGES that made this recur -- a new table created by a
--   schema file that copies the usual `grant select, insert, update, delete`
--   line will reintroduce a DELETE grant. The durable fix is to stop writing
--   `delete` into new schema files; this sweep only cleans what exists now.
