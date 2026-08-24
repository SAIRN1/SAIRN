-- sql/append_only_grant_audit.sql
-- service_role excess-privilege fix. Diagnose, then fix the live tables, then
-- fix the source so it cannot recur. Run the sections in order.
--
-- ── THIS FILE SUPERSEDES TWO OTHERS. DO NOT RUN THEM. ─────────────────────
-- Two sessions investigated this independently on 2026-08-24 and reached the
-- same conclusion by different routes:
--   * this file's own earlier revision (diagnostic-only, 10 hand-listed tables)
--   * sql/service_role_excess_privilege_audit_2026-08-24.sql, commit 5897313,
--     which as of this writing is committed in Documents\SAIRN-cc and NOT
--     pushed to origin.
-- Both are folded in here. Running two overlapping REVOKE/GRANT scripts is not
-- harmful (they are idempotent and agree), but it makes it impossible to say
-- afterwards which one produced the state you are looking at. Run this one.
--
-- What each contributed, so nothing is silently dropped:
--   from 5897313 -- Section 2's list-free discovery sweep (better than a
--                   hand-built list: it finds tables neither session knew to
--                   check), has_table_privilege() as the confirmation style,
--                   and four tables this file had missed: dnt_cred_rules,
--                   rf_jobs, sairnroofing_employee_auth, plus the correct
--                   observation that dnt_cred_rules legitimately needs UPDATE.
--   from this file -- sairncash_waitlist, which 5897313 missed, and the
--                   default-ACL question that turned out to be the real answer.
--
-- ── ROOT CAUSE, NOW CONFIRMED RATHER THAN INFERRED ───────────────────────
-- Confirmed live 2026-08-24 by querying pg_default_acl: postgres's DEFAULT ACL
-- for relations in schema public grants service_role
-- TRUNCATE, REFERENCES, TRIGGER, MAINTAIN on every table postgres creates,
-- automatically, regardless of what the migration file grants.
--
-- That is why `grant select, insert` was never sufficient on nine tables. GRANT
-- is additive -- it cannot remove a privilege the role already holds. This is
-- not nine per-table mistakes; it is the platform default working against every
-- schema file that does not explicitly override it.
--
-- 5897313 reached the right fix from a related but DIFFERENT premise -- the
-- sairn-infra-debugger note that raw-SQL-created tables end up holding "only
-- TRUNCATE/REFERENCES/TRIGGER and nothing else." That describes the same
-- baseline, but as a quirk of table creation rather than as a default ACL, and
-- it predates MAINTAIN (PostgreSQL 17). The distinction matters: a creation
-- quirk implies per-table remediation is the whole job, while a default ACL
-- means every FUTURE table starts wrong too. Hence Section 4, which neither
-- earlier file had.
--
-- MAINTAIN exists only on PostgreSQL 17+. It appeared in this project's real
-- pg_default_acl output, so this server is 17+. On an older server the word
-- MAINTAIN is a syntax error -- drop it from Section 4 if this file is ever
-- reused against one.

-- =========================================================================
-- SECTION 1 -- CONFIRM THE ROOT CAUSE BEFORE CHANGING ANYTHING
-- =========================================================================

-- 1a. The default ACL itself. This is the finding. Look for service_role with
--     the D/x/t/m flags (TRUNCATE/REFERENCES/TRIGGER/MAINTAIN).
select d.defaclrole::regrole as granting_role,
       n.nspname             as schema,
       d.defaclobjtype       as obj_type,
       d.defaclacl           as default_acl
  from pg_default_acl d
  left join pg_namespace n on n.oid = d.defaclnamespace
 where n.nspname = 'public' or n.nspname is null;

-- 1b. The table where it was found. Expect BEFORE the fix:
--     sel=t ins=t upd=f del=f trunc=t refs=t trig=t maint=t
select has_table_privilege('service_role','public.dnt_credentials','SELECT')     as sel,
       has_table_privilege('service_role','public.dnt_credentials','INSERT')     as ins,
       has_table_privilege('service_role','public.dnt_credentials','UPDATE')     as upd,
       has_table_privilege('service_role','public.dnt_credentials','DELETE')     as del,
       has_table_privilege('service_role','public.dnt_credentials','TRUNCATE')   as trunc,
       has_table_privilege('service_role','public.dnt_credentials','REFERENCES') as refs,
       has_table_privilege('service_role','public.dnt_credentials','TRIGGER')    as trig,
       has_table_privilege('service_role','public.dnt_credentials','MAINTAIN')   as maint;

-- =========================================================================
-- SECTION 2 -- DISCOVERY SWEEP (from 5897313; relies on no hand-built list)
-- =========================================================================
-- Every public table where service_role holds TRUNCATE. Rows with
-- has_update/has_delete = false are the append-only-by-design ones, where
-- TRUNCATE defeats the exact guarantee the table exists to keep.
--
-- READ THIS OUTPUT BEFORE RUNNING SECTION 3. If it lists tables absent from
-- Section 3, they were missed by both sessions and need adding.
select t.table_name,
       bool_or(g.privilege_type = 'TRUNCATE')   as has_truncate,
       bool_or(g.privilege_type = 'REFERENCES') as has_references,
       bool_or(g.privilege_type = 'TRIGGER')    as has_trigger,
       bool_or(g.privilege_type = 'UPDATE')     as has_update,
       bool_or(g.privilege_type = 'DELETE')     as has_delete
  from information_schema.tables t
  join information_schema.role_table_grants g
    on g.table_name = t.table_name and g.table_schema = t.table_schema
 where t.table_schema = 'public' and g.grantee = 'service_role'
 group by t.table_name
having bool_or(g.privilege_type = 'TRUNCATE')
 order by bool_or(g.privilege_type = 'UPDATE'), t.table_name;

-- =========================================================================
-- SECTION 3 -- FIX THE LIVE TABLES
-- =========================================================================
-- REVOKE ALL first (clears the default-ACL baseline along with everything
-- else), then re-grant exactly the verbs each table's own app code uses. This
-- is the idiom already proven correct on sairncode_audit_log and
-- stonedesk_audit_log, which is why those two are absent below -- they were
-- already right and need no change.
--
-- Idempotent and re-runnable. Touches no row data.
--
-- THE GRANTS BELOW ARE NOT UNIFORM, ON PURPOSE. Three tables legitimately
-- need UPDATE and keep it; the rest are append-only and do not. Check each
-- against its real write path before running -- revoking UPDATE from a table
-- the application actually updates would break it, silently, at the next
-- write.

-- SAIRNdental. dnt_cred_rules KEEPS update: rules are superseded in place
-- (status flips, effective_to gets set) and the endpoint upserts them.
revoke all on public.dnt_credentials from service_role;
grant select, insert on public.dnt_credentials to service_role;
revoke all on public.dnt_cred_rules from service_role;
grant select, insert, update on public.dnt_cred_rules to service_role;

-- SAIRNcare -- append-only.
revoke all on public.alf_staff_credentials from service_role;
grant select, insert on public.alf_staff_credentials to service_role;
revoke all on public.alf_signals from service_role;
grant select, insert on public.alf_signals to service_role;
revoke all on public.alf_claim_routes from service_role;
grant select, insert on public.alf_claim_routes to service_role;

-- SAIRNlaw audit log. Its migration revoked update/delete, which were never
-- granted -- a no-op that read like a control. truncate/references/trigger
-- were never touched.
revoke all on public.sairnlaw_audit_log from service_role;
grant select, insert on public.sairnlaw_audit_log to service_role;

-- SAIRNscape org intel -- append-only.
revoke all on public.sairnscape_org_intel from service_role;
grant select, insert on public.sairnscape_org_intel to service_role;

-- SAIRNcash waitlist -- append-only (missed by 5897313).
revoke all on public.sairncash_waitlist from service_role;
grant select, insert on public.sairncash_waitlist to service_role;

-- SAIRNroofing -- from 5897313. rf_jobs and sairnroofing_employee_auth keep
-- UPDATE; rf_photos does not. Schema-qualified here, which 5897313's last
-- statement was not.
revoke all on public.rf_photos from service_role;
grant select, insert on public.rf_photos to service_role;
revoke all on public.rf_jobs from service_role;
grant select, insert, update on public.rf_jobs to service_role;
revoke all on public.sairnroofing_employee_auth from service_role;
grant select, insert, update on public.sairnroofing_employee_auth to service_role;

-- =========================================================================
-- SECTION 4 -- FIX THE SOURCE, SO IT CANNOT RECUR
-- =========================================================================
-- Without this, Section 3 is a one-time cleanup and the next table anyone
-- creates starts with the same baseline. With it, `grant select, insert`
-- alone is finally sufficient going forward.
--
-- FOR ROLE postgres matters: a default ACL is scoped to the role that CREATES
-- the object. This covers tables created by postgres, which is what the
-- Supabase SQL editor runs as. If any migration is ever run as a different
-- role, that role needs its own statement -- Section 1a will show it.
--
-- Does NOT affect existing tables. Section 3 is what fixes those.
alter default privileges for role postgres in schema public
  revoke truncate, references, trigger, maintain on tables from service_role;

-- =========================================================================
-- SECTION 5 -- VERIFY
-- =========================================================================

-- 5a. Re-run SECTION 1a. service_role's entry should no longer carry
--     TRUNCATE/REFERENCES/TRIGGER/MAINTAIN for future tables.

-- 5b. Re-run SECTION 2. Expect ZERO ROWS. Any table still listed was missed
--     by Section 3 and needs its own revoke/grant pair added.

-- 5c. Per-table confirmation, the same style as Section 1b. Every append-only
--     table should read t,t,f,f,f,f,f,f -- and the three that keep UPDATE
--     should read t,t,t,f,f,f,f,f.
select tbl,
       has_table_privilege('service_role', tbl, 'SELECT')     as sel,
       has_table_privilege('service_role', tbl, 'INSERT')     as ins,
       has_table_privilege('service_role', tbl, 'UPDATE')     as upd,
       has_table_privilege('service_role', tbl, 'DELETE')     as del,
       has_table_privilege('service_role', tbl, 'TRUNCATE')   as trunc,
       has_table_privilege('service_role', tbl, 'REFERENCES') as refs,
       has_table_privilege('service_role', tbl, 'TRIGGER')    as trig,
       has_table_privilege('service_role', tbl, 'MAINTAIN')   as maint
  from unnest(array[
    'public.dnt_credentials',
    'public.dnt_cred_rules',
    'public.alf_staff_credentials',
    'public.alf_signals',
    'public.alf_claim_routes',
    'public.sairnlaw_audit_log',
    'public.sairnscape_org_intel',
    'public.sairncash_waitlist',
    'public.rf_photos',
    'public.rf_jobs',
    'public.sairnroofing_employee_auth',
    'public.sairncode_audit_log',
    'public.stonedesk_audit_log'
  ]) as tbl
 order by tbl;

-- ── WHAT THIS DOES NOT COVER, stated rather than implied ─────────────────
-- OWNERSHIP. postgres owns these tables and holds every privilege implicitly;
-- no REVOKE here touches that, and none can. This closes the service_role
-- surface -- the one every application code path actually goes through. It is
-- not a defense against dashboard or postgres-level access, and
-- sql/audit_log_immutability_verify.sql already says the same about the audit
-- logs.
--
-- TABLES THAT LEGITIMATELY NEED FULL CRUD (StoneDesk's slab tables,
-- SAIRNgrounds/MSB, and most app data tables) are not in Section 3. TRUNCATE
-- on those is still unwanted and still worth closing, but it does not defeat a
-- specific append-only guarantee the way it does above, and sweeping every
-- table in one pass is a bigger change than this. Section 2 lists them; that
-- is the follow-up, deliberately not bundled here.
--
-- ONCE THIS IS RUN: the two superseded files should be deleted, including
-- 5897313's, which is still unpushed in Documents\SAIRN-cc. Left in place they
-- are two more scripts that look runnable and are not.
