# Recurring bug classes, part 2: standing CLASSES, one per section

**Started 2026-10-28 (cody b56), on Michael's b56 instruction.** `docs/recurring-bug-classes.md` tags single defects in the form PHASE -> SUB-PHASE -> CAUSE, one row per defect. This file records a **class**: a shape that has already happened more than once, and will keep happening, with a name to count it by. It uses the same vocabulary as `tools/defect_register.py`.

Each section gives:
- what the class is;
- the measured occurrences;
- the cause;
- what is mitigated, and what is not.

---

## C1. PUSH RACE UNDER AUTO-MODE: gate duration > remote inter-commit interval

**Phase / sub-phase / cause:** config -> push protocol -> **due to** a pre-push gate whose runtime is longer than the gap between other agents' pushes. By the time the gate passes, the remote tip has moved, and the push is refused. Each retry rebases and pays the full gate cost again, so a retry only succeeds if the remote happens to stay still for a whole gate run.

**What it looks like:** `! [remote rejected] main -> main (cannot lock ref ...: is at X but expected Y)` or `! [rejected] (fetch first)`. The gate output above either line is a full PASS: the gate let the push through and the remote refused it.

**Measured occurrences, cody only:**
- **b53:** every push lost the race. The retry loop was then killed for low memory, and 15 commits stayed local for a batch.
- **b54:** b53's commits landed on attempt 2 of 5, and the b54 fix on attempt 3 of 5.
- **b55:**
  - The work landed on attempt 1.
  - The deliverables then failed all 5 bounded attempts: 2 were `cannot lock ref`, 3 were `fetch first`, and each gate run took about 4 minutes.
  - The deliverables included the `platform` claim release, so fourth's b60 stayed held on a claim that was already released locally.
- **b56:**
  - 1 `push_once.sh` attempt failed with `fetch first`.
  - 1 manual fetch, rebase and push failed: the gate took 75 s and `main` moved during it.
  - The pure-base retry described below landed on its first try at 17:22:01Z.

**Measured intervals:**
- **Gate:** 75 s to about 4 min per run. An `api/sd-data.js` range is the slow case.
- **Remote, 2026-10-28 12:00–17:20Z:** hank b59, hover b91, fourth and the claim commits landed every 1–7 minutes, and often less than 2 minutes apart.

**Cause, stated as a class:** the gate is a single long check run at the last moment against a moving target. The same code is re-validated on every retry even when nothing in it changed.

**MITIGATION (cody b56): a pure-base retry does not re-run the gate.** This is Michael's rule. It lives in the scratchpad `push_once.sh`, now the same file as `push_fast.sh`.
- It makes up to N attempts back to back: fetch, rebase, push. N is 10 by default.
- **A retry skips the gate only when BOTH of these hold:**
  1. The `git patch-id --stable` set of `origin/main..HEAD` is exactly the set the gate last PASSED. A pass is recorded only when the gate let the push reach the remote. So no commit of ours changed, whether by conflict, re-seat or a new commit.
  2. The incoming commits (`old merge-base..new origin/main`) touch none of the files our commits change.
- Anything else runs the full gate.
- Every skip is logged twice: in the scratchpad `gate_skip.log`, and in the repo's `docs/BYPASS-LOG.jsonl` through `tools/bypass_log.py record()`. That way `bypass_log.py` counts it as a pattern rather than it being remembered.

**NOT mitigated, and why it is still a class:**
- **The skip is in a scratchpad script.** Only the session that has it is covered. The durable form belongs in `tools/push_retry.py`, which cc owns: a `--attempts N` single-shot mode with this patch-id rule, and a git timeout longer than the gate's runtime (today it is 120 s). Routed to cc, as before.
- **The base move is not re-checked.** A skipped push never re-runs the whole-tree checks against the new base, such as the derived documents and the credential pattern over the combined range. Condition 2 bounds that risk, but does not remove it. The incoming commits passed their own gates; the combination of theirs and ours was not checked.
- **The real fix is gate duration.** It is either a gate fast enough to beat the interval, or a merge queue. Retry tactics only lower the loss rate.

---

## C2. A CHECK REPORTS SUCCESS FOR WORK IT NEVER DID (not-run read as pass)

**Phase / sub-phase / cause:** coding -> error handling / population -> **due to** an exit path where *could not run*, *read nothing* or *zero population* reaches the same exit code or verdict as *checked and clean*. PR §1.11 names it in general terms. This section exists because the shape keeps recurring inside the tools written to catch it.

**Measured occurrences:**
- **b52–b54:** 13 ratio tools were fixed. Their numerators and denominators included items that never ran or were skipped. The worst was `run_all_tests` counting not-run files as passing.
- **b55, checker_confidence:** an UNRUNNABLE checker was rated HIGH, and `--json` had been broken since 2026-10-14, so its probe's fleet arms never ran.
- **b55, cody's own tools:** 9 of 41 were affected:
  - rework_tracker read 3,524 of 10,587 commits and gave no unread reason;
  - dead_rule_sweep gave CLEAN for a typo'd `--tool`;
  - master_plan published every app as TIERED when its tier check had failed;
  - and six more.
- **b56:**
  - gap_ledger: a Synthesis section in an unread shape yielded zero rows, read as "no gaps". Live case: sairnbiz.
  - write_without_readback: a writer reachable only through an alias produced no record at all. Live case: sairnmechanical `mechPushOne`.

**Standing practice, from Michael b56 item 5.** Before trusting any tool's green, a tool that is touched gets a quick sanity pass on two questions: **does it actually run, and does it actually check anything?** An exit code of 0 answers neither. The pass covers:
- **The population.** Is it non-zero? Is it the one the tool claims?
- **Every subprocess and read.** Is a failure a third state, or is it folded into an empty result?
- **The verdict at zero.** What does the tool print and return when it read nothing?
