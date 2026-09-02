# CHECK constraints the preflight does NOT compare

**Generated 2026-09-02 from `tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/*.sql`.**

`tools/sairn_sql_preflight.py` compares CHECK constraints between `sql/` and the live
database, but **only where both sides state a numeric size bound**. Postgres does not
store the predicate you wrote -- it stores its own rewrite, so
`status in ('active','superseded')` comes back as
`status = ANY (ARRAY['active'::text, 'superseded'::text])`. Those are identical in
meaning and unrecognisable as text, and the first live run reported **33 drift findings
that were all false** for exactly that reason.

## The point of this file

**"Not flagged" is not "verified identical" for anything on this list.** The predicates
below are reported by the tool as NOT COMPARABLE and can never block a push. If one of
them genuinely drifts -- an enum value added live and not in `sql/`, or the reverse --
**nothing on this platform will notice.** They are listed so a future session reads the
gap rather than inferring safety from silence.

Checking one of these means reading `pg_get_constraintdef()` for that constraint and
comparing it to the schema file by eye. There is no tool for it and this file does not
pretend otherwise.

## The 39 predicates (19 tables)

- `alf_claim_routes.alfcr_month_fmt`
- `alf_compliance_rules.alfcp_date_order`
- `alf_compliance_rules.alfcp_status_check`
- `alf_compliance_rules.alfcp_type_check`
- `alf_mar.alfmar_entry_type_check`
- `alf_op_audits.alfopa_type_check`
- `alf_payer_rules.alfpr_date_order`
- `alf_payer_rules.alfpr_program_check`
- `alf_payer_rules.alfpr_status_check`
- `alf_signals.alfsig_signal_type_check`
- `alf_staff_credentials.alfsc_type_check`
- `dnt_cred_rules.dntcr_status_check`
- `dnt_cred_rules.dntcr_type_check`
- `dnt_credentials.dntcd_type_check`
- `rf_cert_rules.rfcr_status_check`
- `rf_cert_rules.rfcr_type_check`
- `rf_certifications.rfcd_expiry_check`
- `rf_certifications.rfcd_type_check`
- `rf_claim_agreements.rfagr_event_check`
- `rf_claim_agreements.rfagr_supersedes_check`
- `rf_claims.rfclm_status_check`
- `rf_company_programs.rfprg_expiry_coherent`
- `rf_company_programs.rfprg_reqs_is_array`
- `rf_company_programs.rfprg_status_check`
- `rf_contingency_rules.rfcon_authority_check`
- `rf_contingency_rules.rfcon_basis_check`
- `rf_contingency_rules.rfcon_count_check`
- `rf_contingency_rules.rfcon_status_check`
- `rf_contingency_rules.rfcon_trigger_check`
- `rf_contingency_rules.rfcon_unit_check`
- `rf_invoice_counters.rfinvc_seq_positive`
- `rf_invoices.rfinv_issued_needs_date`
- `rf_invoices.rfinv_issued_needs_number`
- `rf_invoices.rfinv_payments_is_array`
- `rf_invoices.rfinv_status_check`
- `rf_proposals.rfpro_event_check`
- `rf_proposals.rfpro_supersedes_check`
- `rf_schedule.rfsch_crew_is_array`
- `rf_schedule.rfsch_status_check`
