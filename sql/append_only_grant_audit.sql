-- sql/append_only_grant_audit.sql
-- DIAGNOSTIC ONLY. Changes nothing. Run in the Supabase SQL editor.
--
-- WHY THIS EXISTS: dnt_credentials was found holding TRUNCATE for service_role
-- (select/insert/truncate/references/trigger, no update/delete) after
-- sql/sairndental_credentials_schema.sql was run. UPDATE and DELETE are
-- genuinely denied -- Michael confirmed both fail with 42501 -- so the
-- append-only guarantee holds against the two verbs the application could
-- plausibly issue. TRUNCATE is a different and worse shape of the same risk:
-- it removes EVERY row at once and is not a DELETE, so a control that only
-- revokes update and delete does not stop it.
--
-- ── WHAT IS ESTABLISHED, FROM THE REPO ───────────────────────────────────
-- GRANT is additive. `grant select, insert ... to service_role` cannot remove
-- a privilege the role already holds, so a schema that only grants is at the
-- mercy of whatever the table started with. This repo contains three idioms,
-- and only one of them is actually sound:
--
--   SOUND    revoke all ... from service_role;  then  grant select, insert;
--            -> exactly select+insert, whatever the defaults were.
--            sairncode_audit_log, stonedesk_audit_log.
--
--   PARTIAL  grant select, insert;  revoke update, delete;
--            -> TRUNCATE/REFERENCES/TRIGGER survive if defaults conferred them.
--            sairnlaw_audit_log.
--
--   WEAKEST  grant select, insert;  (no service_role revoke at all)
--            -> whatever the defaults conferred stays.
--            alf_staff_credentials, alf_signals, alf_claim_routes,
--            sairncash_waitlist, rf_photos, sairnscape_org_intel,
--            dnt_credentials.
--
-- Nine append-only-by-design tables use an idiom that cannot subtract. That is
-- the systemic finding, and it is independent of how TRUNCATE arrived.
--
-- ── WHAT IS NOT YET ESTABLISHED, AND MUST NOT BE GUESSED ─────────────────
-- Where TRUNCATE came from. Two candidate mechanisms fit the evidence, and
-- they call for different fixes beyond the table at hand:
--
--   (A) Supabase default privileges granted a broad set to service_role on
--       new public tables, and something later removed update/delete. If so,
--       every future table starts wrong and the fix belongs in the default
--       privileges, not only in each schema file.
--
--   (B) The observed set is the tail of an earlier grant/revoke sequence
--       specific to this project. If so, per-table remediation is enough.
--
-- Query 1 discriminates them. Do not apply a fix before reading its output --
-- fixing dnt_credentials alone would close the symptom and leave (A) intact
-- for the next table anyone creates.

-- ── QUERY 1: what do the DEFAULT privileges say? ─────────────────────────
-- Shows the default ACLs that will be applied to tables created in future.
-- If service_role appears here with more than select+insert (look for a 'D'
-- for TRUNCATE in the ACL string), mechanism (A) is confirmed.
select d.defaclrole::regrole  as granting_role,
       n.nspname              as schema,
       d.defaclobjtype        as obj_type,
       d.defaclacl            as default_acl
  from pg_default_acl d
  left join pg_namespace n on n.oid = d.defaclnamespace
 where n.nspname = 'public' or n.nspname is null;

-- ── QUERY 2: the real grant state of every append-only-by-design table ───
-- The platform-wide picture in one result set. Expect ONLY 'SELECT, INSERT'
-- in privs for each row. Anything else -- TRUNCATE especially -- is a finding.
select c.relname                                   as table_name,
       string_agg(distinct g.privilege_type, ', '
                  order by g.privilege_type)        as privs,
       bool_or(g.privilege_type = 'TRUNCATE')       as has_truncate,
       bool_or(g.privilege_type in ('UPDATE','DELETE')) as has_update_or_delete
  from information_schema.role_table_grants g
  join pg_class c on c.relname = g.table_name
 where g.grantee = 'service_role'
   and g.table_schema = 'public'
   and g.table_name in (
     'dnt_credentials',
     'alf_staff_credentials',
     'alf_signals',
     'alf_claim_routes',
     'sairncash_waitlist',
     'rf_photos',
     'sairnscape_org_intel',
     'sairnlaw_audit_log',
     'sairncode_audit_log',
     'stonedesk_audit_log'
   )
 group by c.relname
 order by has_truncate desc, has_update_or_delete desc, c.relname;

-- ── THE FIX, WRITTEN OUT BUT DELIBERATELY NOT RUN ────────────────────────
-- Correct regardless of which mechanism Query 1 shows, because revoke-then-
-- grant is deterministic: it does not care what the table started with. Run
-- it only after Query 1 has been read, and if (A) is confirmed, fix the
-- default privileges in the same pass or the next new table repeats this.
--
-- Each line is safe to re-run and does not touch row data.
--
--   revoke all on public.dnt_credentials       from service_role;
--   grant select, insert on public.dnt_credentials       to service_role;
--   revoke all on public.alf_staff_credentials from service_role;
--   grant select, insert on public.alf_staff_credentials to service_role;
--   revoke all on public.alf_signals           from service_role;
--   grant select, insert on public.alf_signals           to service_role;
--   revoke all on public.alf_claim_routes      from service_role;
--   grant select, insert on public.alf_claim_routes      to service_role;
--   revoke all on public.sairncash_waitlist    from service_role;
--   grant select, insert on public.sairncash_waitlist    to service_role;
--   revoke all on public.rf_photos             from service_role;
--   grant select, insert on public.rf_photos             to service_role;
--   revoke all on public.sairnscape_org_intel  from service_role;
--   grant select, insert on public.sairnscape_org_intel  to service_role;
--   revoke all on public.sairnlaw_audit_log    from service_role;
--   grant select, insert on public.sairnlaw_audit_log    to service_role;
--
-- CHECK EACH TABLE'S WRITE PATH BEFORE REVOKING. This list is derived from
-- each schema file's own stated intent (select+insert only). If any of these
-- tables is in fact updated by live application code, revoking UPDATE will
-- break it -- and that is worth finding out deliberately here rather than as a
-- production failure. alf_signals appears in TWO schema files
-- (sairncare_signals_schema.sql and sairncare_all_remaining_migrations.sql);
-- confirm which one actually ran before assuming its intent.
--
-- Re-run Query 2 afterwards. Every row should read exactly 'INSERT, SELECT'.
