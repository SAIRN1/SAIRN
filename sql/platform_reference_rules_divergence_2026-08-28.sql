-- sql/platform_reference_rules_divergence_2026-08-28.sql
-- READ-ONLY. No insert, update, delete, grant, revoke, alter, drop, truncate.
-- No temp table, no DO block -- query_to_xml runs the dynamic SQL inside an
-- ordinary SELECT and cannot execute a statement that writes.
--
-- ── WHAT THIS IS FOR ─────────────────────────────────────────────────────
-- A data-side diagnostic for the per-licence reference-content problem, offered
-- to whoever takes the SAIRNlaw rules-scoping work (Hank/Ted). It designs
-- nothing and changes nothing -- it answers the one question that decides how
-- urgent the redesign is:
--
--     ARE LICENCES ALREADY DISAGREEING ABOUT THE SAME RULE?
--
-- If two licences hold the same rule_id with different content, that is not a
-- future risk, it is a live correctness defect today, and a wrong legal deadline
-- looks exactly as authoritative as a right one. If they agree, the redesign is
-- still worth doing but nothing is currently wrong, and it can be sequenced
-- calmly.
--
-- ── WHY IT IS SAFE TO RUN WHILE SOMEONE ELSE IS BUILDING THE FIX ────────
-- It is read-only and it is a NEW file. It cannot collide with a schema change,
-- a migration, or an in-progress branch. Nothing here presumes any particular
-- solution -- a shared table, a platform sentinel licence, a copy-on-provision
-- step, or a rules service are all still open, and this measurement is useful
-- to every one of them.
--
-- ── LIST-FREE, for the same reason as the provenance audit ───────────────
-- Reference tables are DISCOVERED, not enumerated: any table in `public` that
-- has BOTH a `license_hash` column and a name matching the reference-content
-- shape (rules / rates / codes / requirements / holidays / standards / units).
-- New rules tables are picked up automatically as apps add them; a hand-built
-- list would be stale within a week and stale silently.
--
-- ⚠ THE ONE JUDGMENT THIS FILE MAKES, stated so it can be overridden:
-- name-shape is a proxy for "shared reference content", and it is imperfect in
-- BOTH directions. `dnt_coverage_rules` (a practice's own insurance config),
-- `grd_boq_rates` (a company's own rates), `leg_merch_catalog` and
-- `sdn_colorcodes` are legitimately PER-CUSTOMER and will appear here as noise
-- -- divergence between licences is CORRECT for those. Conversely a shared-
-- content table named without one of those words would be missed. Read the
-- table name before reading the number.

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 0 -- SELF-TEST. Run this FIRST, once. It costs nothing, and it proves
-- the mechanism survives the exact case that broke the first version of query 2.
--
-- It calls query_to_xml on a query that returns ZERO rows before aggregation.
-- Expected result: a single row containing the text "(none)".
-- If it instead raises "could not parse XML document / Document is empty", stop
-- -- the fix did not take on this server and query 2 will fail the same way.
-- ═════════════════════════════════════════════════════════════════════════
select (xpath('/row/c/text()',
         query_to_xml(
           $q$ select coalesce(string_agg(x::text, ', '), '(none)') as c
                 from (select 1 where false) t(x) $q$,
           false, true, '')))[1]::text as self_test_expect_none;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1 -- THE COPY COST. How many rows does a licence have to be given?
-- Cheap, and it sizes the problem before you look at content.
-- ═════════════════════════════════════════════════════════════════════════
with ref_tables as (
  select c.table_name
  from information_schema.columns c
  join information_schema.tables t
    on t.table_schema = c.table_schema and t.table_name = c.table_name
   and t.table_type = 'BASE TABLE'
  where c.table_schema = 'public'
    and c.column_name = 'license_hash'
    and c.table_name ~ '(_rules?|_rates?|_codes?|_requirements?|_holidays?|_standards?|_units)$'
),
licences as (
  select k.key, k.app_id, encode(digest(k.key,'sha256'),'hex') as lic_hash
  from public.license_keys k
)
select
  r.table_name,
  l.app_id,
  l.key as licence,
  (xpath('/row/c/text()',
     query_to_xml(format('select count(*) as c from public.%I where license_hash = %L',
                         r.table_name, l.lic_hash), false, true, '')))[1]::text::bigint as rows_held
from ref_tables r
cross join licences l
where (xpath('/row/c/text()',
        query_to_xml(format('select count(*) as c from public.%I where license_hash = %L',
                            r.table_name, l.lic_hash), false, true, '')))[1]::text::bigint > 0
order by rows_held desc, r.table_name, l.app_id;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 2 -- THE ONE THAT MATTERS. Same rule id, DIFFERENT content, across two
-- or more licences. Anything flagged here is two customers being told different
-- things by the same product.
--
-- ── FIXED 2026-08-28 AFTER IT FAILED ON FIRST RUN ───────────────────────
-- Reported error: "could not parse XML document / DETAIL: line 1: Document is
-- empty". TWO separate defects in one call, and the second was hidden behind
-- the first:
--
--   1. EMPTY RESULT SET -> EMPTY DOCUMENT. The inner query ended in
--      HAVING count(distinct license_hash) > 1, which legitimately matches
--      NOTHING for most tables. query_to_xml over a zero-row query returns an
--      empty xml value, and xpath() then tries to parse '' and raises. This was
--      not bad data -- a table with no shared rule ids is the NORMAL case, so
--      the query was guaranteed to fail on any realistic database. It could only
--      have succeeded if every reference table already had divergence, which is
--      the opposite of what anyone expects to find.
--
--   2. WRONG XPATH FOR THE OUTPUT SHAPE. With tableforest = true,
--      query_to_xml emits bare <row> elements with no wrapper, but the xpath
--      asked for '/table/row' -- the wrapped shape that tableforest = false
--      produces. So even on a table WITH divergence it would have matched
--      nothing and reported a confident zero. Defect 1 made it crash; without
--      defect 1, defect 2 would have made it lie. The crash was the lucky part.
--
-- THE FIX avoids the fragile construct rather than patching it. Every dynamic
-- call below returns EXACTLY ONE ROW -- an aggregate, wrapped in coalesce --
-- which is the same single-row shape query 1 uses and which has already run
-- clean on this platform. A one-row result can never be an empty document, and
-- there is no row-splitting xpath left to get wrong.
--
-- The cost, stated plainly: findings arrive as one line per TABLE with the
-- offending ids in a list column, rather than one line per rule id. For a
-- diagnostic whose job is "is anything diverged, and where", that reads better.
-- ═════════════════════════════════════════════════════════════════════════
with ref_tables as (
  select c.table_name
  from information_schema.columns c
  join information_schema.tables t
    on t.table_schema = c.table_schema and t.table_name = c.table_name
   and t.table_type = 'BASE TABLE'
  where c.table_schema = 'public'
    and c.column_name = 'license_hash'
    and c.table_name ~ '(_rules?|_rates?|_codes?|_requirements?|_holidays?|_standards?|_units)$'
    -- REQUIRE a `data` column. Every reference table on this platform today is
    -- (license_hash, <x>_id, data jsonb), so this changes nothing now -- it is
    -- here because the comparison below hashes `data`, and a future reference
    -- table shaped differently would otherwise fail the whole query with a
    -- column-does-not-exist error rather than simply not being comparable.
    -- Same class of unguarded assumption as the empty-document defect above.
    and exists (select 1 from information_schema.columns d
                 where d.table_schema = 'public'
                   and d.table_name = c.table_name
                   and d.column_name = 'data')
),
idcols as (
  -- identity column = the non-license_hash half of the 2-column unique key,
  -- read from pg_constraint rather than guessed from a *_id column name
  select rel.relname::text as table_name, att.attname::text as id_col
  from pg_constraint con
  join pg_class rel on rel.oid = con.conrelid
  join pg_namespace ns on ns.oid = rel.relnamespace
  join lateral unnest(con.conkey) as k(attnum) on true
  join pg_attribute att on att.attrelid = rel.oid and att.attnum = k.attnum
  join pg_type ty on ty.oid = att.atttypid
  where con.contype = 'u' and ns.nspname = 'public'
    and array_length(con.conkey,1) = 2
    and att.attname <> 'license_hash'
    and ty.typname in ('text','varchar','bpchar')
    and exists (select 1 from lateral unnest(con.conkey) as k2(attnum)
                join pg_attribute a2 on a2.attrelid = rel.oid and a2.attnum = k2.attnum
                where a2.attname = 'license_hash')
),
measured as (
  select
    r.table_name,
    i.id_col,
    -- ids held by 2+ licences whose content AGREES everywhere
    (xpath('/row/c/text()',
       query_to_xml(format(
         $f$select count(*) as c from (select %I as k from public.%I group by %I
              having count(distinct license_hash) > 1
                 and count(distinct md5(data::text)) = 1) s$f$,
         i.id_col, r.table_name, i.id_col), false, true, '')))[1]::text::bigint
       as consistent_ids,
    -- ids held by 2+ licences with 2+ DISTINCT versions of the blob
    (xpath('/row/c/text()',
       query_to_xml(format(
         $f$select count(*) as c from (select %I as k from public.%I group by %I
              having count(distinct license_hash) > 1
                 and count(distinct md5(data::text)) > 1) s$f$,
         i.id_col, r.table_name, i.id_col), false, true, '')))[1]::text::bigint
       as diverged_ids,
    -- WHICH ids, as one always-present string. coalesce guarantees a value even
    -- when the inner set is empty, which is what keeps this from ever producing
    -- an empty document -- the whole point of the rewrite.
    (xpath('/row/c/text()',
       query_to_xml(format(
         $f$select coalesce(string_agg(k::text, ', ' order by k), '(none)') as c
              from (select %I as k from public.%I group by %I
                     having count(distinct license_hash) > 1
                        and count(distinct md5(data::text)) > 1) s$f$,
         i.id_col, r.table_name, i.id_col), false, true, '')))[1]::text
       as diverged_id_list
  from ref_tables r
  join idcols i on i.table_name = r.table_name
)
select
  table_name,
  id_col,
  consistent_ids,
  diverged_ids,
  case when diverged_ids > 0
       then 'DIVERGED -- diff these two blobs before calling it a defect'
       else 'consistent' end as verdict,
  diverged_id_list
from measured
order by diverged_ids desc, table_name;

-- ═════════════════════════════════════════════════════════════════════════
-- READING THE RESULT
-- ═════════════════════════════════════════════════════════════════════════
-- ANY table with diverged_ids > 0 that is genuinely shared content
--   (law_deadline_rules, law_holidays, alf_compliance_rules, alf_payer_rules,
--   dnt_cred_rules, rf_cert_rules, rf_contingency_rules,
--   sc_anesthesia_base_units) is a live defect: two customers are being told
--   different things and neither copy is flagged as stale. Fix the DATA before
--   the schema.
--
-- ZERO diverged everywhere does NOT mean the design is fine. It most likely
--   means few licences have been seeded at all. The mechanism that allows drift
--   is unchanged, and every rule correction from here still has to be applied
--   per licence by hand -- including the two deadline fixes made on 2026-08-27.
--
-- A rule present on ONE licence and absent from another is NOT counted here:
--   both columns only consider ids held by 2+ licences. Query 1 shows that gap
--   as unequal row counts, and for a jurisdiction rule set it is usually the
--   more common shape -- customer A got the corrected rule, customer B never did.
--
-- ── LIMIT, stated so it is not assumed away ─────────────────────────────
-- md5(data::text) is sensitive to JSON key ORDER, so two semantically identical
-- blobs written by different code paths can hash differently and read as
-- diverged. Treat diverged_id_list as a candidate list to eyeball, not a
-- verdict: confirm by diffing the two `data` values directly before calling
-- anything a defect. A false DIVERGED is cheap; a missed one is not, which is
-- why the comparison errs in this direction deliberately.

-- ═════════════════════════════════════════════════════════════════════════
-- RESULT OF THE FIRST REAL RUN -- 2026-08-28 (Hank). READ THIS BEFORE
-- RE-RUNNING, or you will re-report a finding that is already resolved.
-- ═════════════════════════════════════════════════════════════════════════
-- The divergence query returned 87 diverged ids in law_deadline_rules and 48 in law_holidays,
-- both between LAW-PINNACLE-2026 and LAW-TEST-2026, and ZERO everywhere else on
-- the platform. All 87 and all 48 are FALSE POSITIVES of exactly the kind the
-- LIMIT note above predicts -- though not for the key-order reason it names.
--
-- CAUSE: api/legal-deadlines.js writes `authority.verified_by` INTO the `data`
-- blob on every add_rule and add_holidays --
--     verified_by: caller ? caller.employee_id : null
-- LAW-TEST-2026 was loaded through an authenticated employee session, so every
-- one of its rows carries "hank-verify". LAW-PINNACLE-2026 was backfilled by
-- tools/load_deadline_seed.py, which sends the bearer key and no session, so
-- every one of ITS rows carries null. That single field is present on 100% of
-- rows by construction, so md5(data::text) differs on 100% of shared ids no
-- matter what the rule says. The counts confirm it exactly: TEST holds 87 rules
-- and 8 jurisdictions x 6 years = 48 calendars. 87/87 and 48/48.
--
-- CONFIRMED, not assumed: a read-only compute-diff of all 89 repo rules in
-- TEST's 8 jurisdictions, on both licences, 178 probes, whole responses compared
-- with verified_by stripped. 160 identical with a real date, 4 identical
-- refusals, 4 for the 2 ids TEST never had, and 10 divergent across 7 ids -- all
-- 7 being rows touched by commits e1aa3f8 and a9daad1, with TEST the stale side.
-- Only frcp-12a1Ai-answer-after-service and frcp-12a2-united-states-official-
-- capacity produce a different DATE. Nothing unexplained remains.
--
-- ⚠ IF YOU FIX THIS QUERY, fix it by EXCLUDING verified_by from the hash, e.g.
--     md5((data #- '{authority,verified_by}')::text)
-- Do NOT widen it to ignore all of `authority` -- retrieved_at and the authority
-- URL are substantive content, and a rule whose cited source changed between two
-- licences is a real defect this query must still catch.
--
-- ALSO NOT A DEFECT: LAW-TEST-2026 is an internal verification tenant
-- (sql/sairnlaw_test_license_seed.sql, customer_email
-- test@sairnlaw-verification.example), deliberately left stale when
-- LAW-PINNACLE-2026 became canonical on 2026-08-25. Two customers are NOT being
-- told different things; one customer and one test tenant are.
--
-- WHAT THE RUN DID FIND, by diffing blobs rather than trusting the count: two
-- fixes committed 2026-08-27 had never been LOADED, so the canonical customer
-- licence was still computing federal answer deadlines three days late. Seed-file
-- changes are inert until tools/load_deadline_seed.py runs. Reloaded and
-- live-verified the same day; see docs/SAIRN-OPEN-WORK-INDEX.md, SAIRNlaw row.
