# Blameless postmortem — the two serious mistakes of 2026-10-06 (Cody)

**Scope: two incidents only.** Both happened while writing a Tier A discharge
into `docs/tier-a-reviews.json`, an append-only ledger three other clones
3-way merge. Neither reached `origin`.

**Blameless means the finding is about the system, not the session.** Both
sections end in a system-level fix, and both fixes are named with their state.

---

## INCIDENT 1 — a shell pasted a local uid into an append-only ledger

### What happened

A review verdict was passed to `tier_a_review_gate.py --discharge` **as a shell
argument**. The shell command-substituted two backticked fragments away and
**replaced a third with the output of `` `id` ``**:

```
AND THE GAP IS NOT EMPTY: api/_lib/sd-store.js:166 writes  into sd_slabs with
slab_id: String(slab.id) as a COLUMN beside it, so uid=197609(marsh)
gid=197609 groups=197609 is duplicated into the blob
```

Three defects in one sentence: `` `data: slab` `` vanished, `` `data: data` ``
vanished, and `` `id` `` became a uid, gid and group list.

### Why the existing control did not fire

**It was not absent. It was unused.** `tier_a_review_gate.py` has had
`--body-file` the whole time, and its own comment at line 1816 reads:

> **`--body-file`: THE SHELL IS WHERE THE TEXT DIES, NOT THIS TOOL**

**The lesson was already written, in the tool, next to the flag that implements
it.** Nothing refused the argument path, because there was no argument path to
refuse — the body was positional, and a positional body is indistinguishable
from a correct call at the moment it is made.

### Contributing conditions, not causes

- **Backticks are the repo's own house style** for naming code in prose, so a
  verdict that cites `file:line` and a field name is *more* likely to contain
  them, not less.
- **The damage is silent and plausible.** `uid=197609(marsh)` reads like text
  somebody meant to write. Nothing in the pipeline looks at a verdict again.
- **`tools/eaten_substitution_check.py` cannot see it** — its subject is commit
  MESSAGES, not a ledger FIELD. Recorded as a gap on 2026-10-05, and this is the
  second instance since.

### System-level fix

| fix | state |
|---|---|
| **`tools/ledger_append.py`** — body text comes **only** from a file or stdin, and **there is no flag that takes it**, asserted against the parser itself. Arms for backticks, `$(...)`, embedded quotes and **the `id`-output case**, each paired with *"and NO `uid=` appears"* | **BUILT, `--fixtures` EXIT 0, 20 arms. CANNOT LAND** — registering needs `tools/tooling_inventory.py`, in hank's live claim. Untracked in the working tree |
| **Widen `eaten_substitution_check.py` to ledger fields** | **ROUTED, not attempted.** Owner to be read from `docs/tool-owner-map.json` before anyone touches it |
| Teach each ledger-writing tool `--body-file` | `tier_a_review_gate.py` already has it. **The gap was use, not existence** — which is precisely why the fix is a tool that cannot be bypassed rather than another note |

---

## INCIDENT 2 — a 5681-line diff on a ledger four clones merge

### What happened

Repairing incident 1 meant editing one `verdict` string. The repair read the
file with `json.load`, patched the string, and wrote it back with
`json.dumps(indent=1)`.

```
docs/tier-a-reviews.json | 11355 ++++++++++++-----------
1 file changed, 5681 insertions(+), 5674 deletions(-)
```

The file's own stored layout is not `indent=1`, so **every line churned**. The
correct diff for the same semantic change was **15 insertions and 8 deletions**.

### Why it mattered more than it looked

`docs/tier-a-reviews.json` declares its own merge policy: **append-only across
four clones, 3-way union merged by `(author_session, opened_at)`**, with
`sairn_rebase_resolve.py` reading from the **common ancestor**. A whole-file
rewrite destroys that: there is no common ancestor left to merge against, and
**every other session would have taken a conflict on every record.**

### Why nothing caught it

- **The push gate checks generated documents against their sources.** This file
  is not generated, so no gate had an opinion.
- **`git diff --stat` was printed and read.** The 5681 was visible. It was
  caught because I looked at the number, which is not a control.
- **`--validate` passed**, correctly: the file was well-formed and the records
  were intact. **A valid file and a mergeable diff are different properties**,
  and only one was being checked.

### System-level fix

| fix | state |
|---|---|
| **`tools/ledger_append.py` bounds the diff** — after writing, `git diff --numstat` must show no more added lines than the entry holds plus a printed allowance; **a breach is REVERTED**, and an arm proves the revert by re-counting the records | **BUILT, EXIT 0. CANNOT LAND** — same claim |
| **JSON ledgers get a targeted single-object insert** — the array's closing bracket is found in the **raw text**, the object is inserted with the preceding sibling's indentation, and the file is **never re-serialised**. `json` is used only to validate the result parses and that the array grew by exactly one | **BUILT** |
| A pre-commit hook rejecting large diffs on ledger paths | **CONSIDERED AND NOT CHOSEN** — it fires after the damage is in the index, and a size threshold is a guess. Recorded in the design note as a possible second layer |

---

## THE SECOND SYSTEM-LEVEL FIX — a detector for tautological arms

**Asked for, and it is a routed spec rather than a patch.**

### The shape

An arm that cannot fail:

1. **`assert.ok(true)`** / `assert(True)` / `arm(..., True)` — a literal-true
   assertion. **I shipped one on 2026-10-06** in
   `api/_lib/firebase-mint.test.js`, with a paragraph explaining why the thing
   could not be tested. It could: the obstacle was a module cache, and a child
   process has an empty one.
2. **An arm matching its own text** — a grep whose needle is written as a
   literal in the same file it scans. **Three instances in two days**, all mine:
   `G2` in `run_dead_rule_sweep_probe.py` (recorded in that file), `L1`/`L2` in
   the same probe, and `clone_health_check.py`'s read-only arm, which matched
   its **own docstring** naming `git worktree prune`.
3. **A passing arm that prints its failure detail** — `ledger_append.py`'s own
   reporter did this on its first run, printing
   ``ok  backticks survives verbatim -- needle '`b`' absent``. A clean line
   indistinguishable from a finding.

### Why it extends an existing checker and does not become a new one

**`tools/checker_selftest_check.py` already asks the adjacent question** — does
a tool demonstrate a known-positive on the run that reports clean — and splits
the answer four ways rather than two. A parallel tool would ask half of the same
question with a second corpus definition and a second criteria lock, which is
the duplication this platform corrects.

### The spec, routed to cc

**`tools/checker_selftest_check.py` is in cc's LIVE claim at HEAD (0.8h).
Claims-checked before writing anything. This is a spec, not a patch.**

| rule | detection | why it is safe to flag |
|---|---|---|
| **T1 literal-true assertion** | via `ast` / a JS parse: an assertion whose sole argument is a literal `True`/`true`, or `assert.ok(true)` | Zero legitimate uses. A placeholder is exactly what this catches |
| **T2 self-matching needle** | a string literal in file *F* used as a search needle against *F* itself, or against a file that provably contains it | **MUST have an exemption for a needle assembled from parts** — `run_dead_rule_sweep_probe.py:124` already builds its needle from `chr(39)`/`chr(34)` precisely so the arm is about the rest of the file. That is the CORRECT pattern and must not be flagged |
| **T3 detail printed on success** | a reporter that passes its failure-detail argument on the success branch | Narrow and mechanical |
| **the negative half, required** | each rule needs a fixture that must NOT fire: a real assertion with a computed argument (T1), an assembled needle (T2), a reporter that branches (T3) | Without these the detector flags every assertion and gets switched off in a day |

**It must report, not gate.** T2 in particular cannot tell a deliberate
self-reference from an accidental one without reading the surrounding comment,
and the direction of its error is a **false positive** — which is the same
reason `gate_parity_check.py` is a report.

---

## WHAT THIS POSTMORTEM DOES NOT CLAIM

- **That `ledger_append.py` would have prevented incident 1.** It removes the
  argument path, so the *specific* corruption cannot recur — but a caller who
  writes a ledger with their own `io.open` is unaffected. **The tool is a
  guardrail, not a wall**, and nothing currently forces its use.
- **That two incidents is the whole count.** Five more mistakes from the same
  batch are listed in `docs/handoff-cody-2026-10-06b.md` §6; they were judged
  less serious and are **not** re-litigated here. Whether that judgement is
  right is somebody else's to check.
- **That the fixes are in place.** **Both are built and neither has landed**,
  blocked on one claim. A fix that cannot be pushed is a fix on paper, and
  saying otherwise would be the thing this document exists to stop.
