-- sql/b29_never_run_tables_verify.sql
--
-- CONCEPT: after the 28 schema files below have been run, ONE read-only query
-- answers, for each of the 37 tables live api/ code queries, whether it now
-- exists -- and it always returns 37 rows, never fewer, so a missing table is
-- a row that says MISSING rather than a row that is not there.
--
-- READ-ONLY. This file creates, alters and grants NOTHING. It is the check for
-- the 28 files, not a 29th migration. Written by cc b29 (2026-10-20), NOT RUN.
--
-- ── WHY 37 AND NOT 23 ─────────────────────────────────────────────────────
-- tools/schema_snapshot_freshness.py reports 23. That is a FLOOR. Its QUERY_RE
-- (line 103) only recognises a literal "/rest/v1/<table>" or rest('<table>').
-- Fourteen more tables are reached through a table-name constant
-- (TOKEN_TABLE = 'sairndental_bi_tokens') or through a generic handler that
-- builds the URL from the dispatched resource name (dnt_gfe, sen_referrals,
-- sf_trustee_audits ...), so the tool files them under "NOT queried by api/".
-- dnt_gfe was confirmed MISSING by a signed-in live read on 2026-10-20.
-- Method for 37: absent from db/schema_snapshot.json (captured 2026-10-20
-- 07:55Z) AND named as a quoted literal on a non-comment line of a non-test
-- file under api/. Six of the 43 absent tables were excluded because api/
-- names them only in comments or not at all: biometric_consent,
-- biometric_template, sairn_circuit_breaker, license_keys_grant_baseline and
-- the two _grant_baseline_2026_08_25 tables.
--
-- ── THE 28 FILES, IN RUN ORDER ────────────────────────────────────────────
-- None of the 28 has a foreign key into another of the 28, so the order is by
-- app for readability, not by dependency. Every file was checked: CREATE TABLE
-- IF NOT EXISTS, idempotent indexes/policies/grants, safe to run twice, and
-- tools/sairn_sql_preflight.py --live db/schema_snapshot.json = 0 findings.
-- Each file's own columns were compared against every api/ line that reads,
-- writes, filters or on_conflicts the table: 0 column mismatches in 37 tables.
--
--   StoneDesk
--    1  sql/sairn_style_profiles_schema.sql           sairn_style_profiles
--    2  sql/sd_approvals_schema.sql                   sd_approvals
--    3  sql/stonedesk_locations_schema.sql            sd_locations
--    4  sql/stonedesk_intake_photos_2026-09-03.sql    sd_quote_request_photos
--    5  sql/sd_supplier_lead_times_schema.sql         sd_supplier_lead_times
--   SAIRNroofing
--    6  sql/sairnroofing_entities_schema.sql          rf_entities (+ ADD COLUMN IF NOT EXISTS rf_locations.entity_id; rf_locations exists)
--    7  sql/sairnroofing_prequal_schema.sql           rf_prequal_documents, rf_bonding
--    8  sql/sairnroofing_safety_schema.sql            rf_safety_equipment, rf_job_hazard_assessments
--    9  sql/sairnroofing_warranties_schema.sql        rf_warranty_tiers, rf_job_warranties
--   10  sql/sairnroofing_supplier_documents_schema.sql rf_supplier_documents (grant hardened b29)
--   SAIRNsenior
--   11  sql/sairnsenior_branches_schema.sql           sen_branches
--   12  sql/sairnsenior_payer_contracts_schema.sql    sen_payer_contracts
--   13  sql/sairnsenior_authorizations_schema.sql     sen_authorizations
--   14  sql/sairnsenior_franchise_schema.sql          sen_franchise_agreements
--   15  sql/sairnsenior_referrals_schema.sql          sen_referral_sources, sen_referrals
--   16  sql/sairnsenior_training_schema.sql           sen_training_rules, sen_training_records
--   17  sql/sairnsenior_applicants_schema.sql         sen_applicants
--   SAIRNdental
--   18  sql/sairndental_gfe_schema.sql                dnt_gfe  (Tier A; the GFE issued date lives only in localStorage until this runs)
--   19  sql/sairndental_recall_schema.sql             dnt_recall_outreach
--   20  sql/sairndental_treatment_plans_schema.sql    dnt_txplans
--   21  sql/sairndental_bi_tokens_schema.sql          sairndental_bi_tokens
--   SAIRNcare / SAIRNvet witnessing
--   22  sql/sairncare_witness_schema.sql              sairncare_witness_policy, sairncare_witness_tokens
--   23  sql/sairnvet_witness_schema.sql               sairnvet_witness_policy, sairnvet_witness_tokens
--   SAIRNfreedom
--   24  sql/sairnfreedom_data_schema.sql              sf_trustee_audits -- WHOLE-FILE RE-RUN. The other 35
--                                                    sf_* tables in it already exist; re-running is idempotent
--                                                    and resets service_role on them to SELECT, INSERT, UPDATE,
--                                                    which is all the code uses (no REST DELETE on any sf_* table).
--   Other apps
--   25  sql/accounting_connector_schema.sql           accounting_consents, accounting_connections
--   26  sql/sairngrounds_caddie_schema.sql            grd_rounds, grd_cart_orders
--   27  sql/mech_credentials_schema.sql               mech_credentials
--   28  sql/sairnscape_org_intel_schema.sql           sairnscape_org_intel (RLS + revoke hardened b29)
--
-- After all 28: run the query below, then re-capture the snapshot
-- (sql/schema_snapshot_query.sql -> save as db/schema_snapshot.json -> COMMIT).
--
-- ── WHAT A PASS IS ────────────────────────────────────────────────────────
-- 37 rows, every one 'PRESENT'. Fewer than 37 rows is a broken query, not a
-- partial pass. Any 'MISSING' names the file above that did not apply.

select '-- current_user (any role can read to_regclass; owner not required)' as tbl, current_user::text as state
union all
select t.tbl, case when to_regclass('public.' || t.tbl) is null then 'MISSING' else 'PRESENT' end
  from (values
    ('sairn_style_profiles'), ('sd_approvals'), ('sd_locations'),
    ('sd_quote_request_photos'), ('sd_supplier_lead_times'),
    ('rf_entities'), ('rf_prequal_documents'), ('rf_bonding'),
    ('rf_safety_equipment'), ('rf_job_hazard_assessments'),
    ('rf_warranty_tiers'), ('rf_job_warranties'), ('rf_supplier_documents'),
    ('sen_branches'), ('sen_payer_contracts'), ('sen_authorizations'),
    ('sen_franchise_agreements'), ('sen_referral_sources'), ('sen_referrals'),
    ('sen_training_rules'), ('sen_training_records'), ('sen_applicants'),
    ('dnt_gfe'), ('dnt_recall_outreach'), ('dnt_txplans'),
    ('sairndental_bi_tokens'),
    ('sairncare_witness_policy'), ('sairncare_witness_tokens'),
    ('sairnvet_witness_policy'), ('sairnvet_witness_tokens'),
    ('sf_trustee_audits'),
    ('accounting_consents'), ('accounting_connections'),
    ('grd_rounds'), ('grd_cart_orders'),
    ('mech_credentials'),
    ('sairnscape_org_intel')
  ) as t(tbl)
union all
select '-- TOTAL (must read 37 present of 37)',
       count(*) filter (where to_regclass('public.' || t2.tbl) is not null) || ' present of ' || count(*)
  from (values
    ('sairn_style_profiles'), ('sd_approvals'), ('sd_locations'),
    ('sd_quote_request_photos'), ('sd_supplier_lead_times'),
    ('rf_entities'), ('rf_prequal_documents'), ('rf_bonding'),
    ('rf_safety_equipment'), ('rf_job_hazard_assessments'),
    ('rf_warranty_tiers'), ('rf_job_warranties'), ('rf_supplier_documents'),
    ('sen_branches'), ('sen_payer_contracts'), ('sen_authorizations'),
    ('sen_franchise_agreements'), ('sen_referral_sources'), ('sen_referrals'),
    ('sen_training_rules'), ('sen_training_records'), ('sen_applicants'),
    ('dnt_gfe'), ('dnt_recall_outreach'), ('dnt_txplans'),
    ('sairndental_bi_tokens'),
    ('sairncare_witness_policy'), ('sairncare_witness_tokens'),
    ('sairnvet_witness_policy'), ('sairnvet_witness_tokens'),
    ('sf_trustee_audits'),
    ('accounting_consents'), ('accounting_connections'),
    ('grd_rounds'), ('grd_cart_orders'),
    ('mech_credentials'),
    ('sairnscape_org_intel')
  ) as t2(tbl);
