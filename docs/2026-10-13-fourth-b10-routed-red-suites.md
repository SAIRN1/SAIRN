# ROUTED — the registered red suites, assigned by directory — 2026-10-13, fourth b10

**The map is `docs/2026-10-13-fourth-b10-red-suite-owners.tsv`, 84 rows, one per
register entry, GENERATED rather than typed.** The owner column is the directory
rule applied to each suite's own path — `api/` hank, `tests/` cody, `tools/` cc,
`docs/` fourth — and the driven/undriven column comes from the b9 sweep log
rather than from any sentence about it.

---

## FIRST: THE NUMBER IN MY OWN b9 DIGEST WAS WRONG, AND THIS IS THE CORRECTION

My b9 digest and handoff said **65 suites unqueued**. **The measured figure is
36.** Re-derived here rather than quoted, which is the only reason it was found:

```
docs/known-red-suites.json entries        84
files with a record in drive_red86.jsonl  50   (43 RED, 5 COULD NOT RUN, 2 GREEN)
  of those, still in the register         48   (the 2 GREEN were moved out in b9)
UNDRIVEN = 84 - 48                        36
```

**WHERE 65 CAME FROM, because the mechanism matters more than the digit.** The
register's own `_b9_census_2026_10_13` marker says *"20 of the 86 entries ... were
driven ALONE"*, and `86 - 20 = 66`; the digest then carried 65. **Its own
authority log has 50 records.** The census sentence was drafted while the sweep
was still running and was never re-derived against the log it names as the
authority — and the marker says so in as many words: *"THE SWEEP LOG IS THE
AUTHORITY, not this sentence."* It was right about where to look and wrong about
the number, and nothing re-read it.

**This is RULE E failing inside the paragraph that states RULE E's own
principle.** The census marker in `docs/known-red-suites.json` has been corrected
in this batch, with the old figure left visible rather than overwritten, because
a number that was published needs a correction and not a silent edit.

---

## THE ASSIGNMENT

| owner | directory | entries | of those UNDRIVEN in b9 |
|---|---|---:|---:|
| **hank** | `api/` | **5** | 0 |
| **cody** | `tests/` | **79** | **36** |
| **cc** | `tools/` | **0** | 0 |
| **fourth** | `docs/` | **0** | 0 |

**cc and I get nothing, and that is stated rather than left as an empty section.**
No registered red suite lives under `tools/` or `docs/`. An assignment table with
two owners silently absent reads as an oversight; this one is a measurement.

**cc's red-suite load being zero is NOT a statement that `tools/` is healthy** —
it is a statement about what this register covers. The register's own
`_scope_limit_2026_10_06` governs that, and a suite nobody has ever driven cannot
be red here.

---

## hank — 5 entries, all under `api/`, none undriven

All five were driven alone in b9 and came back with a real exit code, so these
are **confirmed red at that HEAD**, not stale rows.

| suite | b9 driven | b9 state | diagnosed | cause tag |
|---|---|---|---|---|
| `api/sd-data-cross-tenant-dispatchers.test.js` | yes | RED | NO | — |
| `api/sd-data-customer-soft-delete.test.js` | yes | RED | yes | — |
| `api/sd-data-family-contacts.test.js` | yes | RED | yes | — |
| `api/sd-data-scp-licence-only.test.js` | yes | RED | yes | — |
| `api/sf-auth.test.js` | yes | RED | yes | — |

**Exact next step:** these are `*.test.js` under `api/`, so they are a
`node --test` / node runner question rather than a Python one. Drive each alone
(`node <file>`), compare against the `tail` field the register already stores,
and either fix or write the `why` — **21 of the 84 entries platform-wide carry no
`why` at all**, and the register's own rule is that a blank is a backlog rather
than a shrug.

---

## cody — 79 entries under `tests/`, of which 36 were NEVER DRIVEN

### The 36 undriven — not re-verified by any pass, so their state is UNKNOWN rather than red

**NOT-RUN IS NOT RED AND IT IS NOT GREEN.** Each of these is in the register
because something once failed; none of them has been driven since, so the honest
label is the third state. A sweep that reported them as still-red would be
claiming a measurement nobody took.

| suite | diagnosed | cause tag |
|---|---|---|
| `tests/run_index_duplicate_probe.py` | yes | — |
| `tests/run_nhi_clone_enumeration_probe.py` | yes | — |
| `tests/run_nhi_register_write_flag_probe.py` | yes | implementation/cli-contract/report-only-mode-missing |
| `tests/run_rebase_resolve_probe.py` | yes | implementation/classifier/source-reported-as-generated |
| `tests/run_removal_path_probe.py` | yes | — |
| `tests/run_report_only_checks_probe.py` | yes | — |
| `tests/run_rewrite_convergence_probe.py` | NO | — |
| `tests/run_role_gate_negative_coverage_probe.py` | NO | — |
| `tests/run_secrets_inventory_probe.py` | yes | — |
| `tests/run_selftest_independence_probe.py` | NO | — |
| `tests/run_selftest_sweep_probe.py` | yes | — |
| `tests/run_stored_data_criticality_probe.py` | yes | implementation/parsing/escaped-delimiter |
| `tests/run_subprocess_decode_probe.py` | yes | — |
| `tests/run_tool_selftest_probe.py` | yes | — |
| `tests/run_truthy_sum_probe.py` | yes | — |
| `tests/run_two_axis_tier_parser_probe.py` | yes | — |
| `tests/run_write_path_scan_probe.py` | yes | — |
| `tests/sairncare/test-compliance-rules.js` | yes | test-design/oracle-selection/hardcoded-cardinality |
| `tests/sairncare/test-op-audit.js` | yes | test-design/fixture/mock-drifted-from-handler |
| `tests/sairnfreedom_auth_review_probe.js` | NO | — |
| `tests/sairnfreedom_fault_probe.py` | yes | test-design/dependency/chained-red-baseline |
| `tests/sairnfreedom_segregation_of_duties.js` | yes | implementation/ui-claim/limitation-no-longer-true |
| `tests/sairnfreedom_server_backup.js` | yes | test-design/oracle-selection/hardcoded-cardinality |
| `tests/sairnfreedom_server_backup_probe.py` | yes | test-design/oracle-selection/live-suite-as-baseline |
| `tests/sairnlegacy_fault_probe.py` | yes | test-design/exit-code/could-not-run-as-failure |
| `tests/sairnlegacy_reservation_lock.js` | yes | implementation/role-gate/allow-list-excludes-the-caller |
| `tests/schema_provisioning_probe.py` | yes | test-design/oracle-selection/hardcoded-count-on-live-schema |
| `tests/scp_quotes_review_probe.js` | NO | — |
| `tests/sd_tax_money_coercion.js` | NO | — |
| `tests/seam_check/run_delegation_probe.py` | NO | — |
| `tests/seam_check/run_delegation_residue_control.py` | NO | — |
| `tests/seam_check/run_or_default_probe.py` | yes | tooling/third-state/could-not-tell-where-clean-expected |
| `tests/seam_check/run_ref_probe.py` | yes | test-design/dependency/chained-red-baseline |
| `tests/sql_preflight/run_probe.py` | yes | — |
| `tests/suite_control_backfill_probe.py` | yes | — |
| `tests/write_readback_shape_probe.py` | yes | test-design/oracle-selection/hardcoded-cardinality |

**Exact next step, and the ceiling is the reason it was not done in b9:** 180s
per suite × 36 is up to 1.8 hours, which is why b9 stopped and stated a
denominator instead of consuming the batch. Drive them **in a worktree, not the
live clone** — several of these write when run, which is what
`sweep-runner`-style isolation exists for — one JSON record per suite with its
real exit code and tail, then:

* **exit 0 → move the entry OUT of `entries`.** The register's own rule: an entry
  whose suite has gone green *"swallows the next real failure of that file"*.
* **exit 2, exit 3 or a timeout → LEAVE IT IN PLACE.** b9 found 5 in that state
  and left all 5, because moving one would quietly declare a red suite fixed.
* **exit 1 → fill in `why` if it is blank.**

### The 43 already driven in b9 — confirmed red or confirmed could-not-run

| suite | b9 state | b9 exit | diagnosed |
|---|---|---|---|
| `tests/app_session_isolation.js` | RED | 1 | NO |
| `tests/claims/run_claim_retype_mutation_control.py` | RED | 2 | yes |
| `tests/claims/run_push_verify_probe.py` | RED | 1 | yes |
| `tests/claims/run_registry_claim_probe.py` | RED | 1 | NO |
| `tests/claims/run_registry_claim_sabotage_probe.py` | RED | 2 | yes |
| `tests/defect_register_capa_control.py` | RED | 1 | yes |
| `tests/faults/transport_timeout_sweep.js` | RED | 1 | NO |
| `tests/hover_quotable_session_vocab_check.py` | RED | 1 | yes |
| `tests/install_git_hooks_check_probe.py` | COULD NOT RUN | None | yes |
| `tests/law_reconcile_role_vocab_check.py` | RED | 2 | yes |
| `tests/law_reconcile_role_vocab_control.py` | RED | 1 | yes |
| `tests/local_only_self_evidence_probe.py` | RED | 1 | yes |
| `tests/local_only_shape_probe.py` | RED | 1 | yes |
| `tests/push_gate/check12_probe.py` | COULD NOT RUN | None | yes |
| `tests/push_gate/check8_probe.py` | COULD NOT RUN | None | yes |
| `tests/push_gate/check9_probe.py` | RED | 3 | yes |
| `tests/push_gate/preauth_exemption_anchor_probe.py` | RED | 1 | yes |
| `tests/push_gate/refspec_and_override_probe.py` | COULD NOT RUN | None | NO |
| `tests/rebase_resolve_merge_control.py` | RED | 1 | yes |
| `tests/run_adversarial_prompt_corpus_probe.py` | RED | 1 | yes |
| `tests/run_alf_read_order_sabotage_probe.py` | RED | 1 | NO |
| `tests/run_all_tests_floor_probe.py` | RED | 1 | NO |
| `tests/run_all_tests_pinned_probe.py` | RED | 1 | NO |
| `tests/run_baseline_readiness_probe.py` | RED | 1 | yes |
| `tests/run_blob_coverage_scope_sabotage.py` | RED | 1 | NO |
| `tests/run_checker_control_probe.py` | RED | 1 | yes |
| `tests/run_citation_anchor_hop_sabotage.py` | RED | 1 | NO |
| `tests/run_committer_identity_probe.py` | RED | 1 | NO |
| `tests/run_completeness_probe.py` | RED | 1 | yes |
| `tests/run_concurrency_retry_probe.py` | RED | 1 | yes |
| `tests/run_condition_coverage_probe.py` | RED | 1 | yes |
| `tests/run_copy_exactly_gate_probe.py` | RED | 1 | yes |
| `tests/run_cron_liveness_probe.py` | RED | 1 | NO |
| `tests/run_defect_dispersion_probe.py` | RED | 1 | yes |
| `tests/run_dependency_graph_probe.py` | RED | 1 | yes |
| `tests/run_dispatch_state_probe.py` | RED | 1 | yes |
| `tests/run_eaten_substitution_probe.py` | RED | 1 | yes |
| `tests/run_export_coverage_probe.py` | RED | 1 | yes |
| `tests/run_financial_invariant_probe.py` | RED | 1 | yes |
| `tests/run_first_article_probe.py` | RED | 1 | yes |
| `tests/run_githook_install_probe.py` | COULD NOT RUN | None | yes |
| `tests/run_graduated_exemption_probe.py` | RED | 1 | NO |
| `tests/run_harness_stage_diagnosis_probe.py` | RED | 1 | yes |

**Exact next step:** the 5 `COULD NOT RUN` rows are the sharp end, not the 38
reds — a suite that cannot run is a suite whose verdict nobody has, and it will
read as "still red" for ever without anybody noticing it never executed.

---

## WHAT THIS ROUTING DOES NOT CLAIM

* **It does not decide whether an entry is still a real defect.** The owner
  column is a path, not a judgement about the failure's subject. The register's
  `owner` field was `"unassigned"` on all 84 rows and is now set from this rule,
  with the basis recorded in the file so nobody reads it as an investigation.
* **It does not re-drive anything.** Every state in the map is either b9's
  measurement or an explicit blank.
* **It does not cover suites that are red and unregistered.** The subject here is
  the register's list, not a fresh census — the same limit b9 recorded, and the
  reason a "NEW" count from this pass would be meaningless.
