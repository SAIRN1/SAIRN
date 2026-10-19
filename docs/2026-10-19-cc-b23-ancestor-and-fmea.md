# b23: a citation that only existed in one clone, two suites nobody drove, and eleven risk drafts

**cc, 2026-10-19.** Each item's one-line concept is stated before its
implementation, per the methodology item. Two of the four fixes in here are
defects I introduced earlier in this same batch and caught by measuring rather
than by reading — both are written up at full length, because the sequence is
the useful part.

---

## Item 4 — the one-line concept per item, before the code

**Item 1.** *A citation is only a citation if the commit is on a ref another
clone can reach — so `--check` asks whether the cited sha is an ancestor of
`origin/main` or of `HEAD`, and says COULD NOT TELL when neither ref can be
read rather than passing.*

**Item 2.** *Every file this batch's predecessor changed gets the risk draft
the register asks for, generated from recorded history rather than invented.*

**Item 3.** *A suite hank wrote and nobody drives is wired into the gate's
seam registry only if it clears that registry's own admission bar — a seam, a
recorded defect, and a known exit code measured first.*

**Item 5.** *Take hank's FMEA debt by measuring it instead of trusting the
number in the note, then draft the subset where a defect would cost most and
say plainly what was left.*

---

## Item 1 — `--check` passed on a commit that existed in one clone only

### What was wrong

```python
if git('rev-parse', '--verify', rec['commit'] + '^{commit}'):
    return rec['commit'], 'sha'          # accepted
```

`rev-parse --verify` accepts a **dangling object** for as long as the reflog
holds it. In b22 that is exactly what happened: a rebase replaced `634f7d70`,
`.githooks/post-rewrite` reseated the three new records correctly **in the
working tree**, nothing committed the reseat, and the push landed the
pre-rebase citation. origin/main carried three records naming a commit that
exists in no clone but cc's own reflog — and `--check` printed `OK` throughout.

**The old contract was true of one clone and false of every other.** Its
stated rationale — *"a record pointing at a real object is not a register
pointing at nothing"* — holds only where that object exists. The verdict
depended on who ran it, which is the one thing a shared register cannot afford.

### This reverses a recorded decision, and that is said out loud

`reachable()` has carried this sentence since 2026-09-16: *"`--check`'s
acceptance contract is deliberately unchanged."* That decision is **overturned
here on evidence**, not quietly contradicted. The evidence is the b22 landing
above.

### What is NOT changed, because the reasoning behind it still stands

A sha that is unreachable is **not a failure on its own.** It falls through to
the record's SUBJECT, exactly as an unresolvable one has since 2026-09-11, and
a unique subject match is reported as a RESEAT. Rebasing is normal with five
clones on one branch, and a register that goes red for it is a register
somebody switches off. The only records that now fail are those where neither
a reachable sha nor the subject answers.

### THE FIRST DRAFT WAS WRONG, AND THE PROBE SAID SO WITHIN THE HOUR

The first version used `reseat_base()`, which prefers `origin/main` and falls
back to `HEAD`. That is right for `--reseat` — you want to know what another
clone will fetch — and **wrong for `--check`**:

> `tests/run_defect_register_probe.py`: **152/152 → 6 FAILED**
> (CC18, CC19, J1, J2, J3, J4 — all `--check` returning 1 where 0 or 2 was due)

Because `--add` records a commit **the moment it is made**, and the probe
plants records citing commits it creates in its own throwaway worktree. Those
commits are real, are on that clone's HEAD, and are not on origin/main yet.
Refusing them would make the register red for the entire normal window between
committing and pushing.

So the contract is the **union: `origin/main` OR `HEAD`.** And the b22 failure
is still caught, measured rather than argued:

| sha | resolves here | ancestor of origin/main | ancestor of HEAD | verdict |
|---|---|---|---|---|
| `634f7d709a87` (the orphan) | yes | **no** | **no** | refused |
| `a61abc5ae46e` (its successor) | yes | yes | yes | accepted |

The rebase replaced the orphan, so HEAD does not contain it either. The union
admits legitimate pre-push work and still refuses a reflog orphan — exactly
the line the b22 defect fell across.

**How the baseline was established, because "the probe is red" is only a
finding if it was green before:** the pre-b23 tool was written into
`tools/defect_register.py` from `origin/main` inside a `try/finally`, the probe
driven, and the file restored and byte-compared. **376s, exit 0, 152 checks, 0
failed.** So the 6 failures were mine.

### Verified against this batch's own three records

The b22 records, driven through both the pre-b23 and post-b23 `resolve()`.
Reads the real register; **writes nothing to it** — hank holds that file this
batch.

| case | pre-b23 | post-b23 |
|---|---|---|
| **A.** as they stand on origin (`a61abc5a`) | PASS | PASS — no regression |
| **B.** commit rolled back to the orphan | PASS | RESEAT — visible, not a failure |
| **C.** orphan **and** the subject gone | **PASS** | **FAIL** |

**C is the b22 defect exactly**, and the column that matters is that pre-b23
called it good. Permanent arms: `--selfcheck-reachability`, **16/16**.

The lock **synthesises** the dangling commit with `git commit-tree` rather than
naming `634f7d70`: hard-coding the real instance would make the lock pass
today, pass nowhere else, and stop testing anything the day the reflog expired
— discipline 8 arriving inside the fix for a reachability defect.

### AND A SECOND DEFECT OF MY OWN, in the fix for the first

**A 43-second regression, then a probe timeout.** The first version called
`reachable()` per record: `git merge-base --is-ancestor` each time, **66ms per
call measured on this machine**, 653 non-external records. `--check` went to
50.5s, and `tests/run_defect_register_probe.py` — which drives `--check`
several times — went from passing to a **420-second timeout**.

That is not cosmetic. **A check slow enough to time out is a check that gets
excluded from the sweep, and an excluded check reports nothing while looking
exactly like one that passed** — the same shape this fix exists to close, one
layer out.

`git rev-list` answers the whole question in **one** call: 0.33s for all 9,804
commits. And membership of that set proves existence as well as reachability,
so the `rev-parse` is skipped for every record on the trunk — which removed
**648 of the 661 `rev-parse` subprocesses the function was already making
before b23**. Net: **50.5s → 9.5s**, faster than the code I started with.

**And a third: the cache leaked across repositories.** `ancestor_set` was
keyed on the refs alone. `REPO` is a module global, and
`tests/run_defect_register_superseded_probe.py` reassigns it to drive
`cmd_check()` in-process against a throwaway repo — so 9,804 real ancestors
leaked into the sandbox and one arm went red. The cache is now keyed on
`(REPO, refs)`. **This file's own docstring had already warned that a stale
ancestor set would be "a confident wrong answer about exactly the thing under
test" while nothing stopped one.** Two arms now hold it.

### Final state

`--check` exit 0, 654 records, 9.5s, summary line rewritten to name the refs it
asked about rather than claiming "every commit resolves". All five register
probes green: main 152/152, reseat, superseded, vocab, planned.

---

## Items 2 and 5 — eleven FMEA drafts, and hank's number re-measured

`tools/fmea_draft.py --save`, one file per draft, format unchanged.

**Item 2 — the three files b22 changed** (the register printed `NO DRAFT` for
each of them three times, once per b22 record):

| file | risks drafted |
|---|---:|
| `tools/wcag_contrast_check.py` | 204 |
| `tools/status_board_bridge_check.py` | 200 |
| `tests/run_push_gate_preflight_probe.py` | 197 |

**Item 5 — hank's b18 debt, and the note's figure was low.** Hank's registry
note says *"FMEA drafts are owed for eight new/changed files."* Measured
against the five b18 register records and `docs/fmea/`:

> **55 files cited by the b18 records. 8 had a draft. 47 did not** — 41 of them
> real source, test or SQL rather than evidence logs.

So **41, not 8.** Reported rather than quietly worked to the smaller number.
Eight drafted, chosen by what a defect in them would cost:

| file | why this one |
|---|---|
| `api/_lib/audit.js` | every app's audit trail runs through it |
| `api/_lib/sf-roles.js` | a role module — who may do what |
| `api/sairncash/verify.js` | payment verification |
| `tools/audit_event_type_check.py` | the checker itself |
| `api/b18-countersign-lock.test.js` | wired into the blocking gate this batch |
| `api/b18-passkey-profile-e2e.test.js` | likewise |
| `api/sd-data-cross-tenant-dispatchers.test.js` | tenant isolation |
| `sql/sairnlegacy_audit_log_schema.sql` | representative of the 13 |

**The thirteen `*_audit_log_schema.sql` files are one shape repeated.** One is
drafted as the representative; drafting all thirteen would be bulk with little
marginal value, and that is a judgement being **stated rather than performed as
a silent skip**.

**After: 16 of 55 drafted, 39 owed, 33 of those source/test/SQL.** The
platform-wide `fmea_prediction_check.py` figure moved 203 → 202, which is the
honest number: that metric counts files **with a defect on record** and no
draft, and most of these eleven are cited by a record rather than being its
subject.

---

## Item 3 — hank's two b18 suites, wired into the gate

**Re-measured before acting** rather than taken from the note:
`grep -rlE 'b18-(countersign|passkey)' tools/` returned nothing. It now returns
`tools/sairn_push_gate_hook.py`.

`GUARD_TESTS` is the seam registry — not the full suite, deliberately, because
146 files on every push is a real tax and most of them are the
author-runs-it class. Its admission bar is three things, and both suites clear
all three:

**`api/b18-countersign-lock.test.js`** — a seam between `api/_lib/countersign.js`
(decides) and `api/sd-data.js` (enforces), edited by different work. The
recorded defect is fourth's b26 finding H1: SAIRNlaw's trust hard-lock could be
**deleted entirely** with every suite still green. So this suite removes each
gate on purpose and asserts what goes red **per arm**. Its A1 arm is the one to
read first — neither SQL file has been run, so both locks answer 503
NOT_PROVISIONED in production today, and A1 asserts exactly that, because *"the
lock is inert until Michael runs SQL"* and *"the lock lets writes through until
Michael runs SQL"* are opposite facts. **exit 0, 2.40s, 59 passed.**

**`api/b18-passkey-profile-e2e.test.js`** — a seam between a suite and a 2MB
page, which is the shape that rots silently. The recorded defect is
stonedesk.html's own 2026-08-06 "Granting..." bug, and the sentence that earns
it a place is in that comment: the reset code was *"confirmed present and
correct on every path, CHECKED REPEATEDLY"* and never ran, because a
synchronous ReferenceError happened first. **Reading the code was the method
and the method failed.**

**It fails closed on its own extraction, which is what makes it safe to wire.**
It lifts three functions out of `stonedesk.html` by anchor and **compiles**
them; a lift that is missing or will not parse is reported UNPROVEN and never
as a pass, and a Section Z asserts the extraction before any arm depends on it.
That is the same stale-anchor class cc b22 fixed in
`run_push_gate_preflight_probe.py` — already handled here — and exit 3 routes
to the gate's `exit3_reason()` rather than to a silent skip. **exit 0, 1.38s,
37 passed.**

Gate selftest **56/56** after wiring; `--preflight` clean.

---

## What this batch did NOT do

- **`docs/defect-density-register.json` was not touched.** hank holds it in the
  b20 claim. Item 1 only reads it, and the verification works on in-memory
  copies.
- **The 33 remaining b18-owed drafts.** Named, counted, listed by the command
  that produces them.
- **No record was added for the three defects fixed here.** Two of them are my
  own, introduced and fixed inside this batch; recording them needs the
  register file, which is hank's this batch. Routed rather than skipped.
