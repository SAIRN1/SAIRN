# The 101 suite failures, split by owner — batch 19, 2026-10-08

**SOURCE.** The clean-worktree run of `tools/run_all_tests.py` in batch 18 (`python -u`, captured **EXIT 1**): 757 files, 651 ok, **101 FAIL**, 5 SKIPPED, 2 NOT RUN. Every one of the 101 was then re-run **ALONE**, on a tree restored with `reset --hard` plus `clean -fd` **before each file**, at a 240 s bound.

**WHY ALONE.** The suite dirties its own tree — its footer names five paths and says *"Results above may be CASCADE, not real."* The generators it runs regenerate documents, and every clean-tree probe after that point fails for a reason that is not its own. Running in a clean worktree does **not** fix that; only running each file by itself does.

| verdict | count | meaning |
|---|---:|---|
| **REAL** | **89** | non-zero ALONE, on a restored tree |
| **CASCADE** | **8** | exit 0 alone — failed in the suite only because something earlier dirtied the tree |
| **TIMEOUT** | **4** | exceeded 240 s alone. A third state, folded into neither |

**OWNER IS DERIVED, NOT GUESSED.** `map` = a non-null entry in `docs/tool-owner-map.json`. `claim` = a session DECLARED the file in a claim's `FILES:` list, read out of every record in `.claude/claims/*.json`. **`UNOWNED` means neither source names anybody** — not that nobody wrote it. 502 of the owner map's 680 ownerless entries are under `tests/`, so this is the common case and is counted rather than filled in.

## REAL failures by owner (89)

| owner | count |
|---|---:|
| UNOWNED | 62 |
| **cody** | 11 |
| **fourth** | 8 |
| **cc** | 5 |
| **hank** | 2 |
| **cc+fourth+hank** | 1 |

### UNOWNED — 62 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `api/sd-data-customer-soft-delete.test.js` | - | 1 | FAIL - role "sales" cannot delete a customer -> 403 |
| `api/sd-data-family-contacts.test.js` | - | 1 | FAIL - ROLE GATE: a med_aide is REFUSED the contact list, and the refusal happens before any contact row is fetched |
| `api/sd-data-scp-licence-only.test.js` | - | 1 | FAIL B. customers answers without a session -- a DISCLOSURE, not an endorsement, so widening the scope becomes visible here |
| `api/sf-auth.test.js` | - | 1 | FAIL ROLES_BY_APP, the schema check constraint and CAPABILITIES agree |
| `tests/claims/run_claim_retype_mutation_control.py` | - | 2 | sairn_claim.py retyped-task guard: every arm is shown to FAIL on a sabotaged subject |
| `tests/claims/run_registry_claim_probe.py` | - | 1 | FAIL a claim visible ONLY in the registry BLOCKS |
| `tests/claims/run_released_visibility_probe.py` | - | 1 | FAIL the real CLI still exits 0 on a clear check |
| `tests/defect_register_capa_control.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\defect_register_cap |
| `tests/faults/sd_write_faults.js` | - | 1 | FAIL a TIMEOUT is reported, and named as a timeout |
| `tests/faults/transport_timeout_sweep.js` | - | 1 | FAIL sairncare.html: a TIMEOUT resolves to the failure value, never a rejection |
| `tests/hover_quotable_session_vocab_check.py` | - | 1 | FAILED: 1 session(s) exist that QUOTABLE does not name: cloud |
| `tests/law_reconcile_role_vocab_check.py` | - | 2 | This is exit 2. Nothing was checked, and that is not a pass. |
| `tests/law_reconcile_role_vocab_control.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\law_reconcile_role_ |
| `tests/local_only_self_evidence_probe.py` | - | 1 | 1 ARM(S) FAILED |
| `tests/local_only_shape_probe.py` | - | 1 | 2 ARM(S) FAILED |
| `tests/run_adversarial_prompt_corpus_probe.py` | - | 1 | FAIL 4. the sweep runs and classifies: zero unfenced, 5 reported as fenced |
| `tests/run_alf_read_order_sabotage_probe.py` | - | 1 | FAIL 5. THE FIX IS STILL THERE BUT THE ARM CAN NO LONGER SEE IT: the alf_mar read is hoisted into a local, so the arm finds ZERO list reads for that table. A sweep over a read it never found is not a  |
| `tests/run_all_tests_floor_probe.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\run_all_tests_floor |
| `tests/run_checker_control_probe.py` | - | 1 | FAIL EVERY CONTROLS_FOR under tests/ parses to a subject (these declare nothing: ['tests/criticality_rollup_list_review_probe.py']) |
| `tests/run_coding_rule_channel_probe.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\run_coding_rule_cha |
| `tests/run_committer_identity_probe.py` | - | 1 | FAIL and no local override was left behind |
| `tests/run_concurrency_retry_probe.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\run_concurrency_ret |
| `tests/run_condition_coverage_probe.py` | - | 1 | FAIL 4a a dirty tree exits 2, not 0 or 1 exit 1 |
| `tests/run_copy_exactly_gate_probe.py` | - | 1 | FAIL the gate reads the range in the CURRENT WORKING DIRECTORY's repo |
| `tests/run_cron_liveness_probe.py` | - | 1 | FAIL the pre-change workflow had NO commit step -- only the artifact upload, which is the gap this closes |
| `tests/run_cross_tenant_dispatchers_sabotage_probe.py` | - | 2 | COULD NOT RUN: the baseline is not green (14 failing). A sabotage control on a red baseline cannot distinguish its own mutation from the pre-existing failure. Failing: grd_boq_rates [L] tenant A sees  |
| `tests/run_defect_dispersion_probe.py` | - | 1 | FAIL every dimension is present |
| `tests/run_dependency_graph_probe.py` | - | 1 | FAIL 7a the real register passes against the live graph ks without a measurement |
| `tests/run_dispatch_state_probe.py` | - | 1 | FAIL ...and NO subprocess.run, so it never invokes sairn_claim.py to ask the claim matcher |
| `tests/run_eaten_substitution_probe.py` | - | 1 | FAIL C4 it still finds the cron clock-freeze commit item 18 records |
| `tests/run_financial_invariant_probe.py` | - | 1 | FAIL 7f a judgment for a file the checker no longer flags is called out as stale, not left to look current ation and this cannot see whether it ran. The entries |
| `tests/run_first_article_probe.py` | - | 1 | FAIL api/audit-checkpoint.js: the recorded hash matches a one-shot hash of the file |
| `tests/run_githook_install_probe.py` | - | 1 | FAIL --check passes in this clone |
| `tests/run_graduated_exemption_probe.py` | - | 1 | FAIL ...and the exemption is CONSUMED -- single use, so a third push starts the cycle over rather than riding the same grant |
| `tests/run_index_duplicate_probe.py` | - | 1 | FAIL 7a the real index has no undeclared duplicate pairs exit 1 |
| `tests/run_irreversible_class_probe.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\run_irreversible_cl |
| `tests/run_nhi_clone_enumeration_probe.py` | - | 1 | FAIL THE ARM THAT MATTERS: a clone of the same remote NOT named SAIRN-* is counted. This is the real Documents\SAIRN, the seventh working copy holding the same push credential, and the name filter ski |
| `tests/run_nhi_register_write_flag_probe.py` | - | 1 | FAIL A2. the bare run must report the staleness it declined to fix |
| `tests/run_purge_evidence_probe.py` | - | 1 | FAIL A7 a record dated today passes could not --record: exit=2 |
| `tests/run_rebase_resolve_probe.py` | - | 1 | FAIL ...and the tool REFUSES it, exit 1 |
| `tests/run_rewrite_convergence_probe.py` | - | 1 | FAIL B1 real-repo --verify: anchors resolve and coverage is complete exit=2 |
| `tests/run_role_gate_negative_coverage_probe.py` | - | 1 | FAIL at the pinned number it is OK and exits 0 exit=2 |
| `tests/run_secrets_inventory_probe.py` | - | 1 | FAIL 4c CONTROL: with the real map, there are no vocabulary problems at all ['UNCLASSIFIED SAIRNVET_TRANSCRIBE_URL is read by 1 file(s) and has no entry in SECRETS. A new secret breaks this tool on pu |
| `tests/run_selftest_independence_probe.py` | - | 1 | FAIL nhi_register.py: the self-test passes UNMUTATED, or every arm below is meaningless |
| `tests/run_selftest_sweep_probe.py` | - | 1 | FAIL checker_selftest_check.py --selftest exits 0 |
| `tests/run_tool_selftest_probe.py` | - | 1 | FAIL hover_separation_ci.py --fixtures exit 1: AttributeError: module 'hover_separation_audit' has no attribute 'AUDITOR_SCOPE' |
| `tests/sairncare/test-compliance-rules.js` | - | 1 | FAIL a PCH secured-unit worker owes 18 annual hours (12 + 6), computed not asserted -- mismatch: expected false got null |
| `tests/sairncare/test-op-audit.js` | - | 1 | FAIL ANY authenticated employee can record -- housekeeping is not locked out -- caregiver should be able to record: expected 200 got 502 |
| `tests/sairnfreedom_auth_review_probe.js` | - | 1 | ? 15:11 (2) -- the sf-auth setup guard anchor has moved -- this arm is not reporting agreement it did not check |
| `tests/sairnfreedom_segregation_of_duties.js` | - | 1 | FAIL D4. sf_trustee_audits is NOT in SF_SYNCED -- the panel TELLS the user this record is device-only, and a claim about a limitation has to be true |
| `tests/sairnfreedom_server_backup.js` | - | 1 | FAIL - the registry still holds exactly 35 resources |
| `tests/sairnfreedom_server_backup_probe.py` | - | 2 | FAIL 0. the suite is GREEN in the worktree before anything is planted (exit 1) 5. hydration cannot leave the backup suppressed for the session |
| `tests/sairnlegacy_fault_probe.py` | - | 1 | FAIL 0. the suite is GREEN in the worktree before anything is planted (exit 1) ok leg_merch_units -- the resource the lock is on -- is among them |
| `tests/sairnlegacy_reservation_lock.js` | - | 1 | FAILED: a reservation that wins returns 200 -- 403 |
| `tests/schema_provisioning_probe.py` | - | 1 | 3 ARM(S) FAILED |
| `tests/scp_quotes_review_probe.js` | - | 1 | Node.js v24.16.0 |
| `tests/seam_check/run_delegation_residue_control.py` | - | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\seam_check\run_dele |
| `tests/seam_check/run_or_default_probe.py` | - | 1 | 2 ARM(S) FAILED |
| `tests/seam_check/run_ref_probe.py` | - | 1 | 3 ARM(S) FAILED |
| `tests/sql_preflight/run_probe.py` | - | 1 | FAIL |
| `tests/suite_control_backfill_probe.py` | - | 1 | CONTROLS THAT DID NOT BITE: ['2. a failed read is treated as an empty one', '3. the server copy clobbers local records instead of merging', '4. a no-op boot writes anyway', '1. hydrate runs with no li |
| `tests/write_readback_shape_probe.py` | - | 1 | 2 ARM(S) FAILED |

### cody — 11 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `tests/app_session_isolation.js` | map | 1 | FAILED: sairngrounds: measured SOME, recorded NONE -- NOT DOCUMENTED -- api/grd-auth.js exists; grd_invoices and msb_licenses are Tier A |
| `tests/hover_separation_ci_probe.py` | claim | 1 | FAIL a commit inside the auditor's own directory PASSES |
| `tests/rebase_resolve_merge_control.py` | claim | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\rebase_resolve_merg |
| `tests/run_all_tests_pinned_probe.py` | map | 1 | FAIL the inner command is spawned UNBUFFERED, or the line-by-line relay is a slower communicate() and --out sits empty for the whole run |
| `tests/run_bare_run_write_probe.py` | claim | 1 | FAIL E1. it must refuse a working clone |
| `tests/run_blob_coverage_scope_sabotage.py` | map | 1 | FAIL S1. ATTACK POINT -- every non-test api/**/*.js on disk is INSIDE the scanned universe. os.listdir() is flat, so a subdirectory write is outside the coverage figure without the figure saying so |
| `tests/run_citation_anchor_hop_sabotage.py` | map | 1 | FAIL S1. ATTACK POINT 1 -- a function body that only MENTIONS the resource in a `//` comment must NOT be credited with reaching it |
| `tests/run_harness_stage_diagnosis_probe.py` | claim | 1 | FAIL the baseline goes red, as it must when the subject is not staged |
| `tests/run_stored_data_criticality_probe.py` | claim | 1 | FAIL an ESCAPED pipe inside a cell is content, not a boundary exit=0 -- counting it as a boundary turns one row into nine cells and every positional read after it is wrong |
| `tests/run_two_axis_tier_parser_probe.py` | map | 1 | FAIL 2. the NEW six-cell shape parses, raises no row-level problem, and counts as migrated |
| `tests/sairnfreedom_fault_probe.py` | claim | 1 | FAIL the shipped tree PASSES ge key, as the registry says |

### fourth — 8 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `tests/push_gate/preauth_exemption_anchor_probe.py` | map | 1 | FAIL ...and zero oracles PREAUTH_ORACLES:11 -- the tree carries 11 oracle(s); the named sites follow: stale; the exemption still matched, because it is keyed on the refusal and not on the line. STALE_ |
| `tests/run_completeness_probe.py` | map | 1 | FAIL 2d it found the real one: api/sen-portal.js MANAGEMENT_ROLES |
| `tests/run_removal_path_probe.py` | map | 1 | FAIL the real SAIRN baseline currently accounts for every one |
| `tests/run_subprocess_decode_probe.py` | map | 1 | FAIL zero text-mode subprocess calls without an explicit encoding |
| `tests/run_tier_a_review_gate_probe.py` | map | 1 | 3. FAIL CLOSED -- an unreadable register is 2, never "no findings" |
| `tests/run_truthy_sum_probe.py` | map | 1 | FAIL the real SAIRN tree currently has no UNBASELINED occurrence |
| `tests/run_write_path_scan_probe.py` | map | 1 | FAIL the shipped baseline PASSES today -- a ratchet that fails on a clean tree is one somebody turns off |
| `tests/seam_check/run_delegation_probe.py` | map | 1 | TRACEBACK: (most recent call last): / File "C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad\wt-i3\tests\seam_check\run_dele |

### cc — 5 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `tests/app_session_isolation_probe.py` | map | 2 | FAIL 0. the suite is GREEN in the worktree before anything is planted (exit 1) ok stonedesk: measured SOME, recorded SOME -- DOCUMENTED at SD_LOCAL_RESOURCES: the shared shop record; personnel and fin |
| `tests/claims/run_push_verify_probe.py` | map | 1 | FAIL ...and names the exact command that publishes the earlier entry |
| `tests/install_git_hooks_check_probe.py` | map | 1 | FAIL a properly installed clone passes, and SAYS git fires the hook |
| `tests/run_baseline_readiness_probe.py` | map | 1 | FAIL app is NOT READY on VOLUME -- a shortage of records, which time fixes |
| `tests/run_export_coverage_probe.py` | map | 1 | FAIL sairnmechanical declares mech_credentials in its registry, and it resolves |

### hank — 2 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `tests/run_ghost_field_read_probe.py` | map | 1 | FAIL CONTROL, the other direction: the scan DOES still report `charge_lines` -- the key genuinely does not exist yet, so a clean line here would mean the scan had been silenced rather than satisfied |
| `tests/run_review_gate_validate_probe.py` | map | 1 | FAIL --resources RECORDS an obligation naming exactly those resources rc=2 tion). Provision it once: |

### cc+fourth+hank — 1 REAL

| suite | basis | exit | first failing assertion |
|---|---|---:|---|
| `api/sd-data-cross-tenant-dispatchers.test.js` | claim | 1 | FAIL grd_boq_rates [L] tenant A sees ONLY tenant A rows |

---

## CASCADE — listed separately, and NOT counted as failures (8)

**These exit 0 alone.** Their suite verdict is an artefact of the tree being dirty by the time they ran.

| suite | owner | basis | suite said | ALONE |
|---|---|---|---|---|
| `tests/phi_cache_scope_probe.py` | UNOWNED | - | The baseline is red, so no mutation below would mean anything. Stopping. | **ALL 12 ARMS PASS -- every planted defect was refused (7 mutations).** |
| `tests/phi_cache_scoped_to_user.js` | fourth | claim | 63 passed, 1 failed | **72 passed, 0 failed** |
| `tests/push_gate/redaction_base_probe.py` | cody | claim | 2 failure(s) | **0 failure(s)** |
| `tests/push_gate/refspec_and_override_probe.py` | cody | map | - fixture is valid: the clone is LEVEL with its origin/main, which is the only state where | **0 failure(s)** |
| `tests/run_master_plan_probe.py` | UNOWNED | - | it passes on the committed document (got 1) | **ok a hand-edited row makes it FAIL (got 1)** |
| `tests/run_push_gate_preflight_probe.py` | UNOWNED | - | 12 passed, 1 failed | **13 passed, 0 failed** |
| `tests/sairnbuild_fault_probe.py` | cody | claim | - ...and phi_cache_scoped_to_user.js is green again on it | **0 failure(s)** |
| `tests/sairncare_fault_probe.py` | cc | map | - ...and phi_cache_scoped_to_user.js is green again on it | **0 failure(s)** |

**`tests/phi_cache_scoped_to_user.js` is the one to read twice.** Alone, on a restored tree, it is **72 passed / 0 failed**. Fourth's batch-16 item 4 took it on as *"basis NONE, no owner, blocks three register rows"*. Three register rows may be blocked on a green test.

---

## TIMEOUT at 240 s alone — a third state, classified as neither (4)

**NOT counted as REAL and NOT counted as CASCADE.** Exceeding a bound is not evidence either way, and the bound was mine.

| suite | owner | basis | suite said |
|---|---|---|---|
| `tests/push_gate/check12_probe.py` | UNOWNED | - | check 12: 6 ARM(S) FAILED -- A2 check 12 says nothing at all, B1 the push is REFUSED, B2 and it is check 12 that refused |
| `tests/run_defect_register_probe.py` | cc | map | defect-register: 149 checks, 7 failed |
| `tests/run_hover_audit_method_sabotage_probe.py` | UNOWNED | - | The baseline is red, so no mutation below would mean anything. Stopping. |
| `tests/stale_row_sweep_control.py` | UNOWNED | - | ...and NAMES 1348466a, the finally fix |

**NEXT STEP for these four:** re-run each with NO ceiling on a quiet box. A bound exceeded is a lower bound, not a number — the same discipline batch 18 applied to `dead_rule_sweep.py`.

---

## WHAT THIS TABLE DOES NOT CLAIM

* **It does not claim the 89 are NEW.** They are real *alone*; many are long-standing and some are already in `docs/known-red-suites.json`. `known_red_check.py --from-run` against this same log reports **101 red, registry records 75, 30 RED AND NOT RECORDED** — that register is **fourth's** and is not touched here.
* **It does not diagnose any of them.** The "first failing assertion" column is the first failure line each file printed when driven alone, quoted, not interpreted.
* **`UNOWNED` is a gap in the record, not a verdict.** A file with no owner cannot be routed to anybody, which is the same problem `tools/va_rule_currency.py` had in batch b1.
