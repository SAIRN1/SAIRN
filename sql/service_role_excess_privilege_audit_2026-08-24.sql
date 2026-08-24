-- sql/service_role_excess_privilege_audit_2026-08-24.sql
-- Root-cause diagnosis + platform-wide fix for the gap found live on
-- dnt_credentials: service_role holds TRUNCATE/REFERENCES/TRIGGER on tables
-- whose own migration file never granted those verbs.
--
-- ── ROOT CAUSE, confirmed from what's on disk, not guessed ─────────────────
-- No file anywhere in this repo issues ALTER DEFAULT PRIVILEGES or GRANT ALL
-- (checked: grep -rniE "alter default privileges|grant all" across sql/, api/,
-- docs/, .claude/ returns zero hits). So the grant did not come from any SAIRN
-- migration. It is already documented, from an earlier real incident, in
-- .claude/skills/sairn-infra-debugger/SKILL.md's "GRANTs and RLS are different
-- things" section:
--
--   "A table created by raw SQL migration (rather than Supabase's Table
--   Editor UI, which auto-grants this) can easily end up with service_role
--   holding only TRUNCATE/REFERENCES/TRIGGER -- and nothing else."
--
-- Supabase's own default privileges for the public schema grant service_role
-- that baseline set for any table NOT created through the Table Editor UI --
-- which is every table in this codebase, since all of it is raw SQL migration
-- files. The established remediation pattern since the StoneDesk fe730e2
-- incident (2026-08-08+) has been to add an explicit GRANT for whatever verbs
-- the app needs -- but a GRANT statement only ADDS privileges, it never
-- REMOVES the TRUNCATE/REFERENCES/TRIGGER baseline underneath it. That half of
-- the fix was never written, on any table, until tonight.
--
-- Two tables got this right by accident rather than by chasing this specific
-- bug: stonedesk_audit_log and sairncode_audit_log both do
-- `revoke all on <table> from service_role;` BEFORE their grant, which clears
-- the baseline along with everything else. Every other table on the platform
-- -- including three of tonight's own SAIRNroofing tables -- does not.
--
-- Run Section 1 first to confirm this diagnosis against the REAL live grants
-- before trusting Section 3's fix. Section 2 is the systemic sweep -- it does
-- not depend on this file's own hand-built table list, so it will catch
-- anything missed by grepping schema files.

-- ── SECTION 1: confirm the root cause on the table where it was found ──────
-- Expect: truncate = t, references = t, trigger = t, update = f, delete = f
-- (the exact shape reported live) BEFORE Section 3 runs.
select
  has_table_privilege('service_role', 'public.dnt_credentials', 'SELECT')     as sel,
  has_table_privilege('service_role', 'public.dnt_credentials', 'INSERT')     as ins,
  has_table_privilege('service_role', 'public.dnt_credentials', 'UPDATE')     as upd,
  has_table_privilege('service_role', 'public.dnt_credentials', 'DELETE')     as del,
  has_table_privilege('service_role', 'public.dnt_credentials', 'TRUNCATE')   as trunc,
  has_table_privilege('service_role', 'public.dnt_credentials', 'REFERENCES') as refs,
  has_table_privilege('service_role', 'public.dnt_credentials', 'TRIGGER')    as trig;

-- Confirms (or refutes) that this is Supabase's schema-level default, not
-- something scoped to this one table.
select defaclobjtype, defaclacl
  from pg_default_acl
 where defaclnamespace = 'public'::regnamespace;

-- ── SECTION 2: systemic sweep -- every public table where service_role holds
-- TRUNCATE but not UPDATE (the same asymmetric shape found on dnt_credentials
-- -- present because of the default, absent because nobody added it via an
-- explicit grant). This does NOT rely on any hand-built list, so it will
-- surface tables this session did not know to check.
select
  t.table_name,
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
order by t.table_name;
-- Any row here has the gap. Tables with has_update/has_delete = false alongside
-- has_truncate = true are the append-only-by-design ones where this is most
-- severe -- TRUNCATE defeats the exact guarantee those tables exist to keep.

-- ── SECTION 3: THE FIX -- hand-verified from Section 1/2's own reasoning,
-- not a blind bolt-on. REVOKE ALL first (clears the Supabase-default baseline
-- along with everything else), then re-grant exactly the verbs each table's
-- own app code actually uses -- same shape as stonedesk_audit_log's already-
-- correct pattern. Every one of these already has its target grant re-stated
-- so this file is self-sufficient and re-runnable; running it does not change
-- what any table can already legitimately do.

-- SAIRNdental (found live, the original report)
revoke all on public.dnt_credentials from service_role;
grant select, insert on public.dnt_credentials to service_role;
revoke all on public.dnt_cred_rules from service_role;
grant select, insert, update on public.dnt_cred_rules to service_role;

-- SAIRNcare -- append-only tables with the same grant-only-adds gap
revoke all on public.alf_signals from service_role;
grant select, insert on public.alf_signals to service_role;
revoke all on public.alf_claim_routes from service_role;
grant select, insert on public.alf_claim_routes to service_role;
revoke all on public.alf_staff_credentials from service_role;
grant select, insert on public.alf_staff_credentials to service_role;

-- SAIRNlaw audit log -- PARTIALLY fixed already (its migration revokes
-- update/delete specifically, which were never granted anyway and so that
-- revoke was a no-op) but never touched truncate/references/trigger.
revoke all on public.sairnlaw_audit_log from service_role;
grant select, insert on public.sairnlaw_audit_log to service_role;

-- SAIRNscape org intel -- append-only, same gap
revoke all on public.sairnscape_org_intel from service_role;
grant select, insert on public.sairnscape_org_intel to service_role;

-- SAIRNroofing -- tonight's own three tables, same gap, already committed as
-- the fix in each table's own schema file (sql/sairnroofing_photos_schema.sql,
-- sql/sairnroofing_jobs_schema.sql, sql/sairnroofing_employee_auth_schema.sql)
-- for any future re-run. These three statements are for the tables that are
-- ALREADY live and need the fix applied now, not just on next re-run.
revoke all on public.rf_photos from service_role;
grant select, insert on public.rf_photos to service_role;
revoke all on public.rf_jobs from service_role;
grant select, insert, update on public.rf_jobs to service_role;
revoke all on sairnroofing_employee_auth from service_role;
grant select, insert, update on sairnroofing_employee_auth to service_role;

-- ── SECTION 4: re-run Section 2 after Section 3. Expect zero rows -- every
-- table that had TRUNCATE without UPDATE/DELETE should be gone from the list.
-- Any table still appearing was missed by this file's hand-built list and
-- needs its own revoke added.

-- ── WHAT THIS DOES NOT COVER, stated the same way
-- sql/audit_log_immutability_verify.sql already states it for the three audit
-- logs: table OWNERSHIP (postgres, or whoever ran these migrations) is not
-- touched by any REVOKE here and never was -- an owner always holds every
-- privilege implicitly. This fix closes the service_role/API surface, which
-- is the one every application code path actually goes through. It is not
-- and cannot be a defense against dashboard/postgres-level access.
--
-- NOT SWEPT HERE: tables outside this file's list that legitimately need
-- select/insert/update/delete (StoneDesk's slab tables, SAIRNgrounds/MSB's
-- tables, etc.) were not included above because TRUNCATE there, while still
-- unwanted and still worth closing eventually, does not defeat a specific
-- append-only guarantee the way it does on the tables above. Section 2's
-- sweep will surface every one of them for a broader follow-up pass; this
-- file scopes the FIX to the append-only-by-design tables plus tonight's own
-- new tables, per the actual request, not a platform-wide rewrite in one shot.
