# The 464 JavaScript suites the label-shape checker could not read, ranked — and the one extractor that closed three quarters of it

**2026-09-29 (Cody).**

`tools/assertion_label_shape_check.py` reports a test arm whose **label claims a
universal** while its **comparison is one-sided** — `assert.ok(limits.length >= 4,
'the limits travel with every answer')`. Until today it went through Python's
`ast` and read **347 Python suite files**. The other **464 were JavaScript and
were not read at all**, and the header said so: a CAPABILITY gap, not a sampling
choice.

    CHECKED / UNIVERSE before:  343 of 807 suite files (43%)
    CHECKED / UNIVERSE after:   811 of 811 suite files (100%)

**The denominator moved because the repo moved too** — both figures come from
`git ls-files`, so they are not comparable as a pair without saying that. The
number that matters is the one that did not depend on the repo: **the covered
languages went from one of two to two of two.**

---

## 1. The ranking that decided the build

Measured over the JavaScript suite corpus (`tests/`, `*.test.js`), by assertion
idiom rather than by directory, because the question was *"what is the cheapest
extractor that reaches the most arms"* and directories do not answer it:

| idiom | calls | files |
|---|---|---|
| `assert.X(cond, LABEL)` | 12,365 | 347 |
| `ok(cond, LABEL)` | 4,720 | 351 |
| `check(LABEL, cond)` | 2,976 | 87 |
| `eq(a, b, LABEL)` | 238 | 14 |

**One shape dominates, and the other three are the same shape wearing a different
name:** a call with a condition expression in one argument and a string literal
label in another. So the extractor is not four extractors. It is one balanced-paren
scan over the call's argument list, plus a four-name callee vocabulary.

**Do not quote these figures — re-run them.** They move with every suite added.

## 2. What was built

**A balanced-paren scan over a stripped copy, feeding the SAME `classify()` and
`tier()` as the Python path.** That last part is the whole design:

- **Python** goes through `ast`.
- **JavaScript** goes through a balanced scan over a copy with comments stripped
  and **string interiors blanked** by the canonical, offset-preserving
  `checker_kit.strip_comments`, with regex bodies also blanked.
- **Both feed one classifier.** A finding means the same thing in either
  language, one set of locked fixtures bounds both, and there is no second
  definition of "a universal label" to drift from the first.

**A file whose two stripped copies differ in length is REFUSED** and listed under
COULD NOT RUN rather than counted clean. That is PR §1.11: a file it could not
read is not a file with nothing in it. An offset-preserving stripper that stops
preserving offsets would otherwise silently misattribute every arm in the file.

Criteria lock: **48 fixtures** — 25 shape, 9 tier, 14 JavaScript.

## 3. What is still not read, at 100% of files

The coverage line prints this and it is not zero:

1. **A file whose stripped copy changes length** — refused, named, counted under
   COULD NOT RUN.
2. **An assertion whose label is built from variables** — `assert.ok(cond, msg)`
   yields no arm at all, because there is no literal to classify. It is not a
   clean arm; it is an unjudged one, and the count of those is printed
   separately as NOT JUDGED.
3. **The value-comparison form** — `check(label, got, want)` and
   `assert.strictEqual(a, b, label)` with two non-string arguments. The callee
   compares them, so there is no shape at the call site. The Python path gives
   the same answer for the same reason, and both say NOT JUDGED rather than
   inventing one.
4. **A per-element predicate** — `.every()` carries the universality, not the
   comparison inside it. Exempt, matching the Python path's treatment of
   `all(...)`. **But a floor on the OUTER count is still a finding**, and that is
   a locked fixture, because blanking the callback must not blank the `>= 3`
   around it.

## 4. THE FIRST LIVE RUN FOUND A REAL BUG IN MY OWN SUITE

`api/_lib/sc-denial-reconcile.test.js`, arm E5:

```js
assert.ok(Array.isArray(o.limits) && o.limits.length >= 4,
  'the limits travel with every answer, including the empty one');
```

**The module publishes FIVE limits.** At a floor of four, one could be dropped —
including the limit stating that no probability is computed, which is the single
claim that app has explicitly refused to make elsewhere — and the arm stayed
green. Now compared **exactly**, against the module's own published count, so
adding a limit is a deliberate act that updates one number and dropping one goes
red.

That it was found in the author's own test on the extension's first real run is
the fairest available evidence that the extension was worth building, and it is
recorded here rather than quietly fixed.

## 5. The control moved too, and two of its arms were asserting a closed gap

`tests/run_assertion_label_shape_probe.py`, now **29 arms**:

- **C1** required a non-empty file list; it now requires one **in both
  languages**. A zero in either would have made that half of the verdict vacuous
  and the old arm could not see it.
- **C2** asserted *"the JavaScript suites are declared NOT COVERED"*. They are
  covered now, so **that arm was asserting a gap that had closed** — discipline 8
  staleness, inside the control itself. Rewritten to hold what it was actually
  protecting: the output must still name **what is still not read** even at a
  100% file denominator.
- **C2b** required `universe > checked`, which encoded the capability gap as a
  *requirement* and would have gone red the day the gap closed. Now `checked > 0
  and checked <= universe` — a collapsed `0 of 0` and a count exceeding its own
  universe are both still caught.
- **C5 / C5b / C5c** are the new known-bad JavaScript control, both directions: a
  planted mislabelled universal must be **reported by name**; the same label with
  an **exact** comparison must be **silent**, which is what stops C5 from being
  satisfied by a checker that flags every JS arm; and a **commented-out** arm must
  stay silent, which is what makes the comment-stripping half load-bearing rather
  than assumed.

## 6. And the tool's own clean line was understating its scope

It read:

    CLEAN -- no Python arm labels an exhaustive claim while comparing one-sidedly.

…while the JavaScript half was already running through the same classifier. A
clean verdict that names one of two languages is a label that does not match what
was checked — **the exact failure this tool exists to catch, in the tool's own
summary line.** Corrected to name both.
