# SAIRN handoff — cody b55 (2026-10-28)

Items 1, 2, 5 and 6 are done or running. Items 3 and 4 are not build work, and I have routed them back with evidence (see below). Nothing is half-finished in the tree.

## Committed / pushed state
- **All work LANDED on origin/main** on bounded push attempt 1 of 5. No `--loop`, no force, no skip. Afterwards the clone was 0 ahead and 0 behind.
  - `98bb61e17`: checker_confidence hardening.
  - `19a9a84b8` and `8e2c18f48`: item 5 tool fixes.
  - `1a2377878` and `420975941`: register records.
  - `60a641e6c`: manifest override b55, which replaces b54 (the ten tools/ files).
  - `e016a7f1a`: register re-seat.
- **This deliverables commit** carries the handoff, report, digest, the work-log entry, the scrutiny bookkeeping and the claim release `0651405e3`. The report confirms whether it landed, because this file is written before that push.
- **Claims:** I claimed `platform` this batch (`f4ec825bf`) and RELEASED it (`0651405e3`). fourth's b60 handoff says its item 6 gate held on this claim, so the release matters to fourth.
- **Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. Full `run_all_tests.py`, RUNNING in the background
- **Where:** an isolated worktree, `C:\Users\marsh\AppData\Local\Temp\cody-b55-alltests`, detached at `1feeb7d67`. That commit includes the b54 not-run fix. `node_modules` is a junction to this clone's.
- **Why not the live clone:** probes write tracked files, and this clone was being edited and pushed at the same time.
- **Restart:** I restarted it once with `python -u`, because block-buffered stdout showed 0 lines after 25 minutes.
- **Log:** `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45\scratchpad\b55-alltests.log`. The final line is `EXIT=<n>`.
- **Counts so far** are in the report: passed, failed, and the count at the moment of writing.
- **Next step:** read the log tail. Then `git worktree remove --force` that path and remove the junction first.

## 2. checker_confidence.py hardening: DONE (`98bb61e17`)
- **UNRUNNABLE was rated HIGH.** `stability_band()` had no branch for the ledger's UNRUNNABLE verdict and fell through to HIGH. The live case is `metamorphic_check.py`: six launches, all raised (180s timeout), rated HIGH, "no verdict has ever moved". It is now UNKNOWN. HIGH is given only to STABLE by name, and an unrecognised verdict is UNKNOWN. A verdict judged on an older tree now says so; all 46 measured checkers are older-tree.
- **`--json` was not JSON.** report_only_checks prints a NOTE at import, and since the hook was removed on 2026-10-14 that NOTE led stdout. The probe's section 5 had crashed in `json.loads` ever since, so none of the real-fleet arms ran.
- **The naming join reported a non-run as a measurement.** It returned `{}` on a read failure, which was printed as "a MEASURED zero". It now raises, and the run prints COULD NOT TELL.
- **An unreadable test file read as NONE.** A checker whose control was in that file showed "NO declared control". It is now UNREAD (UNKNOWN). Any partial parse short of BOTH is now UNPARSED.
- **Probe:** 13 new arms, all pass. Ablation check: with the UNRUNNABLE branch removed, the reason arm fails. The tool's exit code is unchanged against HEAD (2).

## 3 and 4. NOT MINE: these are hover auditor items, routed back
A read-only hover-finding-reader pass over both auditor logs found:
- **Item 3, the Semgrep arm that cannot read .html/.sql:** H2 seq1091, 1097, 1099 and 1106. The H2 tooling is `tools-hover2/semgrep_risk_pack.py`, `semgrep_rules_sairn_risk.yaml` and `real_fix_track.py`, under H2's project dir outside the repo. Target is "self", and the status is OPEN. Semgrep removed HTML extract mode in 1.65 (seq1055).
  - Build-side `tools/run_semgrep.py --default` already reports the 4 partially parsed .html files as COULD NOT FULLY SCAN, exit 2. So no build-side arm is hiding them.
- **Item 4, the emailed-anchor leg:**
  - H2 seq813 (b19, Michael retired the emailed anchor in favour of an RFC3161 token) and seq871 (the gate change, with the WEAKENING-FLAGS sign-off still OPEN).
  - H2 seq1111, 1147 and 1156 still list "the emailed-anchor leg (b74 item 5)" as outstanding. That contradicts seq813.
  - H1 seq1704, 1715 and 1721: the drill passed but was "not compared with an emailed anchor". No H1 entry records the b19 retirement for `hover_backup_mirror.py`.
- **"Chain log"** is the auditors' hash-chained log. A build agent has none. The b55 entry is in `SAIRN-ACTIVE-WORK-cody.md` instead.
- **Item 2's word "calibration confidences"** matches H2's `calibration_tracker.py` open confidences (seq1078–1085, 1091, 1109). Those are H2's to resolve. I did the build-side reading, checker_confidence.py, as written.

## 5. Methodology: not-run / skipped / could-not-run read as pass, swept over cody's own tools
- **Population:** the 41 non-archive `tools/*.py` that `docs/tool-owner-map.json` gives to cody (the committed map; regenerating it rewrites the file, so I did not). run_all_tests was fixed in b54.
- **Method:** six read-only auditors, then my own re-read of every HIGH hit before fixing. Worst first, by severity: a gate exiting 0 or publishing a pass, then an overstated count, then cosmetic.
- **FIXED, each measured against HEAD where it could be driven:**

| tool | was | evidence |
|---|---|---|
| rework_tracker | read 3,524 of 10,587 commits; no unread reason | events 127 → 456; a fixture arm, killed by the old split |
| dead_rule_sweep | crashed or hung ablation counted LIVE; `--tool typo.py` and an empty `--segment` were CLEAN, exit 0; unreadable tools not counted | HEAD inner 0 → now 2, via the `--rc-file` wrapper |
| register_freshness_check | one register missing, zero rows, or UNVERIFIABLE-only gave exit 0 | 5 probe arms; 4 fail on the HEAD tool |
| metamorphic_check | zero targets CLEAN; `ls-files` rc unread; `--json` skipped the rewording family | zero targets: HEAD 0 → 2; probe passes |
| master_plan | criticality_tier_check exit unread, so all apps were published TIERED if it failed | refusal driven; `--check` OK; probe passes |
| service_role_tier_a_gate_check | empty Tier A set or empty api/ list gave CLEAN | driven; probe 27/0 |
| eaten_substitution_check | "NOTHING WAS SCANNED", then EXIT_CLEAN | new E5b arm fails on HEAD. C4/C5 had been red: the last-3000 window outgrew the recorded commits; they are now found by subject |
| git_config_isolation | `--rc-file` write failure gave exit 0; the refusal text omitted `--rc-file` | selftest 8/0 |
| hover_separation_audit | failed `git show` read as in-scope | its probe has G11/G14/G21 red **identically at HEAD** (fixture sha 3e8a52155 is now in scope after H1's b86 patch) |

- **Reverted:** my write_without_readback "zero files → 2" change. `results` counts files WITH writes, not files scanned, so it broke two legitimate arms.
- **NOT FIXED, routed.** The sweep report is in the transcript.
  - **HIGH:** H5/H18 partly. gap_ledger: a Synthesis section with zero matched items reads "no gaps" (live: sairnbiz audit :1355). write_without_readback: alias-only callers are skipped (live: sairnmechanical mechPushOne). ledger_append: numstat (0,0). capture_exit: stale status after a failed first write.
  - **MEDIUM:** verify_citator_feedback PARTIAL returns 0. guard_ablation always returns 0. assertion_label_shape_check `strip_comments(src, rel)` arg slot (count is structurally 0). parse_zero_third_state `value=2` matches `indent=2`. unproven_arm `not_assessed` returns 0. metamorphic unexercised relation. entry_point_scope CLEAN_NO_POP counted. control_char "scanned". clone_health and git_config_isolation selftest arms. route_suite_failures drops COULD-NOT-RUN. overrun_inversion. dead_function_sweep >25% blanked still clean. external_file_index ABSENT ok. session_surface `--no-usage`. dead_rule_sweep overlay rc.
  - **Shared (cc):** `checker_kit.tracked()` ignores git's exit code for every caller.
- **Clean, as checked:** append_only_read_order_scan, bare_run_writers, schema_provisioning_check, gate1_verify, capture_exit (apart from one write), claim_provenance, tool_owner_header_check, tool_owner_map, dup_dom_ids_check, dep_surface_check, dependency_graph, wait_for, criticality_tier_check, advisory_lock_isolation_check, staged_parse_check, sairn_reachability_probe (LOW only).

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Full run_all_tests in progress | Read the scratchpad log tail for `EXIT=`, name any FAIL lines, then remove the worktree |
| O2 | Remaining sweep hits (§5) | cody next batch, worst first: gap_ledger, write_without_readback alias, then the MEDIUM list. cc: `checker_kit.tracked()` rc |
| O3 | hover_separation_probe G11/G14/G21 red since H1's b86 patch | cody: re-pick the fixture's out-of-scope commit |
| O4 | Items 3/4 (Semgrep html/sql, emailed anchor) | H2 and H1 respectively, in their own tooling |
| O5 | metamorphic_check UNRUNNABLE under the flake ledger (180s timeout, registry args not passed by `measure()`) | cc (flaky_checker_quarantine): pass the registry args or a bound |
| O6 | Carried from b54: dental timezone (hank), 7 ratio leads, push_retry bounded mode (cc), Tier A reviews | unchanged |
