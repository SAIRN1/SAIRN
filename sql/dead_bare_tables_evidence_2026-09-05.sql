-- sql/dead_bare_tables_evidence_2026-09-05.sql
-- READ-ONLY. Every statement is a SELECT. Nothing here drops, alters, grants
-- or writes. The only DDL in this file is Section 7, which is commented out
-- and is a TEMPLATE, not a recommendation.
--
-- NOT RUN by any session -- no SAIRN clone holds a credential that can read
-- pg_stat_user_tables or pg_depend. Hand-off to the Supabase SQL editor.
--
-- ── WHAT THIS IS FOR ───────────────────────────────────────────────────────
-- docs/SAIRN-OPEN-WORK-INDEX.md carries a row: 19 bare-named tables carry the
-- excess grant baseline and are reachable by NO CODE PATH AT ALL. Its next
-- action is stated precisely: "confirm each is empty and unreferenced before
-- proposing any drop -- dropping a table is a schema owner's call, not a
-- session's." This file is that confirmation, and it stops there.
--
-- ── THE CODE-SIDE HALF IS RE-VERIFIED, NOT INHERITED (2026-09-05) ──────────
-- The finding is from 2026-08-25 and two weeks of commits have landed since.
-- A table that was dead then is not necessarily dead now, so the code scan was
-- RE-RUN from scratch rather than trusted: five reference shapes per table --
-- rest('<t>?…'), a literal /rest/v1/<t>, `from <t>`, insert/update/delete/
-- truncate on <t>, and create table <t> -- across every .js/.html/.py/.sql in
-- the repo, comment lines excluded, `archive/` excluded.
--
-- RESULT: all 19 still unreferenced. The single hit was `customers`, inside a
-- DOCSTRING in tools/sairn_sql_preflight.py describing a hypothetical seed
-- file -- prose, not a call site. That is the third independent confirmation
-- of this list: Cody from the code side 2026-08-25, SAIRN-cc by a different
-- route in dd5327b6, and this re-run.
--
-- ── WHY "EMPTY" IS NOT THE STRONGEST TEST, AND WHAT IS ─────────────────────
-- A table can be empty today and have been written to for a year. Section 3
-- asks pg_stat_user_tables for LIFETIME insert/update/delete counts: a table
-- with zero rows AND zero inserts ever has genuinely never been used.
--
-- GUARD THE GUARD: those counters reset when statistics are reset, and a
-- freshly reset counter reads exactly like a never-used table. Section 3b
-- prints the reset time. If it is recent, Section 3 proves nothing and says so
-- rather than passing vacuously.

-- ══ SECTION 0 — WHO ARE YOU ═══════════════════════════════════════════════
-- pg_stat_user_tables and pg_depend need real privileges, and a lesser role
-- returns a SHORT LIST that reads exactly like a clean answer.
select current_user as must_be_postgres;

-- ══ SECTION 1 — DO THEY EVEN EXIST? ═══════════════════════════════════════
-- Anything missing here is already gone and needs no decision. Anything
-- present that is NOT in this list means the 19 has drifted and the row is
-- stale -- that is itself the finding.
with named(t) as (values
  ('conversations'),('demo_calls'),('gl_entries'),('licenses'),('messages'),
  ('parts'),('payments'),('profiles'),('projects'),('shop_users'),('shops'),
  ('subscriptions'),('usage_logs'),('user_storage'),('webhook_events'),
  ('customers'),('invoices'),('jobs'),('slabs'))
select n.t as table_name,
       (c.oid is not null) as exists_in_public
from named n
left join pg_class c
  on c.relname = n.t
 and c.relnamespace = 'public'::regnamespace
 and c.relkind = 'r'
order by exists_in_public, n.t;

-- ══ SECTION 2 — ARE THEY EMPTY? ═══════════════════════════════════════════
-- A real count, not an estimate: reltuples is a planner statistic and can say
-- 0 for a populated table that has never been analyzed. Nineteen small counts
-- is cheap; being wrong about this one is not.
select 'conversations' t, count(*) from public.conversations
union all select 'demo_calls',    count(*) from public.demo_calls
union all select 'gl_entries',    count(*) from public.gl_entries
union all select 'licenses',      count(*) from public.licenses
union all select 'messages',      count(*) from public.messages
union all select 'parts',         count(*) from public.parts
union all select 'payments',      count(*) from public.payments
union all select 'profiles',      count(*) from public.profiles
union all select 'projects',      count(*) from public.projects
union all select 'shop_users',    count(*) from public.shop_users
union all select 'shops',         count(*) from public.shops
union all select 'subscriptions', count(*) from public.subscriptions
union all select 'usage_logs',    count(*) from public.usage_logs
union all select 'user_storage',  count(*) from public.user_storage
union all select 'webhook_events',count(*) from public.webhook_events
union all select 'customers',     count(*) from public.customers
union all select 'invoices',      count(*) from public.invoices
union all select 'jobs',          count(*) from public.jobs
union all select 'slabs',         count(*) from public.slabs
order by 2 desc, 1;
-- IF A TABLE HERE ERRORS "does not exist", drop it from the list and re-run --
-- Section 1 already told you which. Do not delete the row from the index
-- without saying which table it was.

-- ══ SECTION 3 — HAVE THEY EVER BEEN WRITTEN TO? ═══════════════════════════
-- 3a. Lifetime counters. A table with 0 rows and 0 inserts EVER is dead beyond
--     argument. A table with 0 rows and a nonzero n_tup_ins was used once and
--     emptied -- a materially different fact, and the one that should slow a
--     drop down.
select relname as table_name,
       n_live_tup, n_tup_ins, n_tup_upd, n_tup_del,
       seq_scan, idx_scan,
       last_vacuum, last_autovacuum, last_analyze
from pg_stat_user_tables
where schemaname = 'public'
  and relname in ('conversations','demo_calls','gl_entries','licenses','messages',
                  'parts','payments','profiles','projects','shop_users','shops',
                  'subscriptions','usage_logs','user_storage','webhook_events',
                  'customers','invoices','jobs','slabs')
order by n_tup_ins desc, relname;

-- 3b. GUARD THE GUARD. If this is recent, every zero above is meaningless.
select stats_reset from pg_stat_database where datname = current_database();

-- ══ SECTION 4 — DOES ANYTHING DEPEND ON THEM? ═════════════════════════════
-- 4a. Foreign keys pointing INTO these tables. A single inbound FK means a
--     drop takes something else with it, or fails -- and either way the table
--     is not as isolated as the code scan suggested, because a constraint is a
--     dependency the code never mentions.
select con.conname,
       src.relname  as referencing_table,
       tgt.relname  as referenced_table
from pg_constraint con
join pg_class src on src.oid = con.conrelid
join pg_class tgt on tgt.oid = con.confrelid
where con.contype = 'f'
  and tgt.relnamespace = 'public'::regnamespace
  and tgt.relname in ('conversations','demo_calls','gl_entries','licenses','messages',
                      'parts','payments','profiles','projects','shop_users','shops',
                      'subscriptions','usage_logs','user_storage','webhook_events',
                      'customers','invoices','jobs','slabs')
order by tgt.relname, src.relname;

-- 4b. Views, matviews and rules that reference them by name. A view is not a
--     code path the repo scan can see, and it blocks a plain DROP.
select c.relname as dependent_object,
       c.relkind as kind,
       t
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
cross join (values
  ('conversations'),('demo_calls'),('gl_entries'),('licenses'),('messages'),
  ('parts'),('payments'),('profiles'),('projects'),('shop_users'),('shops'),
  ('subscriptions'),('usage_logs'),('user_storage'),('webhook_events'),
  ('customers'),('invoices'),('jobs'),('slabs')) as v(t)
where n.nspname = 'public'
  and c.relkind in ('v','m')
  and pg_get_viewdef(c.oid) ~* ('\m' || t || '\M')
order by dependent_object, t;

-- 4c. Triggers on them, which also die with the table and may be doing work
--     nobody remembers.
select c.relname as table_name, tg.tgname as trigger_name
from pg_trigger tg
join pg_class c on c.oid = tg.tgrelid
where not tg.tgisinternal
  and c.relnamespace = 'public'::regnamespace
  and c.relname in ('conversations','demo_calls','gl_entries','licenses','messages',
                    'parts','payments','profiles','projects','shop_users','shops',
                    'subscriptions','usage_logs','user_storage','webhook_events',
                    'customers','invoices','jobs','slabs')
order by table_name, trigger_name;

-- ══ SECTION 5 — WHAT GRANTS ARE THEY CARRYING? ════════════════════════════
-- This is the row's original reason for existing: these tables carry the
-- excess baseline. Reported for ALL grantees, not just service_role -- `anon`
-- and `authenticated` have never been swept on any table, and on 2026-09-05
-- they were confirmed to hold nothing on license_keys, which says nothing
-- about these.
select table_name, grantee,
       string_agg(distinct privilege_type, ', ' order by privilege_type) as privs
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('conversations','demo_calls','gl_entries','licenses','messages',
                     'parts','payments','profiles','projects','shop_users','shops',
                     'subscriptions','usage_logs','user_storage','webhook_events',
                     'customers','invoices','jobs','slabs')
group by table_name, grantee
order by table_name, grantee;

-- ══ SECTION 6 — SIZE ══════════════════════════════════════════════════════
-- Not a reason to drop anything by itself. It is here so the decision is made
-- with the cost of NOT dropping visible: if the answer is "a few kilobytes",
-- leaving them alone is a perfectly good outcome and this file should not be
-- read as pressure to act.
select relname as table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) as total_size
from pg_class c
where c.relnamespace = 'public'::regnamespace
  and c.relkind = 'r'
  and c.relname in ('conversations','demo_calls','gl_entries','licenses','messages',
                    'parts','payments','profiles','projects','shop_users','shops',
                    'subscriptions','usage_logs','user_storage','webhook_events',
                    'customers','invoices','jobs','slabs')
order by pg_total_relation_size(c.oid) desc;

-- ══ SECTION 7 — A TEMPLATE, NOT A RECOMMENDATION. DO NOT RUN. ═════════════
-- THE INDEX ROW IS EXPLICIT THAT THIS DECISION IS NOT A SESSION'S TO MAKE, and
-- nothing in Sections 1-6 changes that. A DROP is irreversible without a
-- restore, these tables are very likely the abandoned Fabricor-era schema, and
-- "very likely" is not a standard anything irreversible should be run against.
--
-- If Michael decides to drop them, the preconditions are all four of:
--   * Section 2 shows 0 rows;
--   * Section 3a shows n_tup_ins = 0 AND Section 3b shows stats were NOT
--     recently reset;
--   * Section 4a/4b/4c return nothing for that table;
--   * a backup exists that predates the drop.
--
-- ONE AT A TIME, not a loop, so a mistake is one table and not nineteen.
-- Deliberately NOT written as `drop ... cascade`: cascade is how a dependency
-- nobody checked gets removed silently, and Section 4 exists precisely so that
-- never has to be guessed.
--
-- drop table public.<one_table_name>;   -- no CASCADE, on purpose

-- ══ WHAT THIS FILE DOES NOT ESTABLISH ═════════════════════════════════════
--   * That the tables are safe to drop. It establishes whether they are empty,
--     never-written, undepended-on and ungranted-to-anything-that-matters.
--     Those are inputs to a decision, not the decision.
--   * Anything about the OTHER undeclared-but-LIVE tables. `business_profiles`,
--     `ai_memories` and `employees` are real, used, and covered by
--     sql/introspect_undeclared_tables_2026-08-26.sql. They are not in scope
--     here and must not be confused with these -- the names are similar enough
--     that a hurried reader could.
