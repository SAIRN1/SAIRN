# testint — does your test suite actually check anything?

Most tooling asks *does the code work.* This asks the question underneath it:

> **Does the thing that tells you the code works actually check anything?**

A green suite is evidence. `testint` is about the cases where it is evidence for
the wrong conclusion — where the bar is green because a check stopped checking,
not because the code is right. That failure is invisible by construction: a
check that has stopped checking produces no output to contradict you.

---

## The three shapes it finds

**1. An assertion that matches a COMMENT, not the code.**
A test greps a source file for `'Prompt injection: Active'` to prove a hardcoded
claim was removed. The fix's own header *quotes the dead literal* to record what
it was — so the test fails a correct file. That direction is loud and
self-correcting. **The other direction is silent:** an assertion of *presence* —
*"the guard is still there"* — goes green when the only surviving mention is a
comment describing the feature that was deleted.

**2. A mutation control whose anchor no longer matches.**
A control reintroduces a defect, asserts the suite goes red, and restores the
file. Its anchor is an exact string. Refactor the target and the anchor matches
nothing — the control now mutates nothing, asserts nothing, and passes. One real
control sat that way for a day while its own harness said `ANCHOR-0`; two more
could not be swept at all because they refuse to be imported.

**3. A checker that answers differently on identical input.**
One checker sorted a *set* of strings with `key=len`. `sorted` is stable, so
equal-length strings kept whatever order the set iterated them in — and set
iteration order for strings depends on the interpreter's hash seed. Across six
seeds it produced **six different reports** on the same file, with the pair
numbering shifted so `pair 5` was a different finding each time. Nobody noticed
for weeks, because noticing requires comparing two runs, and nothing compares
two runs unless it sets out to.

---

## Does it apply to YOUR codebase? Measured, per check

The three checks have **materially different reach**, and saying otherwise would
be an overclaim the measurement does not support. Run against two codebases
nobody here wrote — CPython's standard library (1,131 test files) and
third-party npm packages — this is what came back:

| Check | Applies when | Reach |
|---|---|---|
| **`check_determinism`** | you run checkers, linters or generators whose output something reads | **broadest.** No assumptions about test style at all, and it ships a `--self-test` that proves the method can see the defect |
| **`check_mutation_anchor`** | you write mutation controls | **a discipline you have or you do not.** Where controls exist this is immediately useful; where they do not it has nothing to read, and says so |
| **`check_comment_quote`** | **your tests read your source as text** | **narrowest, and honestly so** |

**The honest pitch for `check_comment_quote` is: *if your tests read your source
as text, this finds the assertions that have stopped checking.*** Not *"works on
any test suite"*.

The number behind that. Share of test files that read a file as text:

| Corpus | share |
|---|---:|
| the codebase this came from, JavaScript | **67.3%** (167 of 248) |
| the codebase this came from, Python | **53.0%** (35 of 66) |
| CPython standard library | **17.3%** (196 of 1,131) |

And the CPython reads are of *fixture data*, not of source — so on that corpus
the check reports **COULD NOT RUN**, which is the correct answer and not a clean
one. See `validation/README.md`, including the two false cleans this check
committed on first contact with foreign code before that was fixed.

## Why this suite and not another linter

Every one of the three above was found in a codebase that already had: a full
test suite, thirty automated checkers running after every push, and a blocking
pre-push gate. **None of them caught these, because all of them were downstream
of the thing that was broken.**

The suite is small on purpose. It does one thing that nothing else does.

---

## Install and run

No dependencies beyond Python 3.8+.

```
python -m testint.run --config testint.config.json          # all three
python -m testint.run --config testint.config.json --only comment_quote
python -m testint.run --self-test                           # prove it can see

python -m testint.check_comment_quote   --config testint.config.json
python -m testint.check_mutation_anchor --config testint.config.json
python -m testint.check_determinism     --config testint.config.json
```

**The runner exists because three scripts in a directory is not a mechanism.**
In the codebase this package came from, an inventory found **43 of 99 tools
invoked by nothing at all** — every one written for a real incident, committed,
and never pointed at the codebase again. A tool that exists is not a mechanism;
a tool that runs is.

It deliberately does **not** aggregate findings into a score. A count across
three different questions is a number nobody can act on, and the moment a number
exists somebody drives it to zero by the cheapest route — which for a checker is
switching it off.

| exit | meaning |
|---:|---|
| `0` | ran, found nothing |
| `1` | found something |
| `2` | **could not read** part of its subject |
| `3` | **could not run** at all |

**2 and 3 are never folded into 0.** "We could not check it" and "it is fine"
are the two answers this suite exists to keep apart, and a runner that collapses
them undoes every check underneath it.

---

## Configuration

One file. Everything this suite needs to know about your repo:

```json
{
  "tests":    ["tests/**/*.py", "tests/**/*.js", "**/*_test.go"],
  "checkers": ["tools/**/*.py"],
  "sources":  ["src/**/*.js", "src/**/*.py"],
  "expected_comment_assertions": "testint.allow.json"
}
```

`expected_comment_assertions` is the deliberate-exceptions list — an assertion
that really is *about* a comment (asserting a historical record survives,
locating a block by its heading). **Every entry carries a reason.** An exclusion
with a reason beside it is a decision; an exclusion without one is a silence,
and a suite full of silences is the thing being sold against.

---

## Language support, and what it cannot model

`testint` has to tell prose from code before it can check anything, so it ships
**one** comment/string scanner driven by a per-language profile
(`testint/languages.py`). Adding a language is a table entry, not a code path.

| Profile | Extensions |
|---|---|
| `javascript` | `.js .mjs .cjs .jsx .ts .tsx` — and `.html/.htm`, which also strips `<!-- -->` |
| `python` | `.py .pyi` |
| `c_family` | `.c .h .cpp .hpp .cc .java .cs .go .swift .kt .scala .php` |
| `rust` | `.rs` (block comments **nest**, unlike C) |
| `ruby` | `.rb` |
| `sql` | `.sql` (doubled `''`, nesting block comments) |
| `html` | `.html .htm .vue .svelte` |
| `shell` | `.sh .bash .zsh` |

**An unknown extension raises rather than guessing.** A guessed profile is how a
scanner ends up reading a fraction of a file and reporting clean.

**Known limits are printed, not hidden.** `comments.caveats_for(path)` returns
what the profile cannot model for that language — heredocs, Rust's `r#"..."#`,
Ruby's `%w[]`, JSX text — and a clean result on such a file should be reported
with its caveat rather than as a bare zero.

---

## Why the scanner is a character machine and not a regex

This is the part worth the price on its own.

```html
<input type="file" accept="image/*" capture="environment">
```

The `/*` in that MIME wildcard opens a block comment. A naive `/\*.*?\*/` runs
forward to the first `*/` — which, in the file this came from, lived inside a
regex literal in a later script — and blanked **80.5% of the file**. Three
separate tools in one codebase carried that regex. Measured against real files:

```
one real 500 KB app file, 362 function declarations
  careful implementation      94.6% survives      0 declarations lost
  naive regex implementation  11.1% survives    350 declarations lost
```

All three reported **clean**.

`testint.comments.survival()` returns that number for any file, so you can find
out *before* trusting a clean result rather than after.

---

## How this suite is verified

**`tests/test_checks.py` — 24 arms, one per check, in both directions.** Each
builds a complete throwaway project in a temp directory, plants the defect, and
asserts the check reports it — then plants the clean version and asserts it stays
quiet. **Both halves are required:** a check that always reports passes the first
alone, a check that never reports passes the second alone. Only the pair says
anything. The fixtures double as the clearest documentation of what each check
catches, because each is the smallest project in which the defect is real.

One of those arms asserts something no other test can: `check_mutation_anchor`
**parses** controls and never imports them. The fixture is a control that writes
a file at import time; the arm passes only if that file never appears.

`tests/test_comments.py` — 29 arms, and they come in two kinds, both of which
matter: *a comment really is removed*, and **_code really is not removed_**. The
second kind catches the expensive failure and is the kind a smoke test skips.

The scanner is additionally checked **against a battle-tested single-language
implementation on 23 real production files** — a differential test rather than a
self-assessment. It is byte-identical on all 23.

That test found a real defect in this package before release, which is recorded
in the code rather than quietly fixed: `<` had been included as a
regex-context character, on the correct reasoning that `a < /re/.source` is
legal JavaScript. In HTML-embedded script `</div>` puts a `/` straight after a
`<`; the scan then ran forward for a closing `/`, found it inside the *next HTML
comment*, and 267 characters of comment survived as code. Reading the code would
not have found it. Measuring against a real file did.

---

## Licence

**Proprietary. Copyright (c) 2026 SAIRN Tech LLC. All rights reserved.**
See `LICENSE`. No licence is granted by possession; use requires a separate
written agreement.

Recorded because the choice is one-way: a proprietary work can later be released
under an open licence, and source once released under an open licence cannot be
recalled from anyone who already holds a copy. Starting here keeps both options
open.
