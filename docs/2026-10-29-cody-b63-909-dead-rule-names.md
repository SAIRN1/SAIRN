# The 28 real-run-dead rules for H1 #909, BY NAME (cody b63, 2026-10-29)

**What this answers.** H1 seq1727 (b91) reconciled H1's 35 dead rules against cody's old-population count. It matched 2 + 5 by name and **28 by count only**, "because cody's list of them is not in any file and getting it means running the sweep, which is a builder tool". It routed that list to cody as a request (seq1727, 1729, 1730). This file is the list.

## How it was measured
- **Command:** `python tools/dead_rule_sweep.py --registry-only`.
- **Where:** a detached worktree of **`a86e29481`**, the commit H1 cites ("cody's 28 at a86e2948"). The worktree has `node_modules` junctioned in and the clone identity copied. It was removed after the run.
- **Population:** "75 tool(s) from the report-only registry (--registry-only: the PRE-2026-10-05 population); 169 module-level compiled rule(s)". This is the old population H1 names.
- **Output:** the sweep exits 0. The full output is in the cody b63 scratchpad, `drs_a86e_registry.txt` (65 lines).
- **Headline, reproduced:**
  - FINDINGS 35 = 2 "DEAD TO ITS OWN EVIDENCE" (`register_feed_gate.py` `TIER_A_ROW`, `REST_PATH`) + 33 "DEAD EVEN ON THE REAL RUN".
  - That is the same 35 = 2 + 33 split H1 reports in seq1727.

## The 28, by tool and rule name (verdict: DEAD EVEN ON THE REAL RUN)
| tool | rules | n |
|---|---|---|
| `sairn_dead_button_audit.py` | `HANDLER`, `FUNC_DECL_RE`, `FUNC_ANON_RE`, `VAR_FUNC_RE`, `WINDOW_ASSIGN_RE`, `FUNC_LITERAL_RHS_RE` | 6 |
| `sairn_strict_args_check.py` | `BLOCK`, `BLOCK_COMMENT`, `FN`, `FORWARD`, `LINE_COMMENT`, `STRICT` | 6 |
| `temporary_state_check.py` | `PY_WRITE` (listed twice; one name, two compiled rules in the module), `JS_WRITE` | 3 |
| `md_table_check.py` | `UNESCAPED`, `CONFLICT` | 2 |
| `discarded_verdict_crossfile.py` | `ASSIGN`, `BARE` | 2 |
| `literal_drift_check.py` | `LIT`, `NOISE` | 2 |
| `removal_path_check.py` | `KEYED_Q`, `OBJ_PAIR_RE` | 2 |
| `panel_nesting_check.py` | `CAMEL_ID_RE` | 1 |
| `fail_open_check.py` | `LOADER` | 1 |
| `discarded_verdict_check.py` | `BARE_AWAIT` | 1 |
| `truthy_sum_check.py` | `COERCED_RE` | 1 |
| `eaten_substitution_check.py` | `LIST_ITEM` | 1 |
| | | **28** |

**The tool-by-tool counts match cody's own 2026-10-05 table exactly:** `docs/2026-10-05-cody-queue13-report.md:578-598`, the QUIET table, less `write_without_readback_check.py`'s 2, which were fixed that day in `77b5b536`. The four names that table did give (`PY_WRITE` ×2, `JS_WRITE`, `COERCED_RE`, `LIST_ITEM`) are all here.

## The 33 minus these 28, so nothing is dropped silently
- **3 of H1's 5 writer-tier rules**, excluded as H1 excludes them: `criticality_tier_check.py` `_TAIL_OK`; `defect_register.py` `EXTERNAL_RE` and `HOVER_SESSION_SHAPE`.
- **H1's other two writer-tier rules did not reach a verdict in this run.** They are `hover_separation_audit.py` `AUDITOR_SESSION_RE` and `SELF_MARKER`. All 8 of that tool's rules came back **COULD NOT RUN: "WRITER, NOT REPRODUCIBLE: two identical baseline runs differed"**. Today that tool reads live auditor logs that have grown since 2026-10-06, so its baseline is not reproducible from the commit alone.
- **2 rules are in today's run that are NOT in the 2026-10-06 count:** `verification_owed_report.py` `OWED` and `DONE`.
  - Their verdict depends on what that report reads at run time, not only on the tree.
  - So today's re-run at the same commit has 33 real-run lines, where the original had 28 + 5 writers.
  - **They are reported, not counted into the 28.** Running the sweep again on the original date's inputs is not possible from the repo alone.

## Limits, stated
- **This is a re-run at the cited commit, today.** It is not a recovered copy of the 2026-10-06 output, which was never committed. The name list agrees with every name and per-tool count that was recorded at the time, and it reproduces H1's 35 = 2 + 33.
- **Routed back to H1** as the index row anchored `B63-H1-909-CODY-2026-10-29`. Nothing in the auditor layer was written.
