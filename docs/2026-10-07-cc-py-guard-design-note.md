# Design note — `tools/py_guard_check.py`

**Item 9, batch 14, 2026-10-07 (cc). Committed BEFORE the tool, which is the
instruction and also the point: a design note written after the code is a
description, not a design.**

**This tool is a ONE-TIME EXCEPTION to the standing no-new-builder-tools rule,
granted by Michael.** I build it; every other agent reaches it only through the
existing push gate, report-only.

---

## 1. Goals

One thing, and it is narrow: **find, by static analysis, the four code shapes on
this platform that make a program report a verdict it did not earn.** Not
style, not coverage, not security — the specific family that has produced the
most expensive defects here, where something fails or is skipped and the output
is indistinguishable from a real pass.

Each of the four is a shape that has already been paid for in this repo:

| rule | the shape | what it has cost here |
|---|---|---|
| `ignored-exit` | a `subprocess`/`os` call whose result is thrown away | a tool "ran the suite" and reported clean while the suite exited non-zero |
| `swallowed-exception` | `except:` bare, or a handler whose body is only `pass` | the five-times-fixed fail-open of PR §1.11 — "could not run" folded into "passed" |
| `vacuous-assert` | an assertion that cannot fail | `tools/sabotage_control_check.py` measured 6 of 50 controls as guard-less; an arm that cannot fail is the same thing one level down |
| `exit-code-from-string` | a numeric exit status compared against a string, or `sys.exit("text")` | the `exit_status_attributable` hook exists because a pipeline's status was read as the tool's |

**Success criterion, stated before the first run:** every flag it raises on
`tools/*.py` is either a real instance of its shape or a **named** false
positive. A flag I cannot classify is a defect in the tool, not a finding.

## 2. Non-goals — stated so they are not discovered as gaps

* **NOT a linter.** No naming, no formatting, no complexity, no imports.
* **NOT a security scanner.** `owasp-security` and `sairn-code-scrubber` own that.
* **NOT blocking.** It ships **report-only** through
  `report_only_checks.REGISTRY`. Promotion is a later decision by whoever owns
  the gate's policy, not a thing I do in the same batch that writes the tool.
* **NOT a fixer.** It proposes nothing and edits nothing. Cross-domain
  disciplines item 11: a detector that applies its own repair is item 8 one step
  later.
* **NOT semantic.** It reads syntax. It cannot tell whether an ignored exit code
  is checked three lines later through a different variable, and it says so on
  every run.
* **It will not add a rule it cannot detect mechanically.** Three other shapes
  were considered and REJECTED for exactly that reason — see §5.

## 3. Two alternatives, and why not

**Alternative A — extend an existing checker.** `tools/fail_open_check.py`,
`tools/truthy_sum_check.py` and `tools/bare_run_write_check.py` each own one
shape already, and adding three more rules to one of them would have needed no
exception to the no-new-tools rule.

*Rejected,* for two reasons. Those three are **string/regex** tools, and three
of my four rules are not expressible as a regex without the false-positive rate
that PR §1.2 is about — `except: pass` inside a string literal or a docstring is
text about code, and a regex cannot tell. And folding four rules into a tool
named for one makes its own clean line mean something different without its
docstring changing, which is cross-domain disciplines item 8.

**Alternative B — a runtime harness: execute each tool under a wrapper and
observe what it swallows.** Strictly more powerful: it would catch the ignored
exit code checked through a different variable, which static analysis cannot.

*Rejected on blast radius.* 79 of the 164 ownerless `tools/*.py` have a detected
write site and 85 more could not be proved read-only by any static read. A
harness that runs them runs those writes. The exact mistake was made in this
same batch: an `exec`-based probe that disabled a generator's `--check` to see
what it would write **overwrote a legal-deadline seed**. A checker that must
execute its subjects to report on them is a checker that cannot be run safely on
this tree.

**So: static, AST, and it never executes what it reads.** That is a property of
the implementation, not a promise — `ast.parse` builds a tree and evaluates
nothing, there is no `exec`, no `eval`, no `compile(..., 'exec')`, no
`importlib`, and no `subprocess` invocation of a subject. An arm asserts the
tool's own source contains none of those names.

## 4. The four rules, with their exact mechanical criteria

Locked here, before the tool runs on anything real — cross-domain disciplines
item 1.

### R1 `ignored-exit`
An `ast.Expr` statement (a bare expression, result discarded) whose value is a
`Call` to `subprocess.run`, `subprocess.call`, `subprocess.check_call`,
`subprocess.Popen`, `os.system`, or `os.popen`.
**Why a bare statement and nothing cleverer:** a result assigned to a name and
then not read requires flow analysis, and a wrong answer there is worse than no
answer. A bare statement is certain.
**Known miss, stated now:** `rc = subprocess.run(...)` with `rc` never read.

### R2 `swallowed-exception`
An `ast.ExceptHandler` that is either (a) bare — `handler.type is None` — or
(b) has a body consisting only of `Pass`, or only `Expr(Constant(Ellipsis))`,
or only a docstring.
**Deliberately NOT flagged:** a handler whose body logs, re-raises, returns a
sentinel, or sets a flag. Those are decisions; `pass` is a silence.

### R3 `vacuous-assert`
An `ast.Assert` whose test is any of: a `Constant` that is truthy; a non-empty
`Tuple`, `List`, `Dict` or `Set` literal (always truthy — and the tuple case is
the classic `assert (x, "msg")`); or a `Compare` whose left and single
comparator unparse to the **same source text** (`x == x`).
**Why unparse and not an AST walk:** `ast.unparse` normalises formatting, so
`a.b` and `a .b` compare equal, and it cannot be fooled by whitespace.

### R4 `exit-code-from-string`
Either (a) `sys.exit(x)` / `exit(x)` / `SystemExit(x)` where `x` is a string
`Constant`, a `JoinedStr` (f-string), or a `Call` to `str`/`format` — Python
prints it and exits **1**, so the code is not the one named; or (b) a `Compare`
between a `Name`/`Attribute` whose final identifier matches
`^(rc|ret|retcode|returncode|exit|exitcode|exit_code|status)$` and a string
`Constant` — a numeric status compared to a string can never be equal.

**Each rule carries, in the tool, a one-line statement of what it CANNOT see.**

## 5. Three shapes considered and REJECTED as not mechanically detectable

Named so nobody re-proposes them as oversights.

1. **"an assertion that still exists and no longer tests anything."** The count
   holds, the sense is inverted, and no syntactic test distinguishes it from a
   correct assertion. This is the gap `tools/scrutiny_flag.py` already states it
   cannot close.
2. **"a fixture quietly made easier."** Requires knowing what the fixture is
   for.
3. **"a verdict read from the wrong column."** Needs the data's meaning. It was
   a real defect here (a testability gate reading the wrong column) and it is
   not findable by syntax.

## 6. Security plan

* **It never executes its subjects.** §3. An arm asserts the tool's own source
  contains no `exec`, `eval`, `compile`, `importlib`, `__import__`,
  `subprocess` or `os.system`.
* **It writes nothing.** No output file, no cache, no report path. `git status
  --porcelain` before and after every run is part the evidence.
* **It reads only tracked `.py` files under paths given on the command line**,
  defaulting to `tools/`. No globbing outside the repo, no network, no
  environment secrets.
* **A file it cannot parse is a third state.** `COULD NOT PARSE` is reported and
  counted separately, never folded into clean and never into a finding. PR
  §1.11.
* **An unrecognised flag exits 2 and does nothing** — this batch's own Rule B.

## 7. Test plan

* **A planted-bad and a clean example per rule**, hand-written, in
  `tests/run_py_guard_probe.py`. The bad one must be flagged and the clean one
  must not; both directions, because a rule that flags everything passes a
  one-direction test.
* **An ablation per rule**: the rule is disabled by name and the probe asserts
  its planted-bad example then goes **unflagged**. Per ARM, not per exit code —
  cross-domain disciplines item 12.
* **Three identical runs**, with the first run's result recorded, and `cmp` on
  the captured output.
* **A self-scan**: the tool is run against its own source and against the
  probe's, and every flag on either is explained or fixed.
* **The full `tools/*.py` population**, X of Y stated, **every flag
  hand-verified** against the source line, and **every false positive named** in
  the commit message. An unclassified flag blocks the item rather than being
  reported as a finding.

## 8. What this tool will NOT be allowed to claim

A clean run means: *these four syntactic shapes were not found in the files it
parsed.* It does **not** mean the code fails loudly, that exit codes are
checked, or that the assertions test anything. Those are the questions the
rejected shapes in §5 ask, and this tool cannot answer them.
