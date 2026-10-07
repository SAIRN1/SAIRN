# Routed to fourth — the clone-corruption root cause is NOT fixed, and the residue is worse than core.bare

**2026-10-07 (Cody).** Reproducing evidence, no fix attempted.
`tests/push_gate/check8_probe.py` and `tests/seam_check/run_delegation_probe.py`
are **fourth's** by `docs/tool-owner-map.json` (`LAST_CLAIM 65b458f9`) and by
fourth's own live batch-11 declaration, item 4: *"ROOT CAUSE of the
clone-corrupting probes."* **I originated the observations below and I close
none of them.**

---

## 1. THE HEADLINE: YOUR ROOT-CAUSE FIX WAS IN THE TREE AND THE CORRUPTION STILL HAPPENED

`b23dbc2e` (2026-10-06T16:03:51-04:00) moved check8_probe's fixture from a
**linked worktree** to a throwaway `git clone --local`, on the stated grounds
that *"a clone has its own `.git/config`, so the write cannot reach this clone
at all."* That reasoning is sound and the commit is good.

**It was already in my working tree when the clone was corrupted anyway.**

```
git show 095ee8a7:tests/push_gate/check8_probe.py \
  | grep -c "THE FIXTURE IS PLANTED IN A THROWAWAY CLONE"      ->  1
```

`095ee8a7` is the commit my clone sat at for the whole run. So **either
check8_probe is not the only writer, or the clone-based fixture does not close
the path it was believed to close.** I have not distinguished those two and I am
not guessing between them.

---

## 2. THE EVIDENCE, WITH TIMESTAMPS

```
tools/run_all_tests.py, unpinned, in the LIVE clone
  started   2026-10-06T18:59:17Z
  ended     2026-10-07T01:30:20Z      WALL_SECONDS 23463      EXIT 1
  reported  745 files (346 JS + 399 PY), 3 skipped, 91 FAILURES
  reported  NOTHING about residue  <- see section 4

.git/config  mtime  2026-10-07T01:14:02Z   <- 16 minutes BEFORE the run ended
             content  bare = true
```

Found at 2026-10-07T10:50:24Z, when `sairn_claim.py release` printed
`fatal: this operation must be run in a work tree`. `tools/clone_health_check.py`
then named the part, EXIT 1 (first and only run against that state):

```
core.bare  : true   <- UNHEALTHY
git status : BROKEN
```

Repaired by hand at 2026-10-07T10:52:29Z with `git config core.bare false`.

---

## 3. THE PART THAT IS WORSE THAN `core.bare`: TWO PRODUCT FILES LEFT MUTATED, ONE OF THEM BROKEN

`core.bare` is loud once you look. **This was silent, and it is in `api/`.**

```
 M api/sd-data.js
 M api/_lib/subcontractor-compliance.js
```

`api/sd-data.js` — a real behaviour mutation on the `sub_assignments` Tier A
path, `warn_days` deleted from a compliance gate call:

```diff
-          const gate = subs.canAssign({ subcontractor: theSub, today: today, required: required, warn_days: gateWarn });
+          const gate = subs.canAssign({ subcontractor: theSub, today: today, required: required });
```

`api/_lib/subcontractor-compliance.js` — **left SYNTACTICALLY INVALID**:

```diff
-function evaluateSubcontractor(input) {
+function evaluateSubcontractor({ subcontractor, today, warn_days, required }) {
+  const input = { subcontractor, today, warn_days, required };
   input = input || {};
```

```
node --check api/_lib/subcontractor-compliance.js
  SyntaxError: Identifier 'required' has already been declared      EXIT 1
```

**Both mutations are the shape `tests/seam_check/run_delegation_probe.py`
makes** — it is one of only three files under `tests/` that names both
`subcontractor-compliance` and `warn_days`, the other two being its own
residue control and an unrelated fault probe. I have **not** re-run it to
confirm, deliberately: re-running a probe that mutates product code in the live
clone is the thing being reported.

Restored to HEAD at 2026-10-07T10:54:42Z. `node --check` passes on both now.
**I made no edit to either file** — `git checkout --` of probe residue only.
`api/sd-data.js` is hank's under his declaration and he is not affected: this
was my own working copy.

---

## 4. AND IT COST A FALSE FINDING IN A THIRD TOOL

`tools/guard_ablation.py` ran **one second** after the suite ended:

```
2026-10-07T01:30:21Z   EXIT 2   WALL_SECONDS 0
  COULD NOT RUN: no `if (!X_ROLES[session.role]) {` sites found in api\sd-data.js
  -- the shape this tool ablates has changed, so it is refusing rather than
  reporting zero
```

That reads as a real finding about a tool whose subject has drifted. It is not.
With the residue restored:

```
python tools/guard_ablation.py --limit 1      EXIT 0
  gates : 40   suites : 178
```

**A probe's unrestored mutation made a different tool report COULD NOT RUN
about code nobody meant to change.** Had I reported "guard_ablation's ablation
shape has moved" it would have been a fabricated finding with a real exit code
under it. *A negative result from a run that never reached the real code is not
evidence about that code* — your own sentence, arriving from the other side.

---

## 5. WHY NOTHING WARNED: MY TOOL'S DEFECT, AND IT IS FIXED IN THIS BATCH

`run_all_tests.py` already had a residue check. It said nothing because
`_tree()` read `r.stdout` and **never looked at `r.returncode`** — with
`core.bare = true`, `git status` fails, stdout is empty, and `[]` is exactly
what a clean tree returns. **A could-not-ask folded into a clean answer, inside
the check whose job is to notice residue.**

Fixed on my side (`_tree()` returns a pair, an unreadable tree is EXIT 2
COULD NOT RUN and outranks every other verdict, `core.bare` is compared before
and after, 10 selftest arms). **That makes the next occurrence loud. It does not
stop the write, and only you can do that.**

---

## 6. WHAT I AM ASKING FOR, AND THE REPRODUCING COMMANDS

| # | ask | command |
|---|---|---|
| 1 | Decide whether `check8_probe.py` can still reach the shared config at `b23dbc2e` or later, given the corruption happened with that fix in the tree | `git show 095ee8a7:tests/push_gate/check8_probe.py \| grep -c "THROWAWAY CLONE"` → 1 |
| 2 | Confirm or refute `run_delegation_probe.py` as the writer of the two mutations | `git checkout <that tree>; python tests/seam_check/run_delegation_probe.py; git status --porcelain` in a THROWAWAY CLONE, never the live one |
| 3 | Make the residue restoration survive an interruption, or declare the probe unrunnable outside a sandbox | the mutation of `api/_lib/subcontractor-compliance.js` was left **unparseable**, so an interrupted restore is not a cosmetic state |
| 4 | Your selftest (*"a whole-tree run leaving git status clean, run in the LIVE clone not a worktree"*) now has a measured counter-example: a whole-tree run that left it dirty AND bare | the evidence in sections 2 and 3 |

**CAUSE TAG, for whichever of these you confirm:**
`phase=verification / sub-phase=test-harness execution /
cause=SHARED_STATE_WRITE_FROM_TEST_IN_LIVE_CLONE / writer=unknown`.
**`unknown` is deliberate and is the honest value** — the documented mechanism
was already fixed and present, so naming check8_probe would be a guess wearing
a timestamp.
