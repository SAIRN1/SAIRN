# CC handoff — 2026-10-06 (third), batch 11

**Third handoff of the day.** Batch 9 → `docs/handoff-cc-2026-10-06.md`;
batch 10 → `docs/handoff-cc-2026-10-06b.md`. This one covers batch 11: the
scrutiny-flag build, the eager-probe hoist, the citation residuals and census,
the hook timing, and the all-tools sweep.

**Every figure below carries its command, commit and date. Every exit code was
read from a `tools/capture_exit.py` status file — none from a harness
notification.** Every green states how many times it ran against that SHA and
what the first run returned.

**Transcript:** this session's conversation. No file on disk — it must come from
the terminal scrollback.

---

## 1. Pushed, with the commit for each

| commit | what |
|---|---|
| **`5080cf60`** | the whole batch-11 build, after the gate refused once and was right. Contains `tools/exit_status_attributable.py` (scrutiny classifier + ledger), `tools/sairn_push_gate_hook.py` (CHECK 15), `tests/run_scrutiny_flag_probe.py`, `tools/doc_sha_reseat.py --census`, the six hoisted probes, the design note, routed §14–17, the active-work residual table, and the three regenerated generated documents. |

**Verify rather than trust this table:**

    git fetch origin && git rev-list --left-right --count origin/main...HEAD
    git log --oneline -3 origin/main

**One commit is NOT yet pushed at the time of writing** — the ledger-key fix in
§8 below plus this handoff. The exact next step is at the end of §10.

---

## 2. Claims

**Held by this session:** subject `cc`, batch 11. Release when accepted:

    python tools/sairn_claim.py release cc

**Conflicts declared in the claim text; none reworded past, none overridden.**

---

## 3. BLOCKED, FLAGGED BACK — item 1, the Tier A ranks 7–12

**`docs/tier-a-reviews.json` IS STILL CODY'S.** Claims-checked at the start of
the batch and again at the end, as instructed:

    python <scratch>/whoholds.py docs/tier-a-reviews.json
    #  docs/tier-a-reviews.json    cody

**cody's claim is `2026-10-06T17:34:15Z`, age 4.4h — PAST THE 4h EXPIRY AND
UNRELEASED.** I did **not** take it. The instruction was *never override*, the
chat resolution was that cody is discharging the six oldest **this batch**, and
an expired timestamp is not a release. Taking the identical work on an
unreleased claim is precisely the collision the resolution existed to prevent.
**Flagged back rather than resolved by me.**

**RE-MEASURED AT HEAD `5080cf60`, 2026-10-06T22:00:26Z — nothing quoted from
earlier in the session:**

| | |
|---|---|
| records total | **235** |
| status open | **31** |
| status reviewed | **204** |
| open and authored by `cc` (ineligible — a change is reviewed by another session) | **7** |
| **open and ELIGIBLE to `cc`** | **24** |
| open and already assigned a `reviewer_session` | **0** |

**The counts are identical to the start-of-batch measurement, which means
cody's discharges have not landed on `main` yet** — so ranks 7–12 are still
ranks 7–12:

| rank | age | opened_at | author | resources |
|---|---|---|---|---|
| 7 | 172h | `2026-09-29T14:34:43Z` | cody | `invoices`, `law_matters`, `scp_quotes` |
| 8 | 151h | `2026-09-30T10:58:02Z` | cody | `rf_claims`, `rf_invoices`, `sen_visits` |
| 9 | 151h | `2026-09-30T11:08:08Z` | fourth | `bld_jobs`, `bld_photo_analyses`, `grd_progress_photos`… |
| 10 | 150h | `2026-09-30T12:08:26Z` | cody | `sv_audit_log` |
| 11 | 149h | `2026-09-30T12:59:51Z` | hank | `bld_change_orders`, `bld_inspections`, `bld_toolbox_talks`… |
| 12 | 148h | `2026-09-30T13:59:56Z` | hover2 | `leg_insurance`, `mech_checks` |

**EXACT NEXT STEP:** when cody releases, **re-measure before acting** — the
ranks above are true only as of 22:00Z and cody's six discharges will shift
every one of them. Then:

    python tools/sairn_claim.py check cc tier-a ranks 7-12
    python tools/tier_a_review_gate.py --list

and discharge ranks 7–12 **of that measurement**, not of this table.

---

## 4. CLOSED — item 2, the eager-probe hoist, **6 of 6**

The six probes whose module-level import sat 11–147 lines down now import at the
header, so the registry refusal precedes any of their own output.
**Lines-of-own-output-before-refusal**, fault injected in a detached worktree,
control first:

| probe | before | after |
|---|---|---|
| `run_baseline_readiness_probe.py` | **147** | **0** |
| `run_literal_drift_control_probe.py` | 44 | **0** |
| `run_optimistic_success_probe.py` | 44 | **0** |
| `run_dora_metrics_probe.py` | 21 | **0** |
| `run_risk_event_tree_probe.py` | 19 | **0** |
| `run_assurance_case_probe.py` | 11 | **0** |

**CLEAN-REGISTRY CONTROL after the change:** 5 of 6 exit 0;
`run_baseline_readiness_probe.py` exits 1, **which it also did at `411f29ce`
before any edit of mine.** The hoist ran through a script that **refuses** a file
whose import line or first column-0 `print(` is not uniquely identifiable —
not a find-replace.

---

## 5. CLOSED — item 3, all four citation residuals, and all four were mine

**0 of 26 are unresolvable.** Full account with the command per row:
`SAIRN-ACTIVE-WORK-cc.md`, section *"THE FOUR RESIDUALS ARE RESOLVED"*.

| was | is |
|---|---|
| `74e029a5f373` NO-SUBJECT-MATCH | on `origin/claude/cloud-research-sairncare`, never merged |
| `fe16d5d` UNRESOLVABLE | **`11fc0f30`** — object found in **hank's** store |
| `27d62e7b` UNRESOLVABLE | **`7773af72`** — two commits share the second; the **FILE** disambiguates |
| `eef02009` UNRESOLVABLE | never a broken pointer; quoted as another clone's unpushed tip |

**Three distinct blind spots, all mine, all one shape:** the subject search was
scoped to `origin/main` alone; object existence was tested in **this** clone when
five sit on the machine; and the quoted-as-dead detector only looked inside one
dated heading. **That is the batch-10 rule — a check whose verdict depends on
which clone, which ref or which section it consults is not a check — and I
shipped three fresh instances of it in the classifier that produced the table the
rule appears in.**

---

## 6. CLOSED — item 4, the census, with the definitions

    python tools/doc_sha_reseat.py --census          # at 54e29eba

**150 DEAD of 1155 citations (13.0%)** — ON-MAIN 1005, ORPHAN 38, ABSENT 112.

* **CITATION** = a **backticked** 7–12 character lowercase hex run. Backticks
  are required and that is a measurement: the bare-word form matched 404 tokens
  against 367 on the index, and the 37 extra were decimal figures, 12-hex
  register record ids and one illustrative literal.
* **POPULATION** = the 3 REWRITE + 3 GENERATED + the REPORT-ONLY logs, and
  nothing else. Not "every citation in the repo" — the dated inventories and
  handoffs are point-in-time reports and are deliberately out of scope.

**FIXABLE BY THIS TOOL: 38 of 150. NEVER FIXABLE BY ANY MAP: 112** — an ABSENT
citation was created and orphaned in another clone and is not an object here, so
no rewrite map will name it from anywhere. **Reporting a dead count without that
split would imply a repair that does not exist.**

---

## 7. CLOSED — item 6, already satisfied, not rebuilt

`tests/run_doc_sha_reseat_probe.py` **section C** is three arms proving
`doc_sha_reseat.py` leaves a GENERATED file **byte-unchanged**, says
**REGENERATE** rather than reporting a fix, and **still names the stale pair**
because a stale SHA in a generated file means its *source* is stale.
**19 of 19 arms, EXIT 0, three runs against this SHA, first run 0.**

---

## 8. CLOSED — item 8, the build, and three defects of my own caught before landing

**Design note first:** `docs/2026-10-06-cc-batch-11-design-notes.md` — Goals,
Non-goals, **four** alternatives, cross-cutting table, claims-check.
Alternative A (a standalone tool) rejected on a measured cost: it would be the
**third** program parsing a push's outgoing diff, and `84eb61ea` already records
a pre-flight that duplicated this exact gate.

**Selftests, X of Y, three runs each against `5080cf60`+, first run stated:**

| | arms | exit | runs | first run |
|---|---|---|---|---|
| `--scrutiny-selftest` | **31 of 31** | 0 | 3 | **0** |
| `tests/run_scrutiny_flag_probe.py` | **25 of 25** | 0 | 3 | **0** |
| the original `--selftest` (unchanged) | — | 0 | 1 | 0 |

**THREE DEFECTS OF MINE, EACH CAUGHT BY A DIFFERENT THING, NONE BY READING THE
CODE:**

1. **The check crashed and the gate SILENTLY ALLOWED.** `base` is `None` in
   pretooluse mode, so the git argument list held a `None` and raised
   `TypeError`, which `__main__`'s `except Exception: sys.exit(0)` swallowed.
   **The gate printed nothing and looked like a clean push.** Found because the
   probe's arm A failed with *no gate output at all* — which reads like "the
   check does not work" and meant "the check crashed."
2. **3 of 3 WEAKENING flags on its own landing commit were PROSE.** Comment
   filter applied; **re-measured 2 of 3, and both survivors are still false** —
   prose inside a string literal. **So the WEAKENING level is a triage prompt,
   not a finding, on an n of 1 real push.** Left matching rather than narrowed,
   per scrubber item 24.
3. **The ledger recorded `"sha": "main"`.** The gate's prepush `tip` is a **ref
   name**, so the `(sha, path)` identity could never dedup and no rewrite map
   could ever re-seat it — **9 of the first 18 rows were junk. Found by reading
   the ledger, not the code.** Guarded in **two** places now (the gate resolves
   `tip`; `scrutiny_record` refuses a non-sha outright) with **4 paired arms**,
   including the control that a real sha **is** accepted so the guard did not
   simply refuse everything. The 9 junk rows are removed and the removal is
   recorded inside the file.

---

## 9. OPEN — item 7, ANDON CANDIDATE, worse than the trigger

`report_only_checks.py --hook`, five runs, same tree, the payload the live hook
sends, against its live **600s** `PostToolUse` bound:

```
547.6s (91.3%)  543.1s (90.5%)  577.1s (96.2%)  679.9s (113.3%)  712.4s (118.7%)
mean 612.0s     worst 118.7%    FIRST RUN: EXIT 0 at 91.3%
```

**All five over 50%. Two over 100%. The mean is over the bound.** The `EXIT 0`
column is misleading and must be read with the wall time — `capture_exit.py`
imposes no timeout, so runs 4 and 5 would have been **killed** in the live hook,
and a killed `async` PostToolUse hook reports **nothing**, indistinguishable from
a sweep that found nothing.

**It also drifts upward monotonically after run 2 on an unchanged tree and I have
NOT established why.** Owner per `docs/tool-owner-map.json` is **cc**, CONTESTED
with hank and cody — recorded against my own tool, not routed away.

**EXACT NEXT STEP:** profile the sweep per checker. Nothing in this batch says
*which* checker is slow, and the decision about what to cut affects hank and
cody. Detail: `docs/2026-10-06-cc-routed.md` §16; the same subject is
`docs/known-red-suites.json` entry 55, routed in §13.

---

## 10. OPEN — item 9, the all-tools sweep, and 6 rows are MY sweep's fault

**301 `tools/*.py`, each once in its read-only mode, wall cap 90s, in a detached
worktree. Exit codes from `capture_exit.py` only.**

| | count |
|---|---|
| green (exit 0) | **187** |
| red (exit 1) — usually *findings, report-only* here | **53** |
| COULD NOT RUN (exit 2) | **52**, of which **6 are my sweep's fault** → **46 genuine** |
| other | **9** — 7 timeouts at 90s, 2 exit 3 |
| no read-only mode declared at all (a bare run is the mutating path) | **188 of 301** |

**THE 6 I GOT WRONG, and it is scrubber items 24/25 in my own throwaway
script:** the mode detector matched a flag *string anywhere in the source*,
including prose and `CONTROLLED_BY` lists, so it passed flags the tools reject.
`assurance_case.py --check`, `blob_conversion_coverage.py --list`,
`checker_selftest_check.py --selftest`, `dead_rule_sweep.py --selftest`,
`entry_point_scope_check.py --selftest`,
`role_gate_negative_coverage.py --check` — all `error: unrecognized arguments`.
Driven: `checker_selftest_check.py --fixtures` is **EXIT 0**, 10/10 fixtures.

**EXACT NEXT STEP:** the 53 reds and 46 genuine could-not-runs are **not routed
yet** — that is real remaining work and it is honest to say so rather than imply
a sweep plus a count is a routing. Route each to its owner from
`docs/tool-owner-map.json` with its reproducing command, **after** re-deriving
the mode from `add_argument` only, not from a substring. The raw rows are in the
worktree at `_sweep/rows.json`; **the worktree is scratch and will be removed**,
so re-run rather than cite it.

**AND THE 188 BARE RUNS ARE THE bigger finding than any count here:** for those
tools there is no read-only mode to ask for, so "run it once safely" is not
available, which is why this whole sweep had to happen in a worktree.

---

## 11. Still to push at the time of writing

    git fetch origin && git rebase origin/main
    git push origin main:refs/heads/main      # explicit refspec; the gate
                                              # denies "no ref lines on stdin"

Carrying the §8-defect-3 ledger-key fix, the 4 new arms, the cleaned
`docs/scrutiny-flags.json`, and this file. **The gate will flag this push too**
— it touches `tools/sairn_push_gate_hook.py` — and that is correct.

**A gate-freshness notice fired on the last push:** *"the push gate that just ran
is NOT the one on origin/main."* True and expected — I had just changed it. **So
that push's clean pass is a could-not-tell, not a full pass**, and the next push
is the one that gets the real answer.

---

## 12. What this session did NOT do

* **Did not discharge a review obligation.** 24 eligible; cody holds the file.
* **Did not route the 53 reds / 46 could-not-runs** from item 9. Counted, not
  routed.
* **Did not profile the 600s sweep**, so *which* checker is slow is unknown.
* **Did not measure the WEAKENING false-positive rate beyond n=1.**
* **Did not touch** `docs/tier-a-reviews.json`, `docs/METHODOLOGY.md`,
  `docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/TOOLING-INVENTORY.md` (by hand),
  `tools/tooling_inventory.py`, `tools/dead_rule_sweep.py` — all under live
  claims. Items 5 and 10 are routed artifacts and routed text, not edits.
* **Read no auditor log**, per the build-agent lane.
* **Live-verified nothing against a deployment** — every item is a build-time
  tool, a hook or a document.
* **Closed only findings I originated**, and reclassified none I did not.
