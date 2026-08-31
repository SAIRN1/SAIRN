-- sql/schema_snapshot_query.sql
--
-- Produces the LIVE schema snapshot that tools/sairn_sql_preflight.py needs in
-- order to be a real check rather than a repo-consistency check.
--
-- WHY IT IS A QUERY YOU RUN AND NOT SOMETHING THE TOOL FETCHES. No clone on
-- this platform has generic information_schema access -- the app APIs expose
-- named actions (read/write/roster/whoami), not introspection, and adding an
-- endpoint that returns the whole schema shape to anyone holding a licence key
-- is a worse trade than pasting a query. This follows the pattern already used
-- by sql/introspect_undeclared_tables_2026-08-26.sql and the grant audits.
--
-- HOW TO USE
--   1. Run this whole file in the Supabase SQL editor.
--   2. Copy the single JSON value out of the result cell.
--   3. Save it as db/schema_snapshot.json in the clone (create db/ if needed).
--   4. python tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/your_file.sql
--
-- READ-ONLY. It selects from information_schema and writes nothing.
--
-- THE SNAPSHOT GOES STALE THE MOMENT SOMEONE RUNS A MIGRATION, and the tool
-- cannot tell. The generated JSON therefore carries `_generated_at`; re-run this
-- query whenever a schema file has been applied since, and treat a snapshot
-- older than the last migration as DECLARED-grade evidence, not LIVE.

select jsonb_pretty(
  jsonb_build_object('_generated_at', now()::text)
  || coalesce(
       jsonb_object_agg(t.table_name, t.cols),
       '{}'::jsonb
     )
)
from (
  select c.table_name,
         jsonb_agg(c.column_name order by c.ordinal_position) as cols
    from information_schema.columns c
    join information_schema.tables tb
      on tb.table_schema = c.table_schema
     and tb.table_name   = c.table_name
   where c.table_schema = 'public'
     -- BASE TABLE only. A view's columns are real to a SELECT and not to an
     -- INSERT, and including them would let a preflight pass a write against
     -- something that cannot be written.
     and tb.table_type = 'BASE TABLE'
   group by c.table_name
) t;
