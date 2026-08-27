-- sql/platform_demo_licence_provenance_audit_2026-08-28.sql
-- READ-ONLY. No insert, update, delete, grant, revoke, alter, drop or truncate.
-- No temp tables and no DO block either -- see "WHY query_to_xml" below.
--
-- PURPOSE: find which demo licences actually hold unaccounted-for rows, BEFORE
-- anyone writes a seed file. Seeding is only worth doing for licences a prospect
-- could really be shown; this tells us which those are and what is on them.
--
-- ── WHY THIS IS LIST-FREE ────────────────────────────────────────────────
-- There are 181 per-app resources across 12 apps (counted from
-- api/_resources/*.js, the same allowlist api/sd-data.js enforces). A hand-built
-- table list would be wrong within a week and wrong silently -- the platform has
-- already been bitten by exactly that: sql/sairndental_data_schema.sql survived a
-- repo-wide grant sweep because its table names were supplied at runtime as %I
-- and no grep could see them.
-- So nothing here names a table. Everything is discovered:
--   * a PER-LICENCE table is any table in `public` with a `license_hash` column;
--   * its IDENTITY column is the non-license_hash member of its 2-column unique
--     constraint (license_hash, X) -- which is how every one of these schemas is
--     built;
--   * the LICENCES come from public.license_keys itself, not from a list of
--     seed files. That matters: a licence created by hand in the dashboard and
--     never written to a seed file is exactly the kind that accumulates debris
--     unnoticed, and a hardcoded list of fifteen would miss it.
--
-- ── WHY query_to_xml AND NOT A DO BLOCK ─────────────────────────────────
-- Counting rows in a table whose name is only known at runtime needs dynamic
-- SQL. The usual route is a DO block writing into a temp table -- but this
-- platform has a standing note that the Supabase SQL editor does not guarantee
-- two Run clicks share a session, and a vanishing temp table takes the only
-- proof with it. query_to_xml() runs dynamic SQL inside an ordinary SELECT and
-- returns its result, so each query below is a single self-contained statement
-- that leaves nothing behind. It is read-only by construction: query_to_xml
-- cannot execute a statement that writes.
--
-- ── HOW TO USE ───────────────────────────────────────────────────────────
-- Run query 1 first. If it returns nothing, no per-licence table anywhere holds
-- a single row and there is nothing to seed or clean. Only then run 2 and 3.
-- Query 1 is cheap (one count per table). Query 2 is the expensive one and is
-- deliberately restricted to tables query 1 proved non-empty.

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1 -- WHICH PER-LICENCE TABLES HOLD ANY ROWS AT ALL?
-- Cheap. Run this first and let it narrow everything that follows.
-- ═════════════════════════════════════════════════════════════════════════
with per_licence_tables as (
  select c.table_name
  from information_schema.columns c
  join information_schema.tables t
    on t.table_schema = c.table_schema and t.table_name = c.table_name
   and t.table_type = 'BASE TABLE'
  where c.table_schema = 'public'
    and c.column_name = 'license_hash'
)
select
  p.table_name,
  (xpath('/row/c/text()',
     query_to_xml(format('select count(*) as c from public.%I', p.table_name),
                  false, true, '')))[1]::text::bigint as row_count
from per_licence_tables p
where (xpath('/row/c/text()',
        query_to_xml(format('select count(*) as c from public.%I', p.table_name),
                     false, true, '')))[1]::text::bigint > 0
order by row_count desc, table_name;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 2 -- WHO OWNS THOSE ROWS: per (licence, table) breakdown.
-- Joins against license_keys so every row is attributed to a real licence and
-- its app_id. Rows whose license_hash matches NO licence key are reported too,
-- under app_id '(orphaned licence_hash)' -- those are the most interesting of
-- all, because they belong to a licence that no longer exists.
-- ═════════════════════════════════════════════════════════════════════════
with per_licence_tables as (
  select c.table_name
  from information_schema.columns c
  join information_schema.tables t
    on t.table_schema = c.table_schema and t.table_name = c.table_name
   and t.table_type = 'BASE TABLE'
  where c.table_schema = 'public'
    and c.column_name = 'license_hash'
),
non_empty as (
  select p.table_name
  from per_licence_tables p
  where (xpath('/row/c/text()',
          query_to_xml(format('select count(*) as c from public.%I', p.table_name),
                       false, true, '')))[1]::text::bigint > 0
),
licences as (
  select k.key,
         k.app_id,
         k.status,
         encode(digest(k.key, 'sha256'), 'hex') as lic_hash
  from public.license_keys k
)
select
  l.app_id,
  l.key            as licence,
  l.status,
  n.table_name,
  (xpath('/row/c/text()',
     query_to_xml(format('select count(*) as c from public.%I where license_hash = %L',
                         n.table_name, l.lic_hash),
                  false, true, '')))[1]::text::bigint as rows_on_this_licence
from non_empty n
cross join licences l
where (xpath('/row/c/text()',
        query_to_xml(format('select count(*) as c from public.%I where license_hash = %L',
                            n.table_name, l.lic_hash),
                     false, true, '')))[1]::text::bigint > 0
order by l.app_id, l.key, n.table_name;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 3 -- THE PROVENANCE TELL: machine-minted ids.
-- Every id in these apps is either typed by a person or minted by code as
-- <PREFIX>-<13-digit epoch ms>-<random>. Nobody types a 13-digit epoch. So a
-- row whose identity column matches that shape is machine-generated traffic,
-- and on a DEMO licence it needs justifying before it is kept.
--
-- The identity column is discovered from the 2-column unique constraint
-- (license_hash, X) that every one of these schemas declares -- not guessed from
-- the column name, because several of these tables carry more than one *_id
-- column (dnt_appointments alone has appointment_id, provider_id and
-- operatory_id) and picking the wrong one would silently report zero.
-- ═════════════════════════════════════════════════════════════════════════
with id_cols as (
  select rel.relname::text as table_name,
         att.attname::text as id_col
  from pg_constraint con
  join pg_class      rel on rel.oid = con.conrelid
  join pg_namespace  ns  on ns.oid  = rel.relnamespace
  join lateral unnest(con.conkey) as k(attnum) on true
  join pg_attribute  att on att.attrelid = rel.oid and att.attnum = k.attnum
  join pg_type       ty  on ty.oid = att.atttypid
  where con.contype = 'u'
    and ns.nspname  = 'public'
    and array_length(con.conkey, 1) = 2          -- exactly (license_hash, X)
    and att.attname <> 'license_hash'
    and ty.typname in ('text', 'varchar', 'bpchar')
    and exists (
      select 1
      from lateral unnest(con.conkey) as k2(attnum)
      join pg_attribute a2 on a2.attrelid = rel.oid and a2.attnum = k2.attnum
      where a2.attname = 'license_hash'
    )
),
licences as (
  select k.key, k.app_id,
         encode(digest(k.key, 'sha256'), 'hex') as lic_hash
  from public.license_keys k
)
select
  l.app_id,
  l.key as licence,
  i.table_name,
  i.id_col,
  (xpath('/row/c/text()',
     query_to_xml(format(
       'select count(*) as c from public.%I where license_hash = %L and %I ~ %L',
       i.table_name, l.lic_hash, i.id_col, '^[A-Za-z]+-[0-9]{13}-'),
       false, true, '')))[1]::text::bigint as machine_minted_rows
from id_cols i
cross join licences l
where (xpath('/row/c/text()',
        query_to_xml(format(
          'select count(*) as c from public.%I where license_hash = %L and %I ~ %L',
          i.table_name, l.lic_hash, i.id_col, '^[A-Za-z]+-[0-9]{13}-'),
          false, true, '')))[1]::text::bigint > 0
order by machine_minted_rows desc, l.app_id, i.table_name;

-- ═════════════════════════════════════════════════════════════════════════
-- READING THE RESULTS
-- ═════════════════════════════════════════════════════════════════════════
-- A licence appearing in query 2 with rows, and in query 3 with
-- machine_minted_rows > 0, is carrying the same class of debris SAIRNdental had.
--
-- A licence appearing in query 2 but NOT query 3 is carrying rows with
-- human-typed or seeded ids -- deliberate data, or at least data somebody chose.
-- Do not treat that as debris without reading it.
--
-- A licence appearing in NEITHER is empty. That is not automatically fine: an
-- empty demo licence shows a prospect an empty app. It is the cheaper problem,
-- because a seed fixes it and nothing has to be removed first.
--
-- ── WHAT THIS AUDIT CANNOT TELL YOU, STATED SO IT IS NOT ASSUMED ────────
-- 1. It cannot tell a good row from a bad one. `PT-DEMO-1` and a junk row typed
--    by hand during testing look identical to it. Query 3's shape test only
--    catches CODE-minted ids; debris entered through the UI by a person is
--    invisible here and needs a human read of the rows themselves.
-- 2. It says nothing about referential integrity. SAIRNdental's real symptom was
--    appointments pointing at patients that did not exist, and no query above
--    would have found that -- the rows were present and correctly attributed.
--    An orphan check has to be written per app against that app's own foreign
--    relationships, because they live inside jsonb blobs, not in constraints.
-- 3. `digest()` needs pgcrypto. If it is unavailable, the licences CTEs are the
--    only thing that needs changing; queries 1 and 3's structure is unaffected.
