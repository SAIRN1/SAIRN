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
-- QUERY 1 -- THE COPY COST. How many rows does a licence have to be given?
-- Run first: cheap, and it sizes the problem before you look at content.
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
-- QUERY 2 -- THE ONE THAT MATTERS. Same rule id, DIFFERENT content, on two
-- or more licences. Every row returned here is two customers being told
-- different things by the same product.
--
-- Compares a stable hash of the `data` blob per (table, rule id), counting how
-- many DISTINCT versions exist across licences. 1 = every licence that holds it
-- agrees. 2+ = they have already diverged.
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
idcols as (
  -- identity column = the non-license_hash half of the 2-column unique key,
  -- read from pg_constraint rather than guessed from the column name
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
)
select
  x.table_name,
  x.entry_id,
  x.licences_holding_it,
  x.distinct_versions,
  case when x.distinct_versions > 1
       then 'DIVERGED -- licences disagree about this rule'
       else 'consistent' end as verdict
from ref_tables r
join idcols i on i.table_name = r.table_name
cross join lateral (
  select
    (xpath('/row/t/text()', q))[1]::text            as table_name,
    (xpath('/row/e/text()', q))[1]::text            as entry_id,
    (xpath('/row/n/text()', q))[1]::text::bigint    as licences_holding_it,
    (xpath('/row/v/text()', q))[1]::text::bigint    as distinct_versions
  from unnest(
    xpath('/table/row',
      query_to_xml(format(
        'select %L::text as t, %I as e, count(distinct license_hash) as n,'
        ' count(distinct md5(data::text)) as v'
        ' from public.%I group by %I having count(distinct license_hash) > 1',
        r.table_name, i.id_col, r.table_name, i.id_col), false, true, ''))
  ) as q
) x
order by x.distinct_versions desc, x.licences_holding_it desc, x.table_name, x.entry_id;

-- ═════════════════════════════════════════════════════════════════════════
-- READING THE RESULT
-- ═════════════════════════════════════════════════════════════════════════
-- ANY row with verdict 'DIVERGED' in a genuinely-shared table (law_deadline_rules,
--   law_holidays, alf_compliance_rules, alf_payer_rules, dnt_cred_rules,
--   rf_cert_rules, rf_contingency_rules, sc_anesthesia_base_units) is a live
--   defect: two customers are being told different things by the same product,
--   and neither is flagged as stale. Fix the data before the schema.
--
-- ZERO diverged rows does NOT mean the design is fine. It means nothing has
--   drifted YET -- most likely because few licences have been seeded at all.
--   The mechanism that allows drift is unchanged, and every rule correction
--   made from now on still has to be applied per licence by hand.
--
-- A rule present on ONE licence and absent from another is NOT reported here at
--   all: query 2 only considers ids held by 2+ licences. Query 1 shows that gap
--   as unequal row counts, which for a jurisdiction rule set is usually the more
--   common shape -- customer A has the corrected rule, customer B never got it.
--
-- ── LIMIT, stated so it is not assumed away ─────────────────────────────
-- md5(data::text) is sensitive to JSON key ORDER, so two semantically identical
-- blobs written by different code paths can hash differently and read as
-- diverged. Treat query 2's output as a candidate list to eyeball, not a verdict:
-- confirm any hit by diffing the two `data` values directly before calling it a
-- defect. A false DIVERGED is cheap; a missed one is not, which is why the
-- comparison errs this way deliberately.
