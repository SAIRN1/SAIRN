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

**Measured occurrences, hank (b61, 2026-10-28) -- the class is not cody-only:**
- The b61 docs commit was refused 3 times out of 3, every time with `cannot lock ref 'refs/heads/main': is at X but
  expected Y`. Each was a plain `git push` after fetch and rebase, and the gate PASSED each time.
- origin moved `80d753ef1 -> fe0127562 -> 8798af1a5`, then `0f93cad83 -> b4cea6792`, each during one gate run.
- It was bounded by hand at one retry per dispatch, so it needed three human-timed dispatches and still did not land.

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
- ~~**The skip is in a scratchpad script.**~~ **CLOSED (hank b61): the durable form is in `tools/push_retry.py --loop`.**
  - It is the same rule:
    1. The gate must have PASSED on this run. That means a full push that reached the remote and was refused as `transient`.
    2. The `git patch-id --stable` set of `origin/main..HEAD` must be unchanged since then.
    3. The incoming commits must touch none of our files, and none of `docs/CRITICALITY-TIERS.md`,
       `tools/sairn_push_gate_hook.py` or `.githooks/`.
  - If any of these fails or cannot be read, the retry runs the full gate.
  - A skip pushes `--no-verify` and is recorded in `docs/BYPASS-LOG.jsonl` under cody's check name.
  - The default is 5 attempts. The push has no timeout (b61, `79c4f10cf`).
  - Selftest: 15 C1 arms. 4 mutants go red: no patch-id compare, no overlap check, a skip armed after a gate refusal,
    and a skip never armed.
- **STANDING PATTERN for all 4 build agents (Michael, hank b61): push through `python tools/push_retry.py --loop`,
  never a bare or hand-looped `git push`.**
  - The compare-before-update-ref is git's own: the remote's expected-old-value check is the `cannot lock ref` refusal.
  - What closes the race is responding to it within seconds:
    1. fetch;
    2. rebase;
    3. re-compare the outgoing patch-ids against the gated set;
    4. push without re-paying the gate when nothing of ours changed.
  - A scratchpad `push_fast.sh` and bare `git push` retries are superseded by this.
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

---

## C3. A GATE-SKIPPED (PURE-BASE) PUSH IS NOT RE-CHECKED AGAINST THE NEW BASE

**This resolves the UNVERIFIED flag in cody b56, as Michael asked in b57: decide, implement, and log the decision.**

**Phase / sub-phase / cause:** design -> verification scope -> **due to** a validation that ran over (our patches + the OLD base), reused for (our patches + the NEW base). The C1 skip rule shows that no FILE overlaps. Some checks, though, read the WHOLE TREE, and for those two halves that were each validated can still disagree.

**DECISION: YES. A lightweight whole-tree re-check runs on every pure-base retry, before `--no-verify`.** It is three checks, chosen because they are the whole-tree checks whose answer can change without any file overlap:

| check | why the base move can turn it red | measured |
|---|---|---|
| `tools/defect_register.py --check` | a rebase rewrites our SHAs, and the incoming commits add records | 16 s |
| `tools/master_plan.py --check` | it is derived from EVERY test, resource and tier, so a test from either side changes it | 14 s |
| `tools/traceability_matrix.py --check` | the same: one new test file moves the traced/untraced counts | 15 s |

- **Cost:** run in parallel, it takes **18 s**, measured. The full gate takes 75 s to about 4 min. The remote moves every 1–3 min under auto-mode (C1). So the re-check fits inside the window that the full gate keeps missing.
- **On any red:**
  - the derived documents are regenerated and committed;
  - the try falls back to the FULL gate.
  - A red never reaches `--no-verify`.
- **Recorded:** the skip record in `gate_skip.log` and `docs/BYPASS-LOG.jsonl` says that the re-check ran and was green.

**Why these three and not the whole gate.** The gate's other checks are file-local or range-local: syntax, credential patterns, Tier A obligations, register feed, external files and probe anchors. They read our patches, and the patch-id equality in C1 already proves those are byte-identical. Re-running them would re-answer a question that has already been answered. Only a check that reads files outside our range can change its answer when the base moves.

**This is not hypothetical, measured cody b57.** One new test file, `tests/mech_backup_not_silent.js`, turned BOTH `master_plan --check` and `traceability_matrix --check` red, with exit 1:
- 1054 → 1055 test files;
- 274 → 275 untraced.

A pure-base push carrying a change like that, on top of a base whose own push had regenerated those documents, would have published stale derived documents with the gate skipped.

**What it still does NOT cover:**
- **A check that is slow AND whole-tree,** such as the push gate's Tier A tier lookup against a re-tiered register. If the incoming commits re-tier a resource that our files touch, the obligation verdict could differ. **Mitigated in the same batch:** if the incoming commits touch `docs/CRITICALITY-TIERS.md`, `tools/sairn_push_gate_hook.py` or `.githooks/`, the try always re-runs the FULL gate. The overlap rule cannot see these files, because they are what the gate itself reads. The list is exactly those three. A new whole-tree input to the gate has to be added to it by hand, which is the remaining gap.
- ~~**The mechanism lives in a scratchpad script** (`push_once.sh`).~~ **Superseded cody b58.** The decision is now `tools/pure_base_skip.py`: exit 0 = skip, anything else (1 gate, 2 could not decide) = full gate. The scratchpad script only acts on its exit code.
  - **The re-gate list is DERIVED, not the three hand-listed files.** It is `docs/CRITICALITY-TIERS.md`, all of `.githooks/`, the hook, and every `tools/*.py|js` the hook or `.githooks/pre-push` names or imports: 41 at b58. That closes the "added by hand" gap above. If fewer than 20 are found, the regex has lost its anchor, and the tool exits 2 rather than trusting a short list.
  - **Test-covered:** `tests/run_pure_base_skip_probe.py`, 22 arms. Each of the tier register, two hook files, the hook and a gate-run tool forces GATE. So do re-check rc 1, 2 and did-not-run. An underivable or short read set gives COULD NOT DECIDE. Two ablation arms remove the re-gate rule and the floor, and require the matching arms to flip to SKIP.
  - Moving it into cc's `tools/push_retry.py` is still cc's routing (C1). That is now a call to this tool, not a port of shell logic.

---

## C4. A REMEDY GATED ON AN UNRELATED CONDITION (cc b70)

**Phase / sub-phase / cause:** construction -> automation script (push loop)
-> **due to** a fix being placed inside the branch of a DIFFERENT decision, so
it runs only when that unrelated condition happens to hold. The failure it
exists to prevent then recurs on every other path.

**What it looks like:** a retry loop that keeps failing the same way. The
fix exists in the script, but it never runs on the path that is actually
failing.

**Measured occurrences:**
- **`tools/push_retry.py`, found 2026-10-05.** Derived-doc regeneration sat
  inside `if behind > 0:`. With nothing behind, the loop made six identical
  refused pushes and never regenerated. Fixed by extracting
  `_regenerate_and_fold()` and calling it after every rebase (line 1312) and
  on any refusal that names a generated document (line 1391).
- **cody's scratchpad `push_once.sh`, cody b62, routed as O7.** It regenerated
  `MASTER-PLAN` and `traceability-matrix` only inside
  `if grep -q "whole-tree re-check not green"`, the pure-base-skip decision.
  So:
  - in gate mode the full gate ran on stale documents and refused twice on
    `derived-docs`, which is cody's b62 double refusal;
  - `TOOLING-INVENTORY` was never regenerated on either path.
  - cc b70 confirmed this in the script's source. The fix is in
    `docs/2026-10-29-cc-b70-o7-push-script.md`: regenerate all three
    unconditionally after the rebase and BEFORE the skip decision. The
    recommendation is to retire the script for `tools/push_retry.py`, which
    already does this.

**Cause tags for this batch's fixes (cc b70, lifecycle phase -> sub-phase -> cause):**

| Fix | Tag |
|---|---|
| O7 push-script regeneration (routed fix, cody's script) | construction -> automation script -> remedy gated on an unrelated condition (this class) |

The Tier A discharges, the CRLF cross-check and the field-scope credential
check were reviews and checks. They changed no code, so they carry no fix
tag. The CRLF cross-check found no persisted text-mode log writer in hank's,
cody's or fourth's tools. All 4 append-mode hits are temp fixtures inside
test probes.

**Mitigation, and what it does not cover:**
- `push_retry.py` is correct.
- A private scratchpad loop is invisible to every check and review. Here, it
  diverged from the tracked tool that had already been fixed for this exact
  class.
- The standing remedy is to push through the tracked tool, not a private
  copy of its logic.
---

## C5. CAUSE TAGS FOR EVERY FIX IN cody b63 (Michael's b63 instruction)

**Each fix landed in b63 is tagged phase -> sub-phase -> cause, in the vocabulary of `tools/defect_register.py` (phases: requirement, design, coding, config, unknown).** The tags are listed here because the instruction named this file. The two that are a recurring CLASS rather than a one-off say so, with their earlier occurrences.

| fix (commit subject) | phase -> sub-phase -> **due to** cause | one-off or class |
|---|---|---|
| `saveDoc` could save a duplicate (sairnmechanical, gap d) | coding -> async UI state / re-entrancy -> **due to** a toast made to WAIT on an async server push (b57) while its trigger stayed live, so a second click re-entered the save | **class** -- any push-then-toast save path. Recurrence is open in the register record: saveQuote, saveCheck and other apps' await-then-toast paths were not swept |
| local-write-before-push untested (gap a) | coding -> test assertions / ordering -> **due to** tests that asserted the OUTCOME (a row exists) and never the ORDER (stored before the push was called), so moving the write into the `.then` stayed green | one-off |
| mechPushOne "truthy on success" untested (gap b) | coding -> test assertions / return contract -> **due to** a comment stating a return contract (b57) with no arm holding it, so the pre-b57 return passed | one-off |
| unprovisioned fixture had the wrong shape (gap c) | coding -> test fixtures -> **due to** a fixture written from the ASSUMED response shape (`ok:false`) rather than read from the server branch (`ok:true, data:[], provisioned:false`), so the arm never reached the branch the server drives | **class** -- C2's sibling: a fixture that cannot reach the code it claims to test is a check that "passes" for work it never did |
| redaction wiring probe exit 2 since b58 | coding -> anchor selection -> **due to** a probe anchored on a LITERAL fallback line (`rows[0].data : mPayload`) that a later, correct fix (b58 `10e914b1`) deleted, which turned a structural property into a text match | **class** -- the same shape as `docs/recurring-bug-classes.md` "anchor selection" and the b58 sabotage-probe anchor block on `refuseUnconfirmedWrite` |
| sd-data.js:2301 semgrep hit suppressed (not a defect) | design -> checker exception handling -> **due to** a rule with no way to mark one verified-intended call, so a known-good line kept `run_semgrep` red on every run and a real hit would have read as the usual one | one-off (the finding itself is "intended, verified") |

**Not tagged, because they are not fixes:**
- the H1/H2 routed index rows (item 4);
- the #909 rule-name list (item 3).

---

## C5. A CHECK WITH NO OPERATOR, OR A WORKSPACE WITH NO REAPER (cc b71)

**Phase / sub-phase / cause:** operations -> scheduling / workspace hygiene
-> **due to** a tool or workspace being created by one action, with no second
action responsible for running it or removing it. It stays dormant or stale,
and nothing reports that.

**Measured occurrences:**
- **`tools/sairn_watchdog.py`.**
  - Built in cc b67 "not operated" by instruction.
  - It was first run by hand in cc b68.
  - hank was named operator in cc b69, at batch start only.
  - Between those points, its REGISTRY-BEHIND findings (hank b61 vs b63, then
    b65 vs b66) sat unflagged unless somebody started a batch.
  - Fixed cc b71: Windows Task Scheduler task `SAIRN-watchdog`, every 15
    minutes, reading the Drive handoffs. The first scheduled run wrote hank
    b65 vs b66 at 12:54:26Z.
- **Three Claude Code agent worktrees under `Documents/SAIRN/.claude/worktrees/`.**
  - They were still registered in `git worktree list` long after their
    sessions ended, and each `.git` link file read as a stray `.git` in the
    tree.
  - Fixed cc b71, on Michael's choice: `git worktree remove` for the two
    clean ones (`sairn-precommit-lessons-and-tools`, and
    `stonedesk-chamfered-corners` with --force for `__pycache__` only). Their
    branches are kept.
  - `agent-ad8f80cc19dee3bb4` is KEPT: it holds an uncommitted `api/claude.js`
    change.

**Cause tags for this batch's fixes (cc b71, lifecycle phase -> sub-phase -> cause):**

| Fix | Tag |
|---|---|
| Watchdog scheduled every 15 min | operations -> scheduling -> a check with no operator on a cadence (this class) |
| Two stale agent worktrees removed | operations -> workspace hygiene -> worktrees created per agent session, no reaper (this class) |

**Not fixed this batch, stated:** `ctxmeter.py`'s false-floor bug. No file of
that name exists in the four builder clones, `~/.claude`, the session
scratchpads, the Drive status folder or a 4-deep home search. Michael chose to
skip it.

**Mitigation, and what it does not cover:**
- The scheduled task runs only while the user is logged on, because the
  Drive mount must be present.
- A worktree with uncommitted work is never reaped automatically. That is a
  human decision every time.

---

## C6. CAUSE TAGS FOR EVERY FIX IN fourth b68

**Each fix that landed in b68 is tagged phase -> sub-phase -> cause.** The vocabulary is `tools/defect_register.py`'s. A fix that belongs to a standing class names the class.

| fix (commit) | phase -> sub-phase -> **due to** cause | one-off or class |
|---|---|---|
| bld session-flag arm accepted `!BLD_SESSION_REQUIRED[key]` and `false&&BLD_SESSION_REQUIRED[key]` (`a4de92258`, cause 1) | coding -> test assertions / criterion definition -> **due to** "the argument MENTIONS the map" standing in for "the argument IS the map value". A regex with `[^)]*` before the name admits any operator in front of it | **class.** The proxy shape matches the b17 `key==='bld_bids'` substring and the b23/b28 arms in the same file. Other suites matching an argument with `[^)]*<name>` were not swept |
| the same arm's call-site loop named `bldHydrateOne`, which does not exist (`a4de92258`, cause 2) | coding -> error handling / population -> **due to** a `try { fn(name) } catch { return }` that turned "not found" into a pass, under a comment saying absence is not a pass | **class C2** (not-run read as pass) |
| sairncash: a typed $0 prior-year tax read as "not provided" (`63272f29d`) | coding -> input handling / falsy zero -> **due to** `Number(v) \|\| null` on save, `if (x)` in `calcQuarterlySetAside()`, and `x \|\| ''` on display. Each treats 0 as absent | **class.** "Falsy zero" is the same shape as the b57 `(Number(null)\|\|0)` rendering that this file's own comment warns about. Other apps' `\|\| null` saves of money fields were not swept |

**Not tagged, because they are not fixes:** the bld_bids Tier A discharge (the review itself), and the live check of `sairnmechanical.html`.
