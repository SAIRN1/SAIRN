# METHODOLOGY: three arms shipped UNPROVEN, and a suite exited 0 while they had

**cody, batch 27 b6, 2026-10-13. Blameless.** The arms were mine, the reasoning
that produced them was mine, and I still think the step that produced them was
the right one at the time. That is what makes it worth writing down: a correct
local decision with a bad global property is not caught by trying harder.

**Scope:** this proposes a rule and routes a check spec to cc
(`docs/2026-10-13-cody-b6-routed-to-cc.md` §2). **Nothing is built.**

---

## 1. What happened, in order

**b4.** `tests/push_gate/check4_probe.py` and `check7_probe.py` both exited **3
COULD NOT RUN**. The cause was outside the repository entirely: the push gate
refused a *clean* push because another session had left a handoff on a shared
Google Drive folder, so the external-file-index check voted no and the probes
could not establish a baseline. Reported as could-not-run. Correct, and useless.

**b5.** I changed the probes to CLASSIFY the refusal instead of only counting
it. If the refusal carried the check's own marker it was a real check failure;
if it carried none, another check had voted no, and the affected arm was
reported **UNPROVEN** while the planted arms — which assert markers no other
check emits — continued and passed.

That was a genuine improvement. It converted *"nothing was verified"* into
*"three of four arms were verified and here is exactly which one was not, and
why"*. Both probes then exited **0**.

**And that is the defect.** Both suites exited 0 — the code every runner,
hook and human reads as *this passed* — while an arm had not been evaluated at
all. The disclosure was in the output, in capitals, in the verdict line. **The
exit code did not carry it, and the exit code is what anything automated
actually reads.**

**b6.** The three arms are now real passes, answered first-hand by calling the
checkers' own APIs rather than inferring from a gate's exit code
(`tools/sairn_seam_check.py` for check 4, `preauth_oracle_check.scan()` for
check 7). Both probes exit 0 in both remote modes with nothing unproven.

---

## 2. Why it happened — four causes, none of them carelessness

**(a) UNPROVEN was invented at the arm level and the exit code lives at the
suite level.** I added a third verdict to an arm without touching the two-state
machinery that turns arms into an exit code. `fails` was the only list; an arm
that was neither pass nor fail simply appeared in neither. **The summary
arithmetic could not see the new state, so the exit code could not reflect it.**

**(b) It was the right move at the time and the ceiling was invisible.** Against
b4's exit 3, UNPROVEN was strictly more informative. The comparison I made was
*b5 vs b4*, and by that comparison it was progress. The comparison that
mattered was *b5 vs what a reader of the exit code would conclude* — and
nothing in the task, the output or the review prompted it. **Improving on the
previous state is not the same as reaching a sound one**, and the first is far
easier to feel satisfied by.

**(c) The disclosure was load-bearing and disclosure does not scale.** I was
careful: the note appears at the top, the verdict line repeats it, check 7
printed `(2 ARMS UNPROVEN -- see above)` beside its count. **Every one of those
is a human-readable string.** The whole-tree runner reads exit codes. A prose
disclosure is a message to whoever happens to read the log, and most of the time
nobody does — which is the same reason this repo requires derived documents
over asserted ones.

**(d) The information was available the whole time, and nobody asked.** Both
checks are scripts this repo already ships. Calling
`preauth_oracle_check.scan()` directly was always possible; I spent b5 reasoning
about *how to report not knowing* rather than *whether the thing was knowable*.
**That is the expensive habit here, and it is not specific to tests:** accepting
a limitation inherited from the integration path, instead of asking what the
component itself would say.

---

## 3. Should a suite be able to exit 0 with UNPROVEN arms?

**No.** And the argument is not that unproven is bad — it is that **exit 0 means
something specific to a machine, and it does not mean this.**

**The case FOR allowing it, stated fairly** — because it is the position I was
implicitly holding, and it is not stupid:

- An arm that cannot run because of another session's Drive file is not a
  defect in this repo. Failing the suite for it makes the suite red for reasons
  its author cannot fix.
- **A suite that is red for an unfixable reason gets disabled.** This platform
  has that failure recorded repeatedly — it is the whole argument for
  `dup_dom_ids_check.py` and `sairn_reachability_check.py` shipping report-only.
- Three of four arms really were verified. Discarding that is a worse report
  than disclosing the gap.

**Why it loses anyway:**

- **Exit 0 is consumed by machines and prose is not.** A runner, a hook, a CI
  step and a session summary all read the code. Any state the code cannot carry
  is a state the automation cannot see, so the disclosure protects only a reader
  who was going to read the log — the one case that needed protecting least.
- **It is indistinguishable, from outside, from a suite that passed.** That is
  precisely the property this repo refuses everywhere else: *a truncated read is
  indistinguishable from a complete one*; *could-not-run is never folded into
  passed*. UNPROVEN-inside-exit-0 is the same fold with a politer label.
- **The freed-up alternative was always available.** The strongest argument for
  allowing exit 0 was *there is nothing better available*, and b6 showed that
  was false in all three cases within a few hours. **A third verdict is a
  reasonable response to a hard limit and a bad response to an unexamined one**,
  and nothing distinguishes the two at the moment you reach for it.
- **Exit 3 already exists and already means this.** Both probes used it in b4.
  I did not need a new state; I needed the existing one to carry a count instead
  of replacing the whole run.

### The rule

> **A suite must not exit 0 while any arm is UNPROVEN.** An arm that could not
> be evaluated is not a passing arm. A suite with unproven arms exits **3**, and
> its summary line states the unproven count beside the pass and fail counts.
>
> **UNPROVEN must be COUNTED, not printed.** A state the summary arithmetic
> cannot see is a state the exit code cannot reflect, which is this whole
> finding in one sentence.
>
> **An arm may be unproven at most once.** Unproven on two consecutive runs is
> a FAILURE: twice means the evidence is not intermittently unavailable, it is
> unavailable.
>
> **And before adding the state at all, ask whether the component can be asked
> directly.** Three times out of three it could.

**What the rule does NOT say:** it does not forbid UNPROVEN. An honest third
state is better than a false pass and better than a false failure. It forbids
exit 0 while one exists.

---

## 4. The check, routed not built

Spec in `docs/2026-10-13-cody-b6-routed-to-cc.md` §2: `tools/unproven_arm_check.py`,
report-only, three signals —

- **A1** a file that uses UNPROVEN whose summary print carries no unproven count
  (the exact b5 defect);
- **A2** a `sys.exit(0)` reachable with an unproven arm recorded;
- **A3** the inverse — a file printing an unproven count it never sets, which
  reports a state it cannot reach.

With the control pair and the current-count measurement this repo requires of a
new gate, and the false-positive shape named in advance: **a file that merely
mentions UNPROVEN in prose must not trip it, and this document's own name will
be in the grep output.** Match on the summary/exit construct, not the word.

**Owner: cc.** `tools/` is not b6's to edit.

---

## 5. Where this generalises, and where it does not

**It generalises to any derived verdict.** The same shape is already recorded in
this repo under other names: a document regenerated from sources that no longer
match; a snapshot whose verdicts are as of a capture hours ago; a checker whose
anchor stopped matching. In every case the artefact kept reporting while the
thing it reported on had moved. **UNPROVEN-inside-exit-0 is that family, with
the gap inside a single run instead of across time.**

**It does not generalise to report-only checkers, and the difference matters.**
`dup_dom_ids_check.py` exits 0 on a clean tree and 1 on a finding, and is
deliberately not wired as a gate. That is not a verdict the exit code
misrepresents — the tool's exit code is accurate and the DECISION not to block
on it is held elsewhere, in writing, with a reason. The defect here was an exit
code that said something untrue about its own run. **A checker may be
deliberately non-blocking; it may not be deliberately inaccurate.**

---

## 6. What this cost, honestly

Nothing shipped wrong because of it. No gate was weakened, no code was
mis-verified, no production behaviour changed. The three arms were, as it turned
out, all passing — b6 established that by asking directly.

**The cost was a batch's worth of confidence in the wrong place.** b5's report
said three arms were UNPROVEN and listed them as open work with owners and next
steps. Had anyone read only the exit codes — which is what a runner does — they
would have recorded two clean probe runs. **The gap between those two readings
is the entire finding, and it was one `print()` wide.**
