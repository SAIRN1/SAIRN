# Hank inventory — batch 3, 2026-10-05

Companion to `docs/2026-10-05-register-corrections-hank.md` (items 5–7, which
carries the §0 premise log for all thirteen). This file is what the code half of
the batch found and did not take.

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `rebase_state_guard`: env-prefix, `env`, grouping, `sh -c` and `xargs` bypasses closed | `37d29ef0` | live before/after through `forbidden_forms()`: **15 of 34 wrong → 0 of 34**; probe **31/0** (was 27/0); 15-case negative sweep, 0 false positives |
| `report_only_checks`: reachability derived, persisted, surfaced in `--list`, which now **exits 1** when a registered checker is dead | `1c24f411` | `--list` driven in the no-measurement state; round-trip driven |
| `push_retry`: can print its own usage | `1c24f411` | probe **7/0**, and **5 of 7 arms FAIL on the unfixed tool** |
| The reachability writer's own `io.open` bug | `058c6d31` | caught by its own error handler; round-trip re-driven |
| Hook manifest regenerated, 6 drifts, all traced | `7c3695b3` | `hook_integrity_check` exit 0, `covers itself: yes`, converged in one step |
| Three generated docs | `516fb1ca` | push gate exit 1 cleared; rebase conflict in `traceability-matrix.md` resolved by **re-derivation**, 0 conflict markers (PR §2.5) |
| My two checkers moved out of the dead tail | *(this push)* | **re-measured after the move: reached 38, dead 35** (was 36/37); both now run at cum **2.8s** and **4.7s**. The predicted displacement was ZERO and the measurement confirmed it exactly |

---

## 2. The measurement that changed the answer

The brief said indices 44–72 never run. **Derived at HEAD from a full 600-second
sweep, it is worse: 37 of 73, boundary at index 36.**

    budget 600s, effective cutoff 540s
    reached 36, NEVER REACHED 37
    entry 35  comment_sensitivity_check.py   215.4s   cumulative 548.7s
    entry 36  metamorphic_check.py           first casualty

**One checker costs 215.4 seconds — 40% of the entire budget.** My earlier
figure of 29 was taken from a run where that tool had not yet dominated; the
boundary moved eight slots. So the tail is not a slow accumulation of 73 small
costs, it is **one tool and a long shadow**, and that is the lever:
`comment_sensitivity_check.py` plus `sairn_dead_button_audit.py` (108.2s) are
**54% of the budget between them**.

That is why moving my two was safe and is stated as arithmetic rather than
asserted: entry 35 *started* at cumulative 333.3s, far under the 540s line.
Inserting 3.15s ahead of it moves that start to 336.5s — still under — so the
same 36 entries clear the line and two more run ahead of them. **Nothing is
displaced.** A 60-second insertion would not have been safe, and the difference
is measurable rather than a matter of taste.

**THE PREDICTION WAS CHECKED RATHER THAN TRUSTED.** After the move, a second
full sweep reports **reached 38, never reached 35** -- exactly the 36 that
cleared before, plus my two, with my two at cumulative **2.8s** and **4.7s**.
Zero displacement, predicted from the first measurement and confirmed by the
second. Had it cost somebody their slot, this is where that would be recorded.

**It does not fix the 37.** Raising the budget, splitting the sweep, or capping
that one checker is a decision with an owner. Not taken.

---

## 3. Premise corrections — mine, and the brief's

| Claim | At HEAD |
|---|---|
| "an entry skips silently" (item 2) | **PARTLY FALSE.** `sweep()` already named every skipped tool, printed a dedicated block, and `main()` returned 1 (`:3425`). The silence was in `--list`, which returned 0 unconditionally. |
| "indices 44–72" | **37 of 73, from index 36.** |
| "largest `sb_perf` +1723/+429" | No such offsets. `sb_perf`'s real drifts are `:448` and `:4714`, and **neither is visible to the drift tool.** |
| "one `sb_ap` citation is unrepointed" | `sb_ap` row `:189` cites **nothing**. The unrepointed citation is **`sb_perf`'s**. |
| "`sc_encoder` −7/−7" | Both citations **correct and deliberate** (a read site and a comment the cell quotes). |
| My own "29 of 73" | **Superseded by 37**, same cause measured on a different day. |

---

## 4. Gaps — ranked

Every gap is internal tooling or process; **none is visible to a customer and no
competitor is affected**, so none is ranked on that axis and no competitor
evidence is cited, because there is none.

| # | Gap | Severity |
|---|---|---|
| **1** | **188 of 473 register citations are invisible to `citation_line_drift_check.py`** | **HIGH** |
| **2** | **35 of 73 registry entries never run (37 before my two moved); two tools are 54% of the budget** | **HIGH** |
| **3** | `push_retry --loop` does not regenerate when `behind == 0`, and swallows the gate's reason | **MODERATE** |
| **4** | 237 tools share the cp1252 precondition — a population, **not** 237 crashes | **MODERATE** |
| **5** | `citation_no_source_report` exits on its exempt population, not its defect bucket | **MODERATE** (carried) |
| **6** | Nothing checks an index row against the repo | **MODERATE** (carried) |
| **7** | Measured-vs-advised convention | **MODERATE** (carried, now 3 instances) |

### 1. The drift checker reads 60% of its subject and does not say so — HIGH

`citation_line_drift_check.py` extracts citations with `` `:(\d+)` `` — the bare
form only. Over `docs/CRITICALITY-TIERS.md` at HEAD:

    bare  `:NNN`            285   <- the only form the tool reads
    named `file.html:NNN`   188   <- INVISIBLE to it
    rows carrying a named-form citation: 147

**Every verdict that tool has printed covers 285 of 473 citations and presents
it as the answer.** `sb_perf`'s two genuinely drifted citations sat in the
invisible 188 — found by reading the row, not by the tool. This is the
coverage-disclosure class, in the same function I corrected yesterday for
presenting an inference as an instruction.

**Not fixed:** a criteria change to a checker needs its own claim and its own
known-bad control, and I already hold one change to that file this week. The
measurement is in `docs/2026-10-05-register-corrections-hank.md` §4 so it need
not be re-derived. **Fixing the regex without first measuring how many of the
188 are sound would turn a silent 60% into a loud false-positive storm** — the
named form includes `api/sd-data.js:2051`, which is a different file from the
app the tool was pointed at.

### 2. Thirty-five dead entries, and two tools own the budget — HIGH

See §2. What is new since my last inventory is **where the cost is**: not spread,
concentrated. `comment_sensitivity_check.py` 215.4s + `sairn_dead_button_audit.py`
108.2s = 323.6s of a 540s cutoff. **Capping either one would revive roughly a
dozen entries**, which makes this a cheaper decision than it looked when the
tail was assumed to be death by a thousand cuts.

### 3. The retry loop cannot fix the failure it is named for — MODERATE

`push_retry.py --loop` advertises *fetch → rebase → regenerate → push*. Observed
today, both directions:

* `behind 1` → printed *"regenerated documents folded into your own commit"*, pushed.
* `behind 0`, six consecutive attempts → **no regeneration**, six identical
  `push refused: error: failed to push some refs` lines.

The gate's actual reason — three named generated documents, with the command to
fix each — appeared only on a bare `git push`. **So the loop both fails to do
the regeneration and hides why it failed**, and the combination is what makes it
costly: a session trusting the loop sees six opaque refusals.

Not fixed: I hold a claim on that file for the encoding bug, and this is a
different defect in it. It also deserves a known-bad control that drives the
`behind == 0` path, which is the one nobody wrote.

### 4. The cp1252 population — MODERATE, and deliberately not a crash count

**237 of 286 `tools/*.py` carry non-ASCII with no `reconfigure`.** That is a
**precondition count**. Two spot-checks (`report_only_checks.py`,
`accepted_risk_scan.py`) have the precondition and exit 0, because whether it
fires depends on which non-ASCII reaches stdout on which path. **I am not
reporting 237 broken tools.** The real number needs a sweep that runs each one
and greps for `UnicodeEncodeError` — a tool, not a claim.

*(My own derivation script hit this bug mid-batch, three commits after I fixed
it in `push_retry`. Recorded because it is evidence the precondition is live,
not dormant.)*

---

## 5. What I will not claim

* **No live verification applies.** Four tools, two probes, four documents.
  Nothing deployed changed, so there is no deployed URL to check.
* **`SAIRN_SEED_GATE` was never used.** The gate refused this push once, for
  three stale generated documents, and it was right; the fix was to regenerate.
* **I did not review the 15 traced hook diffs for correctness** — only that each
  traces to a real commit. The manifest now reads clean, and a hook that was
  wrong when it was generated is still wrong.
* **I did not read the prose of the other 31 drifted rows** the tool flags
  across `sb_`, `sen_`, `sdn_`, `sc_` and `leg_`. After `sb_perf` and
  `sc_encoder` the base rate says roughly half will be deliberate citations.
* **I cannot see hover log #745** and did not infer its five repoints.
* **The `sdn_vendors` tier call is mine and is arguable** — rested on the
  `properties` precedent, stated in the corrections doc with the
  counter-argument.
* **The dead-entry figure is one measurement on one machine.** `comment_sensitivity_check.py`
  at 215.4s is what sets it, and a faster machine would move the boundary.
* **I ran `git stash` against a live background sweep earlier in this batch**,
  which invalidated one 600-second measurement. Recorded in `1c24f411`.
