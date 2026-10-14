-- sql/2026-10-14-hank-b9-ai-safeguards.sql
-- ---------------------------------------------------------------------------
-- THE AI-NOTICE ACKNOWLEDGEMENT COLUMNS. One idempotent block, run it as many
-- times as you like.
--
-- Adds to EVERY `%_employee_auth` table:
--
--   ai_notice_version    text         the notice version acknowledged
--   ai_notice_acked_at   timestamptz  when
--
-- ── DERIVED FROM information_schema, NOT A LIST OF SIXTEEN TABLE NAMES ────
-- api/_lib/auth.js's AUTH_TABLE_BY_APP holds sixteen apps today and has gained
-- one twice in six weeks. A hand-written list here would be a seventeenth copy
-- of that vocabulary, and the apps added AFTER this file ran would silently
-- miss the columns -- at which point api/ai-notice.js answers 503
-- AI_NOTICE_NOT_PROVISIONED for that app alone and somebody has to work out
-- why one app is different. The loop below finds the tables, so re-running
-- this file after adding an app is the whole fix.
--
-- THE SELECTION IS BY SUFFIX AND THAT IS THE ONE THING TO CHECK BEFORE
-- RUNNING. It matches `%\_employee_auth` in the PUBLIC schema. Every table in
-- AUTH_TABLE_BY_APP ends in `_employee_auth`; if a future app does not, this
-- loop will not reach it and NOTHING WILL SAY SO -- so the verification query
-- at the foot compares the count against the number of apps, and that is the
-- step that is not optional.
--
-- ── NO ROW IS WRITTEN, SO THE RECOVERABILITY GUARD DOES NOT APPLY ─────────
-- PR 3.4 requires the two-safe-end-states guard on SQL that writes credential
-- rows. This file writes none: it adds two NULLABLE columns and touches no
-- data. Null means "has not acknowledged yet", which is the state every
-- existing row starts in and is not an error. Said explicitly rather than
-- left for a reviewer to work out, because "it does not apply" and "it was
-- forgotten" look identical in a file that simply lacks the guard.
--
-- ── NOTHING IS REVOKED AND NOTHING IS GRANTED ────────────────────────────
-- A column added to an existing table inherits the table's grants, so
-- service_role's existing access covers these two and no `grant` line belongs
-- in this file. Adding one would widen the surface for no reason.
-- ---------------------------------------------------------------------------

do $$
declare
  t record;
  n int := 0;
begin
  for t in
    select table_name
      from information_schema.tables
     where table_schema = 'public'
       and table_name like '%\_employee\_auth'
     order by table_name
  loop
    execute format(
      'alter table public.%I
         add column if not exists ai_notice_version text,
         add column if not exists ai_notice_acked_at timestamptz',
      t.table_name);
    n := n + 1;
    raise notice 'ai-notice columns ensured on %', t.table_name;
  end loop;

  -- A LOOP THAT MATCHED NOTHING IS A FAILURE, NOT A NO-OP. Without this an
  -- empty match prints nothing, exits clean, and reads exactly like a
  -- successful run on a database where the credential tables have not been
  -- created yet -- which is the silent pass this platform keeps paying for.
  if n = 0 then
    raise exception 'NO %%_employee_auth TABLE MATCHED. Nothing was altered. '
      'Either the credential schemas have not been run in this database, or '
      'the naming convention has changed and this file can no longer find '
      'them. Do not treat this as done.';
  end if;

  raise notice 'ai-notice columns ensured on % table(s)', n;
end $$;

-- ── VERIFY, AND THIS STEP IS NOT OPTIONAL ────────────────────────────────
-- Expect ONE ROW PER CREDENTIAL TABLE, each with both columns present. Compare
-- the count against the number of entries in api/_lib/auth.js's
-- AUTH_TABLE_BY_APP -- SIXTEEN when this file was written, and the figure to
-- re-derive rather than trust, because it is the thing that moves:
--
--   node -e "console.log(Object.keys(require('./api/_lib/auth').AUTH_TABLE_BY_APP).length)"
--
-- A table in this result and not in that map is a stale credential table; an
-- app in that map and not in this result gets 503 AI_NOTICE_NOT_PROVISIONED
-- from api/ai-notice.js and nothing else will mention it.
select c.table_name,
       count(*) filter (where c.column_name = 'ai_notice_version')  as has_version,
       count(*) filter (where c.column_name = 'ai_notice_acked_at') as has_acked_at
  from information_schema.columns c
 where c.table_schema = 'public'
   and c.table_name like '%\_employee\_auth'
   and c.column_name in ('ai_notice_version', 'ai_notice_acked_at')
 group by c.table_name
 order by c.table_name;
