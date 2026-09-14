# Scoping: tolerance stack-up, closing error, and known-rate drift

**Written 2026-09-13 (Fourth).** Three items from the civil-engineering /
surveying research, scoped before anything is built, with a real size against
each. Where a claim carries a number, the command that produced it is named,
because a scoping document that asserts its own figures is the thing item 1 is
about.

**STATUS, updated 2026-09-13 after the scoping was approved — this is no longer
a plan.** Items 1 and 2 are BUILT (`6ac7d8af`, `a4d88cbd`). Item 3 was SPLIT
rather than assigned to one owner: `cc` keeps `db/schema_snapshot.json`,
Fourth took `docs/TOOLING-INVENTORY.md`, and that half is done. The sizes below
are left as they were ESTIMATED, not corrected after the fact, so the estimate
can be judged against what it cost. Item 1 came in at M as scoped; item 2 at S.

Convention references below are to `docs/2026-09-13-cross-domain-disciplines.md`.

---

## Item 1 — tolerance stack-up

### The question

Does any *"vertical finished"* or *"clean"* declaration on this platform
compound several individually-approximate numbers without anyone having bounded
what the COMBINED error of that chain actually is?

### The answer: yes, once, and the components have already drifted apart

`docs/MASTER-PLAN.md` is the only document on the platform that defines a
combined end state. Its own words:

> A vertical is **FINISHED** when all four are true of it.
> 1 BUILT · 2 TIERED · 3 TRACEABLE · 4 FAULT-TESTED

Four gates, four separately-measured numbers, one conjunctive verdict. That is
a stack-up by construction. It also says, in the present tense:

> **Every number below is derived, not asserted.**

**It is not.** It was derived once, on 2026-09-10, by hand. There is no
generator, no `--check`, and nothing under `tests/` asserts any figure in it —
verified by `grep -rn "MASTER-PLAN" tools/ tests/`, which returns five test
files citing it as *motivation* in a docstring and zero assertions.

**THE DRIFT IS MEASURABLE TODAY, THREE DAYS LATER.** The document cites
`docs/traceability-matrix.md` as its source for one figure:

| Claim | Where | Value |
|---|---|---|
| "Traceability is **86 of 273** across the platform" | `MASTER-PLAN.md`, cites the matrix | 31.5% |
| "**135 of 328** test files are traced to a stated requirement" | `traceability-matrix.md`, regenerated today | 41.2% |
| "186 dedicated suites, **53 of them traced**" | `MASTER-PLAN.md`, same document | 28.5% |

Three traced counts, three denominators, two documents, one cited source. The
numerator moved 86 → 135 and the denominator 273 → 328 in three days. The
third figure (53 of 186) is a different population again and the document does
not say so — it reads as the same measurement stated twice.

**This is the stack-up, and it is not hypothetical.** A reader asking "is
SAIRNscape finished?" gets a conjunction of four numbers, one of which is 49
behind, one of which is a different population, and none of which carries the
error of the classifier that produced it. `traced` is a keyword-and-citation
match — an approximate classifier — and nothing states its false-positive rate.

### What the fix is, and it is not new design

Convention 3 already answers it: *a named, itemized uncertainty table — never a
combined number*, plus its corollary, *publish the denominator*. Applied here:

1. `MASTER-PLAN.md` becomes DERIVED, with `--check`, like the other two
   documents. Its judgment half — what the four gates MEAN — is good and stays
   hand-written; only the numbers move.
2. Every figure carries its denominator and the tool that produced it, one row
   each, so the four gates never collapse into a single verdict.
3. The `traced` classifier states what it cannot tell — it already does this
   well in the matrix's own "what this cannot tell you" section; the status
   document drops that caveat when it quotes the number.

### Size: **M — one session**

Not L. The population is small and was measured rather than guessed:

- `git ls-files tools/*.py` + a scan for tools that WRITE a `docs/*.md` file:
  **2 generators**, both already with `--check` (`tooling_inventory.py`,
  `traceability_matrix.py`).
- tools printing a computed ratio or percentage: **6**
  (`defect_register`, `fmea_draft`, `fmea_prediction_check`, `jscomments`,
  `sairn_dead_function_sweep`, `testability_gate`).
- documents compounding several of them into one verdict: **1**
  (`MASTER-PLAN.md`).

So the audit half is **S** and is effectively done by this section. The build
half is a third generator plus its control, which is the same shape as the two
that exist.

**One thing to decide before building, not during:** whether the per-vertical
table stays a table of four numbers or becomes four separate rows per vertical.
The first is readable, the second is what convention 3 asks for. That is a
judgment call about the document's audience, not a technical one.

---

## Item 2 — closed-traverse closing error

### The question

For any document re-derived from source, does re-running the derivation
actually loop back to the same real source without silent drift — the way a
surveyed traverse must return to its known starting point within tolerance?

### The answer: `--check` is not a closing-error check, and today proved it twice

Both generators have `--check`, and both pass right now:

    python tools/tooling_inventory.py --check    -> OK: matches the repo
    python tools/traceability_matrix.py --check  -> OK: matches its sources

**But `--check` compares the document to what the generator produces TODAY.
Both ends of that comparison come from the same instrument.** It proves the
document has not been hand-edited. It cannot prove the generator still reads
what it used to read. In surveying terms it re-measures the last leg and calls
the traverse closed; it never returns to the known point.

**Two demonstrations from this session, both in `tooling_inventory.py`:**

- Its probe column named the wrong test file for **27 tools** — a comment
  mentioning a tool counted as running it. `--check` was byte-clean the entire
  time, because the document faithfully matched a reader that was wrong.
- Fixing that, the pre-filter tested the FILENAME while `import x as M` never
  writes `.py`, so the generator briefly saw **no probe at all** for five
  promoted checkers that have thorough controls. `--check` stayed clean through
  that too. It was caught by reading the regenerated diff, not by the check.

**The failure mode has a name here already:** a check that reads as coverage
and structurally cannot fire — the one **seven of the eight** conventions defend
against. (This line read *"all six"* when written on 2026-09-13; the document
gained a seventh and an eighth the same day. Item 7, byte-identical-is-not-
safe-in-context, is the exception and defends against something else.)

### What the fix is

A **closing-error tripwire per generator**: every derivation SOURCE must yield
a non-zero count, and a source that yields zero is a refusal, not a quiet zero.
`tooling_inventory.py` already does exactly this for one input — it REFUSES to
run if `PURPOSES` names a tool that does not exist, or a tool has no entry. It
does not do it for `suite_refs`, `hooked`, or `gate_invokes`, which is why the
27-tool error was silent.

Concretely, per generator: list the inputs, assert each contributes, and print
the contribution counts in the document so a reader sees the traverse close.
`report_only_checks.py` already models the shape — `app_files()` raises rather
than returning `[]` when `git ls-files` fails, with the reason written at the
raise.

### Size: **S — under a session, for both existing generators**

Two generators, roughly four inputs each, and the refusal pattern already
exists in the same file. Add **M** if `MASTER-PLAN.md` becomes the third
generator under item 1, in which case do item 1 first and this one inherits it.

**Build the control first** — the disciplines document's **closing rule**, which
is deliberately unnumbered so it cannot collide with a section: *build the
control that makes it fail before you trust the run that says it passed.* (This
said *"the seventh convention"* when written, meaning that closing rule at a time
when the document had six numbered sections. It now has eight, and section 7 is a
different thing entirely.) Drive each generator from a copy of the tree with one
source deliberately emptied, and assert it REFUSES rather than reporting a clean
document. Without that arm this is another check that cannot fire.

---

## Item 3 — known-rate drift correction · **SPLIT, 2026-09-13**

### The question

`db/schema_snapshot.json` and `docs/TOOLING-INVENTORY.md` both go stale on a
knowable pattern. Is a scheduled, forced re-derivation on a known cadence the
right fix — actively compensating for a known bias before tolerance is
exceeded, rather than detecting it once blown?

### Status

**SPLIT ON MICHAEL'S CALL, 2026-09-13 — scoped-and-reassigned, not dropped.**
The two halves have different drift mechanics (see the hand-over notes below),
so this is not a collision to settle by picking one owner:

- **`db/schema_snapshot.json` stays with `cc`**, who holds
  `schema-snapshot-staleness-cadence` and already has it in progress. It is
  the half that genuinely needs the human-paste mechanism.
- **`docs/TOOLING-INVENTORY.md` came to Fourth** and is DONE — see
  `python tools/tooling_inventory.py --drift`. The answer turned out to be
  that a schedule adds little: measured over its 16 regenerations, the worst
  staleness it has ever reached is FIVE source commits and the median is two,
  because `--check` already runs on every push. What was missing was
  convention 4 — an alarm tighter than the failure point — so it now reports
  the MARGIN, warning at three, a line taken from that measurement rather
  than chosen.

### What to hand over

Two observations from items 1 and 2 that bear on it, so they are not
re-derived:

1. **The two documents have different drift mechanics and should not share a
   cadence.** `TOOLING-INVENTORY.md` is derived from the repo and can be
   regenerated by anyone at any time at zero cost — its staleness is a
   *scheduling* problem. `db/schema_snapshot.json` cannot be regenerated from
   the repo at all; it requires a live Supabase capture pasted in by a human,
   and that relay has now failed at least twice (`tools/load_schema_snapshot.py`
   exists specifically because of it). Its staleness is a *hand-off* problem,
   and a cron that cannot perform the capture will report drift it cannot fix.
2. **A forced re-derivation on a cadence does not close item 2's gap and must
   not be read as closing it.** Re-running a generator more often produces a
   fresher document from the same instrument. If the instrument has stopped
   reading a source, a cadence makes the wrong document arrive more promptly.
   The two fixes are complementary; neither substitutes.

---

## What was deliberately NOT done here

No tool was written, no document was regenerated, and no number in
`MASTER-PLAN.md` was corrected. Correcting the figures without making them
derived would reset the clock on exactly the drift this scoping describes, and
would make the document look current while remaining hand-maintained — which is
the failure `docs/2026-09-09-tooling-inventory.md` already recorded when it was
correct on the day and stale within three.
