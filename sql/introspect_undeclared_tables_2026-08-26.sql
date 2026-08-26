-- sql/introspect_undeclared_tables_2026-08-26.sql
-- READ-ONLY. Six independent SELECTs, no shared state -- run them one at a
-- time. Nothing here writes, creates, drops, grants or alters.
--
-- WHY. `business_profiles`, `ai_memories` and `employees` are live in
-- production and declared in NO schema file anywhere in sql/. Found from two
-- directions on 2026-08-25: Cody reached them from the code side (registered
-- resources `profile`, `memory`, `employees` with no same-named table and no
-- `create table` for their real targets), and they are 3 of the 25
-- `live_but_not_declared` rows returned by
-- sql/provisioning_gap_check_2026-08-25.sql. A rebuild from sql/ alone would
-- silently omit all three -- including `business_profiles`, which every
-- StoneDesk profile read and write depends on.
--
-- The migration files cannot be written from the code. The code shows which
-- COLUMNS are touched; it cannot show types, defaults, primary keys, indexes,
-- RLS policies or grants, and guessing those is how a "restored" table comes
-- back subtly different from the one it replaced. This file exists to get the
-- real structure first.
--
-- ── WHAT THE CODE ALREADY IMPLIES, to be checked against the output ────────
-- Recorded here as a CROSS-CHECK, not as the answer. If section 1 disagrees
-- with any of this, the database wins and the disagreement is itself worth a
-- line in docs/SAIRN-OPEN-WORK-INDEX.md.
--
--   business_profiles  license_hash, app_id, data (jsonb), shop_id, updated_at
--                      UNIQUE (license_hash, app_id)
--                        -- proven by `?on_conflict=license_hash,app_id`
--                        -- with Prefer: resolution=merge-duplicates
--                        (api/sd-data.js:288)
--   ai_memories        license_hash, app_id, shop_id, data (jsonb), created_at
--                      plain INSERT, no on_conflict -- so a surrogate key is
--                      likely, and `created_at` must default server-side: the
--                      writer never sends it, but the reader orders by it
--                      (api/sd-data.js:303, :320)
--   employees          customer_email, employee_id, source_app, status,
--                      data (jsonb), updated_at
--                      UNIQUE (customer_email, employee_id)
--                        (api/sd-data.js:432)
--                      NOTE: scoped by customer_email, NOT license_hash --
--                      the only table on the platform keyed this way. Confirm
--                      before copying the pattern anywhere.

-- ── 1. COLUMNS: name, type, nullability, default ───────────────────────────
select table_name,
       ordinal_position                as pos,
       column_name,
       data_type,
       character_maximum_length        as maxlen,
       numeric_precision,
       numeric_scale,
       is_nullable,
       column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name in ('business_profiles', 'ai_memories', 'employees')
 order by table_name, ordinal_position;

-- ── 2. CONSTRAINTS: primary key, unique, foreign key, check ────────────────
-- pg_get_constraintdef() gives the exact text to put in the migration, so the
-- restored constraint is character-identical rather than reconstructed.
select rel.relname                     as table_name,
       con.conname                     as constraint_name,
       case con.contype when 'p' then 'PRIMARY KEY'
                        when 'u' then 'UNIQUE'
                        when 'f' then 'FOREIGN KEY'
                        when 'c' then 'CHECK'
                        else con.contype::text end as kind,
       pg_get_constraintdef(con.oid)   as definition
  from pg_constraint con
  join pg_class rel on rel.oid = con.conrelid
  join pg_namespace ns on ns.oid = rel.relnamespace
 where ns.nspname = 'public'
   and rel.relname in ('business_profiles', 'ai_memories', 'employees')
 order by rel.relname, con.contype, con.conname;

-- ── 3. INDEXES ─────────────────────────────────────────────────────────────
-- Includes the ones backing the constraints above; the extras are the ones
-- that would be silently lost in a rebuild and only show up later as a slow
-- query nobody can explain.
select tablename                       as table_name,
       indexname,
       indexdef
  from pg_indexes
 where schemaname = 'public'
   and tablename in ('business_profiles', 'ai_memories', 'employees')
 order by tablename, indexname;

-- ── 4. RLS: enabled flag, and every policy in full ─────────────────────────
select c.relname                       as table_name,
       c.relrowsecurity                as rls_enabled,
       c.relforcerowsecurity           as rls_forced,
       p.polname                       as policy_name,
       p.polcmd                        as command,
       pg_get_expr(p.polqual,     p.polrelid) as using_expr,
       pg_get_expr(p.polwithcheck, p.polrelid) as with_check_expr
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  left join pg_policy p on p.polrelid = c.oid
 where n.nspname = 'public'
   and c.relname in ('business_profiles', 'ai_memories', 'employees')
 order by c.relname, p.polname;

-- ── 5. GRANTS ──────────────────────────────────────────────────────────────
-- Expect select/insert/update and NO delete, matching the platform-wide state
-- after the 2026-08-25 sweep. If DELETE shows up here, that is a finding: it
-- means these three were missed by that sweep the same way the two
-- `execute format(...)` loops were.
select table_name,
       grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
  from information_schema.role_table_grants
 where table_schema = 'public'
   and table_name in ('business_profiles', 'ai_memories', 'employees')
 group by table_name, grantee
 order by table_name, grantee;

-- ── 6. SANITY: all three present, and how much data is at stake ────────────
-- Run this FIRST if you only run one. If any table_name is missing from the
-- result, sections 1-5 are describing fewer tables than this file claims and
-- the migrations must not be written from a partial answer.
select c.relname                       as table_name,
       c.reltuples::bigint             as approx_rows,
       pg_size_pretty(pg_total_relation_size(c.oid)) as total_size
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public'
   and c.relkind = 'r'
   and c.relname in ('business_profiles', 'ai_memories', 'employees')
 order by c.relname;
