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
alter default privileges in schema public
  grant select on tables to sairn_backup_reader;
alter default privileges in schema public
  grant select on sequences to sairn_backup_reader;

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
