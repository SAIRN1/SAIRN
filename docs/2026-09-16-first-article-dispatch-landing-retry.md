# First Article Inspection — `dispatch_state.py`, `landing_verification.py`, `retry_backoff_check.py`

**2026-09-16, Hank.** Three artefacts the FAI gate reported as first committed on
or after `required_from: 2026-09-16` with no inspection record. Two written by
other sessions, one written by me the same morning.

Records: `docs/first-article-inspections.json`. Gate: `python tools/first_article_check.py`.

---

## The pattern held for a third day running

Fourth's 2026-09-16 inspection of three tools found **the same two gaps on all
three**: a header stating REPORT ONLY that nothing checked, and an exit-2
contract with arms for exit 0 and 1 only.

These three carried it again, and the shape is worth stating plainly because it
is now six tools out of six:

| | REPORT ONLY checked? | exit contract checked? |
|---|---|---|
| `dispatch_state.py` | **no** | yes — both could-not-run directions |
| `landing_verification.py` | **no** | yes — all three, via `verdict()` |
| `retry_backoff_check.py` | **no** | **exit 2 only** |

**A header sentence is a requirement, and REPORT ONLY is the one nobody tests
because it is about what the tool does NOT do.** An arm for it has to be written
as an absence, and absences do not announce themselves when they stop being
true.

---

## What "REPORT ONLY" was taken to mean, and why it is not the exit code

On this platform a report-only check is *registered* with `by_exit` and is
**expected** to exit 1 on a finding. So the claim is not about exit codes at
all — it is that the tool never **mutates**. Every arm added here tests for
mutation, from two structurally different directions:

* **the SOURCE** — no writer is written down (AST, not grep);
* **a RUN** — `git status --porcelain` before and after, so nothing was created,
  modified or deleted anywhere in the repository.

The source arm is what fails the day somebody *adds* a writer. The run arm is
what fails if a writer already exists somewhere the source arm cannot see. One
without the other is half a check.

---

## Four defects the inspection found — three in my own arms, one in a tool

### 1. A regex source-check walked straight past the sabotage written to defeat it

The first version asked ``open\s*\([^)]*['"][rbt]*[wax]``. The sabotage was
`io.open(os.path.join(REPO, '.dispatch_cache'), 'w', encoding='utf-8')` — and
`[^)]*` stops at the inner `)` of `os.path.join(...)`, so the pattern never
reaches the `'w'`. **The arm reported clean against a tool that had just been
made to write a file.** Replaced with an AST walk.

### 2. …and then the AST version fired on four ordinary READS

Checking *every* string argument for a write character flagged four calls in
`tools/retry_backoff_check.py`, because `errors='replace'` contains an `a`.
Narrowed to the **mode argument only** — positional index 1 or the `mode=`
keyword. An arm that cries wolf on any file that reads carefully gets deleted,
which is a slower way of having no arm at all.

Both corrections came from **running the thing on a second file**, not from
re-reading it.

### 3. The "nothing changed" arm took its baseline too late

It hashed the index and the claim files — *the two things the tool reads* — and
took its `before` snapshot inside the new section, by which point the earlier
sections had already run the tool four times. A sabotage that created a **new
file elsewhere** was present in both snapshots and the arm passed.

Now: `git status --porcelain` over the **whole** working tree, captured at module
import **before the suite runs the subject even once**.

### 4. `landing_verification.run()` bound `cwd=REPO` as a default argument

Found while writing the arm the inspection said was missing for
`baseline_tip()`. A Python default argument is evaluated **once, at `def`
time** — so a control that repointed `lv.REPO` at a fixture repository went on
running `git` in the real clone, and its assertions were about the wrong
repository. Late-bound to `cwd or REPO`.

This is the vacuous-control shape, sitting in the seam a control needs.

---

## And one real defect in a tool, not in an arm

**`retry_backoff_check.py --json` carried its own exit rule and disagreed with
the text path on the same input, in two ways.**

```
    return EXIT_FINDING if (bare or unclear) else EXIT_CLEAN     # --json
    return finish(findings, cnr, ...)                            # text
```

* **UNCLEAR.** The text path routes it through `could_not_run`, so it exits **2**.
  The json path called it a **FINDING** and exited 1. *Could not tell* and *found
  something* are the two states this repo most insists on keeping apart, and
  which one a caller got depended on an output flag.
* **The breaker, and this is the sharper half.** The text path adds *"the only
  breaker on the platform cannot fire"* to its findings when
  `breaker_importers()` is empty — the tool's own headline result. **The json
  path never looked at `importers` at all**, so against today's real repo
  `--json` exits **0** while the text run does not. Anything wired to the
  machine-readable mode would have read the platform as clean.

Fixed: the verdict is computed once and both renderings return it. Pinned by
`7 ...and --json returns the SAME code on the same input` and
`7 A PLATFORM WITH NO BREAKER IMPORTER IS A FINDING IN BOTH MODES`.

---

## A fifth defect, in the gate that sent me here

`first_article_check.arm_labels()` recognised exactly `check(` and `ck(`.
Measured across `tests/*.py` on 2026-09-16: **2,342 labelled calls visible, 617
`ok(` and 103 `arm(` calls not.** The worksheet for
`tools/dispatch_state.py` printed **ARMS (0)** for a suite with **38 passing
arms** — an inspector handed an empty right-hand column concludes the tool is
unverified.

**That is this tool's own recorded defect happening a second time.** Its
open-work row says *"the tool that found it read a real 24-arm suite as ZERO
first"*.

Appending `'ok'` to the tuple would have fixed today and rotted on the next
helper name, so the question asked is now **structural**: a function defined in
the suite, taking a label as its first parameter, whose body asserts, raises,
prints something containing `FAIL`, or increments a failure counter. That is
what an assertion helper *is*, whatever it is called.

**Recognition is a UNION with the old names**, deliberately — the predicate
misses `check` in the handful of suites that import it rather than define it, so
`check`/`ck` stay recognised unconditionally and the change can only *widen*
what is visible. **And the error direction is chosen rather than accepted:** this
feeds a worksheet a human reads, where an extra non-assertion label costs a
moment and a 38-arm suite reported as empty costs an inspection.

### And a sixth, smaller one, found by the gate refusing my own record

A `by` field that *paraphrases* an arm is refused — the gate requires an exact
quoted substring of a real label. Six of mine were paraphrases. But
`tests/run_dispatch_state_probe.py` built nine of its labels with `%s`
(`'...and no %s' % writer`), which reaches the AST as the literal `'...and no
%s'` — **so those nine arms cannot be named by any label-based tool, including
the worksheet.** A label that cannot be cited cannot be cited in an inspection
record. Spelled out.

---

## Dispositions

All three records are **complete**: every claim carries a disposition and none
is `unverified`. Two claims are `cannot-test` and say why in the record rather
than here.

**`landing_verification.py` is a SELF-INSPECTION and that is a real weakness
rather than a formality.** I wrote the tool earlier the same day, so the
claim-to-arm mapping is the author reading his own header — exactly the blind
spot the independent-review rule exists for. It is recorded because the gate
named the artefact and leaving it uninspected is worse, and it should be re-read
by another session.

## What this does not close

* **`tools/dispatch_state.py` carries a dormant `import subprocess`** that
  nothing uses — Guardian check 0d, one line, another session's tool. Reported
  rather than folded into this work. The report-only arms assert no subprocess
  *call*, which is the behaviour that matters, so the dormant import cannot hide
  a real invocation.
* **The claim-to-arm mapping is human and is not checked.** The gate verifies a
  mapping exists, disposes of every claim, and still describes the bytes on
  disk. Whether the arm somebody named actually tests the claim they named it
  for is a judgement, and automating it scored 38% with five false positives out
  of five.
* **170 artefacts pre-date the requirement date and are uninspected.** Visible
  debt, printed on every run, not an amnesty.
