# The dead-rule universe is now DERIVED, and the list it replaced was hiding 352 rules

**2026-10-05 (Cody). `tools/dead_rule_sweep.py` no longer reads its population
from `report_only_checks.REGISTRY`.** It reads every tracked `tools/*.py` from
`git ls-files` and classifies each one. **Regenerate this list rather than quoting it:**

    python tools/dead_rule_sweep.py --universe

---

## THE DELTA, WHICH IS THE WHOLE REASON FOR THE CHANGE

| | files | rules |
|---|---|---|
| tracked `tools/*.py` | **295** | &mdash; |
| compile at least one module-level rule &mdash; **THE UNIVERSE** | **150** | **521** |
| &nbsp;&nbsp;of those, IN the report-only registry &mdash; *the old universe* | 45 | **169** |
| &nbsp;&nbsp;of those, **OUTSIDE it** &mdash; *invisible until today* | **105** | **352** |
| compile no module-level rule &mdash; nothing to ablate, derived | 145 | 0 |
| **exempt by declaration** | **0** | 0 |

**The sweep had been reporting on 169 of 521 rules &mdash; 32% &mdash; and printing
that figure as the platform.** Yesterday the same hole was found one name at a time:
`gap_ledger.py` was missing, the figure was corrected to "162 of 169", and two entries
were added. **That closed two names and left the mechanism.**

**NOTHING REFUSED THE OTHER 352.** They were not reachable from the only list the
sweep read, and it had no way to say so. A universe derived from a hand-maintained
list reports confidently about the part of the fleet that list happens to name.

## THE DECLARED EXEMPTION LIST IS EMPTY, AND THAT IS MEASURED, NOT AN OVERSIGHT

The first entry written into `EXEMPT` was `dead_rule_sweep.py` itself, reasoned as
*"neutralising its own rule mid-run measures the harness, not the subject"*. That
sentence is true and the exemption was **useless**: this file compiles no module-level
rule, so the mechanical branch already excluded it. The `STALE_EXEMPT` check refused
the run and named it &mdash; **on its author, within minutes of being written.**

So all 295 files are classified by a **rule**, not a judgement. If that stops being
true, the entry has to carry a reason somebody can argue with.

## `--registry-only` KEEPS THE OLD FIGURE REPRODUCIBLE

The pre-2026-10-05 population is still reachable on purpose. Two populations under
one name is how a past document becomes unquotable &mdash; three of mine already
reported this sweep without even an exit code.

## AND THE RUN IS NOW SEGMENTED, BECAUSE IT IS 3.3x LONGER

`--segment I/N` sweeps one slice and **prints that it is a slice**, so a partial run
cannot be read as the platform figure. The tenth standing convention: no long run
whose first check is at the end.

---

## THE 105 FILES THAT ENTERED THE UNIVERSE TODAY

Rule count first, as `--universe` prints them.

```
OUT_REG (105 file(s), 352 rule(s))
   21  cross_tenant_isolation_scope.py
   12  retry_policy_audit.py
   11  role_gate_negative_coverage.py
   10  confidentiality_candidate_flagger.py
    9  sairn_claim.py
    9  suite_control_coverage.py
    8  citation_no_source_report.py
    8  csv_formula_injection_check.py
    8  retry_backoff_check.py
    7  fail_open_scan.py
    7  sabotage_control_check.py
    7  sairn_stale_snapshot_scan.py
    6  numeric_default_coalesce_scan.py
    6  sairn_ai_fact_scan.py
    6  stale_row_sweep.py
    5  ai_prompt_refusal_check.py
    5  blob_overrides_column_scan.py
    5  cleanup_residue_check.py
    5  first_article_inspection.py
    5  live_probe_residue_audit.py
    5  preauth_oracle_check.py
    5  shape_antipattern_check.py
    5  sync_write_result_check.py
    5  tier_sentence_gate.py
    4  ai_output_resource_scan.py
    4  copy_exactly_gate.py
    4  cron_beat_refusal_check.py
    4  idempotency_check.py
    4  known_red_check.py
    4  live_probe_declaration_check.py
    4  local_only_collection_check.py
    4  primitive_obsession_check.py
    4  purpose_expired_measure.py
    4  rotation_blast_radius.py
    4  sairn_reachability_check.py
    4  second_pass_coverage_scan.py
    4  unreachable_failure_path_scan.py
    4  write_path_fault_scan.py
    3  adversarial_prompt_corpus.py
    3  append_only_read_order_scan.py
    3  checker_control_check.py
    3  message_assertion_audit.py
    3  missing_dom_target_check.py
    3  pinned_list_drift_check.py
    3  push_failure_reason.py
    3  rebase_state_guard.py
    3  rewrite_convergence_map.py
    3  sairn_sql_preflight.py
    3  staged_conflict_marker_check.py
    3  text_gate_literal_sweep.py
    3  tier_a_replaceability_check.py
    3  weakness_combination.py
    2  auth_header_name_sweep.py
    2  blob_conversion_coverage.py
    2  citation_line_drift_check.py
    2  coding_rule_discovery.py
    2  employee_auth_guard_check.py
    2  entitlement_freshness_check.py
    2  exit_status_attributable.py
    2  gate_caller_impact.py
    2  git_discovery_anchoring_check.py
    2  hedge_carry_check.py
    2  idempotence_double_run.py
    2  negated_status_assertion_scan.py
    2  optimistic_success_scan.py
    2  sairn_dead_function_sweep.py
    2  sairn_push_gate_hook.py
    2  sairn_rebase_resolve.py
    2  seam_cannot_tell_watch.py
    2  shape_search.py
    2  tier_a_bypass_check.py
    2  tier_a_review_gate.py
    2  va_rule_currency.py
    1  audit_licence.py
    1  bare_run_write_check.py
    1  benford_check.py
    1  checker_selftest_check.py
    1  claim_provenance.py
    1  claim_search.py
    1  dispatch_state.py
    1  fmea_draft.py
    1  fmea_prediction_check.py
    1  ghost_field_read_scan.py
    1  git_push_master_guard.py
    1  guard_ablation.py
    1  hook_integrity_check.py
    1  hover_auditor_scope_gate.py
    1  invocation_path_scan.py
    1  load_schema_snapshot.py
    1  plugin_upgrade_check.py
    1  probe_selector.py
    1  redaction_check.py
    1  register_freshness_propose.py
    1  report_only_checks.py
    1  review_ledger_reseat.py
    1  run_all_tests.py
    1  sairn_reachability_probe.py
    1  sairn_session_identity.py
    1  schema_provisioning_check.py
    1  session_recheck_coverage.py
    1  staged_credential_check.py
    1  stored_data_criticality_check.py
    1  suite_control_triage.py
    1  tool_owner_header_check.py
    1  verification_plan_staleness_check.py
```

## AND THE 45 THAT WERE ALREADY IN IT

```
IN (45 file(s), 169 rule(s))
    9  advisory_lock_isolation_check.py
    8  assertion_label_shape_check.py
    8  hover_separation_audit.py
    8  register_freshness_check.py
    7  gap_ledger.py
    7  temporary_state_check.py
    7  write_without_readback_check.py
    6  completeness_check.py
    6  dependency_graph.py
    6  export_coverage_check.py
    6  metamorphic_check.py
    6  removal_path_check.py
    6  sairn_dead_button_audit.py
    6  sairn_strict_args_check.py
    5  ai_action_approval_audit.py
    5  criticality_tier_check.py
    5  register_feed_gate.py
    4  accepted_risk_expiry_audit.py
    4  overrun_inversion_scan.py
    3  key_collision_check.py
    3  md_table_check.py
    3  service_role_tier_a_gate_check.py
    3  sql_column_exists_check.py
    3  traceability_matrix.py
    2  cleanup_confirm_check.py
    2  comment_quote_check.py
    2  committer_identity_check.py
    2  defect_register.py
    2  discarded_verdict_crossfile.py
    2  duplicate_global_check.py
    2  gate_column_check.py
    2  literal_drift_check.py
    2  master_plan.py
    2  panel_nesting_check.py
    2  schema_snapshot_freshness.py
    2  tooling_inventory.py
    2  truthy_sum_check.py
    2  verification_owed_report.py
    1  bypassed_constant_check.py
    1  claim_activity_check.py
    1  discarded_verdict_check.py
    1  eaten_substitution_check.py
    1  fail_open_check.py
    1  hover_routing_gap_check.py
    1  pattern_enumeration_sweep.py
```

---

## THE DRIFT RATE, MEASURED RATHER THAN ASSUMED

**Re-run roughly one hour after the table above, on the same machine:**

```
tracked tools/*.py   295 -> 296
THE UNIVERSE         150 -> 151   ->  521 -> 528 rule(s)
  OUTSIDE registry   105 -> 106   ->  352 -> 359 rule(s)
```

**One new file in the universe (`suite_override_consistency.py`, 2 rules) and
five more rules inside files that were already in it** — four other clones push
to this branch, so the population moves without anybody editing this document.

**That is the number to take from this section, not the totals: +7 rules in
about an hour.** The eighth standing convention asks for a re-reference cadence
taken from a *measured* drift rate, and this is the measurement. It is also why
every figure here says to run the command: a document that chased the total
would be wrong again by the time it was committed, which is exactly what
happened to "162 of 169" yesterday.

## WHAT THIS DOES NOT ESTABLISH

- **That the 352 new rules are dead, or alive.** This is the POPULATION. The ablation
  verdicts are a separate run, reported separately.
- **That 521 is every rule on the platform.** Only a module-level
  `NAME = re.compile(...)` is reachable; a rule built at runtime or compiled inside a
  function is still invisible, and `tools/*.py` is not `tests/`, `scripts/` or `api/`.
  **521 is a floor at 3.1x the old floor, not a total.**
- **That the mechanical exclusion is always right.** "Compiles no module-level rule"
  means nothing to ABLATE, not that the file carries no criteria.
