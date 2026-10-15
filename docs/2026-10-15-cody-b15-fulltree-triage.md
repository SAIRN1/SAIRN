# The full-tree run — 811 files, 99 failures, triaged by owner

**Written 2026-10-15 by cody, batch b15 item 1.** The first full-tree run since
b14, which ran five suites and said plainly that the other 958 were not run.

**The run:** `python tools/run_all_tests.py --pinned --out <log>` →
**exit 1**, read from `echo "EXIT=$?"` on its own line.
**RAN: 385 JS + 426 PY = 811 files**, 3 skipped, 2 not run (SQL fixtures),
**1 excluded** (`tests/run_selftest_independence_probe.py`, pinning-incompatible
by the runner's own record — a worktree has no sibling clones to enumerate).

**`--pinned`, NOT the live clone, and NOT a worktree.** `--pinned` makes a real
`git clone --local`, so `.git` is a DIRECTORY. A `git worktree` leaves `.git` as
a FILE and several probes resolve a clone sentinel that cannot resolve in that
shape — that produced **two false RED verdicts** on this platform in b9. The
distinction is the reason the numbers below can be read at all.

---

## 1. THE RUN WARNED THAT ITS OWN FAILURE LIST MIGHT BE FICTION

Verbatim from the run's own output:

```
THE SUITE DIRTIED THE TREE (1 path(s)) -- a probe did not clean up:
     M docs/report-only-reachability.json
    Results above may be CASCADE, not real: a modified tracked file
    fails every clean-tree probe after it. Restore with git and re-run
    before believing any failure. Nothing was restored for you.
```

**So the 99 were not reported as findings.** `tools/known_red_check.py
--from-run` split them against the register first:

| bucket | count | meaning |
|---|---|---|
| **KNOWN** | 37 | already in `docs/known-red-suites.json`, unchanged |
| **CHANGED** | 16 | registered red, now failing on a **different arm** — a second defect hiding inside an entry that says the first |
| **NEW** | 46 | red and **not recorded** |
| **RECOVERED** | 9 | registered red and **GREEN in this run** — the entry is stale |

Then **every one of the 46 NEW was re-driven ALONE on a genuinely clean tree**,
in an isolated `git clone --local`, with `git checkout -- .` before each file
and `git status --porcelain` after it.

| verdict | count |
|---|---|
| **STILL RED on a clean tree — real** | **39** |
| **GREEN on a clean tree — the full-tree failure was CASCADE** | **1** |
| **COULD NOT RUN — a third state** | **6** |

**One file was pure cascade: `tests/run_save_reviews_retry_probe.py`** — 9/10 in
the full-tree run, **10/10 alone on a clean tree**. Had the 99 been reported
as-is, that would have been a fabricated regression.

**And the re-run found the OTHER tree-dirtier the full-tree run could not
attribute:** `tests/run_capa_fields_probe.py` leaves
`docs/_capa_probe_tmp.json` behind, and **timed out at 180s**.

---

## 2. THE 39 REAL FAILURES, BY DIRECTORY OWNER

**Routing rule for this batch: `api/` → hank, `tools/` → cc, `docs/` → fourth,
`tests/` → cody.** The failing FILE's directory decides the owner, except where
the failure is a true statement about another directory's code — those are
called out by name.

### 2a. `api/` → HANK (3)

| file | what it says | next step |
|---|---|---|
| `api/sd-data-law-trusttx-session.test.js` | `active-credential re-check DID NOT RUN for app "sairnd…"` | the pre-gate does not fire for that app. **Same cause as `tests/sd_data_family_mar_gate.js` below — one fix, two files** |
| `api/sd-data-leg-session-gate.test.js` | 19 passed, 1 failed | read the failing arm's own name; it is one arm, not a sweep |
| `api/sd-data-memory-app-scope.test.js` | throws — last line is `}` | an uncaught error, not an assertion. Run it alone and read the stack |

### 2b. `tests/` → CODY, and TWO ARE FIXED IN THIS BATCH (36)

**FIXED HERE, both at cause, both now green:**

| file | the defect | fixed |
|---|---|---|
| `tests/run_criticality_tier_probe.py` | **`NameError: name '_rm_ro' is not defined`**. It was defined ~20 lines BELOW the module-level `finally:` that calls it. Python resolves a name when the line runs, and that `finally` runs during module execution — **so the error landed in the CLEANUP PATH and discarded every verdict the arms above had just reached** | definition moved above its first use. **exit 0, 0 failed** — the probe had been fully passing and saying so to nobody |
| `tests/gated_resource_direct_fetch_header.js` | **anchor rot, and the guard caught it.** It sliced between `API.indexOf('SD_SESSION_GATED')` and `API.indexOf('SD_GATE_APP')` on the RAW source. Both identifiers are **discussed in comments long before they are declared** — the first `SD_SESSION_GATED` is a comment at `:99`, the declaration is at `:859` — so the slice spanned 58,800 characters of the wrong region and parsed **17** names. Its own `>= 20` guard refused | anchored on `const <NAME> = {` and sliced from the **comment-stripped** source the file already imported and was not using. **66 names, exit 0, 5 passed** |

**NOT FIXED IN THIS BATCH — 34 files, each with its next step.** Said plainly:
34 test files is not one batch's work, and the alternative to saying so is a
silent partial sweep that reads as a complete one.

*Clusters first, because they are not 34 independent problems:*

| cluster | files | the shared next step |
|---|---|---|
| **A session-name argument is refused** — all end `where <name> is one of the session names already used by this p…` | `tests/claims/run_registry_claim_probe.py`, `tests/run_irreversible_class_probe.py`, `tests/run_tier_a_review_gate_sabotage_probe.py` (exit 3) | ONE diagnosis, not three. A tool these three drive refuses an argument it used to accept. Find the refusal's own source and decide whether the probes or the tool moved |
| **`active-credential re-check DID NOT RUN`** | `tests/sd_data_family_mar_gate.js`, plus `api/sd-data-law-trusttx-session.test.js` (hank's) | the pre-gate is not firing for those apps. **The fix is in `api/`, so the test half is cody's and the cause is hank's** |
| **Baseline red, so the sabotage is meaningless** (exit 2, the probe's own refusal) | `tests/law_trusttx_session_probe.py`, `tests/run_leg_session_gate_sabotage_probe.py`, `tests/run_server_wins_hydration_sabotage_probe.py` | **these are COULD-NOT-RUN, not failures.** Each is blocked by ITS OWN BASELINE suite, which is a different file. Fix the baseline and the probe recovers by itself — do not touch the probe |
| **`sairnbuild` retry/backup pair** | `tests/sairnbuild_backup_pending.js` (TypeError at `:241`, reading `payload` of undefined), `tests/sairnbuild_fault_probe.py` (`...and sairnbuild_backup_pending.js is green again on it`) | the fault probe plants a defect and asserts the suite catches it; the suite now **crashes** instead. Fix the crash first, then the fault probe's verdict means something again |
| **Session-gate sabotage probes reporting a WIDENED gate** | `tests/run_sf_session_gate_sabotage_probe.py` (`the gate WIDENS to sf_officers and sf_tickets`), `tests/run_sv_session_gate_sabotage_probe.py` (`the gate MOVES AFTER the witness lock`) | both are statements about `api/` gate placement. **Verify the claim against `api/sd-data.js` before routing** — a sabotage probe reporting a widened gate may be right, and then it is hank's |

*The remainder, one line each — file, its own last line, owner:*

| file | its own last line | owner |
|---|---|---|
| `tests/claims/run_claim_audit_probe.py` | `…it exits non-zero, because a phantom block is a real cost` | cody |
| `tests/claims/run_own_claim_overlap_probe.py` | `…and BOTH live incidents are among them` | cody |
| `tests/hook_command_anchoring_probe.py` | `the anchored form is actually in use (0 command(s))` | cody — **0 is the population; an arm over zero passes for ever** |
| `tests/mech_docs_redaction_wiring_probe.py` | `7. saveDoc no longer says "Saved on this device" while syncing` | cody, claim about app code |
| `tests/push_gate/check3_probe.py` | `…it is NOT check 2, the credential guard, answering instead` | cody — **176s, near the ceiling** |
| `tests/push_gate/redaction_base_probe.py` | `3 failure(s)` | cody — **124s** |
| `tests/run_audit_event_type_probe.py` | `10 passed, 1 failed` | cody |
| `tests/run_batch_cleanup_probe.py` | `…written into the list file, so the removal is au…` | cody |
| `tests/run_batch_manifest_probe.py` | `…and every fixture ran` | cody |
| `tests/run_checker_confidence_probe.py` | `json.decoder.JSONDecodeError: Expecting value: line 1 column 1` | cody — **a crash on empty/absent JSON, not an assertion** |
| `tests/run_claim_doc_freshness_probe.py` | `4 arm(s) FAILED: clean fixtures -> exit 0, four OK rows` | cody |
| `tests/run_closing_error_probe.py` | `…and says which source was empty` | cody |
| `tests/run_condition_coverage_sandbox_probe.py` | `7 passed, 3 failed` | cody |
| `tests/run_conflict_preflight_hook_probe.py` | `conflict_preflight_hook probe: 2 failed` | cody |
| `tests/run_estimate_fusion_probe.py` | `…and --quiet really is quiet` | cody |
| `tests/run_fail_open_probe.py` | `THE CONTROL: audit tool present and CLEAN -> runs and allows` | cody — **a CONTROL failing is worse than an arm failing** |
| `tests/run_known_red_probe.py` | `7 failure(s)` | cody — **it tests the register this batch edited; re-run after this push** |
| `tests/run_mutation_anchor_probe.py` | `7a the real repo has zero bad anchors and zero unguarded probes` | cody — **and b15 just fixed a bad anchor, so re-run** |
| `tests/run_out_of_service_probe.py` | `13 passed, 2 failed` | cody |
| `tests/run_python_escape_hygiene_probe.py` | `SyntaxWarning: "\d" is an invalid escape sequence` | cody — the probe's own subject, emitted by its own run |
| `tests/run_register_feed_gate_probe.py` | `CONTROL: a good ref line first still yields its range` | cody — **a CONTROL** |
| `tests/run_sairnbuild_server_wins_sabotage_probe.py` | `6. [BLOCKER C] THE RETRY SENDS bld_bids WITHOUT ITS SESSION` | cody, claim about `api/` |
| `tests/run_tier_a_open_basis_probe.py` | `10/27 arm(s) pass (5 fail-first fixture, 21 real record)` | cody — **17 failing arms; the largest single gap here** |
| `tests/run_tooling_inventory_probe.py` | `a SessionStart hook is ADVISORY` | cody — **110s** |
| `tests/sairnlegacy_fault_probe.py` | `8. app_id is taken from the client again` | cody — **this is a real statement about `api/` if true. VERIFY IT FIRST: if `app_id` is client-taken, it is a tenancy defect and hank's, urgently** |
| `tests/sd_data_write_attribution_three_apps.js` | `17 passed, 3 failed` | cody |
| `tests/server_wins_hydration.js` | `178 passed, 1 failed` | cody — 1 of 179 |
| `tests/run_dead_rule_sweep_probe.py` | exit 2, `indistinguishable from a sweep that found nothing` | cody — **COULD NOT RUN** |
| `tests/run_capa_fields_probe.py` | **TIMEOUT at 180s**, and leaves `docs/_capa_probe_tmp.json` | cody — **it is also the tree-dirtier the full-tree run could not name.** Fix the cleanup first |

### 2c. `tools/` → CC (0) and `docs/` → FOURTH (0)

**No failing file lives in `tools/` or `docs/`.** Several failures are
statements ABOUT `tools/` code (`run_tooling_inventory_probe`,
`run_register_feed_gate_probe`, `run_fail_open_probe`,
`run_tier_a_open_basis_probe`, `run_batch_manifest_probe`,
`run_batch_cleanup_probe`, `run_dead_rule_sweep_probe`) — **the probe is
cody's, the subject is cc's.** Each needs its claim verified against the tool
before it is routed, and this document does not route any of them on the
strength of the probe's own wording.

---

## 3. THE 9 STALE REGISTER ROWS

Registered red, **green in this run**. The register's own rule is that such a
row must go: *while it stands, the next real failure of that file reads as
KNOWN.* **Not removed in this batch** — each needs driving alone before it is
moved, which is the discipline b14 used, and the full-tree run is one process
per file but not one tree per file.

`api/sf-auth.test.js` · `tests/faults/transport_timeout_sweep.js` ·
`tests/push_gate/check12_probe.py` · `tests/push_gate/check8_probe.py` ·
`tests/run_b12_routed_findings_probe.py` ·
`tests/run_secrets_inventory_probe.py` · `tests/run_selftest_sweep_probe.py` ·
`tests/run_subprocess_decode_probe.py` · `tests/sql_preflight/run_probe.py`

**`tests/run_b12_routed_findings_probe.py` going green is a RESULT, not
bookkeeping:** it held four `api/` findings red on purpose (T16, T17, T18, N4),
and green means **hank landed them.** Confirm against `api/` before closing the
row.

## 4. THE 16 "CHANGED" ROWS

Registered red and now failing on a **different arm** — a second defect inside
an entry that names the first. **Not opened in this batch.** The next session
should take these before the NEW ones: an entry that absorbs a different
failure is worse than no entry, because it reports coverage it does not have.

---

## 5. WHAT THIS DOCUMENT DOES NOT CLAIM

* **Not that the 39 are 39 distinct defects.** Five clusters are named above;
  the real count of causes is lower and is not measured here.
* **Not that any probe's claim about `api/` or `tools/` is TRUE.** A probe
  saying *"app_id is taken from the client again"* is a lead, not a finding.
  Every such line is marked **verify first** and none is routed on its wording.
* **Not that the 37 KNOWN rows are still accurate.** They were not re-driven.
* **Not a clean-tree verdict for the 16 CHANGED or the 9 RECOVERED.** Only the
  46 NEW were re-driven alone on a clean tree.
* **The floor moved and is not committed here:** the run raised the test-file
  floor to **811** in its pinned clone and said *"Commit
  docs/test-file-floor.json: it is a record, not dirt."* That write happened in
  the throwaway clone, so **this clone's copy is unchanged** — and the ratchet
  stays at its old value until somebody runs it where it can be committed.
  Noted rather than done, because a floor raised from a run whose failures were
  still being triaged is a ratchet set on an unfinished measurement.
