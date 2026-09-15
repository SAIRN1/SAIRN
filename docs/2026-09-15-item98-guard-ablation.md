# Item 98 — ablation: 17 of 38 role gates can be removed and nothing goes red

**2026-09-15 (Fourth).** Asked whether ablation testing — the ML practice of
removing a component and measuring the drop — has anything to offer a codebase.

**Answer: it asks a different question from mutation testing, and on this
platform the difference points at the architecture rather than at the test
suite.** Tool: `tools/guard_ablation.py`.

---

## 1. Why this is not mutation testing with a new name

| | Question | What a negative result blames |
|---|---|---|
| **Mutation testing** | Does a test catch this defect? | the test suite |
| **Ablation** | If I remove this component, does the measured outcome change **at all**? | the architecture |

The distinction earned itself hours before this tool existed. A three-layer peel
of SAIRNcare's pharmacy-review gate found its innermost role check is
**unreachable by construction** — an outer gate has already refused every role
it names by the time it runs. `tests/sairncare/test-alf-phase3.js` carries an
assertion literally called *"med_aide CANNOT accept a pharmacy order"*, and that
assertion passes on a **different gate entirely**.

Mutation testing reports "not caught" and sends you to write a test. The test
already exists. Ablation reports "removing it changes nothing" and sends you to
the gate above it, which is where the answer was.

---

## 2. What was measured

**Subject:** `api/sd-data.js`. **Gates:** every site of the exact shape
`if (!SOMETHING_ROLES[session.role]) {`, derived by scanning rather than listed,
so a gate added tomorrow is ablated tomorrow. Each is replaced with
`if (false) {` — the guard stops refusing anybody — one at a time, in a
throwaway worktree.

**Observers:** all 93 tracked suites that load `api/sd-data.js` and are green on
the shipped tree.

| Verdict | Count |
|---|---|
| **LOAD-BEARING** — at least one suite goes red, and it is named | **21** |
| **SILENT** — 93 suites, none notice | **17** |
| COULD-NOT-RUN | 0 |

*(Composite, and both halves were measured rather than inferred: 37 gates from
one sweep at subject sha256 `b1cd5520`, plus one gate re-measured after the
regex fix in §4. The recovered gate came back SILENT.)*

**SILENT is reported as a question, never as a verdict**, and the tool says so
in its own output. It means one of two things and the tool cannot tell them
apart:

- **(a) redundant** — another guard refuses the same request, so behaviour is
  unchanged. Fine, and worth writing down where it sits.
- **(b) untested** — behaviour genuinely changed and nobody looks. A hole.

Folding those into one number would be the fabrication this platform keeps
paying for. `packages/testint/`'s README already states why: a count across
different questions is a number nobody can act on.

---

## 3. Answering (a) vs (b) by hand, where a suite already drives the path

There is a cheap discriminator for the subset of SILENT gates whose path a suite
does exercise: **if a suite drives that request and still gets the same status
code, the gate is redundant — the suite passing IS the evidence.**

Two worked examples, both in SAIRNcare's MAR:

- **`ALF_MAR_ROLES` at the WRITE branch — REDUNDANT.**
  `tests/sairncare/test-alf-mar.js` asserts *"caregiver has zero MAR access:
  write is 403"*. With the gate ablated that assertion still passes, so the
  response is still 403 — a later gate refuses. Reading the path: the live
  assignee look-up refuses, because `RES-1` is assigned to `MA-1` and
  `ALF_MAR_BROAD_ROLES[caregiver]` is false. The outer role gate is a second
  lock on a door the inner one already holds.
- **`ALF_MAR_ORDER_ROLES` in the pharmacy-review block — REDUNDANT, and
  unreachable.** Already established independently by
  `tests/sairncare_fault_probe.py`'s three-layer peel. **Two structurally
  different methods reached the same conclusion about the same gate**, which is
  the independence requirement from
  `docs/2026-09-13-cross-domain-disciplines.md` satisfied by accident rather
  than by design — and is the strongest evidence in this document.

**The other 15 are not classified here**, and guessing would be worse than
leaving them open. They are printed by the tool, by role-table name, and the
question to ask each is in §2.

---

## 4. The tool found three defects in itself, and that is the reportable part

Every one produced a **clean-looking wrong answer** rather than an error. None
would have been visible without a control that asserted a known result.

1. **String-replace instead of a line index.** The first version did
   `src.replace(anchor, ..., 1)`. `if (!CRM_MANAGEMENT_ROLES[session.role]) {`
   appears at **four** sites, so four real gates became four non-answers — and
   had the count not been checked, `replace(..., 1)` would have silently damaged
   the *first* site four times while claiming to test four different ones. Now
   indexed by line, which cannot be ambiguous.

2. **Copying the subject without its dependencies.** A run overlapping
   uncommitted work put a `sd-data.js` that `require`s a NEW lib into a worktree
   that did not have that lib. **48 of 93 suites went red on the baseline**, so
   nearly every gate came back SILENT — a report that reads as a platform-wide
   coverage catastrophe when the real cause was a broken worktree. The tool named
   all 48, which is how it was caught. It now copies every modified tracked file,
   and **refuses outright** when more than a third of suites are red on the
   baseline: a collapsed observer set is a finding, not a smaller run.

3. **`\s*` where `[ \t]*` was meant.** `\s` includes the newline, so with `re.M`
   the `^` could match at a BLANK line and `(\s*)` would eat that newline plus
   the next line's indentation — producing an anchor spanning two lines that can
   never equal any single line. It hit **exactly one gate in 38**: the one
   preceded by a blank line. It was reported as COULD-NOT-RUN rather than
   skipped, which is the only reason anybody saw it.

### 4.1 And the staleness guard fired on its own report

A full sweep takes tens of minutes. The **first** real run was overlapped by an
unrelated edit to `api/sd-data.js`, and every line number in its report was
silently off by one by the time it was read — internally consistent, externally
wrong, with nothing saying so. That is the eighth cross-domain discipline
exactly: *nothing announces the day a check stops describing its subject.*

The tool now prints the subject's sha256 at the top and **re-reads the working
tree at the end**. On the final sweep it printed:

```
  !! api/sd-data.js CHANGED DURING THIS RUN.
     The verdicts are valid for sha256 b1cd55206c37; the LINE NUMBERS are
     not valid for the file on disk now. Use the role-table names,
     or re-run against a quiet tree.
```

The verdicts stand — they were measured against a real file. The line numbers do
not. **A stale report that says it is stale is a different object from a wrong
one**, and that is the whole value of the check.

---

## 5. A red suite found incidentally, and not fixed here

The baseline refuses to count an already-red suite as an observer — a suite that
cannot pass cannot report a mutation, and folding it into "did not notice" would
be a lie in the safe direction. That refusal surfaced
**`tests/stonedesk_server_backup.js`, red on a clean `origin/main` worktree**
(22 passed, 1 failed). Full detail in `docs/SAIRN-OPEN-WORK-INDEX.md`; it
belongs to item 97, which is CC's active claim, so it is recorded rather than
fixed.

---

## 6. What this does NOT claim

- **It is not a gate and must not become one.** A SILENT result is a question
  for a person. A number that exists gets driven to zero by the cheapest
  available route, which for a checker is switching it off.
- **It says nothing about the 15 unclassified SILENT gates.** Not "those are
  holes". Not "those are fine". The tool's whole design is that it cannot tell,
  and this document does not quietly resolve that.
- **It covers one file.** `api/sd-data.js` is where SAIRN's role gates live, but
  the app HTML files and the `api/_lib/*` engines have guards this never
  touched.
- **One gate SHAPE.** `if (!X_ROLES[session.role]) {` and nothing else. A gate
  written any other way is invisible to this, and the tool refuses rather than
  reporting zero if that shape ever stops matching.
