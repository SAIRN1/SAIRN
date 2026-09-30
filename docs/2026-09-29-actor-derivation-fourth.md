# Actor derivation: the declared map measured against the repository

**Fourth, 2026-09-30.** `tools/rewrite_convergence_map.py --derive`.

A declaration is the author's claim. This is the same question asked of the
repository, by three clauses that never read `ACTORS`:

1. every file under the directory `core.hooksPath` **actually** names;
2. every file that calls git with a **mutating** verb -- commit, add, push,
   rebase, reset, merge, amend, checkout -- **on this tree** rather than on a
   sandbox it built itself;
3. every file that opens a **git-tracked** path for writing.

## The result: the declaration was an undercount, by two

```
ACTOR DERIVATION -- declared vs measured
core.hooksPath           : .githooks
declared actors          : 14 in 11 file(s)
derived files            : 15
  also declared          : 7
  named in OUT_OF_SCOPE  : 8
  UNACCOUNTED FOR        : 0

DECLARED BUT NOT DERIVED -- 4, and NOT a finding.
Clause 2 only sees a MUTATING GIT VERB, so a hook that shells out to
another tool, a regenerator that only writes a file, and several
sub-actors sharing one file are all invisible to it. A file-granular
scan cannot resolve push_retry.py into four actors.
  tools/defect_register.py                       defect_register_reseat
  tools/master_plan.py                           regen_master_plan
  tools/tooling_inventory.py                     regen_tooling_inventory
  tools/traceability_matrix.py                   regen_traceability_matrix

OK -- every derived file is either a declared actor or named in
OUT_OF_SCOPE with the reason it is not in the convergence chain.
```

## What driving it found, and what it cost to get there

**Two real actors the twelve-entry map missed**, both squarely inside the
convergence chain, both now declared:

- **`tools/sairn_claim.py`** -- add, commit, push, **and rebase**, on every
  claim and every release. It fires `post-rewrite` exactly as the push loop
  does, so it can enter the livelock from a completely different door. What
  keeps it out is that it refuses outright on an unstaged change rather than
  staging by breadth -- which is a property of that tool, not of the map.
- **`tools/sairn_rebase_resolve.py`** -- stages the merged ledger, never
  commits, and refuses on a deleted record rather than unioning it back.

A map written by the session that built the chain missed two of its own
members. That is the whole argument for deriving rather than declaring.

**Two defects in the derivation itself, both found by driving it:**

- Clause 2 without a sandbox discriminator answered **85 files**. Almost all
  were probes committing into their own `mkdtemp` repo. A gate that flags 85
  correct files is a gate somebody deletes.
- Clause 3 first asked two separate questions and ANDed them -- does this file
  contain a write-mode `open` anywhere, and does it mention a tracked path
  anywhere. Every probe in `tests/` satisfies both: it names its subject (a
  tracked file it only reads) and writes to a tempdir. That answered **122
  unaccounted**. The tracked path now has to be the **argument** of the write,
  read off the AST, so the two facts are joined at the call.

## The declared-but-not-derived four are not a finding

Clause 2 only sees a mutating git verb. `.githooks/post-rewrite` shells out
to `defect_register.py` and calls no git verb of its own; the three
regenerators only write files; and a file-granular scan cannot resolve
`push_retry.py` into its four actors. Both sets are printed with their
symmetric difference and neither is treated as the answer.

## Every "does not re-trigger" was driven twice

Each regenerator was run, its output hashed, run again, and the second hash
required to match. A generator that stamps a run time into its own output
fails this -- which is the shape `--simulate --inject-loop` models.

```
F. every declared "does not re-trigger" is DRIVEN TWICE, not believed
ok   F0 the regenerators are read off the map, not listed here        3 found
ok   F regen_master_plan          second run changes nothing (docs/MASTER-PLAN.md) exit=0,0  first-run-changed=False
ok   F regen_traceability_matrix  second run changes nothing (docs/traceability-matrix.md) exit=0,0  first-run-changed=False
ok   F regen_tooling_inventory    second run changes nothing (docs/TOOLING-INVENTORY.md) exit=0,0  first-run-changed=False

18 passed, 0 failed
```

## The known-bad controls for the derivation

**E4** plants an undeclared actor -- a file that runs `git add -A` and
`git commit` on the real tree with no sandbox -- into a mirrored tree, and
requires `--derive` to fail and to name it. Without E4, E1 passing means
only that the repository happens to be clean, which is also what a
derivation finding nothing at all would report.

**E5** is the other direction: a file that inits and commits into its own
`mkdtemp` must **not** be reported. That is the discriminator whose absence
produced 85 instead of 15.
