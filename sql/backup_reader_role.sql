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
-- WRITTEN 2026-09-14. NOT RUN.
-- ---------------------------------------------------------------------------

-- 1. The role. Replace the password before running; it goes straight into the
--    GitHub secret BACKUP_PGPASSWORD and nowhere else.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'sairn_backup_reader') then
    create role sairn_backup_reader
      with login
           nosuperuser
           nocreatedb
           nocreaterole
           noinherit
           bypassrls
           password 'REPLACE_ME_BEFORE_RUNNING';
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
-- migration runner and several extensions create objects as `supabase_admin`.
-- A table created that way would carry no grant for this role, `pg_dump` would
-- skip it without an error, and the backup would be missing a table WHILE
-- EXITING ZERO -- the identical silent-omission shape as the RLS gap above,
-- arriving months later and only for the tables added after today.
--
-- Found by review before the role was ever created. Both grantors are covered
-- explicitly.
--
-- AND IT FAILS LOUDLY IF IT CANNOT. `FOR ROLE x` requires membership in x, and
-- `postgres` is not always a member of `supabase_admin`. A statement that
-- silently could not be applied would leave exactly the gap it was added to
-- close, so each one is attempted and a failure RAISES with what to do about
-- it. "Could not set it" is a third state and it is not "set".
do $$
declare
  r text;
begin
  foreach r in array array['postgres', 'supabase_admin'] loop
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
      raise exception
        'Could not set default privileges FOR ROLE % -- you must be a member '
        'of that role. Run this file as a role that is (supabase_admin), or '
        'grant membership first. STOPPING: leaving it unset would mean every '
        'table % creates from today on is silently absent from the backup, '
        'which is the exact failure this clause exists to prevent.', r, r;
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

-- 2b. THE DEFAULT ACLs ACTUALLY TOOK, AND FOR WHICH GRANTOR. Expect ONE ROW PER
--     GRANTOR that exists on this deployment -- `postgres` and `supabase_admin`
--     -- each showing a grant to sairn_backup_reader.
--
--     A SINGLE ROW HERE IS THE FAILURE, not a pass: it means only the role that
--     ran this file is covered, and every table the OTHER one creates from
--     today on is silently absent from the backup. That is what `FOR ROLE`
--     exists to prevent and this is the only query that proves it worked.
select pg_get_userbyid(d.defaclrole) as objects_created_by,
       d.defaclobjtype                as object_type,
       d.defaclacl                    as acl
  from pg_default_acl d
  join pg_namespace n on n.oid = d.defaclnamespace
 where n.nspname = 'public'
   and array_to_string(d.defaclacl, ',') like '%sairn_backup_reader%'
 order by 1, 2;

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
