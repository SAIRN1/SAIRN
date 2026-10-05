-- sql/zz_confirm_2026-10-05_missing_tables.sql
--
-- THE CONFIRM HALF OF THE 2026-10-05 MISSING-TABLE RUNBOOK. Read-only: every
-- statement here is a SELECT against information_schema and nothing in this
-- file creates, alters or drops anything.
--
-- WHY IT EXISTS AS A FILE RATHER THAN AS TEXT IN A DOCUMENT. A multi-statement
-- paste into the Supabase SQL editor can truncate silently and half-apply while
-- still reporting success -- that has happened on this platform -- so every
-- CREATE paste needs a confirm that is run separately and read. A confirm query
-- living in a markdown document gets retyped; one living here gets pasted.
--
-- WHY IT DOES NOT CONTAIN THE CREATE STATEMENTS. The twenty schema files
-- already exist in sql/ and are idempotent. Concatenating them into one
-- runbook file would create a SECOND COPY of twenty migrations, and the day one
-- of the originals changes the copy goes stale with nothing to notice -- item 43
-- (Ariane 5): a second copy is not a second opinion, it is a second thing to
-- drift. So this file confirms and never creates, and the runbook names the
-- originals to paste.
--
-- HOW TO USE IT: run ONE section at a time, immediately after pasting that
-- app's schema files. Running the whole file at the end cannot tell you WHICH
-- paste truncated, which is the entire point of confirming.
--
-- The expected row count is stated above every section. FEWER ROWS THAN STATED
-- MEANS A PASTE TRUNCATED -- re-paste that file and re-run that section. Do not
-- assume.
--
-- Full account: docs/2026-10-05-michael-sql-runbook.md
--              docs/2026-10-05-gate1-missing-table-triage.md


-- ===========================================================================
-- SECTION 1 -- StoneDesk.  EXPECT 2 ROWS.
--   after: sql/stonedesk_locations_schema.sql
--          sql/sd_approvals_schema.sql
-- ===========================================================================
select 'stonedesk' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('sd_locations', 'sd_approvals')
order by table_name;


-- ===========================================================================
-- SECTION 2 -- StoneDesk, the supplier lead-time table.  EXPECT 1 ROW.
--   after: sql/sd_supplier_lead_times_schema.sql
--
-- SEPARATE FROM SECTION 1 ON PURPOSE. This table is reached through the BARE
-- resource name `supplier_lead_times` while the table is `sd_supplier_lead_times`,
-- and its register cell has carried a NOT-PROVISIONED note since 2026-09-29
-- that was re-driven and still held on 2026-10-05. It is also the table whose
-- absence exposed that the Gate-1 sweep was reading 113 schema files of 147,
-- so it gets its own confirm rather than being folded into a count.
-- ===========================================================================
select 'stonedesk' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'sd_supplier_lead_times';


-- ===========================================================================
-- SECTION 3 -- SAIRNgrounds.  EXPECT 2 ROWS.
--   after: sql/sairngrounds_caddie_schema.sql
-- ===========================================================================
select 'sairngrounds' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('grd_rounds', 'grd_cart_orders')
order by table_name;


-- ===========================================================================
-- SECTION 4 -- SAIRNdental.  EXPECT 3 ROWS.
--   after: sql/sairndental_gfe_schema.sql
--          sql/sairndental_recall_schema.sql
--          sql/sairndental_treatment_plans_schema.sql
-- ===========================================================================
select 'sairndental' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('dnt_gfe', 'dnt_recall_outreach', 'dnt_txplans')
order by table_name;


-- ===========================================================================
-- SECTION 5 -- SAIRNmechanical.  EXPECT 1 ROW.
--   after: sql/mech_credentials_schema.sql
-- ===========================================================================
select 'sairnmechanical' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'mech_credentials';


-- ===========================================================================
-- SECTION 6 -- SAIRNsenior.  EXPECT 9 ROWS. The largest single app.
--   after: sql/sairnsenior_applicants_schema.sql
--          sql/sairnsenior_authorizations_schema.sql
--          sql/sairnsenior_branches_schema.sql
--          sql/sairnsenior_franchise_schema.sql
--          sql/sairnsenior_payer_contracts_schema.sql
--          sql/sairnsenior_referrals_schema.sql      (TWO tables)
--          sql/sairnsenior_training_schema.sql       (TWO tables)
-- ===========================================================================
select 'sairnsenior' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules')
order by table_name;


-- ===========================================================================
-- SECTION 7 -- SAIRNroofing.  EXPECT 8 ROWS.
--   after: sql/sairnroofing_entities_schema.sql
--          sql/sairnroofing_prequal_schema.sql             (TWO tables)
--          sql/sairnroofing_safety_schema.sql              (TWO tables)
--          sql/sairnroofing_supplier_documents_schema.sql
--          sql/sairnroofing_warranties_schema.sql          (TWO tables)
-- ===========================================================================
select 'sairnroofing' as app, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'rf_entities', 'rf_bonding', 'rf_prequal_documents',
    'rf_job_hazard_assessments', 'rf_safety_equipment',
    'rf_supplier_documents', 'rf_job_warranties', 'rf_warranty_tiers')
order by table_name;


-- ===========================================================================
-- SECTION 8 -- THE WHOLE SET.  EXPECT 26 ROWS.
--
-- Run this LAST, after all seven sections above have each returned their stated
-- count. It is a total and not a substitute: a total of 26 tells you nothing
-- about which file to re-paste, which is why it is here and not first.
-- ===========================================================================
select count(*) as tables_present, 26 as expected
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'sd_locations', 'sd_approvals', 'sd_supplier_lead_times',
    'grd_rounds', 'grd_cart_orders',
    'dnt_gfe', 'dnt_recall_outreach', 'dnt_txplans',
    'mech_credentials',
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules',
    'rf_entities', 'rf_bonding', 'rf_prequal_documents',
    'rf_job_hazard_assessments', 'rf_safety_equipment',
    'rf_supplier_documents', 'rf_job_warranties', 'rf_warranty_tiers');


-- ===========================================================================
-- SECTION 9 -- THE GRANTS, which are the half a re-paste can silently skip.
--
-- EXPECT: every row below reads `select, insert, update` -- or, for the three
-- append-only tables, `select, insert` with NO update.
--
-- WHY THIS SECTION EXISTS. A CREATE TABLE that succeeds while its GRANT block
-- does not leaves a table the app cannot reach, and api/sd-data.js reports that
-- as 503 NOT_PROVISIONED -- the SAME answer as a table that does not exist. The
-- two are indistinguishable from the app, so confirming the table exists is not
-- confirming the migration worked.
--
-- THERE MUST BE NO `DELETE` AND NO `TRUNCATE` ON ANY ROW.
-- sql/unused_delete_grant_revoke_2026-08-24.sql revoked delete platform-wide
-- across 134 tables and several of these files carry that warning themselves.
-- A delete grant appearing here means a paste picked up the wrong block.
-- ===========================================================================
select table_name,
       string_agg(lower(privilege_type), ', ' order by privilege_type) as privs
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee = 'service_role'
  and table_name in (
    'sd_locations', 'sd_approvals', 'sd_supplier_lead_times',
    'grd_rounds', 'grd_cart_orders',
    'dnt_gfe', 'dnt_recall_outreach', 'dnt_txplans',
    'mech_credentials',
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules',
    'rf_entities', 'rf_bonding', 'rf_prequal_documents',
    'rf_job_hazard_assessments', 'rf_safety_equipment',
    'rf_supplier_documents', 'rf_job_warranties', 'rf_warranty_tiers')
group by table_name
order by table_name;


-- ===========================================================================
-- SECTION 10 -- ROW LEVEL SECURITY, the other half.  EXPECT every row true.
--
-- Two patterns are both correct on this platform and both appear among the 20
-- files, so this section asserts RLS is ON and does NOT require a policy:
--
--   RLS on + a `svc only <table>` policy  -- the explicit form
--   RLS on + NO policy at all            -- relies on service_role's BYPASSRLS
--
-- MEASURED BEFORE WRITING THIS: 91 tables in sql/ use the no-policy form and 81
-- of them are confirmed live and readable today, so the absence of a policy is
-- the dominant platform pattern and not a defect. `mech_credentials` and
-- `rf_supplier_documents` are the two in this set that use it.
--
-- WHAT WOULD BE A DEFECT is `rowsecurity = false`: that leaves the table open
-- to `anon` and `authenticated`, which is the state
-- sql/anon_authenticated_schema_usage_revoke_stage_b_2026-08-26.sql exists to
-- prevent.
-- ===========================================================================
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in (
    'sd_locations', 'sd_approvals', 'sd_supplier_lead_times',
    'grd_rounds', 'grd_cart_orders',
    'dnt_gfe', 'dnt_recall_outreach', 'dnt_txplans',
    'mech_credentials',
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules',
    'rf_entities', 'rf_bonding', 'rf_prequal_documents',
    'rf_job_hazard_assessments', 'rf_safety_equipment',
    'rf_supplier_documents', 'rf_job_warranties', 'rf_warranty_tiers')
order by tablename;
