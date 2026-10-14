# The first 12 of fourth b10's 36 never-driven suites — DRIVEN

**cody, batch b8, 2026-10-14.** Routed by
`docs/2026-10-13-fourth-b10-undriven-suites.md`, whose cody section lists 36
registered red suites under `tests/` that **had never been driven since being
registered**. This closes the first 12 — numbers 1 to 12 of that table, in its
order.

**DRIVEN IN AN ISOLATED GIT WORKTREE, NOT THE LIVE CLONE**, because fourth's own
next-step says so and because several of these write when run. Worktree created
from `433860be`, every `python tests/...` run with cwd inside it, removed with
`git worktree remove --force` + `git worktree prune` afterwards and
`git worktree list` confirmed back to the live clone alone.

**ONE AT A TIME, exit code read from `echo "EXIT=$?"` on its own line after the
command**, never inferred from the text and never piped through anything that
would mask it. Full output per suite redirected to its own log inside the
worktree; the tails below come from those logs.

---

## 0. THE HEADLINE, AND IT IS NOT WHAT THE REGISTER EXPECTED

| real exit | suites | what the routing rule says to do |
|---|---|---|
| **1** | **11** | fill in `why` if blank |
| **TIMEOUT at 180s** | **1** (suite 11) | **LEAVE IN PLACE** — third state |
| **0** | **ZERO** | *(would have been: move the entry OUT of `entries`)* |
| 2 / 3 | zero as a suite's own exit | — |

**NOT ONE OF THE TWELVE HAS GONE GREEN, so no register entry is removed.** That
is the measurement, and it is worth stating plainly because the register's own
rule — *an entry whose suite has gone green "swallows the next real failure of
that file"* — is the reason the sweep was asked for, and it turned out not to
apply to any of these twelve.

**THREE `why` FIELDS WERE BLANK AND ARE NOW FILLED** (suites 7, 8, 10), per
fourth's exit-1 rule. **One stored `tail` was found to CONTRADICT the
re-measurement** (suite 6) and the contradiction was appended rather than the
row overwritten — §3.

**EVERY SUITE WAS RUN TWICE** except 11 and 12. Ten pairs were byte-identical
with the same exit code. The reason for the re-runs is in §4 and it is my own
error, not a property of the suites.

---

## 1. THE TWELVE, with evidence and `file:line`

Every `file:line` below was **independently re-verified by reading that exact
line in the live clone**, not taken from the runner's report.

### 1. `tests/run_index_duplicate_probe.py` — **EXIT 1** · 12 PASS / 1 FAIL
`tests/run_index_duplicate_probe.py:143` — `sys.exit(1 if failures else 0)`
Failing arm: **`7a  the real index has no undeclared duplicate pairs`** (tool
exit 1; **835 rows compared**).
**This is the suite finding a real defect in the index, not a broken suite.**
Arm `7b` passed — *"and it compared a real number of rows"* — which is the
control that stops `7a` from being a zero-row vacuous read. Every synthetic arm
passed, including the strikethrough and one-defect-two-apps cases.
Register `tail` was `  7a  the real index has no undeclared d…` — **agrees.**

### 2. `tests/run_nhi_clone_enumeration_probe.py` — **EXIT 1** · 5 passed / 3 failed
`tests/run_nhi_clone_enumeration_probe.py:178` — `sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)`
Failing arms, verbatim: *"THE ARM THAT MATTERS: a clone of the same remote NOT
named `SAIRN-*` is counted"*; *"and so is one whose name matches no convention
at all — the predicate is 'clone of the same origin', not a spelling"*;
*"exactly the 3 real same-origin clones, no more (got 1: `['SAIRN-me']`)"*.
**A REAL UNDERCOUNT, and the suite's own text says it is the THIRD instance of
it.** The enumeration filters by directory NAME rather than by remote, so a
same-origin clone that is not called `SAIRN-*` is invisible to a rotation
blast-radius calculation. Register `tail` `5 passed, 3 failed` — **agrees
exactly.**

### 3. `tests/run_nhi_register_write_flag_probe.py` — **EXIT 1** · 4 passed / 8 failed
`tests/run_nhi_register_write_flag_probe.py:244` — `sys.exit(main())`, and
`main` returns at `:240` — `return 1 if _fail else 0`
Failing arms: `A2 A3 A4 B1 B2 C1 C2 C3`.
**THESE EIGHT ARE A COULD-NOT-MEASURE FOLDED INTO FAIL, AND THE CAUSE IS THE
SANDBOX LOCATION.** The tool exits **2** with its own words: *"REFUSING: 78
candidate repositories in `C:\Users\marsh\AppData\Local\Temp`, which is above
the cap of 32 — this is not a clone parent… Run this from a real clone, or pass
`repo=` explicitly."* The probe builds its sandbox under `%TEMP%`, which is also
where the worktree lives, so **the tool's own safety cap fires and the probe
scores the refusal as eight failures.**
**The tool is behaving correctly and the probe cannot see the difference** — the
same third-state collapse §5 is about. **This result is therefore NOT evidence
about the tool**, and the entry stays red with that said rather than guessed.
What DID pass is the part that still means something: `D1` *"ANCHOR: the guard
is still `if '--write' not in argv:`"*, `D2`, and `D3` *"the sweep refuses to
measure a non-git sandbox (exit 2, COULD NOT RUN) rather than reporting this
tool clean."*
**Register `tail` said `5 passed, 7 failed`; measured `4 passed, 8 failed` —
CHANGED**, and plausibly only because `%TEMP%` has accumulated repositories
since.

### 4. `tests/run_rebase_resolve_probe.py` — **EXIT 1** · 7 ok / 8 failures
`tests/run_rebase_resolve_probe.py:213` — `sys.exit(1 if fails else 0)`
Failing arms: *"…and the tool REFUSES it, exit 1"*, *"…and names the file"*,
*"…and classifies it SOURCE, not generated"*, *"`--dry` reports it as GENERATED
and changes nothing"*, *"…and NO conflict marker survives in the staged file"*,
*"MIXED: one source + one generated → REFUSES, exit 1"*, *"a file naming a
generator that does not exist is COULD NOT TELL (2)"*, *"…and says nothing was
staged"*.
**ONE SYMPTOM EXPLAINS ALL EIGHT: the tool prints `No conflicted files. Nothing
to do.` and exits 0 where the probe created a real rebase conflict.** So the
tool is not seeing the conflict the fixture set up — a detection failure, not
eight classifier bugs. **A tool that answers "nothing to do" on a real conflict
is the silent-failure shape, and it is the highest-value finding in these
twelve.** Register `tail` named the MIXED arm — **agrees.**

### 5. `tests/run_removal_path_probe.py` — **EXIT 1** · 37 ok / 1 FAILED
`tests/run_removal_path_probe.py:432` — `sys.exit(1)`, inside `if fails:`
Failing arm: **`the real SAIRN baseline currently accounts for every one`** —
`expected 0, actual 1`.
**37 of 38 green and the one red arm is the real-repo baseline, not a fixture.**
Every synthetic arm passed, including the derived-resource exemptions being
*"COUNTED AND NAMED, not silently subtracted"*. So the classifier works and
**one real resource's removal path is unaccounted for.** Register `tail`
`1 FAILED` — **agrees.**

### 6. `tests/run_report_only_checks_probe.py` — **EXIT 1** · 85 checks / 4 failed · ~130s
`tests/run_report_only_checks_probe.py:989` — `sys.exit(1 if bad else 0)`
Failing arms: *"H2 and prints nothing"*, *"H4 a prose mention is not a push"*,
*"J6 the hook entry declares a timeout at all"*, *"J7 and the sweep budget
equals it rather than a hardcoded fallback"*.
**THE REGISTER SAYS THIS SUITE TIMED OUT AFTER 300s. IT DID NOT TIME OUT — it
finished in roughly 130s and named its four arms.** That is a changed reason,
handled in §3. J6/J7 are a pair about the hook's own declared timeout, which is
plausibly the same subject as the original hang. 81 of 85 green, including the
whole shard-rotation block and the fail-closed budget arm.

### 7. `tests/run_rewrite_convergence_probe.py` — **EXIT 1** · 14 passed / 4 failed · `why` WAS BLANK
`tests/run_rewrite_convergence_probe.py:282` — `sys.exit(1 if FAIL else 0)`
Failing arms: `B1 real-repo --verify: anchors resolve and coverage is complete`
(exit 2), `B1b the mirror verifies before it is damaged` (exit 2), `B4 a hook on
disk the map does not name is exit 1` (exit 2), `E1 --derive: nothing is derived
that is neither declared nor exempted` (exit 1).
**THREE ARE EXIT 2 COULD-NOT-RUN AND THE CAUSE IS A REAL REPO-STATE DEFECT, NOT
A SANDBOX ONE:** *"COULD NOT RUN — 1 anchor(s) unresolvable. This is NOT a pass:
`post_rewrite_hook .githooks/post-rewrite` contains its anchor
`'--post-rewrite'` **3 times** — an ambiguous anchor is not evidence."* **That is
a uniqueness guard refusing rather than grading the wrong region**, which is the
correct direction and still a check that cannot fire. **Fix the anchor, not the
probe.** `E1` is a genuine exit-1 failure — the tool working.
**`why` filled in `docs/known-red-suites.json` by this batch.**

### 8. `tests/run_role_gate_negative_coverage_probe.py` — **EXIT 1** · 19 ok / 4 failed · `why` WAS BLANK
`tests/run_role_gate_negative_coverage_probe.py:283` — `sys.exit(1 if fails else 0)`
Failing arms, all four pin-file arms, all four reporting **exit 2**: *"at the
pinned number it is OK and exits 0"*, *"…and says a ratchet is not a pass on the
same run"*, *"a NEW uncovered gate is a REGRESSION, exit 1"*, *"an added
negative arm reads as IMPROVED and asks to be re-pinned"*.
**THE DISCRIMINATING FACT: the probe's own real-repo section passed ENTIRELY**,
including *"it runs against the shipping repo and exits 0 or 1, never 2"*,
*"UNCOVERED and COVERED are BOTH non-zero — if either is 0 the classifier has
stopped discriminating"*, and *"IT WROTE NOTHING to `api/` — bytes AND mtime"*.
**So the classifier works against real source and the four red arms are about
the pin file the fixture constructs** — and section 7 proves exit 2 is the
tool's *correct* answer to a missing or unparseable pin. **Most likely a
probe-side path problem, stated as likely rather than as diagnosed.**
**`why` filled by this batch.**

### 9. `tests/run_secrets_inventory_probe.py` — **EXIT 1** · 15 PASS / 5 FAIL
`tests/run_secrets_inventory_probe.py:184` — `sys.exit(1 if failures else 0)`
Failing arms: `4c`, `5a`, `6a`, `6b`, `6c`.
**ONE REAL FINDING REPEATED FIVE TIMES, and it is a live-code finding:
`SAIRNVET_TRANSCRIBE_URL` and `SAIRN_RESEND_TIMEOUT_MS` are read by the code and
have NO `SECRETS` entry**, so the tool exits 2 on every real-document arm. **Two
unclassified secrets is the finding; five red arms is one finding wearing five
hats.** The arms that passed are the ones that matter for trust in the tool:
*"no CREDENTIAL value is printed anywhere in the document"*, and *"the document
states what it CANNOT see, including that it reads the CODE and not the
deployment"*. Register `tail` named `6c` — **agrees.**

### 10. `tests/run_selftest_independence_probe.py` — **EXIT 1** · 33 ok / 2 failed · `why` WAS BLANK
`tests/run_selftest_independence_probe.py:209` — `sys.exit(1 if fails else 0)`
Failing arms: *"`nhi_register.py`: the self-test passes UNMUTATED, or every arm
below is meaningless"* and *"`nhi_register.py`: the self-test passes again after
restore, so the mutants left nothing behind"*.
**BOTH ARE ONE DEFECT IN A THIRD TOOL, AND THE PROBE IS WORKING.**
`nhi_register.py`'s own self-test is red at HEAD on the arm *"with an unreadable
repo root it RAISES rather than returning a list"*, and **the first failing arm
is the BASELINE GUARD that makes the other 33 interpretable** — a mutation suite
whose unmutated subject is already red proves nothing, and this probe refuses to
pretend otherwise.
**What passed and matters:** every mutation arm caught its mutant, and the tree
was verified **byte-for-byte unchanged** after three tools were deliberately
broken and restored — *"the finally clause runs is the assumption this arm
refuses to make."*
**`why` filled by this batch.**

### 11. `tests/run_selftest_sweep_probe.py` — **TIMEOUT at 180s · EXIT=124 · NO EVIDENCE AT ALL**
`tests/run_selftest_sweep_probe.py:196` — `sys.exit(1 if fails else 0)` — **never reached.**
**The log is 0 bytes. The suite printed nothing before the cap**, so there are no
arm counts, no arm names, and nothing to attribute. **This is the only one of
the twelve that produced no evidence, and it is reported as the third state:
UNPROVEN / COULD-NOT-COMPLETE-at-180s — not a pass and not a failure.**
Per fourth's rule a timeout **LEAVES THE ENTRY IN PLACE**, and it is left in
place. **Zero output is itself a finding:** a sweep that emits nothing for three
minutes cannot be segmented, cannot be attributed, and cannot be told from a
hang — which is the no-long-run-whose-first-check-is-at-the-end discipline. Its
register `tail` (`- ooda_phases.py --selftest exits 0`) implies it once ran far
enough to report per-tool results, so **something changed or the cap is simply
too low for it.** 180s is the cap I set; the suite may well be legitimately
longer. **NEXT STEP: re-drive this one alone with a much larger cap and
unbuffered output (`python -u`), and if it still prints nothing, that is the
defect.**

### 12. `tests/run_stored_data_criticality_probe.py` — **EXIT 1** · 17 ok / 2 failed
`tests/run_stored_data_criticality_probe.py:383` — `sys.exit(1 if fails else 0)`
Failing arms: *"an ESCAPED pipe inside a cell is content, not a boundary"*
(exit=0 where a refusal was expected) and *"THE PAIRED POSITIVE: both real rows
are still parsed and counted"*.
**THIS CONFIRMS THE CAUSE TAG THE ROUTING DOC ALREADY CARRIED** —
`implementation/parsing/escaped-delimiter`. The suite's own arm text states the
consequence: *"counting it as a boundary turns one row into nine cells and every
positional read after it is wrong."* **That is the split-on-`|` defect CLAUDE.md
names, measured.** The fail-closed arms all passed: missing `api/_resources` is
exit 2 never 0, a failing criteria lock judges nothing real, and a failing lock
does not also print a clean row count. Register `tail` named both arms —
**agrees.**

---

## 2. What was written to the register, and what was not

**Written** (`docs/known-red-suites.json`):

* `why` filled for suites **7, 8 and 10**, each stating its exit code, its arm
  names, its cause where established, and `file:line` for the exit — plus
  `diagnosed: 2026-10-14`, `diagnosed_by: cody`.
* Suite **6**'s stale-tail contradiction appended to its existing `why`, with a
  new `tail_remeasured_2026_10_14` field.

**NOT written, deliberately:**

* **No entry removed.** No suite exited 0.
* **No entry's `tail` overwritten.** §3.
* **No suite edited.** Not one line of any of the twelve was changed. A sweep
  that fixes what it measures cannot report what it found.

---

## 3. THE STALE TAIL, AND WHY IT IS APPENDED RATHER THAN CORRECTED

Suite 6's stored `tail` is `TIMED OUT after 300s -- a hang is not a …`. It now
exits **1** in ~130s with four named arms. **The register's whole function is to
let `tools/known_red_check.py` tell a CHANGED reason from a NEW failure**, and
it does that by comparing the stored `tail` against the observed one. **So
silently rewriting the tail would destroy the only evidence that the reason
changed** — the row would look as though it had always said this.

The contradiction is therefore recorded **inside `why`**, marked, with both
readings, and the re-measured tail stored under its own dated key. **A register
whose rows are edited in place cannot be used for the one thing it exists for.**

Two other tails also disagree with the measurement and are recorded here rather
than touched: suite **3** (`5 passed, 7 failed` → `4 passed, 8 failed`, and the
likely cause is `%TEMP%` accumulating repositories, not the tool) and suite
**11** (a per-tool result line → no output at all).

---

## 4. MY OWN ERROR, DECLARED: a global `taskkill` mid-sweep

Partway through the sweep I ran `taskkill //F //IM python.exe` in the live clone
to stop a different tool of mine — `tools/red_suite_register_check.py`, which
runs every registered suite **with `cwd=repo` and no isolation**
(`tools/red_suite_register_check.py:96`), which is precisely what should not run
in the live clone. **Stopping it was right; stopping it that way was not.**
`taskkill //IM` is process-wide, so it also killed whichever sweep suite was in
flight.

**What was done about it, rather than hoped:** the runner was told, and **every
suite already run was re-run from the start.** All ten re-runs came back
**byte-identical with the same exit code**, so no number above is
kill-contaminated. Suites 11 and 12 were only ever run after the kill.

**The tree was checked afterwards and was clean** — only my own intended
changes, no suite-written residue — and the two orphaned gate worktrees the
killed process left behind (`gate12-29652-2`,
`sairn-gate-base-433860be9668`) were removed by hand and pruned, because a stale
worktree entry makes the next `git worktree add` refuse.

**The lesson is narrow and worth the line:** kill by PID, not by image name,
when anything else of yours is running. **A result I could not rule out as
contaminated would have been worth nothing**, and ten re-runs is a cheap price
for not having to say so.

---

## 5. THE PATTERN ACROSS THE TWELVE, which is worth more than any single result

**TWENTY of the 42 failing arms are the subject tool exiting 2 COULD NOT RUN,
scored as a FAILED ARM by the probe** — all 8 in suite 3, 3 of 4 in suite 7, all
4 in suite 8, and all 5 in suite 9 are that shape. Arithmetic, so it can be
checked: the eleven suites that produced evidence failed 1+3+8+8+1+4+4+4+5+2+2 =
**42** arms between them (suite 11 printed nothing and contributes none), and
8+3+4+5 = **20** of those are a refusal rather than a defect. **Just under half.**

**None of those probes has an unproven counter.** Their summary arithmetic has
two buckets, so a could-not-run has nowhere to go and lands in `fails`. **That
is the exact defect `docs/2026-10-13-cody-b6-methodology-unproven.md` was written
about, running in the opposite direction:** that document's case was an unproven
arm hidden inside exit 0; this is an unproven arm reported as exit 1. **Both
collapse a third state, and both mislead — one says "passed" when it does not
know, the other says "broken" when the tool was right to refuse.**

`tools/unproven_arm_check.py` cannot see this family: A1 and A2 look for files
that already HAVE an unproven mechanism. **A fourth signal — *a probe that
records a subject's exit 2 and has no third bucket to put it in* — would have
flagged all four of these suites.** Recorded as an observation with a measured
denominator behind it (20 of 42 arms, 4 of the 11 suites that
produced evidence); **not built, and not claimed to be worth building.**

---

## 6. What remains

**24 of fourth's 36 are still undriven.** Numbers 13 to 36 of
`docs/2026-10-13-fourth-b10-undriven-suites.md`, beginning at
`tests/run_subprocess_decode_probe.py`. **Same method: isolated worktree, one at
a time, real `$?`, a log per suite, and the timeout reported as a third
state.** On this batch's evidence, budget for **roughly 11 of 12 to exit 1** and
expect **just under half the failing arms to be could-not-run rather than
defects** — and read §5 before scoring any of them.

Suite 11 needs a separate, longer, unbuffered re-drive and is the one concrete
carry-over.

---

*Measured at `433860be` in a worktree of the same sha, with `origin/main` at
`aeea051f` unmerged at run time. Every `file:line` above was re-read in the live
clone before being written here.*
