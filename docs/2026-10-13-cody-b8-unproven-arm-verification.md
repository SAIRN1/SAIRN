# `unproven_arm_check` — VERIFIED AGAINST ITS OWN SPEC, not rebuilt

**cody, batch b8, 2026-10-14.** Item 4 of the b8 brief reads *"build
`unproven_arm_check` per `docs/2026-10-13-cody-b6-methodology-unproven.md`, with
a failing-first test."*

**IT ALREADY EXISTS. IT WAS BUILT IN b7 AND IT LANDED.** Building a second one
would be the orthogonal-change failure, so what b8 did instead is **check that
what exists is what the spec asked for, and re-measure it at this HEAD.** This
document is that check. Nothing in `tools/` or `tests/` was edited by it.

    tools/unproven_arm_check.py      23,909 bytes, tracked
    tests/run_unproven_arm_probe.py  20,835 bytes, tracked

**NAME DIFFERENCE, DECLARED:** my b8 claim string listed
`tests/run_unproven_arm_check_probe.py`. The real file is
`tests/run_unproven_arm_probe.py`. **The claim is wrong, not the repo** — the
file predates the claim by a day. No file was created under the claimed name;
that would have made two probes for one tool.

---

## 1. The spec, clause by clause, against what is on disk

`docs/2026-10-13-cody-b6-methodology-unproven.md` §4 asked for a report-only
tool with three signals, a control pair, a current-count measurement, and one
named false-positive shape. All six clauses:

| the spec asked for | present? | where |
|---|---|---|
| **A1** a file using UNPROVEN whose summary print carries no unproven count | yes | `tools/unproven_arm_check.py:18-19`, implemented `:337-350` |
| **A2** a `sys.exit(0)` reachable with an unproven arm recorded | yes | `:20-22`, implemented `:380-391` |
| **A3** the inverse — a printed unproven count the file never sets | yes | `:23-25` |
| **report-only**, as a decision held in writing | yes | `:32-45`, and registered with its measured count in `tools/report_only_checks.py:161-177` |
| **the control pair** | yes, in **both directions** | `tests/run_unproven_arm_probe.py`, §2 below |
| **the named false-positive shape** — *"a file that merely mentions UNPROVEN in prose must not trip it, and this document's own name will be in the grep output"* | yes, and it is an ARM | arms 2a / 2b / 2c, §2 |

**And the spec's own carve-out is honoured.** §4's rule *"match on the
summary/exit construct, not the word"* is what arms 2a-2c prove; §3's sub-rule
*"an arm may be unproven at most once; twice is a FAILURE"* is a property of two
consecutive RUNS, and the tool **says out loud that it does not check it** —
`A4 ("unproven at most once") is NOT CHECKED` appears in its own output rather
than being quietly absent. **That is the difference between a gap and a silence.**

---

## 2. The failing-first requirement — satisfied by arms that FIRE, re-measured here

A detector's failing-first test is the arm that **fires on a planted defect** and
would go green if the detector were removed. All fifteen arms, verbatim from the
run:

    python tests/run_unproven_arm_probe.py        EXIT 0
      ok    1a. A1 FIRES on verdict-printed-never-counted (the b5 defect)
      ok    1b. A1 STAYS SILENT when the summary carries the count
      ok    2a. a PROSE sentence (check4_probe.py:526 verbatim) trips NOTHING
      ok    2b. a COMMENT mention trips NOTHING
      ok    2c. a verdict print inside a TRIPLE-QUOTED fixture body trips NOTHING
      ok    3a. A2 FIRES when the exit expression cannot see the unproven counter
      ok    3b. A2 STAYS SILENT when the exit expression names it
      ok    3d. A2 FIRES on the boolean-outcome-flag form (check4_probe.py shape)
      ok    3e. A2 STAYS SILENT on the delegating `sys.exit(main())` shape
      ok    3f. ABLATION -- A2 fires on BOTH real instances at c465743b~1
      ok    3c. A3 FIRES on a printed count nothing ever sets
      ok    4a. A1 FIRES on the .test.js form
      ok    4b. A1 STAYS SILENT on the correct .test.js form
      ok    5. an empty tests/ tree -> exit 2 COULD NOT RUN
      ok    6. this probe is CLEAN against its own subject

    15 passed, 0 failed, 0 unproven

**Five arms are FIRES arms and five are STAYS-SILENT arms.** A detector tested
only one way is the vacuous-pass shape this repo keeps paying for; a `FIRES`
arm without a `STAYS SILENT` partner is a detector nobody has shown to be
discriminating. Both halves are present for A1 and A2, and A3 has its FIRES arm.

**Arm 5 is the fail-closed arm**, and it is the one worth naming: an empty
`tests/` tree gives **exit 2 COULD NOT RUN**, not exit 0. A checker that reports
clean when it had nothing to read is the defect `CLAUDE.md` puts above all
others.

**Arm 3f is the ablation**, and it is the reason to believe the real-tree zero:
against the only two real instances (`check4_probe.py` and `check7_probe.py` at
`c465743b~1`) the FIRST version of the tool caught **neither** — it quarantined
both as NOT ASSESSED, which is the right failure direction and still a checker
that cannot fire. **0 of 2 before, 2 of 2 after.**

---

## 3. The current count, RE-MEASURED at this HEAD and it moved

    python tools/unproven_arm_check.py            EXIT 0
      files scanned                             404
      with a pass/fail summary construct        151
      with an unproven mechanism                  3
      IN SCOPE for A1 (summary + mechanism)       3
          tests/mar_billing_grant.test.js
          tests/run_unproven_arm_probe.py
          tests/run_worktree_isolation_probe.py
      A1 NOT ASSESSED (mechanism, no summary)     0
      A1 findings 0 · A2 findings 0 · A3 findings 0

**b7 measured 399 / 146 / 1. b8 measures 404 / 151 / 3.** The denominator moved
because files were added, and the in-scope count tripled because **two of the
three in-scope files are b7's and b8's own work**. That is a measurement with a
cause, not drift — and it is the reason the probe **reports** the real-tree
figure rather than asserting it: an assertion that the tree is clean turns every
future real finding into a failure of the probe.

**THE NEW MAR SUITE IS IN SCOPE AND CLEAN, AND THAT IS THIS SESSION'S ONE REAL
TEST OF THE TOOL.** `tests/mar_billing_grant.test.js` was written today, counts
`unproven` in a third counter, names it in its summary line, and exits
`fail ? 1 : (unproven ? 3 : 0)`. The tool was pointed at it without being told
it existed, found it, scoped it, and passed it. **A checker whose scope grows by
itself when a conforming file appears is the only kind worth keeping**, and the
A1 NOT ASSESSED count being 0 is what says the growth was scoped rather than
quarantined.

**NEITHER NUMBER MAY BE QUOTED ALONE** — the tool prints that line itself. `0
findings over 404 files` with `3 in scope` is a much smaller claim than `0
findings over 404 files`, and only the first is true.

---

## 4. What this does NOT establish

* **A4 is unchecked**, by design and out loud (§1).
* **Report-only is a decision, not an accident**, and it is unchanged: nothing
  in `tools/sairn_push_gate_hook.py` reads this tool. Promoting it is a separate
  judgement with an owner, and b8 did not make it.
* **The zero is a zero over 3 in-scope files**, two of which are my own. The
  tool has not yet been exercised against a file written by somebody who had
  never heard of it. That is the next real test and it arrives on its own.

---

*Measured at `433860be` (`origin/main` at `aeea051f`, unmerged when these were
run). Both commands are named above; re-run them rather than quoting these
figures.*
