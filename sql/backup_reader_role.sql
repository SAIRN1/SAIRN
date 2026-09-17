-- sql/backup_reader_role.sql
-- ---------------------------------------------------------------------------
-- THE DEDICATED CREDENTIAL THE NIGHTLY BACKUP USES, AND NOTHING ELSE USES.
-- Michael's decision, 2026-09-14: a NEW Postgres role, SELECT-only, scoped to
-- this job -- NOT the shared service-role key.
--
-- Run this as the `postgres` superuser in the Supabase SQL editor. It is the
-- only part of the backup that a human has to do by hand, and that is
-- deliberate: a workflow that could mint its own database credentials would be
-- a bigger hole than the one this closes.
--
-- ── THE ONE LINE THAT DECIDES WHETHER THE BACKUP CONTAINS ANYTHING ─────────
-- BYPASSRLS. Without it this produces a backup that RESTORES PERFECTLY AND IS
-- EMPTY, and that is not a theoretical risk on this platform:
--
--     sairnlaw_audit_log, sairncode_audit_log, stonedesk_audit_log,
--     sairn_audit_checkpoint, sairn_cron_heartbeat ... all carry
--     `alter table ... enable row level security`.
--
-- Row-level security applies to every role EXCEPT a superuser, the table owner,
-- and a role with BYPASSRLS. `service_role` bypasses it because Supabase grants
-- it that. A fresh SELECT-only role does NOT -- so `pg_dump` run as that role
-- would emit the schema, emit zero rows for every RLS-protected table, and EXIT
-- ZERO. The dump would be the right size in a listing, restore without an
-- error, and contain none of the records the backup exists for.
--
-- THAT FAILURE IS SILENT AT EVERY STAGE EXCEPT ONE, which is the whole reason
-- the nightly workflow restores the dump and runs the coherence checker against
-- it: the audit checkpoint digests would not match an empty table, and the job
-- fails that night rather than on the day somebody needs the data.
--
-- BYPASSRLS IS A REAL PRIVILEGE AND IT IS NARROWED EVERYWHERE ELSE:
--   * NOLOGIN is NOT set -- the job has to connect -- but the password lives in
--     one GitHub secret used by one workflow.
--   * SELECT only. No INSERT, UPDATE, DELETE, TRUNCATE, or CREATE anywhere.
--   * No membership in service_role, postgres, anon or authenticated.
--   * `NOINHERIT` so it cannot pick up privileges from a future grant to PUBLIC.
--
-- ── WHY NOT REUSE service_role ─────────────────────────────────────────────
-- Because a backup job needs to READ EVERYTHING and should be able to do
-- NOTHING ELSE, and service_role can write to every table on the platform. A
-- credential that leaks from CI should cost a disclosure, not a database.
--
-- WRITTEN 2026-09-14. THE ROLE EXISTS -- Michael confirmed `sairn_backup_reader`
-- is present in Supabase on 2026-09-15, so step 1 will take its else-branch and
-- ROTATE the password rather than create the role.
--
-- WHAT IS STILL UNANSWERED, AND ONLY THIS DATABASE CAN ANSWER IT: which role
-- actually creates tables here. Verify 2c is the query; 2d says whether every
-- such role is covered. Until those two have been run and read, the default-ACL
-- half of this file is WRITTEN AND UNVERIFIED -- which is a different state from
-- both "working" and "broken", and is the state it is in.
-- ---------------------------------------------------------------------------

-- 1. The role. Replace the password below before running; it goes straight into
--    the GitHub secret BACKUP_PGPASSWORD and nowhere else.
--
-- ── THE FILE REFUSES TO RUN WHILE THE PLACEHOLDER IS STILL HERE ────────────
-- Found by CC's independent review, 2026-09-14, before the role had ever been
-- created. Fixed the same day. The original was:
--
--     if not exists (...) then create role ... password 'REPLACE_ME_BEFORE_RUNNING';
--
-- Three things made that a HIGH finding rather than an untidy default:
--
--   1. THIS REPOSITORY IS PUBLIC, so the placeholder is not a placeholder. It
--      is a published string, and running the file un-edited mints a LOGIN role
--      with BYPASSRLS and SELECT on every table in `public` whose password
--      anybody can read.
--   2. `if not exists` MADE THE SLIP PERMANENT. Re-running the corrected file
--      changed nothing, because the role already existed. A one-time mistake
--      became a standing one, and the guard that did it was there to make the
--      file safe to re-run.
--   3. NOTHING IN THE FIVE VERIFY STEPS LOOKED AT THE PASSWORD. The file
--      checked privileges thoroughly and never asked the one question that
--      mattered.
--
-- "Replace it before running" is a note, and a note is not a control. So:
--
--   * the block RAISES while the literal is present -- the file cannot be run
--     un-edited at all, rather than being run and then detected;
--   * the password is set UNCONDITIONALLY, `create` on first run and `alter`
--     on every run after. That closes the if-not-exists trap AND makes this
--     file the remediation for a role already created with the placeholder:
--     re-run it with a real password and the old one is rotated out.
--
-- WHY THERE IS NO "IS THE PASSWORD STILL THE PLACEHOLDER" VERIFY QUERY, stated
-- rather than left as an omission: `pg_authid.rolpassword` holds a SALTED SCRAM
-- verifier, so the same password hashes differently every time and cannot be
-- compared to a known string. The check has to be PREVENTIVE, which is why it
-- is a raise and not an assertion afterwards.
do $$
declare
  -- REPLACE THIS. It is the only edit this file needs.
  v_pw text := 'REPLACE_ME_BEFORE_RUNNING';
begin
  if v_pw = 'REPLACE_ME_BEFORE_RUNNING' or length(v_pw) < 16 then
    raise exception
      'REFUSING TO RUN: the backup role password is still the placeholder '
      'committed to a PUBLIC repository (or is under 16 characters). Running '
      'this file as-is would create a LOGIN role with BYPASSRLS and SELECT on '
      'every table in public, with a password anybody can read -- and the old '
      'if-not-exists guard meant re-running the corrected file would not have '
      'changed it. Edit v_pw above, then run this again.'
      using errcode = 'invalid_password';
  end if;

  if not exists (select 1 from pg_roles where rolname = 'sairn_backup_reader') then
    execute format(
      'create role sairn_backup_reader with login nosuperuser nocreatedb '
      'nocreaterole noinherit bypassrls password %L', v_pw);
    raise notice 'created sairn_backup_reader';
  else
    -- THE ROTATION PATH, and the reason it is unconditional. If this file was
    -- ever run un-edited, the role exists with a published password and no
    -- amount of re-running the old version would have fixed it.
    execute format('alter role sairn_backup_reader with password %L', v_pw);
    -- Re-assert the attributes too: a role created by an earlier version, or
    -- altered by hand since, must not be assumed to still carry them.
    execute 'alter role sairn_backup_reader with login nosuperuser nocreatedb '
            'nocreaterole noinherit bypassrls';
    raise notice 'sairn_backup_reader already existed -- password ROTATED and '
                 'attributes re-asserted. If this role was ever created from '
                 'the un-edited file, the published password is now dead.';
  end if;
end
$$;

-- 2. Read the schemas. USAGE only -- it may look inside, not create anything.
grant usage on schema public to sairn_backup_reader;

-- 3. SELECT on everything that exists today...
grant select on all tables in schema public to sairn_backup_reader;
grant select on all sequences in schema public to sairn_backup_reader;

-- 4. ...AND ON EVERYTHING ADDED LATER, which is the half that is usually
--    forgotten. Without this, every table created after today is absent from
--    the backup and nothing says so -- the same silent-omission shape as the
--    RLS one above, arriving later.
--
-- ── FOR ROLE IS NOT OPTIONAL, AND LEAVING IT OFF IS THE SAME BUG ONE LEVEL IN
-- `ALTER DEFAULT PRIVILEGES` WITHOUT `FOR ROLE` APPLIES ONLY TO OBJECTS CREATED
-- BY THE ROLE RUNNING THE STATEMENT. Run this as `postgres` and it covers
-- exactly the tables `postgres` goes on to create -- and NOTHING made by
-- anything else.
--
-- On Supabase that is not a corner case. The dashboard's table editor, the
-- migration runner and several extensions HAVE created objects as
-- `supabase_admin` -- past tense as of 2026-09-17, because Supabase's 2022
-- security patch moved that ownership onto `postgres` and this project measured
-- 100% `postgres` on 2026-08-26 (see 2c). The hazard is unchanged whoever the
-- role turns out to be: a table created by a role with no default-ACL entry
-- carries no grant, `pg_dump` skips it without an error, and the backup is
-- missing a table WHILE EXITING ZERO -- the identical silent-omission shape as
-- the RLS gap above, arriving months later and only for the tables added after
-- today. Which is why the grantor list is derived and not named.
--
-- Found by review before the role was ever created. Every grantor that owns a
-- table in `public` is covered -- read from the catalog, not named here. See
-- the derivation note below, and 2026-09-17 for why naming them was worse than
-- deriving them.
--
-- AND IT FAILS LOUDLY IF IT CANNOT. `FOR ROLE x` requires membership in x, and
-- `postgres` is not always a member of `supabase_admin`. A statement that
-- silently could not be applied would leave exactly the gap it was added to
-- close, so each one is attempted and a failure RAISES with what to do about
-- it. "Could not set it" is a third state and it is not "set".
-- ── THE LIST OF GRANTORS IS DERIVED, NOT WRITTEN DOWN (2026-09-15) ────────
-- The previous version looped over a HARDCODED array['postgres',
-- 'supabase_admin']. Verify 2b proved those two took -- and nothing anywhere
-- proved the LIST WAS COMPLETE. A table created by any THIRD role would carry
-- no grant, `pg_dump` would skip it without an error, and 2b would show two
-- healthy rows while the backup quietly lost a table.
--
-- That is a hand-written list claiming to match a population nothing compares
-- it to, which is the defect shape this platform has now been bitten by four
-- times (SC_TIER_A_WRITE_GATED six-vs-seven, the 28-name delete grant, the
-- transport-name table, and this).
--
-- So the loop runs over the roles that ACTUALLY OWN TABLES in `public` today,
-- read from pg_tables, unioned with `current_user`.
--
-- ── AND THE `supabase_admin` HALF OF THAT UNION MADE THE FILE UNRUNNABLE
-- ── (2026-09-17). THIS IS THE CORRECTION, AND IT IS NOT A LOOSENING.
--
-- The previous version unioned in a HARDCODED array['postgres',
-- 'supabase_admin']. That was written to be safe and it was the one thing here
-- that could not work:
--
--   * `supabase_admin` EXISTS on every Supabase project, so the `no such role`
--     skip below never fires for it;
--   * `postgres` is NOT a member of `supabase_admin` on hosted Supabase, and
--     `ALTER DEFAULT PRIVILEGES FOR ROLE x` requires membership in x;
--   * so the loop reaches it, raises `insufficient_privilege`, and the
--     exception handler below RAISES -- correctly, by its own design;
--   * and this is ONE `do` block in ONE transaction with `order by 1`, so
--     `postgres` sorts first, succeeds, and is ROLLED BACK with it.
--
-- NOTHING TOOK. The file failed at the one clause that was pure insurance, and
-- took the load-bearing one down with it.
--
-- THE ANSWER TO THE QUESTION THAT CLAUSE WAS GUESSING AT IS ON DISK AND WAS
-- MEASURED: Michael ran `sql/supabase_admin_default_acl_check_2026-08-26.sql`
-- on 2026-08-26 and ownership across `public` was 100% `postgres` -- all 251
-- tables, 4 sequences and 11 functions, ZERO owned by `supabase_admin`.
-- Supabase's own 2022 security patch moved dashboard and SQL-editor entity
-- ownership off `supabase_admin` onto `postgres`, which is why. So the widely
-- reported behaviour this clause was written against is REAL HISTORY and is
-- not this project's present.
--
-- THAT EVIDENCE IS STALE AND THE FIX DOES NOT DEPEND ON IT. 380 tables now
-- against the 251 it was measured on -- `tools/ownership_evidence_drift.py`
-- is RED and says 129 is a LOWER bound. The repair is therefore NOT "we
-- checked, drop the clause": it is that a DERIVED loop cannot need the clause.
-- If `supabase_admin` ever does own a table in `public`, `pg_tables` returns
-- it, the loop covers it, and -- if this role cannot grant for it -- the
-- exception below fires FOR A REAL REASON, on a deployment where tables really
-- would be missing from the backup. That is the failure worth aborting on, and
-- it is now the only one that can.
--
-- `current_user` replaces the other half of the hardcoded pair, and is the one
-- addition that can never raise: you are always a member of yourself. It
-- covers the role that runs migrations even on the day it owns nothing yet,
-- which is the forward-looking property the array was reaching for.
--
-- WHAT IS GIVEN UP, SAID PLAINLY RATHER THAN LEFT FOR SOMEBODY TO FIND: a role
-- that owns nothing today and creates its first table tomorrow is NOT
-- pre-covered any more. It is DETECTED rather than prevented -- verify 2d
-- below reports `uncovered` non-zero the next time anybody runs it, and 2c
-- names the owner. Prevention was never real for that case anyway: the array
-- only pre-covered two names somebody thought of, which is the hand-written
-- list this same comment block already records being bitten by four times.
--
-- VERIFY 2c BELOW STILL ANSWERS THE OWNERSHIP QUESTION FOR THIS DEPLOYMENT
-- rather than repeating any report -- run it and read the owners.
do $$
declare
  r text;
begin
  for r in
    select rolname from (
      select tableowner as rolname from pg_tables where schemaname = 'public'
      union
      select current_user
    ) x
    where rolname is not null
    order by 1
  loop
    if not exists (select 1 from pg_roles where rolname = r) then
      raise notice 'default privileges NOT set for %: no such role on this '
                   'deployment. If objects are never created by it, that is '
                   'correct; confirm rather than assume.', r;
      continue;
    end if;
    begin
      execute format(
        'alter default privileges for role %I in schema public '
        'grant select on tables to sairn_backup_reader', r);
      execute format(
        'alter default privileges for role %I in schema public '
        'grant select on sequences to sairn_backup_reader', r);
      raise notice 'default privileges set for objects created by %', r;
    exception when insufficient_privilege then
      -- REACHING THIS NOW MEANS SOMETHING, WHICH IT DID NOT BEFORE 2026-09-17.
      -- The loop is derived from pg_tables, so % is a role that ACTUALLY OWNS
      -- TABLES in public on this deployment. Aborting is right: those tables,
      -- and everything that role creates from today on, would be absent from
      -- the backup with pg_dump exiting zero.
      raise exception
        'Could not set default privileges FOR ROLE % -- you must be a member '
        'of that role, and `ALTER DEFAULT PRIVILEGES FOR ROLE` requires it. '
        'THIS ROLE OWNS TABLES IN public (see verify 2c), so this is not a '
        'precaution firing on a role that owns nothing -- run `grant % to '
        'current_user` as a role that can, or run this file as a member of %. '
        'STOPPING: leaving it unset would mean every table % creates from '
        'today on is silently absent from the backup, which is the exact '
        'failure this clause exists to prevent.', r, r, r, r;
    end;
  end loop;
end
$$;

-- 5. Belt and braces: it must not be able to write, ever.
revoke insert, update, delete, truncate, references, trigger
  on all tables in schema public from sairn_backup_reader;
revoke create on schema public from sairn_backup_reader;

-- ── VERIFY, one query per statement with the answer it must give ───────────

-- 1. The role exists and CAN bypass RLS. Expect: t | f | f | f
--    (bypassrls true; superuser, createdb, createrole all false)
select rolbypassrls, rolsuper, rolcreatedb, rolcreaterole
  from pg_roles where rolname = 'sairn_backup_reader';

-- 2. It holds SELECT and NOTHING ELSE. Expect exactly one row: SELECT
select distinct privilege_type
  from information_schema.role_table_grants
 where grantee = 'sairn_backup_reader'
 order by privilege_type;

-- 2a. HOW MANY TABLES, NOT WHICH PRIVILEGE. Expect: missing = 0
--     Added 2026-09-14 from CC's Finding 3. Query 2 above asks WHICH PRIVILEGES
--     this role holds and answers SELECT -- and it answers SELECT whether the
--     role can read 380 tables or three, because a table with no grant simply
--     does not appear in the result. COVERAGE was never checked, which is the
--     same silent-omission shape this file names one level up about FOR ROLE.
--
--     A NON-ZERO `missing` IS THE FAILURE and it names the tables, because a
--     count alone would tell you something was wrong and not what.
with granted as (
  select distinct table_name
    from information_schema.role_table_grants
   where grantee = 'sairn_backup_reader' and table_schema = 'public'
), present as (
  select table_name
    from information_schema.tables
   where table_schema = 'public' and table_type = 'BASE TABLE'
)
select (select count(*) from present)                     as tables_in_public,
       (select count(*) from granted)                     as tables_granted,
       (select count(*) from present
         where table_name not in (select table_name from granted)) as missing,
       (select string_agg(table_name, ', ' order by table_name)
          from present
         where table_name not in (select table_name from granted)) as missing_names;

-- 2b. THE DEFAULT ACLs ACTUALLY TOOK, AND FOR WHICH GRANTOR. Expect one row per
--     object_type for EVERY ROLE 2c LISTS AS OWNING TABLES, plus `current_user`.
--
--     ⚠ THIS EXPECTATION WAS REWRITTEN 2026-09-17 AND THE OLD ONE WOULD NOW
--     REPORT A CORRECT RESULT AS A FAILURE. It read: "Expect ONE ROW PER
--     GRANTOR -- `postgres` and `supabase_admin`... A SINGLE ROW HERE IS THE
--     FAILURE, not a pass." That was written when the loop unioned in a
--     hardcoded pair. The loop is now DERIVED from pg_tables, and on this
--     deployment ownership was measured at 100% `postgres` -- so ONE ROW PER
--     OBJECT TYPE IS THE CORRECT AND EXPECTED ANSWER, and reading it as a
--     failure would send somebody chasing a gap that does not exist.
--
--     THE REAL PASS CONDITION IS NOT A ROW COUNT AT ALL, WHICH IS WHY IT MOVED
--     TO 2d. "Is there an entry for every role that creates tables here" is a
--     comparison against a population, and a number typed into a comment
--     cannot make it. 2d makes it: `uncovered = 0`. Read 2b to see WHICH
--     grantors took, read 2c to see who actually owns tables, and read 2d for
--     the verdict. If 2b shows a grantor that 2c does not list, that is not an
--     error either -- it is `current_user` covered ahead of owning anything.
select pg_get_userbyid(d.defaclrole) as objects_created_by,
       d.defaclobjtype                as object_type,
       d.defaclacl                    as acl
  from pg_default_acl d
  join pg_namespace n on n.oid = d.defaclnamespace
 where n.nspname = 'public'
   and array_to_string(d.defaclacl, ',') like '%sairn_backup_reader%'
 order by 1, 2;

-- 2c. WHO ACTUALLY CREATES TABLES ON THIS DEPLOYMENT -- the open question, and
--     the only thing that can answer it is this database.
--     Added 2026-09-15. Michael's question: does Supabase's dashboard/migration
--     runner create tables as `supabase_admin`? If it does, then every table
--     added through the dashboard from today on needs a default-ACL entry FOR
--     THAT ROLE, and a grant set only FOR ROLE postgres would silently miss all
--     of them.
--
--     ANSWERED 2026-08-26 BY MEASUREMENT, and re-asked here because the answer
--     has a shelf life. Michael ran
--     `sql/supabase_admin_default_acl_check_2026-08-26.sql`: ownership across
--     `public` was 100% `postgres` -- 251 tables, 4 sequences, 11 functions,
--     ZERO `supabase_admin`. Supabase's 2022 security patch moved dashboard and
--     SQL-editor ownership off `supabase_admin` onto `postgres`, which is why.
--     THAT WAS 251 TABLES AGO AND THERE ARE 380 NOW -- run this query; do not
--     quote the paragraph you just read.
--
--     READ THE RESULT LIKE THIS:
--       * only `postgres` appears      -> matches the 2026-08-26 measurement.
--                                         The loop covered it because it OWNS
--                                         tables, not because it was named
--       * `supabase_admin` appears     -> the 2022 patch did not fully take on
--                                         this project, or something re-created
--                                         objects as it. The derived loop picks
--                                         it up automatically -- and if this
--                                         role cannot grant for it, section 4
--                                         ABORTS, which is now correct rather
--                                         than collateral
--       * a THIRD role appears         -> exactly what deriving the list is for.
--                                         2d proves it was covered
--
--     WHATEVER APPEARS, 2d IS THE VERDICT. This query informs; it does not pass
--     or fail anything on its own.
select tableowner                       as objects_created_by,
       count(*)                         as tables_owned,
       min(tablename)                   as example_table
  from pg_tables
 where schemaname = 'public'
 group by tableowner
 order by tables_owned desc;

-- 2d. EVERY OWNER IS COVERED BY A DEFAULT ACL. Expect: uncovered = 0
--     This is the completeness half that 2b does not provide. 2b asks "did the
--     grants I made take"; this asks "did I make one for every role that
--     creates tables here". A hand-written list passes 2b while failing this,
--     which is exactly how the gap would have survived.
with owners as (
  select distinct tableowner as rolname
    from pg_tables where schemaname = 'public'
), covered as (
  select distinct pg_get_userbyid(d.defaclrole) as rolname
    from pg_default_acl d
    join pg_namespace n on n.oid = d.defaclnamespace
   where n.nspname = 'public'
     and array_to_string(d.defaclacl, ',') like '%sairn_backup_reader%'
)
select (select count(*) from owners)                          as distinct_owners,
       (select count(*) from owners
         where rolname not in (select rolname from covered))  as uncovered,
       (select string_agg(rolname, ', ' order by rolname)
          from owners
         where rolname not in (select rolname from covered))  as uncovered_names;

-- 3. It is a member of nothing. Expect: 0
select count(*)
  from pg_auth_members m
  join pg_roles r on r.oid = m.member
 where r.rolname = 'sairn_backup_reader';

-- 4. It can see the RLS-protected tables. Expect a NON-ZERO count once the
--    audit tables have rows -- and ZERO is the answer that means BYPASSRLS did
--    not take, which is the silent failure this file exists to prevent.
set role sairn_backup_reader;
select count(*) from sairnlaw_audit_log;
reset role;

-- 5. It cannot write. Expect: ERROR permission denied for table
--    (run it, read the error, then move on -- a statement that SUCCEEDS here
--    means the revoke above did not take)
-- set role sairn_backup_reader;
-- insert into sairnlaw_audit_log (license_hash, event_type) values ('x', 'login_success');
-- reset role;

-- 6. THE PASSWORD IS SET AND IS A SCRAM VERIFIER. Expect: SCRAM-SHA-256
--    Added 2026-09-14 with the placeholder fix. READ WHAT THIS DOES AND DOES
--    NOT PROVE: a salted verifier cannot be compared to a known string, so this
--    CANNOT tell you the password is not the published placeholder. It tells
--    you only that a password exists and is stored in the modern format. The
--    control against the placeholder is the RAISE in step 1, which is
--    preventive; this is a completeness check, not a second detector.
select case
         when rolpassword is null then 'NO PASSWORD -- the role cannot log in'
         when rolpassword like 'SCRAM-SHA-256%' then 'SCRAM-SHA-256'
         else 'UNEXPECTED FORMAT: ' || left(rolpassword, 12)
       end as password_state
  from pg_authid where rolname = 'sairn_backup_reader';

-- 7. THE ATTRIBUTE THAT DECIDES WHETHER THE BACKUP CONTAINS ANYTHING, asked
--    again AFTER any rotation. Expect: t
--    Step 1 re-asserts bypassrls on the existing-role path; this is the query
--    that proves the re-assertion landed rather than assuming it did.
select rolbypassrls from pg_roles where rolname = 'sairn_backup_reader';

-- ── IF THIS FILE WAS EVER RUN UN-EDITED, READ THIS ────────────────────────
-- The role exists with a password published in a public repository. Rotating
-- it is necessary and is NOT sufficient on its own:
--   1. Re-run this file with a real password -- step 1's else-branch rotates it
--      and re-asserts the attributes.
--   2. Update the GitHub secret BACKUP_PGPASSWORD to match, or the workflow
--      starts failing to connect, which is the safe direction but is an outage.
--   3. Treat the window between the two as a disclosure: a LOGIN role with
--      BYPASSRLS and SELECT on every table in public was reachable by anyone
--      who read the repo. What that is worth depends on whether the database
--      host is reachable from the internet, which is a separate question and
--      is NOT answered by this file.
