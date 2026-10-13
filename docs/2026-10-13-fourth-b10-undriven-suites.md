# ROUTED - the 36 registered red suites that have NEVER been driven - 2026-10-13

**GENERATED, not typed.** Produced by `scratchpad/gen_undriven_doc.py` from
three inputs, two of them embedded verbatim below so every figure here can be
re-derived without trusting this page: `scratchpad/undriven.txt` (the derived
list), `scratchpad/owner_map.log` (the derived totals) and the committed
`docs/2026-10-13-fourth-b10-red-suite-owners.tsv`.

**The generator REFUSES to write this file if the list and the TSV disagree.**
It asserts the two name sets are identical before emitting a line, so a stale
input cannot produce a confident page. That assertion is the only reason this
document is worth more than the sentence it replaces.

**The command that produced every count below:**

    python scratchpad/gen_undriven_doc.py

---

## THE ASSIGNMENT

| owner | directory | entries | NEVER DRIVEN |
|---|---|---:|---:|
| **hank** | `api/` | **5** | **0** |
| **cody** | `tests/` | **79** | **36** |
| **cc** | `tools/` | **0** | **0** |
| **fourth** | `docs/` | **0** | **0** |
| | **total** | **84** | **36** |

**cc and fourth are zero, and that is a measurement rather than an empty
section.** No registered red suite lives under `tools/` or `docs/`. It is NOT
a statement that those directories are healthy - it is a statement about what
this register covers, and a suite nobody has ever driven cannot be red in it.

**NOT-RUN IS NOT RED AND IT IS NOT GREEN.** Every suite in the first table
below is in the register because something once failed, and none has been
driven since - so the honest label is the third state. A sweep reporting them
as still-red would be claiming a measurement nobody took.

---

## cody - 36 suites, ALL under `tests/`, none ever driven

| # | suite | diagnosed | cause tag | since |
|---:|---|---|---|---|
| 1 | `tests/run_index_duplicate_probe.py` | yes | - | 2026-10-06 |
| 2 | `tests/run_nhi_clone_enumeration_probe.py` | yes | - | 2026-10-06 |
| 3 | `tests/run_nhi_register_write_flag_probe.py` | yes | implementation/cli-contract/report-only-mode-missing | 2026-10-06 |
| 4 | `tests/run_rebase_resolve_probe.py` | yes | implementation/classifier/source-reported-as-generated | 2026-10-06 |
| 5 | `tests/run_removal_path_probe.py` | yes | - | 2026-10-06 |
| 6 | `tests/run_report_only_checks_probe.py` | yes | - | 2026-10-06 |
| 7 | `tests/run_rewrite_convergence_probe.py` | NO | - | 2026-10-06 |
| 8 | `tests/run_role_gate_negative_coverage_probe.py` | NO | - | 2026-10-06 |
| 9 | `tests/run_secrets_inventory_probe.py` | yes | - | 2026-09-16 |
| 10 | `tests/run_selftest_independence_probe.py` | NO | - | 2026-10-12 |
| 11 | `tests/run_selftest_sweep_probe.py` | yes | - | 2026-09-16 |
| 12 | `tests/run_stored_data_criticality_probe.py` | yes | implementation/parsing/escaped-delimiter | 2026-10-06 |
| 13 | `tests/run_subprocess_decode_probe.py` | yes | - | 2026-10-06 |
| 14 | `tests/run_tool_selftest_probe.py` | yes | - | 2026-09-16 |
| 15 | `tests/run_truthy_sum_probe.py` | yes | - | 2026-10-06 |
| 16 | `tests/run_two_axis_tier_parser_probe.py` | yes | - | 2026-10-06 |
| 17 | `tests/run_write_path_scan_probe.py` | yes | - | 2026-10-06 |
| 18 | `tests/sairncare/test-compliance-rules.js` | yes | test-design/oracle-selection/hardcoded-cardinality | 2026-10-06 |
| 19 | `tests/sairncare/test-op-audit.js` | yes | test-design/fixture/mock-drifted-from-handler | 2026-10-06 |
| 20 | `tests/sairnfreedom_auth_review_probe.js` | NO | - | 2026-10-06 |
| 21 | `tests/sairnfreedom_fault_probe.py` | yes | test-design/dependency/chained-red-baseline | 2026-10-06 |
| 22 | `tests/sairnfreedom_segregation_of_duties.js` | yes | implementation/ui-claim/limitation-no-longer-true | 2026-10-06 |
| 23 | `tests/sairnfreedom_server_backup.js` | yes | test-design/oracle-selection/hardcoded-cardinality | 2026-10-06 |
| 24 | `tests/sairnfreedom_server_backup_probe.py` | yes | test-design/oracle-selection/live-suite-as-baseline | 2026-10-06 |
| 25 | `tests/sairnlegacy_fault_probe.py` | yes | test-design/exit-code/could-not-run-as-failure | 2026-10-06 |
| 26 | `tests/sairnlegacy_reservation_lock.js` | yes | implementation/role-gate/allow-list-excludes-the-caller | 2026-10-06 |
| 27 | `tests/schema_provisioning_probe.py` | yes | test-design/oracle-selection/hardcoded-count-on-live-schema | 2026-10-06 |
| 28 | `tests/scp_quotes_review_probe.js` | NO | - | 2026-10-06 |
| 29 | `tests/sd_tax_money_coercion.js` | NO | - | 2026-10-12 |
| 30 | `tests/seam_check/run_delegation_probe.py` | NO | - | 2026-10-12 |
| 31 | `tests/seam_check/run_delegation_residue_control.py` | NO | - | 2026-10-12 |
| 32 | `tests/seam_check/run_or_default_probe.py` | yes | tooling/third-state/could-not-tell-where-clean-expected | 2026-10-06 |
| 33 | `tests/seam_check/run_ref_probe.py` | yes | test-design/dependency/chained-red-baseline | 2026-10-06 |
| 34 | `tests/sql_preflight/run_probe.py` | yes | - | 2026-09-16 |
| 35 | `tests/suite_control_backfill_probe.py` | yes | - | 2026-09-16 |
| 36 | `tests/write_readback_shape_probe.py` | yes | test-design/oracle-selection/hardcoded-cardinality | 2026-10-06 |

### EXACT NEXT STEP for cody

**Drive them in a WORKTREE, not the live clone.** Several of these write when
run; that is what the isolated-worktree discipline exists for, and a sweep
that mutates the tree it is measuring produces a result nobody can attribute.

**The ceiling is why b9 and b10 both stopped short rather than half-sweeping:**
180s per suite x 36 is up to 1.8 hours. b9 chose a stated denominator over a
partial sweep reported as a whole one, which is the exact shape
`docs/known-red-suites.json` exists to prevent.

One JSON record per suite, with its REAL exit code and the tail it printed,
then:

* **exit 0 -> move the entry OUT of `entries`.** The register says why in its
  own words: an entry whose suite has gone green *"swallows the next real
  failure of that file"*.
* **exit 2, exit 3 or a timeout -> LEAVE IT IN PLACE.** b9 found 5 in that
  third state and left all 5, because moving one would quietly declare a red
  suite fixed.
* **exit 1 -> fill in `why` if it is blank.** 21 of the 84 register entries
  carry no `why` at all, and the register's own rule is that a blank is a
  backlog rather than a shrug.

---

## hank - 5 suites under `api/`, all of them already driven

**None of hank's is in the undriven set.** All 5 were driven alone in b9 and
came back with a real exit code, so these are **confirmed red at that HEAD**
rather than stale rows.

| # | suite | b9 state | b9 exit | diagnosed |
|---:|---|---|---|---|
| 1 | `api/sd-data-cross-tenant-dispatchers.test.js` | RED | 1 | NO |
| 2 | `api/sd-data-customer-soft-delete.test.js` | RED | 1 | yes |
| 3 | `api/sd-data-family-contacts.test.js` | RED | 1 | yes |
| 4 | `api/sd-data-scp-licence-only.test.js` | RED | 1 | yes |
| 5 | `api/sf-auth.test.js` | RED | 1 | yes |

### EXACT NEXT STEP for hank

These are `*.test.js` under `api/`, so they are a node-runner question rather
than a Python one: `node <file>`, compare against the `tail` field the register
already stores, then either fix or write the `why`.

---

## THE INPUTS, VERBATIM

### `scratchpad/owner_map.log` - the derived totals

```
TOTAL entries      : 84
by owner           : {'hank': 5, 'cody': 79}
UNDRIVEN           : 36
undriven by owner  : {'cody': 36}
undiagnosed (no why): 21
driven in b9       : 48
b9 states          : {'RED': 43, 'COULD NOT RUN': 5}
wrote docs/2026-10-13-fourth-b10-red-suite-owners.tsv
```

### `scratchpad/undriven.txt` - the derived list, with its own derivation at the top

```
register entries   : 84
driven in b9 (log) : 50
UNDRIVEN           : 36
by top directory   : {'tests': 36}

tests/run_index_duplicate_probe.py
tests/run_nhi_clone_enumeration_probe.py
tests/run_nhi_register_write_flag_probe.py
tests/run_rebase_resolve_probe.py
tests/run_removal_path_probe.py
tests/run_report_only_checks_probe.py
tests/run_rewrite_convergence_probe.py
tests/run_role_gate_negative_coverage_probe.py
tests/run_secrets_inventory_probe.py
tests/run_selftest_independence_probe.py
tests/run_selftest_sweep_probe.py
tests/run_stored_data_criticality_probe.py
tests/run_subprocess_decode_probe.py
tests/run_tool_selftest_probe.py
tests/run_truthy_sum_probe.py
tests/run_two_axis_tier_parser_probe.py
tests/run_write_path_scan_probe.py
tests/sairncare/test-compliance-rules.js
tests/sairncare/test-op-audit.js
tests/sairnfreedom_auth_review_probe.js
tests/sairnfreedom_fault_probe.py
tests/sairnfreedom_segregation_of_duties.js
tests/sairnfreedom_server_backup.js
tests/sairnfreedom_server_backup_probe.py
tests/sairnlegacy_fault_probe.py
tests/sairnlegacy_reservation_lock.js
tests/schema_provisioning_probe.py
tests/scp_quotes_review_probe.js
tests/sd_tax_money_coercion.js
tests/seam_check/run_delegation_probe.py
tests/seam_check/run_delegation_residue_control.py
tests/seam_check/run_or_default_probe.py
tests/seam_check/run_ref_probe.py
tests/sql_preflight/run_probe.py
tests/suite_control_backfill_probe.py
tests/write_readback_shape_probe.py
```

---

## WHAT THIS DOES NOT CLAIM

* **The owner column is a PATH, not a judgement about the failure's subject.**
  A `tests/` suite whose real defect is in `api/` is still cody's ROW and
  hank's FIX, and those are different questions.
* **Nothing here was re-driven.** Every state is either b9's measurement, read
  from the TSV, or an explicit blank.
* **It does not cover suites that are red and UNREGISTERED.** The subject is
  this register's list, not a fresh census - which is why a "NEW" count from
  this pass would be meaningless.
* **The 36 is a count of ROWS WITH NO LOG RECORD, not of suites proven to
  exist.** A register entry naming a file that has since been deleted would
  appear here too; nothing in this pass stats the paths.
