# `--pinned` IS NOT ISOLATION FOR CONFIG WRITES — and that is what breaks this clone

**Found by fourth, 2026-10-07, running the pinned whole-tree suite that item 3
of batch 11 existed to finish. Routed as an ARTIFACT, not a patch.**
`tools/run_all_tests.py` is in **no active claim** at `9e380383`
(`python tools/sairn_claim.py check tooling "run_all_tests pinned worktree
isolation shared config"` → `CLEAR`), so this is routed for scheduling rather
than ownership, and the reason it is not fixed here is stated at the bottom.

---

## WHAT HAPPENED

`python tools/run_all_tests.py --pinned --pinned-ignore-dirty` was run at HEAD
`762b084b`. It completed — **`PROGRAM_EXIT=1`**, read from the program's own
stdout, `83 FAILING TEST FILE(S)`, 782 lines of output.

**And it left this clone unusable.** Immediately after:

    $ git config --get core.bare
    true
    $ git status --porcelain
    fatal: this operation must be run in a work tree

The `.git/config` delta, diffed against a copy taken before the run, is a
single line:

    7a8
    > 	bare = true

**This is the same corruption batch 9 recorded and batch 10 contained, and it
happened in the mode that is supposed to prevent it.**

## IT IS NOT `check8_probe`, AND THAT IS MEASURED

`tests/push_gate/check8_probe.py` is **`ok`** at line 655 of that very run, and
separately, run standalone in the live clone at `6b77545f`:

    === CONFIG DELTA ===   CONFIG UNCHANGED   (byte-for-byte)
    === STATUS DELTA ===   STATUS UNCHANGED
    === HEAD ===           unmoved

`b23dbc2e` fixed it, and it now carries its own arms asserting
`.git/config` is byte-identical to a pre-run copy. The writer is something
else.

## THE MECHANISM, REPRODUCED IN TWO COMMANDS

    git worktree add -q --detach /c/Users/marsh/AppData/Local/Temp/ted-wt-repro-b11 HEAD
    git -C /c/Users/marsh/AppData/Local/Temp/ted-wt-repro-b11 config core.bare true

**Observed:** `SET_FROM_WORKTREE_EXIT=0`, and
`C:\Users\marsh\Documents\SAIRN-fourth\.git\config` gains

    7a8
    > 	bare = true

**which is byte-for-byte the delta the pinned run left.** Every git command in
the clone then fails. (Repaired with `git config --unset core.bare`; the
worktree was removed with `git worktree remove --force`.)

**A linked worktree does not have its own config.** Unless
`extensions.worktreeConfig` is enabled and the write is `--worktree`-scoped,
`git config` executed anywhere inside a worktree writes the **common**
`.git/config` — the clone's. So `--pinned` isolates *files* and does not
isolate *configuration*.

## THE PROMISE IS ONE-DIRECTIONAL, AND THE DANGEROUS DIRECTION IS THE UNSTATED ONE

`tools/run_all_tests.py:740` prints:

    Nothing done in C:\Users\marsh\Documents\SAIRN-fourth during this run can reach it.

That sentence is **true** and it is about clone → worktree. The direction that
broke the clone is **worktree → clone**, and nothing in the banner, the
docstring or the output speaks to it. A reader takes "throwaway worktree" to
mean two-way isolation; it is one-way.

## THE SAME DEFECT IS ALREADY FIXED ONE LAYER DOWN, BY THE OBVIOUS FIX

`b23dbc2e` fixed `check8_probe`'s fixture by making it **a throwaway CLONE
instead of a worktree** — its commit subject says so: *"the fixture is a
throwaway CLONE now, so a config write inside it cannot reach this clone at
all."* `run_all_tests.py --pinned` still uses a **worktree**. The fix shape is
known, proven, and already in the tree; it has simply not been applied to the
runner.

Two candidate fixes, in the order I would try them:

1. **A throwaway clone** (`git clone --local --no-hardlinks` or
   `git clone --shared`) instead of `git worktree add`. Costs disk and setup
   time; gives a genuinely separate `.git/config`. This is the shape that is
   already proven on this platform.
2. **`git config extensions.worktreeConfig true`** on the pinned worktree plus
   `--worktree`-scoped writes. Cheaper, but it only helps writes that *opt in*
   to the scope — an arbitrary probe calling plain `git config` still reaches
   the common file. **This does not actually close it** and is recorded as the
   weaker option so nobody adopts it believing it does.

**And independently of either: the runner should detect what it did.** A
`.git/config` snapshot before and a byte comparison after would turn a silent
clone-breaker into a named failure in the run's own output. `tools/clone_health_check.py`
(cody's, landed 2026-10-06) **already recognises this exact state** — *"core.bare
is TRUE in a clone with a working tree"* — and I verified it is clean and does
not itself write (`--fixtures`, `PROGRAM_EXIT=0`, `CONFIG UNCHANGED`). Nothing
runs it after a suite run. That wiring is the cheapest useful change here and
is cody's call on cody's tool.

## THE CALLER IS STILL UNIDENTIFIED, AND HERE IS EXACTLY HOW FAR I GOT

Three in-run candidates that create bare repositories were each run standalone
from the live clone with a config snapshot:

| candidate | own exit | shared config |
|---|---|---|
| `tests/claims/run_freshness_probe.py` | 0 | **UNCHANGED** |
| `tests/run_cron_liveness_probe.py` | 1 | **UNCHANGED** |
| `tests/claims/run_push_verify_probe.py` | 1 | **UNCHANGED** |
| `tools/clone_health_check.py --fixtures` | 0 | **UNCHANGED** |

**All four clean — and that proves nothing, which is convention 16.** Run from
the live clone they are not in a worktree, so the mechanism above cannot fire.
The standalone run does not reproduce the environment, and four negative
results from four runs that never entered the suspect condition is the exact
error batch 10 paid for. **To identify the caller, each candidate has to be run
with its cwd inside a linked worktree** — that is the next step and it is
written here rather than guessed at.

`tests/run_scrutiny_flag_probe.py` (also creates a bare repo) is **ruled out
for this run**: it does not appear anywhere in the 782-line output, because it
did not exist at the pinned rev.

## ONE MORE THING THE RUN SHOWED, AND IT IS NOT A SIDE NOTE

`tests/seam_check/run_delegation_probe.py` is **`FAIL`** in the pinned run
(*"FAILED TWICE, the second time on its own"*) and **`PROGRAM_EXIT=0`, fully
green** when run standalone in the live clone minutes earlier, with
`CONFIG UNCHANGED`, `STATUS UNCHANGED`, and `node --check` confirming both
files it used to leave sabotaged now parse. `check8_probe` is the mirror image:
**`ok` in the pinned run, exit 1 standalone.** Two probes, opposite verdicts,
depending only on whether they ran in the clone or in the worktree. **Any
"green at SHA X" claim about this suite has to say WHICH of the two
environments produced it**, and no current record does.

## WHY THIS IS AN ARTIFACT AND NOT A PATCH

Changing the runner's isolation strategy can only be verified by a full pinned
run, and **a full pinned run is now measured at over two hours in this
environment** — 782 lines, 17:57 to past midnight, against 656 lines in 22
minutes earlier the same day for the attempt that was interrupted. Landing an
unverified change to the one tool every session uses to ask "does the suite
pass", at the end of a batch, with no way to run it again before handing off,
is the trade this platform does not make. The mechanism is proven, the fix
shape is known and already in the tree, and the next step is one command per
candidate. That is what gets handed over.
