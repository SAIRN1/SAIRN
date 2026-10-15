# cc b15 item 1 -- the full suite sweep, and who each failure belongs to

**Command, and the log is the deliverable rather than console scroll:**

    python tools/run_all_tests.py > docs/sweep-2026-10-15.log 2>&1

**Exit 1. `docs/sweep-2026-10-15.log`, 51439 bytes, one log for one
run and nothing else wrote to it** -- b14 destroyed its own sweep output by
reusing a `/tmp` name a live process held an fd on.

## What the run measured

    RAN: 385 JS + 426 PY = 811 files (3 skipped)
    TEST-FILE FLOOR RAISED to 811 (was 808). The guard was stale: it is a

**It took 3h55m**, measured: started 08:12, exited 12:07. b14 recorded this
sweep as *"~17 minutes"* and that figure is wrong by an order of magnitude.
It is corrected here because two batches planned around it, and because the
lock ceiling in item 2 was sized against it.

## READ THIS BEFORE ATTRIBUTING ANY FAILURE

The run was CONCURRENT with cc's own commits, and the log says so itself:

    THE SUITE DIRTIED THE TREE (3 path(s)) -- a probe did not clean up:
         M .claude/claims/cc.json
         M docs/report-only-reachability.json
         M docs/scrutiny-flags.json
    Results above may be CASCADE, not real

**`.claude/claims/cc.json` was modified by cc BEFORE the run started** (the
claim-refusal record that `sairn_claim.py` writes uncommitted), and cc
committed seven times to `tools/` and `docs/` WHILE it ran. One probe said
so in its own words:

> *this run left NOTHING newly dirty in this clone -- 1 file(s) were already
> modified before it started and are not this probe's doing*

So every clean-tree-dependent failure below is **UNATTRIBUTED, not
confirmed**. That is the rule `tools/bare_run_write_check.py`'s A8 arm
encodes -- a concurrent writer's change is not the subject's -- arriving
here as the thing cc did to its own measurement. **The routing below is a
WORK LIST, not a defect list**, and the first instruction on every item is
to re-run it against a clean tree.

## The routed list -- 101 failing test files

| owner | count | why it is theirs |
|---|---:|---|
| **hank** | 6 | owns `api/` |
| **cody** | 95 | owns `tests/` |

**No `tools/` file is in the list, so cc has no sweep-routed failure of
its own** -- said explicitly, because an empty bucket and a bucket
nobody looked at read identically.

### -> hank (6)

- `api/sd-data-customer-soft-delete.test.js`  **[known-red]**
- `api/sd-data-family-contacts.test.js`  **[known-red]**
- `api/sd-data-law-trusttx-session.test.js`
- `api/sd-data-leg-session-gate.test.js`
- `api/sd-data-memory-app-scope.test.js`
- `api/sd-data-scp-licence-only.test.js`  **[known-red]**

### -> cody (95)

- `tests/approval_persistence_probe.py`
- `tests/claims/run_claim_audit_probe.py`
- `tests/claims/run_claim_retype_mutation_control.py`  **[known-red]**
- `tests/claims/run_own_claim_overlap_probe.py`
- `tests/claims/run_push_verify_probe.py`  **[known-red]**
- `tests/claims/run_registry_claim_probe.py`  **[known-red]**
- `tests/claims/run_registry_claim_sabotage_probe.py`  **[known-red]**
- `tests/defect_register_capa_control.py`  **[known-red]**
- `tests/gated_resource_direct_fetch_header.js`
- `tests/hook_command_anchoring_probe.py`
- `tests/hover_quotable_session_vocab_check.py`  **[known-red]**
- `tests/install_git_hooks_check_probe.py`  **[known-red]**
- `tests/law_reconcile_role_vocab_check.py`  **[known-red]**
- `tests/law_reconcile_role_vocab_control.py`  **[known-red]**
- `tests/law_trusttx_session_probe.py`
- `tests/local_only_self_evidence_probe.py`  **[known-red]**
- `tests/local_only_shape_probe.py`  **[known-red]**
- `tests/mech_docs_redaction_wiring_probe.py`
- `tests/push_gate/check12_probe.py`  **[known-red]**
- `tests/push_gate/check3_probe.py`
- `tests/push_gate/check7_probe.py`  **[known-red]**
- `tests/push_gate/preauth_exemption_anchor_probe.py`  **[known-red]**
- `tests/push_gate/redaction_base_probe.py`
- `tests/rebase_resolve_merge_control.py`  **[known-red]**
- `tests/run_adversarial_prompt_corpus_probe.py`  **[known-red]**
- `tests/run_alf_read_order_sabotage_probe.py`  **[known-red]**
- `tests/run_audit_event_type_probe.py`
- `tests/run_baseline_readiness_probe.py`  **[known-red]**
- `tests/run_batch_manifest_probe.py`
- `tests/run_capa_fields_probe.py`
- `tests/run_checker_confidence_probe.py`
- `tests/run_checker_control_probe.py`  **[known-red]**
- `tests/run_claim_doc_freshness_probe.py`
- `tests/run_closing_error_probe.py`
- `tests/run_completeness_probe.py`  **[known-red]**
- `tests/run_concurrency_retry_probe.py`  **[known-red]**
- `tests/run_condition_coverage_probe.py`  **[known-red]**
- `tests/run_condition_coverage_sandbox_probe.py`
- `tests/run_conflict_preflight_hook_probe.py`
- `tests/run_copy_exactly_gate_probe.py`  **[known-red]**
- `tests/run_criticality_tier_probe.py`
- `tests/run_dead_rule_sweep_probe.py`
- `tests/run_defect_dispersion_probe.py`  **[known-red]**
- `tests/run_defect_register_probe.py`  **[known-red]**
- `tests/run_dependency_graph_probe.py`  **[known-red]**
- `tests/run_dispatch_state_probe.py`  **[known-red]**
- `tests/run_eaten_substitution_probe.py`  **[known-red]**
- `tests/run_estimate_fusion_probe.py`
- `tests/run_export_coverage_probe.py`  **[known-red]**
- `tests/run_fail_open_probe.py`
- `tests/run_financial_invariant_probe.py`  **[known-red]**
- `tests/run_first_article_probe.py`  **[known-red]**
- `tests/run_githook_install_probe.py`  **[known-red]**
- `tests/run_harness_stage_diagnosis_probe.py`  **[known-red]**
- `tests/run_index_duplicate_probe.py`  **[known-red]**
- `tests/run_irreversible_class_probe.py`
- `tests/run_known_red_probe.py`
- `tests/run_leg_session_gate_sabotage_probe.py`
- `tests/run_mutation_anchor_probe.py`
- `tests/run_nhi_clone_enumeration_probe.py`  **[known-red]**
- `tests/run_nhi_register_write_flag_probe.py`  **[known-red]**
- `tests/run_out_of_service_probe.py`
- `tests/run_python_escape_hygiene_probe.py`
- `tests/run_rebase_resolve_probe.py`  **[known-red]**
- `tests/run_register_feed_gate_probe.py`
- `tests/run_removal_path_probe.py`  **[known-red]**
- `tests/run_report_only_checks_probe.py`  **[known-red]**
- `tests/run_rewrite_convergence_probe.py`  **[known-red]**
- `tests/run_sairnbuild_server_wins_sabotage_probe.py`
- `tests/run_server_wins_hydration_sabotage_probe.py`
- `tests/run_sf_session_gate_sabotage_probe.py`
- `tests/run_stored_data_criticality_probe.py`  **[known-red]**
- `tests/run_sv_session_gate_sabotage_probe.py`
- `tests/run_tier_a_open_basis_probe.py`
- `tests/run_tier_a_review_gate_sabotage_probe.py`
- `tests/run_tool_owner_header_probe.py`
- `tests/run_tooling_inventory_probe.py`
- `tests/run_write_path_scan_probe.py`  **[known-red]**
- `tests/sairnbuild_backup_pending.js`
- `tests/sairnbuild_fault_probe.py`  **[known-red]**
- `tests/sairncare/test-compliance-rules.js`  **[known-red]**
- `tests/sairncare_compliance_window_boundary.test.js`  **[known-red]**
- `tests/sairnfreedom_auth_review_probe.js`  **[known-red]**
- `tests/sairnfreedom_segregation_of_duties.js`  **[known-red]**
- `tests/sairnlegacy_fault_probe.py`  **[known-red]**
- `tests/schema_provisioning_probe.py`  **[known-red]**
- `tests/scp_quotes_review_probe.js`  **[known-red]**
- `tests/sd_data_family_mar_gate.js`
- `tests/sd_data_write_attribution_three_apps.js`
- `tests/sd_tax_money_coercion.js`  **[known-red]**
- `tests/seam_check/run_or_default_probe.py`  **[known-red]**
- `tests/seam_check/run_ref_probe.py`  **[known-red]**
- `tests/server_wins_hydration.js`
- `tests/suite_control_backfill_probe.py`  **[known-red]**
- `tests/write_readback_shape_probe.py`  **[known-red]**

## Cross-checked against docs/known-red-suites.json

**58 of the 101 are already recorded as expected-red:**

- `api/sd-data-customer-soft-delete.test.js`
- `api/sd-data-family-contacts.test.js`
- `api/sd-data-scp-licence-only.test.js`
- `tests/claims/run_claim_retype_mutation_control.py`
- `tests/claims/run_push_verify_probe.py`
- `tests/claims/run_registry_claim_probe.py`
- `tests/claims/run_registry_claim_sabotage_probe.py`
- `tests/defect_register_capa_control.py`
- `tests/hover_quotable_session_vocab_check.py`
- `tests/install_git_hooks_check_probe.py`
- `tests/law_reconcile_role_vocab_check.py`
- `tests/law_reconcile_role_vocab_control.py`
- `tests/local_only_self_evidence_probe.py`
- `tests/local_only_shape_probe.py`
- `tests/push_gate/check12_probe.py`
- `tests/push_gate/check7_probe.py`
- `tests/push_gate/preauth_exemption_anchor_probe.py`
- `tests/rebase_resolve_merge_control.py`
- `tests/run_adversarial_prompt_corpus_probe.py`
- `tests/run_alf_read_order_sabotage_probe.py`
- `tests/run_baseline_readiness_probe.py`
- `tests/run_checker_control_probe.py`
- `tests/run_completeness_probe.py`
- `tests/run_concurrency_retry_probe.py`
- `tests/run_condition_coverage_probe.py`
- `tests/run_copy_exactly_gate_probe.py`
- `tests/run_defect_dispersion_probe.py`
- `tests/run_defect_register_probe.py`
- `tests/run_dependency_graph_probe.py`
- `tests/run_dispatch_state_probe.py`
- `tests/run_eaten_substitution_probe.py`
- `tests/run_export_coverage_probe.py`
- `tests/run_financial_invariant_probe.py`
- `tests/run_first_article_probe.py`
- `tests/run_githook_install_probe.py`
- `tests/run_harness_stage_diagnosis_probe.py`
- `tests/run_index_duplicate_probe.py`
- `tests/run_nhi_clone_enumeration_probe.py`
- `tests/run_nhi_register_write_flag_probe.py`
- `tests/run_rebase_resolve_probe.py`
- `tests/run_removal_path_probe.py`
- `tests/run_report_only_checks_probe.py`
- `tests/run_rewrite_convergence_probe.py`
- `tests/run_stored_data_criticality_probe.py`
- `tests/run_write_path_scan_probe.py`
- `tests/sairnbuild_fault_probe.py`
- `tests/sairncare/test-compliance-rules.js`
- `tests/sairncare_compliance_window_boundary.test.js`
- `tests/sairnfreedom_auth_review_probe.js`
- `tests/sairnfreedom_segregation_of_duties.js`
- `tests/sairnlegacy_fault_probe.py`
- `tests/schema_provisioning_probe.py`
- `tests/scp_quotes_review_probe.js`
- `tests/sd_tax_money_coercion.js`
- `tests/seam_check/run_or_default_probe.py`
- `tests/seam_check/run_ref_probe.py`
- `tests/suite_control_backfill_probe.py`
- `tests/write_readback_shape_probe.py`

## The auditor-scope half

**Nothing in this list is under `.claude/skills/sairn-hover-auditor/`**, so
no failure routes to H1 or H2 from this sweep. Checked rather than assumed:
`discover()` walks `tests/` and `api/` only.

