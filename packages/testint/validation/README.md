# Validation against codebases nobody here wrote

**Run 2026-09-12.** The package plan committed to this rather than to a claim:
*"run each ported suite against real outside codebases and publish the measured
false-positive rate per checker rather than a claim that it works."* This is
that, including the parts that are not flattering.

Reproduce with the configs beside this file.

---

## The corpora

| Corpus | What it is | Size |
|---|---|---|
| **CPython standard library** | `C:/Python314/Lib` — written by hundreds of people over thirty years, with no knowledge of any convention here | 2,246 `.py` files, **1,131 of them tests** |
| **third-party npm packages** | `node_modules` — real published JavaScript | **66 test files** across 23 packages that ship a `test/` directory |
| **the home repo** | the codebase these checks were extracted from | 314 test files |

---

## Result, stated before the detail

| Check | home repo | CPython | npm |
|---|---|---|---|
| `check_comment_quote` | 384 inspected, 223 resolved, **7 findings, 0 false positives** | **COULD NOT RUN** | **COULD NOT RUN** |
| `check_mutation_anchor` | 70 anchors, 0 bad | n/a — no declaring controls | n/a |
| `check_determinism` | 6 runs, 0 varies | n/a — applies to checkers, not to a library | n/a |

**`check_comment_quote` could not classify a single assertion on either outside
corpus.** That is the headline and it is not a bug — but it took two real
defects to arrive at it honestly.

---

## The two false cleans this check committed on first contact with foreign code

Both would have shipped. Both were invisible on the repo the check was written
for, because there it works.

**1. It inspected 0 assertions across 1,131 real test files and printed
`No undeclared comment-only assertion`, exit 0.** The Python binding pattern
expected the one-line `x = open(p).read()`. Measured across 400 CPython test
files, that form appears **zero times** and `with open(...) as f:` appears
**750**. The dominant idiom in the language was simply not matched.

**2. Fixed, it then inspected 21 and SKIPPED all 21 — and printed a clean line
again.** `inspected` counts *attempts*; only `inspected - skipped` counts
*answers*. A guard on the wrong one of those two is no guard.

It now exits **3, COULD NOT RUN**, and says so in those words. A check that
classified nothing has not passed — which is the rule this whole suite is sold
on, broken twice by the suite itself and caught only by pointing it at code
nobody here wrote.

---

## Why it cannot run there, measured rather than assumed

`check_comment_quote`'s premise is **source-inspection testing**: a test reads a
source file as text and searches it for a literal. How common that is:

| Corpus | test files reading a file as text |
|---|---:|
| this repo, JavaScript | **67.3%** (167 of 248) |
| this repo, Python | **53.0%** (35 of 66) |
| CPython stdlib | **17.3%** (196 of 1,131) |
| third-party npm | too few test files found to report |

And the CPython reads are of **fixture data**, not of source — which is why all
21 resolvable-looking targets resolved to nothing against a `**/*.py` source
glob. The check is not broken there. It has nothing to say there.

---

## What this means for the product, stated plainly

**The three checks in this suite have materially different reach, and selling
them as one thing would be a claim the measurement does not support.**

- **`check_determinism`** — applies to any codebase that runs checkers,
  linters or generators whose output is read by a machine. No assumptions about
  test style at all. **The broadest of the three, and it ships with a
  `--self-test` that proves the method can see the defect.**
- **`check_mutation_anchor`** — applies wherever mutation controls exist. That
  is a discipline a team either has or does not; where it exists this is
  immediately useful, where it does not the check has nothing to read and says
  so.
- **`check_comment_quote`** — applies where a codebase does **source-inspection
  testing**. Common here, three to four times rarer in CPython, and the honest
  description is *"if your tests read your source as text, this finds the
  assertions that have stopped checking"* — not *"this works on any test
  suite"*.

**The mitigation the plan named is doing its job.** The value of running against
outside code was never the false-positive rate; it was finding the two silent
false cleans above, neither of which any amount of reading would have surfaced.
