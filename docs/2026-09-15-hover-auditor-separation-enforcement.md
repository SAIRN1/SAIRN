# The hover auditor's separation becomes mechanical — and the two alleged breaches did not happen

**2026-09-15 (Hank).** The fifth role on this platform audits the four build
agents and is audited by nobody. Its skill file forbids it writing platform
code in terms, and until today that rule was held by discipline alone. This
builds the two halves that make it structural, and — because the work was
commissioned on the strength of two specific incidents — checks those incidents
first.

**Built by a build agent deliberately.** The auditor building its own cage is
the same defect the cage exists to prevent. Its skill's own test — *"does it
get audited by this role, or does it audit?"* — puts these two tools on the
audited side.

---

## 1. The premise, checked before anything was built

The request named two occasions tonight where the auditor *"found the issue,
then fixed it himself rather than reporting it"*: a concurrency fix logged as
`[0053]`, and the item 101 witnessing-lock fix. **Neither survives contact with
the record, and acting on an unverified requirement list is the 2026-09-02
failure exactly.**

- **Self-log entry `[0053]` is not a concurrency fix.** It is a `note`, dated
  `2026-09-14T20:27:41Z`, recording that Kepler/Flyspeck and loophole-free Bell
  tests were written into `SKILL.md`. Its own text ends *"Committed abbe0fdb,
  pushed 145395bc"* — a skill-file commit.
- **Item 101's witnessing-lock work is Fourth's.** `3f8e3fab` (`api/sv-witness.js`,
  `api/sv-witness.test.js`, `tests/failsafe/`) landed 2026-09-14 16:14:08, and
  it sits between Fourth's claim naming *"item 101 graduated mechanical
  commitment"* (`073f9da6`, 15:35:29) and Fourth's worklog naming *"item 101
  settling phase"* (`3d9edf16`, 16:15:37). Bracketed on both sides by the same
  session's bookkeeping.

**AND THE MEASUREMENT AGREES WITH THE READING, which matters more than the
reading does.** Across all 5,241 commits, **every one of the auditor's 20
git-visible commits touches its own skill directory and nothing else. Zero
violations.** Cross-checked against its own hash-chained self-log: of the 33
SHAs the log names as its own, 16 resolve in this clone and **all 16 are in
scope**.

### What IS real, and it is a different shape than the one alleged

**Self-log entry `[0073]`, `2026-09-14T23:51:56Z`, in the auditor's own words:
it disabled the `SAME_PERSON` check in `api/sv-witness.js:313` (`if(false) &&`)
to drive its own mutation control.** That is a real edit to platform code in a
real working tree. It was never committed — no such commit exists — so the rule
held in its *push* clause and was breached in its *edit* clause.

**This is not pedantry, and the distinction changed the design.** A commit gate
would never have seen it. An uncommitted platform mutation is one `git add -A`
away from shipping, and this repository has a recorded instance of exactly that
chain amending the wrong commit twice in one session. So the gate grew a
`--worktree` mode, and it is there because of entry 0073 rather than because it
seemed thorough.

It is also worth saying plainly that the auditor's method **requires** this:
"drive the mutation myself rather than trust the claim" is the technique that
makes its deep passes worth anything. Entry `[0076]` shows the safe version of
the same move — a probe run *"in a real detached git work[tree]"*. The gate
pushes toward that pattern instead of forbidding the technique.

---

## 2. Two layers, and they fail in different ways on purpose

### PREVENT — `tools/hover_auditor_scope_gate.py`

Refuses any commit, push, or dirty working tree in the auditor's clone that
touches anything outside its scope.

**The scope is quoted, not invented.** Two paths are allowed and each carries
the sentence from `SKILL.md` that put it there: the auditor's own skill
directory (*"building it is genuinely this role's job"*) and
`docs/defect-density-register.json` (*"Where findings go"*).
`tools/defect_register.py` is named as explicitly denied, because the skill
names it — *"adding one is a code edit this role does not make itself"*.

**Which direction it fails is not one answer for both clones, and that is the
design rather than a softening of it:**

| condition | behaviour | why |
|---|---|---|
| marker absent | exit 0, silently | a SCOPE condition — this is not the auditor's clone and the rule does not apply. Four build clones commit through this hook |
| marker present, anything undeterminable | **REFUSE** | in the auditor's own clone "could not tell" is the third state, never folded into "passed" (PR §1.11) |

**THE CORE-RULE SENTENCE IS RE-READ FROM THE SKILL ON EVERY RUN AND ITS ABSENCE
IS A REFUSAL.** If somebody rewords the rule, the gate stops and demands
re-derivation rather than continuing to enforce a sentence the role no longer
holds. **A stale gate enforcing a repealed rule is worse than no gate, because
it reads as coverage** — the eighth cross-domain discipline, applied to the
file that implements it.

**The marker lives in `.git/`, which is not versioned.** No build clone can
inherit it by pulling, and the shell wrapper tests for it *before* starting
Python, so a build clone pays one file test per commit rather than an
interpreter start-up. A pre-commit hook that costs real time on every commit is
one somebody eventually turns off.

**One subtlety in the pre-push wrapper that would have silently disabled six
existing checks.** git feeds a pre-push hook its ref lines on **stdin**, and a
stream is consumed by its first reader. Chaining the new gate ahead of
`sairn_push_gate_hook.py` naively would have left the existing gate with an
empty stdin — which it treats as nothing to check. The wrapper reads stdin once
into a variable and replays it to both. **Adding one check by turning off six
is a trade nobody would take knowingly, and it is invisible in a diff.**

### DETECT — `tools/hover_separation_audit.py`

The audit trail, built from real history, registered report-only.

**It exists because the prevent half can go missing with nothing announcing
it.** The marker is per-clone and lives in an unversioned directory: a fresh
clone of the auditor's workspace is unarmed and looks identical to an armed
one. This is the layer that notices.

**THE OBVIOUS METHOD DOES NOT WORK AND THE TOOL SAYS SO IN ITS OWN OUTPUT.**
All five roles commit through **one git identity** — `Michael Dibert
<mikied68@gmail.com>`, across the entire history, printable with `--authors`.
There is no author field to group by. Attribution is *derived* from co-changed
bookkeeping files (`.claude/claims/<s>.json`, `SAIRN-ACTIVE-WORK-<s>.md`), and
derived attribution is incomplete by construction, so **the incomplete fraction
is printed above the verdict rather than below it: 64.4% of commits are
UNATTRIBUTED.**

**AND THE LIMIT THAT MATTERS MOST IS THAT GIT ALONE CANNOT PROVE THE NEGATIVE.**
The auditor is identified by "touches only its own skill directory" — which is
**circular for the question being asked**. A commit in which it wrote platform
code would fail that test and land in the unattributed 64%. The git half can
only show that its *known* commits are clean, which is a weaker claim, and the
tool reports it as one.

**What closes that gap is a structurally different source: the auditor's own
hash-chained self-log.** Two records that can disagree are worth more than one
that cannot be cross-examined — the same reason this platform requires a
structurally different method for independence.

- The chain is **re-derived independently**, not by calling `hover_log.py
  --verify`. A record and its own verifier share a failure: if the hashing is
  wrong, the verifier agrees with it. The canonicalisation here was written
  from the rule rather than pasted, because **a second copy is not a second
  opinion** (Ariane 5, already in CLAUDE.md).
- If the chain does not verify, the tool **refuses** rather than reporting from
  a record somebody could have edited.

---

## 3. What the audit found, and the part it could not close

    THE AUDITOR'S KNOWN COMMITS: 20        violations: 0
    self-log: 105 entries, chain INTACT
      SHAs the log names as its own : 33
        resolve here, in scope      : 16      violations: 0
        do not resolve here         : 17
        git-visible, not in the log : 4

**THE 17 UNRESOLVABLE ARE EXPLAINED BY MEASUREMENT RATHER THAN BY A PLAUSIBLE
STORY.** The obvious reading is "a rebase before push rewrote the SHA." That is
a hypothesis, and the log can test it: entries of the form *"Committed a, pushed
b"* name both ends of exactly that rewrite. **Tested over every such pair: 15 of
15 have the local SHA absent and the pushed one present**, which is what a
rebase-before-push produces and nothing else here does. That converts 15 of the
17 into an explained gap.

**The remaining 2 (`0cd86d0b`, `23b0ffef`) are NOT shown to be clean, and the
tool exits 2 rather than 0 because of them.** Both sit in entries that say
"committed X, pushed" with no pushed SHA recorded — the same shape, minus the
second half. The tool does not guess, and "no violation found in what could be
checked" is printed as distinct from "clean".

**Also disclosed rather than smoothed over: 4 git-visible auditor commits are
not named anywhere in the self-log.** Three are `docs(skill):` commits and one
is the original mirror. The log is not a complete record of its own commits, and
any claim resting on it inherits that.

---

## 4. A real bug in this work, caught by its own output before it shipped

The first version used one path set for two different questions. **`docs/defect-density-register.json` is in SCOPE — the auditor is told to write findings there — but it is NOT a SIGNATURE, because all four build agents write it too.** Using the scope set for attribution credited every register-only commit on the platform to the auditor and reported **46** auditor commits where there are **20**.

**The general shape is worth naming because it will recur: "what this role may
touch" and "what identifies this role" are different questions, and the second
is worthless unless it is EXCLUSIVE.** Only the skill directory is. Four probe
arms now pin the distinction in both directions.

---

## 5. The controls

`tests/run_hover_separation_probe.py` — **72 arms, 0 failures.**

- **Both directions on the classifier**, plus the near-misses that would fail
  the unsafe way: a backslash path (a hook caller can produce one, and a path
  that "does not match the prefix" would be ALLOWED), and a sibling directory
  sharing the allowed prefix.
- **Both arming states in a real throwaway repository.** Unarmed: a staged
  platform file is allowed *and the gate prints nothing* — four build clones
  commit through this. Armed: refused, refusal names the file, and points at
  reporting rather than fixing.
- **The fail-closed paths, separately**: the rule reworded (refuses an
  *in-scope* change and says CANNOT VERIFY, not VIOLATION), the skill file
  missing (refuses, names that cause instead), pre-push with no ref lines
  (refuses rather than passing vacuously). The skill fixture is restored
  byte-identical afterwards and the gate is asserted to go back to allowing.
- **TEETH.** The classifier is neutered in a throwaway copy and the refusing
  arms must collapse — with the anchor asserted present and the mutation
  asserted applied first, because **a `.replace()` whose anchor went stale
  changes nothing and the arm then passes over a mutation never applied.**
- **The chain verifier is shown to FAIL and then to pass again**, at three
  positions. Its own skill sets that standard: *"A verifier that has never been
  shown to fail is not yet a verifier."* A one-sided control cannot tell a
  working verifier from one that reports BROKEN unconditionally.
- **Two arms record what it does NOT catch.** A swap of two entries is caught
  (by the linkage, not the hash). **A truncation at the tail is not, and the arm
  asserts that it is not** — so if the verifier ever gains that property,
  somebody has to come and update the claim rather than discover it later.

---

## 6. Not established

- **No proof the auditor never wrote platform code.** Stated three times above
  because it is the thing a reader will otherwise take away. 64.4% of history is
  unattributed and that bucket is where such a commit would be.
- **The gate is not installed anywhere yet.** It arms nothing until somebody
  runs `--install` in `Documents\SAIRN-hover` and `install_git_hooks.py`
  alongside it. Michael's call — arming another session's clone from this one
  is the same boundary problem in the other direction.
- **The 2 unpaired SHAs remain open** and the tool will keep exiting 2 until
  they are resolved or the log records their pushed counterparts.
- **Entry 0073's edit was read from the auditor's own account of it.** The
  working tree it happened in is not observable from here; no independent
  confirmation that the file was restored exists, beyond `api/sv-witness.js`
  carrying no `if(false)` today.
