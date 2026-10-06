# Every suite in the tree, driven once — and the run is not the finding

**2026-10-06 (Fourth).** Item 8 of the batch asked for one drive of every suite
with exit codes on their own lines, the red suites outside the register
registered, and the total run against the total existing. All of that is below.

**But the finding is not the census. It is that a whole-tree run of this
platform corrupts the clone it runs in, and two of the suites it drives are the
reason.** Both are named, both were attributed by measurement rather than by
reading, and both are reproducible.

---

## 0. The headline: three ways the whole-tree run poisoned its own measurement

`tools/run_all_tests.py` drove the tree once. Exit code, on its own line:

```
1
```

```
RAN: 344 JS + 395 PY = 739 files (3 skipped)
84 FAILING TEST FILE(S)
```

**That 84 is not a census of what is red at HEAD, and here is why — three
confounds, each evidenced, not suspected.**

### 0.1 The tree moved under it

The run log says:

```
  ok   node  tests/sairnbiz_vendor_ytd_derivation.js
```

At the time I drove that same suite by hand it exited **1**, failing at module
scope on `sbVendorPaidUndatedPriorYear not found -- anchor moved`, because cc
renamed that function in `sairnbiz.html` and the rename arrived in this clone
mid-run. **`tools/run_all_tests.py --pinned` exists for exactly this** — its own
header says a detached worktree at a fixed commit is *"the only way"* to get a
stable answer on a five-clone branch that moves hourly — and I did not use it.
That is my mistake and it is the cheapest of the three to avoid.

### 0.2 The run MUTATED the tree it was measuring

**`tests/seam_check/run_delegation_probe.py` left two live API files carrying
planted sabotage.** Found by digesting a watch-list after every suite:

```
MUTATED: tests/seam_check/run_delegation_probe.py -> ['api/sd-data.js', 'api/_lib/subcontractor-compliance.js']
```

What was left behind, read before restoring:

* `api/sd-data.js` — `subs.canAssign({... required: required, warn_days: gateWarn})`
  had `warn_days: gateWarn` **removed**.
* `api/_lib/subcontractor-compliance.js` — `function evaluateSubcontractor(input)`
  replaced by a destructured signature followed by `const input = {...}` and
  then the original `input = input || {}` and `const today = ...`. **That does
  not parse.**

So every suite driven after it was reading an API library that does not load.
**This changed at least one verdict:** of the four suites driven after it,
`tests/seam_check/run_probe.py` exits **1** on the sabotaged tree and **0** on
the restored one. The whole-tree log reports it with an `OSError`.

The probe restores correctly when it completes — a later run printed
`restored_baseline True`. It leaves residue when it does not.

### 0.3 The run CORRUPTED THE CLONE, and this is the serious one

**`tests/push_gate/check8_probe.py` leaves `.git/config` with
`core.bare = true` and a fixture identity:**

```
MUTATED: tests/push_gate/check8_probe.py -> ['.git/config']
```

```
[core]
	bare = true
[user]
	email = fx@example.invalid
	name = fx
```

After that, **every git command in the clone fails**:

```
fatal: this operation must be run in a work tree
```

Not `git status`, not `git commit`, not `git push`. **Observed three separate
times on 2026-10-06** — once during the whole-tree run and twice during the
individual drive — and repaired by hand each time with
`git config core.bare false` and `git config --remove-section user`.

**THE ATTRIBUTION IS MEASURED; THE MECHANISM IS NOT PINNED, and that
distinction is the honest part.** `.git/config`'s sha256 changed across the
execution of that one suite, three times. What I can say about how:

* The probe creates a real `git worktree` on this clone and removes it from an
  **`atexit` handler**. It was **killed by a 300-second ceiling** on every run
  where the corruption appeared, so `atexit` never ran.
* `fx@example.invalid` / `fx` is the exact fixture identity written by
  `tools/copy_exactly_gate.py:_fx_repo()`, which runs **inside the pre-push
  gate** that this probe deliberately invokes with
  `git push --dry-run origin HEAD:main`.
* Running `tools/copy_exactly_gate.py --fixtures` **alone does not touch this
  clone's config** — checked, in both directions. So the corruption needs the
  probe's context, not just that function.

I did not chase it further, and a guess at the mechanism would be worse than
the measurement. **Routed to the owners of those two files.**

### 0.4 And 15 leaked worktrees

`git worktree list` shows **16 entries**, one of them this clone and the other
fifteen temp directories from probes killed before their cleanup ran —
`check8-probe-28176`, `condcov-75668`, `condcov-78672`, `defreg-probe-78908`,
`gate-missing-79544`, `gate12-76884-4`, `gate12-79544-4`, `invis-c0-78472`,
`r5-cover-79732`, four `sairn-sab-*`, `sairn-gate-base-*`, and a locked
`cc-review-*`. `git worktree prune` removed none of them, because the
directories still exist. Harmless today and a disk and confusion cost that
grows with every killed run.

---

## 1. So the census was re-measured, one process per suite

Every one of the 84 failing files that was **not already registered** — 74 of
them — plus the **3 registered files the run showed GREEN**, driven
**individually**, each in its own process, against a tree whose `.git/config`,
`api/sd-data.js` and `api/_lib/subcontractor-compliance.js` were digested after
every single suite so a corrupting suite is named rather than silently
poisoning the rest of the list.

```
DRIVEN                 : 77
RED (non-zero)         : 66
GREEN (exit 0)         : 7
COULD NOT RUN          : 4
```

**Totals, run against existing:**

| | |
|---|---|
| suite files in the tree | **739** (344 JS + 395 PY) |
| driven by the whole-tree run | **739** — 736 ran, **3 SKIPPED**, which is a precondition unmet and NOT a pass |
| reported FAILING by that run | **84** |
| of those, already registered | **10** |
| of those, re-driven individually | **74** + the 3 registered-but-green = **77** |
| confirmed RED when driven alone | **66** |
| GREEN when driven alone | **7** — four of them FAIL in the whole-tree log |
| COULD NOT RUN (300s ceiling) | **4** |

### The seven that are green alone and were not green in the run

| suite | in the whole-tree log | driven alone |
|---|---|---|
| `tests/run_ai_action_approval_control.py` | FAIL | **0** |
| `tests/run_closing_error_probe.py` | FAIL | **0** |
| `tests/run_tooling_inventory_probe.py` | FAIL | **0** |
| `tests/seam_check/run_probe.py` | FAIL (`OSError`) | **0** — and 1 on the sabotaged tree, so this one is attributable to §0.2 |
| `tests/run_fmea_probe.py` | ok | **0** — registered as red since 2026-09-16, **RECOVERED** |
| `tests/run_mutation_anchor_probe.py` | ok | **0** — registered since 2026-09-16, **RECOVERED** |
| `tests/sairnbiz_vendor_ytd_derivation.js` | ok | **0** — registered 2026-10-05, **RECOVERED**: cc repointed the anchor |

**Three register entries deleted.** The register's own rule is that an entry
whose suite has recovered must go, because while it stands it absorbs the next
real failure of that file.

### The four that could not be answered

Each exceeded a 300-second ceiling when driven alone. Exit codes, each on its
own line, as `COULD NOT RUN` — which is neither red nor green:

```
tests/install_git_hooks_check_probe.py
COULD NOT RUN
tests/push_gate/check12_probe.py
COULD NOT RUN
tests/push_gate/check8_probe.py
COULD NOT RUN
tests/run_report_only_checks_probe.py
COULD NOT RUN
```

Whether each is **slow or stuck has not been established** and the register
says so rather than guessing. All four do real git work — pushes, hook
invocations, worktrees — so a minute-scale runtime is plausible and so is a
hang.

---

## 2. What went into the register, and the part that is a backlog

`docs/known-red-suites.json`: **13 entries → 80.** Three deleted as RECOVERED,
seventy added.

**66 of the 80 carry an EMPTY `why`.** That field is defined by the register
itself as *"NOT DIAGNOSED YET, recorded as empty rather than guessed. An
invented cause is worse than a blank one."* So:

> **Every one of the 66 was driven alone and had its exit code recorded. NOT
> ONE of them was read arm by arm.** That is a 66-item diagnosis backlog and
> the largest single addition this register has ever had. An entry makes a
> failure ATTRIBUTABLE, never acceptable.

The mitigation that makes a 66-entry register safe rather than an allow-list is
`tools/red_suite_register_check.py`, added today: it drives every registered
entry, prints each exit code on its own line, and **exits non-zero the moment
one of them passes** — so a stale entry gets reported instead of swallowing the
next regression in the one file somebody already decided not to look at.

---

## 3. What this pass did NOT do, stated rather than left to be discovered

* **It did not use `--pinned`**, which is the one tool that would have removed
  confound §0.1 entirely. The individual re-drive is a worse substitute for it:
  it answers per suite against a tree that was still moving between suites.
* **It did not fix either corrupting probe.** `tests/push_gate/check8_probe.py`
  and `tests/seam_check/run_delegation_probe.py` are untouched, and §0.3's
  mechanism is unestablished. Routed.
* **It did not diagnose 66 of the 80 register entries**, per §2.
* **It did not re-drive the 66 twice.** A suite red once when driven alone is
  recorded as red; flakiness is not measured here at all, and on a platform
  where five clones push hourly that is a real limit rather than a theoretical
  one.
* **It left the 15 leaked worktrees in place.** Removing another session's
  temp worktree while that session may still be using it is not a cleanup.
