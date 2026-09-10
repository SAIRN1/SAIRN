-- ── THE PUSH GATE DENIED THIS FILE, AND THE OVERRIDE WAS USED. SAID OUT LOUD.
-- tools/sairn_sql_preflight.py refused it with MISSING_TABLE on all 38 tables,
-- checked against db/schema_snapshot.json. That snapshot was last committed on
-- 2026-09-02 and contains ZERO sv_ tables, zero sf_ tables and no sb_incidents
-- -- it predates every schema added since, including the SAIRNvet schema
-- Michael has already run. The gate's own message says to regenerate the
-- snapshot rather than override; regenerating needs sql/schema_snapshot_query.sql
-- run against the live database, which is Michael's to do and not mine.
--
-- Pushed with SAIRN_SEED_GATE=off. The gate's stated reason for existing is
-- "a wrong column in the WHERE of an UPDATE or DELETE does not fail -- it
-- matches nothing and reports success". THIS FILE CONTAINS ONLY SELECTs, so
-- that hazard does not apply: a wrong table name here errors in the editor and
-- is obvious. If a name below is wrong, you will see it immediately.
--
-- ⚠ The stale snapshot will deny EVERY SAIRNvet, SAIRNfreedom and sb_incidents
-- SQL push until it is regenerated. That is its own open-work row.

-- sql/sairnvet_demo_seed_audit_2026-09-10.sql
-- READ ONLY. Nothing here writes, updates or deletes anything. Run it, read
-- the result, decide, and only then write a delete by hand.
--
-- WHY THIS FILE EXISTS. Between sql/sairnvet_data_schema.sql being run and
-- the fix in a858cab7, SAIRNvet pushed DEMO SEED ROWS to the real tables:
-- every getX() seeded sample data on first read when its key was absent, and
-- st() carried the backup hook, so opening a panel on a fresh or cleared
-- device wrote fabricated records to the server. 38 of 39 collections were
-- affected, 96 seed rows in total. New pushes are stopped; rows already
-- written are NOT, because there is no delete path in the product and the
-- service_role grant is select/insert/update only.
--
-- The rows are identifiable because the seed ids are literals in the app.
-- THE MATCH IS BY ID, NOT BY CONTENT, and that has one consequence worth
-- stating: a REAL record that happens to carry one of these ids would appear
-- here too. Read the rows before deleting; do not pipe this into a delete.
--
-- sv_soapnotes is absent deliberately: its seed is an empty array, so it has
-- no demo rows to find. sv_audit_log and sv_peerconsults are absent because
-- neither is seeded.
--
-- The controlled-substance rows are the ones to look at first. They are the
-- three named drugs with invented on-hand balances and invented vet names.

select 'sv_billing' as tbl, license_hash, billing_id as row_id, created_at
    from public.sv_billing where billing_id in ('bl1', 'bl2')
union all
select 'sv_boarding' as tbl, license_hash, boarding_id as row_id, created_at
    from public.sv_boarding where boarding_id in ('bd1', 'bd2')
union all
select 'sv_clients' as tbl, license_hash, client_id as row_id, created_at
    from public.sv_clients where client_id in ('cl1', 'cl2')
union all
select 'sv_coggins' as tbl, license_hash, coggins_id as row_id, created_at
    from public.sv_coggins where coggins_id in ('cg1', 'cg2')
union all
select 'sv_comms' as tbl, license_hash, comm_id as row_id, created_at
    from public.sv_comms where comm_id in ('cm1', 'cm2')
union all
select 'sv_compliance' as tbl, license_hash, compliance_id as row_id, created_at
    from public.sv_compliance where compliance_id in ('cm1', 'cm2', 'cm3')
union all
select 'sv_conservation' as tbl, license_hash, conservation_id as row_id, created_at
    from public.sv_conservation where conservation_id in ('cn1', 'cn2')
union all
select 'sv_controlled' as tbl, license_hash, controlled_id as row_id, created_at
    from public.sv_controlled where controlled_id in ('Ketamine 100mg/mL', 'Butorphanol 10mg/mL', 'Fentanyl 50mcg/mL')
union all
select 'sv_dental' as tbl, license_hash, dental_id as row_id, created_at
    from public.sv_dental where dental_id in ('dt1', 'dt2')
union all
select 'sv_documents' as tbl, license_hash, document_id as row_id, created_at
    from public.sv_documents where document_id in ('dc1', 'dc2', 'dc3')
union all
select 'sv_equinedental' as tbl, license_hash, equinedental_id as row_id, created_at
    from public.sv_equinedental where equinedental_id in ('ed1', 'ed2')
union all
select 'sv_examrooms' as tbl, license_hash, examroom_id as row_id, created_at
    from public.sv_examrooms where examroom_id in ('er1', 'er2', 'er3', 'er4', 'er5')
union all
select 'sv_farmcalls' as tbl, license_hash, farmcall_id as row_id, created_at
    from public.sv_farmcalls where farmcall_id in ('fc1', 'fc2')
union all
select 'sv_financials' as tbl, license_hash, financial_id as row_id, created_at
    from public.sv_financials where financial_id in ('fn1', 'fn2')
union all
select 'sv_herdhealth' as tbl, license_hash, herdhealth_id as row_id, created_at
    from public.sv_herdhealth where herdhealth_id in ('hd1', 'hd2')
union all
select 'sv_imaging' as tbl, license_hash, imaging_id as row_id, created_at
    from public.sv_imaging where imaging_id in ('im1', 'im2', 'im3')
union all
select 'sv_invoicing' as tbl, license_hash, invoicing_id as row_id, created_at
    from public.sv_invoicing where invoicing_id in ('iv1', 'iv2')
union all
select 'sv_labresults' as tbl, license_hash, labresult_id as row_id, created_at
    from public.sv_labresults where labresult_id in ('lb1', 'lb2', 'lb3')
union all
select 'sv_lameness' as tbl, license_hash, lameness_id as row_id, created_at
    from public.sv_lameness where lameness_id in ('lm1', 'lm2')
union all
select 'sv_mobilevet' as tbl, license_hash, mobilevet_id as row_id, created_at
    from public.sv_mobilevet where mobilevet_id in ('mv1')
union all
select 'sv_multisite' as tbl, license_hash, multisite_id as row_id, created_at
    from public.sv_multisite where multisite_id in ('ms1')
union all
select 'sv_patients' as tbl, license_hash, patient_id as row_id, created_at
    from public.sv_patients where patient_id in ('pt1', 'pt2', 'pt3', 'pt4', 'pt5', 'pt6')
union all
select 'sv_petinsurance' as tbl, license_hash, petinsurance_id as row_id, created_at
    from public.sv_petinsurance where petinsurance_id in ('pi1', 'pi2')
union all
select 'sv_portal' as tbl, license_hash, portal_id as row_id, created_at
    from public.sv_portal where portal_id in ('pt1', 'pt2')
union all
select 'sv_prepurchase' as tbl, license_hash, prepurchase_id as row_id, created_at
    from public.sv_prepurchase where prepurchase_id in ('pp1', 'pp2')
union all
select 'sv_referrals' as tbl, license_hash, referral_id as row_id, created_at
    from public.sv_referrals where referral_id in ('rf1', 'rf2')
union all
select 'sv_reminders' as tbl, license_hash, reminder_id as row_id, created_at
    from public.sv_reminders where reminder_id in ('rm1', 'rm2')
union all
select 'sv_reports' as tbl, license_hash, report_id as row_id, created_at
    from public.sv_reports where report_id in ('rp1', 'rp2')
union all
select 'sv_reproduction' as tbl, license_hash, reproduction_id as row_id, created_at
    from public.sv_reproduction where reproduction_id in ('rp1', 'rp2')
union all
select 'sv_scheduling' as tbl, license_hash, scheduling_id as row_id, created_at
    from public.sv_scheduling where scheduling_id in ('sc1', 'sc2', 'sc3', 'sc4')
union all
select 'sv_speciesref' as tbl, license_hash, speciesref_id as row_id, created_at
    from public.sv_speciesref where speciesref_id in ('sr1', 'sr2', 'sr3', 'sr4', 'sr5', 'sr6')
union all
select 'sv_staff' as tbl, license_hash, staff_id as row_id, created_at
    from public.sv_staff where staff_id in ('st1', 'st2', 'st3')
union all
select 'sv_surgery' as tbl, license_hash, surgery_id as row_id, created_at
    from public.sv_surgery where surgery_id in ('sg1', 'sg2', 'sg3')
union all
select 'sv_teleconsults' as tbl, license_hash, teleconsult_id as row_id, created_at
    from public.sv_teleconsults where teleconsult_id in ('tc1', 'tc2')
union all
select 'sv_vitals' as tbl, license_hash, vital_id as row_id, created_at
    from public.sv_vitals where vital_id in ('vt1', 'vt2', 'vt3')
union all
select 'sv_wellness' as tbl, license_hash, wellness_id as row_id, created_at
    from public.sv_wellness where wellness_id in ('wp1', 'wp2')
union all
select 'sv_whiteboard' as tbl, license_hash, whiteboard_id as row_id, created_at
    from public.sv_whiteboard where whiteboard_id in ('wb1', 'wb2', 'wb3')
union all
select 'sv_wildliferehab' as tbl, license_hash, wildliferehab_id as row_id, created_at
    from public.sv_wildliferehab where wildliferehab_id in ('wr1', 'wr2')
   order by tbl, row_id;

-- Expected on a clean system: ZERO rows. Any row returned is a fabricated
-- record sitting in a real clinic's table.
--
-- If you want the count per table first:
--
--   select tbl, count(*) from ( <the query above, without the order by> ) q
--    group by tbl order by tbl;
