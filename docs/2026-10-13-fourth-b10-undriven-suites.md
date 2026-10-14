# ROUTED - the registered red suites that have NEVER been driven - regenerated 2026-10-14

**GENERATED, not typed.** `scratchpad/gen_undriven_b13.py`, from ONE source:
`docs/known-red-suites.json`. Re-derive rather than quoting this page.

**THIS PAGE SAID 36 UNTIL 2026-10-14 AND THE NUMBER WAS FROZEN, NOT TRUE.**
The previous generator read `scratchpad/undriven.txt` -- inside a dead
session's temp directory -- and a committed TSV, and asserted them against
each other. It therefore printed the same 36 after the tests owner drove
twelve suites on the morning of 2026-10-14. Of the original 36 names,
**29 now carry a `diagnosed` value** in the register and **7 do not**.

| | | command |
|---|---:|---|
| register entries | 85 | `len(json.load(...)["entries"])` |
| **UNDRIVEN (`diagnosed` blank)** | **20** | `[e for e in entries if not e["diagnosed"]]` |
| entries with no `why` | 18 | same shape on `why` |
| b10 TSV undriven, frozen | 36 | `awk -F$'\t' '$4=="NO"' docs/2026-10-13-fourth-b10-red-suite-owners.tsv` |
| of those, now diagnosed | 29 | by `file` join against the register |
| register last touched | `a47cdf2d 2026-10-14T06:26:21-04:00` | `git log -1 --format='%h %cI' -- docs/known-red-suites.json` |
| TSV last touched | `a149769d 2026-10-13T07:59:02-04:00` | same, on the TSV |
| generated at HEAD | `6a3e0fd5` | `git rev-parse --short=8 HEAD` |

## UNDRIVEN by owner

* **cody - 19**
* **hank - 1**

## The 20 undriven entries, in full

Each is a registered red suite whose `diagnosed` field is blank: nobody has
driven it and written down what happened. **Exit 0 moves the entry out of
`entries`; exit 1 fills in `why`; exit 2 or a timeout is COULD NOT RUN and
must NOT be recorded as either.**

* `api/sd-data-cross-tenant-dispatchers.test.js` - owner **hank**, since 2026-10-12, kind node
* `tests/app_session_isolation.js` - owner **cody**, since 2026-10-12, kind node
* `tests/claims/run_registry_claim_probe.py` - owner **cody**, since 2026-10-07, kind py
* `tests/faults/transport_timeout_sweep.js` - owner **cody**, since 2026-10-06, kind node
* `tests/push_gate/refspec_and_override_probe.py` - owner **cody**, since 2026-10-06, kind py
* `tests/run_alf_read_order_sabotage_probe.py` - owner **cody**, since 2026-10-06, kind py
* `tests/run_all_tests_floor_probe.py` - owner **cody**, since 2026-10-06, kind py
* `tests/run_all_tests_pinned_probe.py` - owner **cody**, since 2026-10-12, kind py
* `tests/run_blob_coverage_scope_sabotage.py` - owner **cody**, since 2026-10-12, kind py
* `tests/run_citation_anchor_hop_sabotage.py` - owner **cody**, since 2026-10-12, kind py
* `tests/run_committer_identity_probe.py` - owner **cody**, since 2026-10-12, kind py
* `tests/run_cron_liveness_probe.py` - owner **cody**, since 2026-10-06, kind py
* `tests/run_graduated_exemption_probe.py` - owner **cody**, since 2026-10-12, kind py
* `tests/run_selftest_sweep_probe.py` - owner **cody**, since 2026-09-16, kind py
* `tests/run_tool_selftest_probe.py` - owner **cody**, since 2026-09-16, kind py
* `tests/sairnfreedom_auth_review_probe.js` - owner **cody**, since 2026-10-06, kind node
* `tests/scp_quotes_review_probe.js` - owner **cody**, since 2026-10-06, kind node
* `tests/sd_tax_money_coercion.js` - owner **cody**, since 2026-10-12, kind node
* `tests/seam_check/run_delegation_probe.py` - owner **cody**, since 2026-10-12, kind py
* `tests/seam_check/run_delegation_residue_control.py` - owner **cody**, since 2026-10-12, kind py

## What this page does NOT say

* **It does not say the 20 are failing.** A blank `diagnosed` means nobody
  has looked, which is a different fact from red.
* **It does not credit a drive that was never written down.** If a suite was
  run and the register was not updated, this page counts it as undriven -
  and that is the correct direction: the register is the record.
* **It is a snapshot of `docs/known-red-suites.json` at `6a3e0fd5`.** Re-run the generator.
