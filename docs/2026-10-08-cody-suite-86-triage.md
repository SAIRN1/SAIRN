# The 86 pinned-suite failures, triaged one by one — 2026-10-08 (cody)

**batch 26 item 2.** The suite run that produced them: `--pinned` at `aa2f014dd21b088711944b5675104471c43b0502`, started 2026-10-08T00:08:09Z, `EXIT 1` at 03:21:50Z, 759 files, 671 ok, **86 FAIL**, and one residue path (`M docs/report-only-reachability.json`).

## THE HYPOTHESIS IS OVERTURNED. The contamination explains **3 of 86**.

The question was whether these were artifacts of the dirtied tree. They are not.

```
method  : re-run EVERY ONE alone, in a `git clone --local` at the SAME commit
          the suite ran, which is clean by construction. 420s bound each.
commit  : ae70cf24        date: 2026-10-08
verdict rule, fixed BEFORE the run so it could not be fitted afterwards:
  REAL          -- fails alone on a clean tree at the same commit
  ARTIFACT      -- passes alone (the suite-run failure was not reproducible)
  COULD-NOT-RUN -- exits 2, times out, or will not launch; never folded into either

  REAL            76 of 86
  COULD-NOT-RUN    7 of 86
  ARTIFACT         3 of 86
```

**So 76 of 86 are real defects in the suite, not collateral.** The three artifacts are the only ones the residue hypothesis accounts for, and even they are "not reproducible in isolation" rather than proven contaminated — the weaker of the two claims, and the one the evidence supports.

**AND THE CLEAN CLONE STAYED CLEAN: `git status --porcelain` was taken after **every** probe, and 0 of 86 dirtied it.** Where one did, the tree was restored before the next, so no probe inherited another's mess — which is exactly what the whole-tree run could not do.

## THE THREE ARTIFACTS

| probe | kind | alone | in the suite run |
|---|---|---|---|
| `tests/sairncare/test-alf-alerts-endpoint.js` | node | **rc 0** | 19 passed, 1 failed |
| `tests/run_push_gate_preflight_probe.py` | py | **rc 0** | ok   P6. preflight reads the OUTGOING range like a real push, not the  |
| `tests/stale_row_sweep_control.py` | py | **rc 0** | ...and NAMES 1348466a, the finally fix |

## THE SEVEN COULD-NOT-RUN — not a pass and not a failure

| probe | rc | seconds | in the suite run |
|---|---|---|---|
| `tests/app_session_isolation_probe.py` | 2 | 21 | COULD NOT RUN: the pre-fix suite is not green against curren |
| `tests/law_reconcile_role_vocab_check.py` | 2 | 0 | This is exit 2. Nothing was checked, and that is not a pass. |
| `tests/run_cross_tenant_dispatchers_sabotage_probe.py` | 2 | 4 | 405 passed, 14 failed |
| `tests/run_hover_audit_method_sabotage_probe.py` | TIMEOUT | 420 | The baseline is red, so no mutation below would mean anythin |
| `tests/sairnfreedom_server_backup_probe.py` | 2 | 7 | The baseline is red, so no mutation below would mean anythin |
| `tests/claims/run_claim_retype_mutation_control.py` | 2 | 38 | 3 passed, 2 failed |
| `tests/claims/run_registry_claim_sabotage_probe.py` | 2 | 10 | The baseline is red, so no mutation below would mean anythin |

## THE 76 REAL ONES

Each **failed alone, on a clean tree, at the same commit**. `rc` is the process exit code from the isolated run; the last column is the one-line reason the suite printed, kept so the two can be compared.

| probe | kind | rc | s | suite reason |
|---|---|---|---|---|
| `api/sd-data-cross-tenant-dispatchers.test.js` | node | 1 | 3 | 405 passed, 14 failed |
| `api/sd-data-customer-soft-delete.test.js` | node | 1 | 0 | 5 passed |
| `api/sd-data-family-contacts.test.js` | node | 1 | 0 | FAILURES ABOVE |
| `api/sd-data-scp-licence-only.test.js` | node | 1 | 0 | 23 passed, 1 failed |
| `api/sf-auth.test.js` | node | 1 | 4 | 37 passed, 1 failed |
| `tests/app_session_isolation.js` | node | 1 | 2 | ok   sairnscape: measured SOME, recorded SOME -- GAP CLOSED 2026-09-25 ( |
| `tests/claims/run_push_verify_probe.py` | py | 1 | 34 | 68 passed, 1 failed |
| `tests/claims/run_registry_claim_probe.py` | py | 1 | 4 | - end to end: a registry claim whose PROCESS IS GONE does not block, how |
| `tests/defect_register_capa_control.py` | py | 1 | 0 | ok   malformed JSON is refused rather than stored as a string |
| `tests/faults/sd_write_faults.js` | node | 1 | 0 | 7 passed, 11 FAILED |
| `tests/faults/transport_timeout_sweep.js` | node | 1 | 1 | 77 passed, 4 FAILED |
| `tests/hover_quotable_session_vocab_check.py` | py | 1 | 0 | have gone unnoticed. Add the name to QUOTABLE. |
| `tests/hover_separation_ci_probe.py` | py | 1 | 3 | audit = set(A.AUDITOR_SCOPE) |
| `tests/install_git_hooks_check_probe.py` | py | 1 | 257 | 2 ARM(S) FAILED |
| `tests/law_reconcile_role_vocab_control.py` | py | 1 | 0 | CRITERIA LOCKED BEFORE THE REAL RUN |
| `tests/local_only_self_evidence_probe.py` | py | 1 | 22 | 1 ARM(S) FAILED |
| `tests/local_only_shape_probe.py` | py | 1 | 20 | 2 ARM(S) FAILED |
| `tests/push_gate/check4_probe.py` | py | 1 | 7 | FAILED TWICE, the second time on its own: CHECK 4 VERIFIED (planted bloc |
| `tests/push_gate/check7_probe.py` | py | 1 | 8 | FAILED TWICE, the second time on its own: FAILED  check7_probe: 11 check |
| `tests/push_gate/preauth_exemption_anchor_probe.py` | py | 1 | 1 | FAILED  preauth_exemption_anchor_probe: 1 failed |
| `tests/rebase_resolve_merge_control.py` | py | 1 | 2 | a1_clean_append |
| `tests/run_adversarial_prompt_corpus_probe.py` | py | 1 | 3 | 3 arm(s) FAILED: 4. the sweep runs and classifies: zero unfenced, 5 repo |
| `tests/run_alf_read_order_sabotage_probe.py` | py | 1 | 8 | - 5. THE FIX IS STILL THERE BUT THE ARM CAN NO LONGER SEE IT: the alf_ma |
| `tests/run_all_tests_floor_probe.py` | py | 1 | 0 | 2. _main_body() -- THE COPY A HUMAN RUNS |
| `tests/run_all_tests_pinned_probe.py` | py | 1 | 32 | Nothing don |
| `tests/run_baseline_readiness_probe.py` | py | 1 | 1 | - ...and says NO ENTITY IS READY rather than printing a table and stoppi |
| `tests/run_blob_coverage_scope_sabotage.py` | py | 1 | 0 | FAIL -- 3 passed, 2 failed |
| `tests/run_checker_control_probe.py` | py | 1 | 11 | EVERY CONTROLS_FOR under tests/ parses to a subject (these declare nothi |
| `tests/run_citation_anchor_hop_sabotage.py` | py | 1 | 0 | FAIL -- 2 passed, 4 failed |
| `tests/run_completeness_probe.py` | py | 1 | 6 | 6b  ...and the finding it exits 1 for is the real one, not any line that |
| `tests/run_concurrency_retry_probe.py` | py | 1 | 0 | B. the retry is driven with synthetic files, not the real three |
| `tests/run_condition_coverage_probe.py` | py | 1 | 29 | 5. THE PLANTED GAP -- it must find an operand no test covers |
| `tests/run_copy_exactly_gate_probe.py` | py | 1 | 5 | 0 passed, 1 failed |
| `tests/run_cron_liveness_probe.py` | py | 1 | 5 | FAILED: the pre-change workflow had NO commit step -- only the artifact  |
| `tests/run_defect_dispersion_probe.py` | py | 1 | 1 | ok   layer has a population of exactly three |
| `tests/run_defect_register_probe.py` | py | 1 | 365 | defect-register: 149 checks, 2 failed |
| `tests/run_dependency_graph_probe.py` | py | 1 | 17 | 7q  a PAST-DUE date prints REVIEW DUE and does NOT fail -- failing a pus |
| `tests/run_dispatch_state_probe.py` | py | 1 | 4 | FAILED: ...and NO subprocess.run, so it never invokes sairn_claim.py to  |
| `tests/run_eaten_substitution_probe.py` | py | 1 | 1 | eaten_substitution_check: 2 ARM(S) FAILED |
| `tests/run_export_coverage_probe.py` | py | 1 | 0 | - sairnmechanical declares mech_credentials in its registry, and it reso |
| `tests/run_financial_invariant_probe.py` | py | 1 | 2 | 7f  a judgment for a file the checker no longer flags is called out as s |
| `tests/run_first_article_probe.py` | py | 1 | 80 | - NO RECORDED INSPECTION is stale, incomplete, or cites an arm that does |
| `tests/run_ghost_field_read_probe.py` | py | 1 | 89 | 11 passed, 5 failed |
| `tests/run_githook_install_probe.py` | py | 1 | 83 | - --check passes once the clone is really installed |
| `tests/run_graduated_exemption_probe.py` | py | 1 | 1 | - ...proven: the third push is refused again |
| `tests/run_harness_stage_diagnosis_probe.py` | py | 1 | 8 | 1 failure(s) |
| `tests/run_index_duplicate_probe.py` | py | 1 | 64 | 7a  the real index has no undeclared duplicate pairs |
| `tests/run_nhi_clone_enumeration_probe.py` | py | 1 | 2 | 4 passed, 4 failed |
| `tests/run_nhi_register_write_flag_probe.py` | py | 1 | 10 | 4 passed, 8 failed |
| `tests/run_rebase_resolve_probe.py` | py | 1 | 34 | - ...and says nothing was staged |
| `tests/run_removal_path_probe.py` | py | 1 | 5 | 1 FAILED |
| `tests/run_rewrite_convergence_probe.py` | py | 1 | 32 | FAILED: E1 --derive: nothing is derived that is neither declared nor exe |
| `tests/run_role_gate_negative_coverage_probe.py` | py | 1 | 6 | FAILED  run_role_gate_negative_coverage_probe: 4 failed |
| `tests/run_secrets_inventory_probe.py` | py | 1 | 10 | 6c  SILENT: against the real committed document the same entry point exi |
| `tests/run_selftest_sweep_probe.py` | py | 1 | 234 | - subprocess_decode_check.py --selftest exits 0 |
| `tests/run_stored_data_criticality_probe.py` | py | 1 | 8 | 2 ARM(S) FAILED: an ESCAPED pipe inside a cell is content, not a boundar |
| `tests/run_subprocess_decode_probe.py` | py | 1 | 6 | - zero text-mode subprocess calls without an explicit encoding |
| `tests/run_tool_selftest_probe.py` | py | 1 | 173 | FAILING (1): hover_separation_ci.py |
| `tests/run_two_axis_tier_parser_probe.py` | py | 1 | 1 | - 2. the NEW six-cell shape parses, raises no row-level problem, and cou |
| `tests/run_write_path_scan_probe.py` | py | 1 | 34 | 1 ARM(S) FAILED: the shipped baseline PASSES today -- a ratchet that fai |
| `tests/sairncare/test-compliance-rules.js` | node | 1 | 0 | 47 passed, 3 failed |
| `tests/sairncare/test-op-audit.js` | node | 1 | 0 | 12 passed, 14 failed |
| `tests/sairnfreedom_auth_review_probe.js` | node | 1 | 1 | ? 15:11 (2) -- the sf-auth setup guard anchor has moved -- this arm is n |
| `tests/sairnfreedom_fault_probe.py` | py | 1 | 7 | FAILED  sairnfreedom_fault_probe: 1 failed |
| `tests/sairnfreedom_segregation_of_duties.js` | node | 1 | 0 | FAIL -- 25 passed, 1 failed |
| `tests/sairnfreedom_server_backup.js` | node | 1 | 0 | FAILED  sairnfreedom_server_backup: 16 passed, 1 failed |
| `tests/sairnlegacy_fault_probe.py` | py | 1 | 9 | The baseline is red, so no mutation below would mean anything. Stopping. |
| `tests/sairnlegacy_reservation_lock.js` | node | 1 | 0 | 1. reserving is an atomic conditional PATCH, not a read-then-write |
| `tests/schema_provisioning_probe.py` | py | 1 | 1 | 3 ARM(S) FAILED |
| `tests/scp_quotes_review_probe.js` | node | 1 | 0 | NOT REPRODUCED -- this finding appears to be closed. |
| `tests/sd_tax_money_coercion.js` | node | 1 | 0 | 12 passed, 1 failed |
| `tests/seam_check/run_or_default_probe.py` | py | 1 | 46 | 2 ARM(S) FAILED |
| `tests/seam_check/run_ref_probe.py` | py | 1 | 75 | 3 ARM(S) FAILED |
| `tests/sql_preflight/run_probe.py` | py | 1 | 5 | sairn_circuit_breaker_schema.sql: UNDECLARED_TABLE sairn_circuit_breaker |
| `tests/suite_control_backfill_probe.py` | py | 1 | 16 | CONTROLS THAT DID NOT BITE: ['2. a failed read is treated as an empty on |
| `tests/write_readback_shape_probe.py` | py | 1 | 75 | 2 ARM(S) FAILED |

## SLOWEST IN ISOLATION, which is a different question from the suite

| probe | seconds alone |
|---|---|
| `tests/run_hover_audit_method_sabotage_probe.py` | 420 |
| `tests/stale_row_sweep_control.py` | 408 |
| `tests/run_defect_register_probe.py` | 365 |
| `tests/install_git_hooks_check_probe.py` | 257 |
| `tests/run_selftest_sweep_probe.py` | 234 |
| `tests/run_tool_selftest_probe.py` | 173 |
| `tests/run_ghost_field_read_probe.py` | 89 |
| `tests/run_githook_install_probe.py` | 83 |

**420 s IS THE BOUND, NOT A MEASUREMENT, and the distinction matters here.** `tests/run_hover_audit_method_sabotage_probe.py` is the **only** probe of the 86 that hit the 420 s ceiling, so its isolated runtime is **at least** 420 s and is unknown above that — it is recorded COULD-NOT-RUN rather than REAL for exactly that reason. It is now the best-evidenced candidate for the long stall (batch 22 suspected it from alphabetical adjacency; batch 23 measured 567 s for it on a different, early-exit path), but **candidate is not named**: the stall could equally sit among the 671 probes that passed, which this run did not time. `childwatch.py` — fixed, never yet run against a full suite — is the instrument that would settle it.

## WHAT THIS DOES NOT ESTABLISH

- **It does not say the 76 are 76 distinct defects.** Several share a cause; nothing here clusters them.
- **It does not say the suite run was sound.** It says the failures were not caused by the residue. The residue is still a real finding against whichever probe wrote `docs/report-only-reachability.json` mid-run.
- **A single isolated run is one run.** A flaky probe that fails alone once is recorded REAL here on that evidence; nothing was run twice.
