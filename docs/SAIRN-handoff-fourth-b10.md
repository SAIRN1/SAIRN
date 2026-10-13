# HANDOFF — fourth / ted, batch b10, 2026-10-13

**Written BEFORE the report**, at a point where nothing is half-finished: the
b10 work is committed and pushed, `HEAD == origin/main`, no git operation is in
progress, no stash is held, and every queue item is closed with evidence or
named open with its exact next step.

**NAMING.** This file is `SAIRN-handoff-fourth-b10.md`, which is the convention
b10 established and applied backwards:
**`SAIRN-handoff-<session>-b<n>.md`**, `-2` appended when one batch writes a
second handoff. A batch number is a fact about the work; a date is a fact about
the keyboard, and the two came apart the moment b9's handoff was typed
`2026-10-16`. The two b9 handoffs are now
`docs/SAIRN-handoff-fourth-b9.md` (superseded) and
`docs/SAIRN-handoff-fourth-b9-2.md` (the authoritative b9 one).

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\d1bef68d-f747-45a9-89b1-59dd99a42ae2\scratchpad\`
Derivations are scripts and logs, not prose: `owner_map.py` (+ `owner_map.log`),
`undriven.txt`, `hank_rows.md`, `cody_undriven.md`, `cody_driven.md`,
`meth_b10.md`, `ext_b10.log`, `known-red-suites.before.json`, `stale_refs.txt`,
and from b9 and still cited: `drive_red86.jsonl` (the red-suite authority),
`gate_arm_unfetched.log`, `cte_reseated.log`, `item2_audit.log`,
`dropped-scratch-manifest-2026-10-13.txt`,
`refs-salvage-b6-2026-10-13.bundle`.

---

## 0. COMMITTED / PUSHED STATE

| | |
|---|---|
| HEAD | `a149769d` |
| `origin/main` | `a149769d` |
| ahead / behind | **0 / 0** |
| working tree | clean (tracked); no untracked files |
| b10 push | `a756ee4e..a149769d`, **1 commit** |
| `SAIRN_SEED_GATE=off` | **not used**, in any form |
| `.claude/settings.json` | **not committed**; hooks still **0 groups, 0 entries** |
| files under `tools/` edited | **0** — item 1 was route-only, by instruction |

**`a149769d` IS THE STATE AT THE MOMENT THIS HANDOFF WAS FINALISED, and it is
one commit stale by the time you read it.** A handoff written *before* the
report cannot include the commit that carries the report, so HEAD advances
past it by design. The ranges that followed are in
`SAIRN-report-fourth-b10.txt` §6 and §0, which names the same limit about
itself. **Re-derive HEAD rather than quoting either document** — three
rebases in b9 rewrote every local sha, which is what RULE E exists for.

The push was **not forced**. It lost one race to another clone
(non-fast-forward), was rebased, and landed on the second attempt. Both are in
the report.

---

## 1. THE ONE THING THE NEXT SESSION MUST NOT "FIX"

**`tools/tooling_inventory.py` CANNOT BE RUN IN THIS WORKING TREE and that is
correct.** It derives one of seven sources from `.claude/settings.json`, which
has hooks cleared on purpose, reads 0 entries, and refuses (exit 2) rather than
writing a thinner document. **Regenerate it inside a detached worktree of the
commit** and copy the result in. Do not restore hooks and do not "fix" the
refusal. (The former second item on this list — a stash holding a pre-cc
`settings.json` — no longer exists; it was dropped in b9 and no stash is held.)

---

## 2. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | route the 4th unfetched-base instance to cc | **DONE — routed, nothing in `tools/` touched** | cc applies the `:402`–`:409` replacement in `docs/2026-10-13-fourth-b10-routed-to-cc.md`, or records a NOT_PROMOTED decision for the checker |
| 2 | record the push evidence properly | **DONE — in the b10 report, §1** | nothing |
| 3 | assign the unqueued suites by directory | **DONE — 84 rows mapped; the count corrected from 65 to 36** | **cody drives the 36 undriven, in a worktree, one JSON record each**; hank drives his 5 |
| 4 | handoff naming | **DONE — 2 renamed, 2 Drive copies renamed, index rows carry `renamed_from`** | nothing; 9 stale references are named and deliberately left |
| 5 | the multi-defect-refusal procedure + NEXT FREE | **DONE — in `docs/METHODOLOGY.md`** | whoever runs convention intake may number it; **NEXT FREE is 35 as of `a149769d`** |
| 6 | push and confirm, no force | **DONE — `a756ee4e..a149769d`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

### Item 3 — the number in my own b9 digest was wrong, and that is the finding

**b9 said 65 unqueued. The measured figure is 36.** Re-derived rather than
quoted, which is the only reason it surfaced:

```
docs/known-red-suites.json entries        84
files with a record in drive_red86.jsonl  50   (43 RED, 5 COULD NOT RUN, 2 GREEN)
  of those, still in the register         48   (the 2 GREEN were moved out in b9)
UNDRIVEN = 84 - 48                        36   ALL of them under tests/
```

The register's `_b9_census_2026_10_13` marker says *"20 of the 86 entries ...
were driven ALONE"* — and its own authority log has **50** records, while the
same marker says *"THE SWEEP LOG IS THE AUTHORITY, not this sentence."* It was
right about where to look and wrong about the number: the sentence was drafted
mid-sweep and nothing re-derived it. **RULE E failing inside a paragraph that
states RULE E's own principle.** The marker is now corrected in the register
with the old text left visible rather than overwritten.

**The assignment, by the directory rule on each suite's own path:**

| owner | directory | entries | undriven |
|---|---|---:|---:|
| hank | `api/` | 5 | 0 |
| cody | `tests/` | 79 | **36** |
| cc | `tools/` | **0** | 0 |
| fourth | `docs/` | **0** | 0 |

**cc and I get nothing, and that is a measurement rather than an empty
section.** It is also **not** a statement that `tools/` is healthy — it is a
statement about what this register covers.

---

## 3. CLAIMS AND EXTERNAL HOLDS

| hold | count | detail |
|---|---:|---|
| repo claims held | **1** | b10, 11 declared FILES, committed **and pushed**, so every other clone sees it without a fetch |
| session locks held | **1** | `fourth.lock`. The release has now been DENIED by the permission layer in **four** successive batches, and that is a standing fact about this clone rather than an event |
| locks released by me | **0** | 14 lock files exist in `~/SAIRN-SESSION-LOCKS/`; none of the dead ones is attributable to me |
| worktrees besides main | **4** | **none of them mine**: `gate12-65340-3`, `invis-c0-75132`, `sairn-abl-q_gv10j5`, `sairn-gate-base-d78d62e71203`. The last is the push gate's own throwaway, which it failed to remove and says so on stderr |
| `git stash` | **0** | |
| `refs/salvage/*` | **0** | bundled, verified and deleted in b9 |

**Nothing was edited outside the declared `FILES` set this batch.** The two
Drive-side renames are not repo files; their index rows are in the declared set.

**NO FILE UNDER `tools/` WAS EDITED**, by instruction. Item 1's whole output is
a document.

---

## 4. WHAT IS OPEN, AND WHY

* **`tools/hover_auditor_scope_gate.py:409`** — the 4th unfetched-base
  instance, unfixed. **cc's.** The exact replacement is written out at
  `file:line` in `docs/2026-10-13-fourth-b10-routed-to-cc.md`, with three arms
  to drive it. It runs first in `.githooks/pre-push` and has passed every push
  attempt, so it is not blocking anybody — which is also why it will stay
  unfixed unless somebody picks it up.
* **No checker exists for the unfetched-base SHAPE.** Fully specified in the
  same document — taint source, four sinks, what counts as a guard, three exit
  states, six fixture arms. **Built by nobody.** Recorded as a *planned* action
  on defect record `55777a74`. A fifth gate can still be authored with it.
  **Next step:** cc builds it, or records a NOT_PROMOTED decision with the
  reason, which is strictly better than the spec sitting unread.
* **36 registered red suites have never been driven.** **cody's**, all under
  `tests/`. Next step in `docs/2026-10-13-fourth-b10-routed-red-suites.md`: 180s
  ceiling × 36 is up to 1.8 hours, so drive them **in a worktree** (several
  write when run), one JSON record per suite; exit 0 moves the entry out of
  `entries`, exit 2/3/timeout **must not**.
* **5 red suites under `api/`** — **hank's**, all confirmed red in b9 with a
  real exit code, so not stale rows. They are `*.test.js`, a node question.
* **21 of the 84 register entries carry no `why` at all.** The register's own
  rule is that a blank is a backlog, not a shrug.
* **5 of the 48 driven entries came back COULD NOT RUN.** Sharper than the 43
  reds: a suite that cannot run has no verdict and will read as "still red" for
  ever without anybody noticing it never executed.
* **The audit-log constraints** — 3 tables reject 11 emitted values and
  `sv_audit_log` has no `event_type` CHECK at all. **hank's**, and it needs one
  live `pg_constraint` read or one real insert; the tool reads `sql/*.sql` and
  says so, so "the migration did not take" and "the repo's DDL lags the
  database" are indistinguishable from this clone.
* **4 pre-existing bad rows in `docs/scrutiny-flags.json`** — `2a3a95c2` and
  `3ead2e86` accused of changes their diffs do not contain. **Already on
  `origin/main`, not added by me**, measured: the checker exits 1 with exactly
  those 4 rows against a clean worktree of `origin/main`. **cody's files.** They
  make `tools/sairn_rebase_resolve.py` REFUSE on every scrutiny-flags conflict,
  which is a tax on every rebase in every clone.
* **`docs/TOOLING-INVENTORY.md` under-reports every pre-commit-wired tool as
  UNWIRED.** The generator derives wiring from `.claude/settings.json` hooks and
  from the push gate, and reads `.githooks/` for neither. Not fixed — it is a
  change to the inventory's source list in a file two sessions contest. **Next
  step:** add `.githooks/` as an eighth derivation source, with that file's
  owner.
* **Nothing mechanises the NEXT FREE heading count.** No check counts the
  convention headings or refuses a duplicate or a gap, so the discipline holds
  only while sessions run the snippet by hand. Routed as an observation in
  `docs/METHODOLOGY.md`; nobody owns the conventions file, so it is not a plan.
* **9 Drive-side handoffs are UNINDEXED** in
  `docs/external-files-index.json` — **none of them mine**, and the check is
  warn-only on handoff names since 2026-10-13, so it reports and does not
  refuse. Deliberately not declared by me: a build agent declaring another
  session's artefact is what produced the five hand-declared rows already there.
* **9 files still reference the old handoff names** and are deliberately not
  edited — two cody handoffs, a cc handoff, three sealed reports including my
  own b9 report, and three claim-ledger files. Each is listed with its reason in
  `docs/SAIRN-handoff-fourth-b9.md`'s banner. All prose or append-only records;
  no tool resolves them as paths.
* **`fourth.lock`** — still held; the release has been denied four batches
  running.

**Nothing is partial.** Every item above is either another session's, or an
observation with its owner named, or a measurement with its denominator stated.
