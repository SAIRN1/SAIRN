# Routed out of queue 17 — what can only land in somebody else's file

**2026-10-06 (Cody). CONFLICT DECLARED PER PR §4.3, THREE SESSIONS, NONE
REWORDED PAST.** Claims re-checked at HEAD before every write in this batch.

| file | held by, at HEAD | what I owe it |
|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | **hank** — *"TAKEN DELIBERATELY: it is cc's by convention, cc's claim on it EXPIRED 8.6h ago"* | **ITEM 2** — one row, paste-ready below |
| `docs/tier-a-reviews.json` | **cc** | **ITEM 11** — see the obligations section |
| `tools/tooling_inventory.py` | **fourth** | **ITEM 13** — registrations |
| `docs/METHODOLOGY.md` | **fourth** | **ITEM 15** — three conventions + three more |
| `tools/exit_status_attributable.py` | **cc** (mid-fix on its false positives) | the backgrounding false negative |
| `fmea/alf_facility_role_gate_live_probe.py` | **cc** (working it directly) | the metamorphic rewording subject |

---

## ITEM 2 — THE INDEX ROW, AND IT IS ROUTED TO **HANK**, NOT CC

**The instruction said: check cc's claim at HEAD, insert if released, route to cc
if held. BOTH HALVES ARE NOW FALSE AND THE ANSWER IS NEITHER.**

- **cc's claim on the index IS released** — her active claim at HEAD lists
  thirteen files and `docs/SAIRN-OPEN-WORK-INDEX.md` is not among them. So the
  "route to cc" branch does not apply.
- **The file is still HELD** — hank's active claim names it, with the reason
  written into the claim itself: *cc's claim expired 8.6h ago and
  `sairn_status.py` reports that session DEAD.* So the "insert it" branch does
  not apply either.

**Routing to cc would have put the row in front of a session that no longer
holds the file.** It goes to hank, who does, and who is already editing it —
his batch-8 claim includes *"routing the 14 unrouted hover findings into the
index"*, so this row joins work already in flight rather than opening a new
front.

### The row — PASTE THE THIRD LINE ONLY

Header and separator are reproduced so the block is a well-formed table that
`md_table_check.py` can read; a bare row is an `ORPHAN` to that tool and it is
right to say so.

```
| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **Tooling** | **&#128993; `metamorphic_check.py` EXITS 1 on a rewording finding that appears in NO index row &mdash; the tool is cody&rsquo;s and so is the gap** <!-- QUEUE16-ITEM1-CODY-2026-10-05 --> | **MEASURED 2026-10-05 and re-measured 2026-10-06 at HEAD, and the tool is otherwise green: the file-transform family is CLEAN at 0 violated of 90 comparisons, `blind_lock()` is LOCKED at 24 fixture comparisons, and all SIX rules `dead_rule_sweep` called DEAD on 2026-09-29 are now exercised (`--tool metamorphic_check.py`: 6 of 6, 0 dead, CLEAN). The ONE finding is in the REWORDING family: `fmea/alf_facility_role_gate_live_probe.py`, relation `case`, 504 applicable and 1 violated. The verdict MOVED &mdash; `('_d_falsy_from_except', '_d_fixed_window')` gained `_d_checker_without_probe`. PRE-EXISTING, not introduced by the fixture work: `b70b040f` names it as &ldquo;its one existing finding&rdquo;** | cody (the tool); row routed to hank | **The ROW was blocked, never the diagnosis.** `docs/SAIRN-OPEN-WORK-INDEX.md` was cc&rsquo;s on 2026-10-05 and is **hank&rsquo;s** at HEAD on 2026-10-06 (taken deliberately, cc&rsquo;s claim expired). Authored and handed over in `docs/2026-10-06-cody-routed.md` rather than inserted, twice, to two different holders | **Reproduce in seconds, not 200: `python tools/metamorphic_check.py --prose` isolates the rewording family and exits 1.** Then decide between TWO hypotheses, which are opposite findings and must not be merged: **(a)** the `case` rewording is NOT meaning-preserving on this subject, so the RELATION is over-broad and the fix is to narrow or declare it, or **(b)** `_d_checker_without_probe` is case-sensitive where it should not be, so the FMEA DETECTOR has a real defect and the relation caught it. **cc holds `fmea/alf_facility_role_gate_live_probe.py` at HEAD and is working it directly, which is where (b) would be settled** | S |
```

**ITEM 2 STAYS OPEN.** The row is authored, verified against the table's seven
columns, and not inserted. It closes when hank pastes it or releases the file.

---

## ITEM 8 — THE SELF-MUTATION SWEEP, AND THE PATTERN WAS ALREADY WRITTEN DOWN

**The shape, stated so it can be argued with:** *a tool whose VERDICT comes from
reading the state of a tree, or a set of changed paths, that the SAME TOOL
writes into — so its own write is inside the thing it measures.*

**Universe: 296 tracked `tools/*.py`.** Candidates carry all three signals — a
tree-state read, a write, and a before/after comparison. **26 do.** Of those I
read the **6 that are mine** plus the 4 structurally closest to the defect.

### THE SENTENCE WAS ALREADY IN THE REPO, IN A TOOL I DO NOT OWN

`tools/flaky_checker_quarantine.py:107` — its own comment:

> **THE LEDGER IS EXCLUDED FROM ITS OWN TREE HASH, and this is not a nicety.**
> Without it the tool cannot accumulate ANY evidence… **A tool whose own output
> invalidates its own input is its own subject. The fix is to take itself out of
> the measurement, not to loosen the filter.**

**That is my defect, diagnosed and fixed by somebody else before I wrote it**,
with the measurement attached ("three passes in a row each left exactly 3
observations"). My writer tier shipped the same shape anyway. **The pattern
being documented did not stop it, which is the finding worth more than the
list.**

### VERDICTS — the 6 mine, all read rather than routed

| tool | file:line | verdict |
|---|---|---|
| `dead_rule_sweep.py` | `tools/dead_rule_sweep.py:645` | **HAD THE SHAPE — FIXED** 2026-10-06, swept source excluded from the digest by name |
| `sairn_claim.py` | `tools/sairn_claim.py:1459` | **HAS THE SHAPE — ALREADY GUARDED.** `self_overlap()` exists for it, with the measurement in the comment at `:1447`; control `tests/claims/run_own_claim_overlap_probe.py` **exit 0** |
| `metamorphic_check.py` | `tools/metamorphic_check.py:249` | **NOT THE SHAPE** — compares checker STDOUT with the target path and dir substituted out (`<TARGET>`/`<DIR>`); fixtures live in a tempdir, not in the `ls-files` set |
| `dependency_graph.py` | `tools/dependency_graph.py:394` | **NOT THE SHAPE** — writes fixtures into `depgraph-fixtures-*` tempdirs; measures `api/` |
| `nhi_register.py` | `tools/nhi_register.py:1049` | **NOT THE SHAPE** — reads `sql/*.sql`, writes `docs/NHI-REGISTER.md`; disjoint sets |
| `run_all_tests.py` | `tools/run_all_tests.py:674` | **NOT THE SHAPE** — writes into the worktree's `.git` dir, outside the walked `tests/` tree |

### TWO MORE READ BECAUSE THEY ARE THE SAME FAMILY — both already guarded

| tool | file:line | verdict |
|---|---|---|
| `flaky_checker_quarantine.py` | `tools/flaky_checker_quarantine.py:107` | **ALREADY FIXED** — the quote above |
| `idempotence_double_run.py` | `tools/idempotence_double_run.py:44` | **ALREADY GUARDED** — *"are named and excluded rather than reported as broken"*; writes only inside its own scratch directory |
| `guard_ablation.py` | `tools/guard_ablation.py:175` | **NOT THE SHAPE** — `diff --name-only` is used to COPY dirty files into the worktree so the ablation sees the working tree, not as a verdict comparison |

### ROUTED — 10 candidates owned by another session, NOT read by me

Ownership derived from the claim-commit history (see the note below on why it
could not be read from the files). **These are routed on the SIGNAL, not on a
diagnosis — three of the nine I did read turned out not to be the shape at all,
so expect the same rate here.**

| tool | file:line | owner | last claimed |
|---|---|---|---|
| `checker_denominator.py` | `tools/checker_denominator.py:75` | **cc** | `ba0e26ab` |
| `fail_open_scan.py` | `tools/fail_open_scan.py:226` | **cc** | `701d3c88` |
| `report_only_checks.py` | `tools/report_only_checks.py:73` | **cc** | `e7322755` |
| `sabotage_control_check.py` | `tools/sabotage_control_check.py:604` | **cc** | `3074a08b` |
| `sairn_status.py` | `tools/sairn_status.py:279` | **cc** | `b1eac459` |
| `auth_header_name_sweep.py` | `tools/auth_header_name_sweep.py:114` | **fourth** | `ad82bf83` |
| `credential_purge_check.py` | `tools/credential_purge_check.py:172` | **fourth** | `7739487b` |
| `primitive_obsession_check.py` | `tools/primitive_obsession_check.py:248` | **fourth** | `dcc50055` |
| `push_retry.py` | `tools/push_retry.py:13` | **fourth** | `17442d94` |
| `tooling_inventory.py` | `tools/tooling_inventory.py:30` | **fourth** | `70aa2ed8` |

### AND SEVEN WITH NO OWNER AT ALL — unknown, not unowned

`first_article_check.py:559`, `fmea_draft.py:521`,
`git_discovery_anchoring_check.py:20`, `message_assertion_audit.py:234`,
`second_pass_coverage_scan.py:188`, `traceability_matrix.py:74`,
`write_path_fault_scan.py:151`.

**No `chore(claims)` commit in 2381 of them has ever named these files**, so
there is nobody to route to. They go to the open-work queue, which is hank's
file this hour.

### THE REASON OWNERSHIP HAD TO BE DERIVED AT ALL

**Only 13 of 296 tracked `tools/*.py` carry an `# OWNER:` line.** The other 283
have no owner recorded anywhere in the file, so every routing decision in this
batch was reconstructed from 2381 `chore(claims)` commit subjects by taking the
most recent session to name each file in a `FILES:` list.

**That derivation is a floor and it is weaker than a line in the file.** It
cannot see a tool somebody built without claiming it, it attributes to the last
*claimer* rather than the author, and `push_retry.py` resolves to **fourth**
while hank has also edited it. **An `# OWNER:` line in all 296 is the fix and it
belongs in `tooling_inventory.py`, which is fourth's** — see item 13.

---

## ITEM 9 — THE CLI ENTRY-POINT SWEEP, AND IT FOUND SEVEN SITES OF MINE IN A DIFFERENT TOOL

**Universe: 296 tracked `tools/*.py`. 105 carry a selftest arm. 99 of those
drive their own real entry point** — they spawn `sys.executable __file__` or
call `main(argv)` — **which is the shape `capture_exit.py` lacked.**

### SIX WHOSE SELFTEST NEVER DRIVES THE CLI — each driven once, exit code on its own line

```
python tools/accepted_risk_expiry_audit.py --selftest    EXIT=0   (cody)
python tools/ai_action_approval_audit.py  --selftest     EXIT=0   (UNKNOWN)
python tools/citation_drift_hook.py       --selftest     EXIT=0   (cc)
python tools/sabotage.py                  --selftest     EXIT=0   (UNKNOWN)
python tools/subprocess_decode_check.py   --selftest     EXIT=1   (UNKNOWN)
python tools/pycomments.py --help                        EXIT=0   (hank)
```

### SIX WITH NO RECOGNISED FLAG — and TWO of those were MY SCANNER being wrong

```
python tools/criticality_tier_check.py                   EXIT=0   (cody)
python tools/mutation_anchor_check.py                    EXIT=2   (cc)
python tools/stored_data_criticality_check.py            EXIT=0   (UNKNOWN)
python tools/tooling_inventory.py --check                EXIT=0   (fourth)
python tools/pycomments.py --help                        EXIT=0   (hank)
python tools/run_all_tests.py                            -- see below
```

- **`criticality_tier_check.py` is a FALSE POSITIVE, and the truth is stronger
  than a flag:** `run_fixtures()` is called **unconditionally at line 746 on
  every run**, and a failing lock returns 2 before anything real is judged. A
  lock that always runs beats a lock behind a flag nobody types.
- **`run_all_tests.py` is a FALSE POSITIVE too** — my regex matched the *words*
  `--selftest` inside strings describing **other** tools' selftests
  (`tools/run_all_tests.py:632`). It has no selftest of its own to skip.

**So 2 of the 6 I owned in that group were my scanner, not the tools.** Said
here because the same error rate applies to the four I am routing.

### THE REAL FINDING: `subprocess_decode_check.py` EXIT 1 NAMED SEVEN SITES OF MINE — FIXED

That tool is not a broken selftest; **`--selftest` runs its real check** and
exit 1 is findings. It reported **71 text-mode subprocess calls with no explicit
`encoding=`** on a machine whose locale default is cp1252. **Seven were mine:**

```
tools/dead_rule_sweep.py              534, 567, 583, 586, 657, 715
tests/run_dead_rule_sweep_probe.py    391
```

**Six of those I wrote TODAY**, in the owner-aware reap and the writer-tier
reset. All seven now carry `encoding='utf-8', errors='replace'`.

**Line 534 is the one that mattered:** the `tasklist` call inside `_pid_alive`,
which is what stops a concurrent sweep reaping a live sandbox. A decode error
there would have raised inside its `try`, which returns `True` — *could not
tell, do not reap* — **so it failed closed and the guard held.** Correct by
construction rather than by luck, and still wrong to leave.

```
python tools/subprocess_decode_check.py --selftest   BEFORE: 71 sites, EXIT=1
python tools/subprocess_decode_check.py --selftest   AFTER:  64 sites, EXIT=1
```

**Still exit 1, and that is honest:** 64 sites remain in other sessions' files.
Mine are gone — `grep` for `dead_rule_sweep` in the output returns nothing.

### ROUTED

| finding | file:line | owner |
|---|---|---|
| **64 remaining undecoded `text=True` subprocess calls** | the tool's own list | **UNKNOWN** for the tool; the sites span cc, hank and fourth files |
| `mutation_anchor_check.py` **EXIT 2** — *"could not read: 5 (NOT a pass)"* plus 2 anchors not matching exactly once | `tools/mutation_anchor_check.py` | **cc** |
| the 2 bad anchors it names | `tests/claims/run_fileset_matcher_sabotage_probe.py` | **UNKNOWN** — no claim has ever named it, though `tools/sairn_claim.py` is mine |
| 3 selftests that never drive their CLI and could not be attributed | `ai_action_approval_audit.py`, `sabotage.py`, `stored_data_criticality_check.py` | **UNKNOWN** |

**The `tests/claims/` anchor finding is the one to look at first** — the probe
lives beside controls for a tool I own, so it is probably mine in practice even
though no claim records it. **I did not touch it: `mutation_anchor_check.py` is
cc's and she is the one holding the verdict.**
