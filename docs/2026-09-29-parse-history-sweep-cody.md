# Did every file parse at the commit that touched it? 3 of 4,784, and all three would be caught

**2026-09-29 (Cody).** Three shell-quoting defects of one class in two days —
a literal backspace where `\b` was meant, an apostrophe that broke a Python file
I then pushed, and command substitution that ate half a review instruction. The
**parse** half of that class is measurable over the whole history, so it was
measured rather than estimated.

## Method

Every commit touching a `.py` or `.js` file under `tools/`, `tests/` or `api/`;
every such file read **as it stood at that commit** and parsed. Python through
`ast.parse` in process; JavaScript through `node --check`, one process per file,
which is the same scope a staged-file check would have.

    commits touching a .py/.js under tools|tests|api : 1,674
    file-at-commit pairs checked                     : 4,784   (3 skipped, no blob)

    PAIRS THAT DID NOT PARSE                         : 3
    COMMITS CARRYING AT LEAST ONE                    : 3 of 1,674   (0.18%)
    FIXED BY THE NEXT COMMIT TOUCHING THAT FILE      : 3 of 3

## The three

| commit | date | file | failure |
|---|---|---|---|
| `c915cc8c4c87` | 2026-09-29 | `tools/tooling_inventory.py` | unterminated string literal, line 1335 |
| `a40065e91cf9` | 2026-09-15 | `api/_lib/dnt-rollup.js` | `<<<<<<< HEAD` — conflict markers committed, line 238 |
| `f7429d6e9740` | 2026-09-13 | `tools/flaky_checker_quarantine.py` | unterminated string literal, line 99 |

## TWO recurring cause shapes, not one

**(i) UNTERMINATED STRING LITERAL — 2 of 3.** Both are quoting damage from
writing Python through a shell heredoc: a quote character inside the content
closes the literal. `c915cc8c` is mine, sixteen days after `f7429d6e`, which is
the same shape in the same directory. **Nothing between the two noticed the
pattern**, because each was fixed in the next commit and left no standing
record.

**(ii) COMMITTED CONFLICT MARKERS — 1 of 3.** `<<<<<<< HEAD` reached
`api/_lib/dnt-rollup.js`, a shipped API library, inside a commit whose own
subject is about closing review findings. This one *is* now guarded:
`tools/conflict_marker_check.py` runs in the push gate, and
`tools/conflict_marker_preflight.py` exists as well. The guard postdates the
incident, which is the normal direction.

**So the class that remains unguarded is (i), and it is the one that recurred.**

## Would the item-6 check have caught each? 3 of 3 — YES

The check as specified — `python -m py_compile` for `.py`, `node --check` for
`.js`, over staged files under `tools/`, `tests/` and `api/`:

| commit | in scope? | detected? |
|---|---|---|
| `c915cc8c` | `.py` under `tools/` | **yes** — `py_compile` fails on an unterminated literal |
| `a40065e9` | `.js` under `api/` | **yes** — `node --check` fails on `<<<<<<<` |
| `f7429d6e` | `.py` under `tools/` | **yes** — same as the first |

**Not built.** Claiming `tools/sairn_push_gate_hook.py` was refused:

> `DO NOT start this. Flag it back to the coordinating chat session and let it
> decide who runs it.`
> `REFUSAL RECORD: cc held 'platform' on overlapping work (registry, not yet on
> origin)`

So this document is the evidence for it rather than the thing itself. **The base
rate is low and the cost of the check is one subprocess per staged file** — and
the argument for it is not the rate, it is that the failure is *invisible in the
diff*. All three of these look completely normal in `git show`.

## What this does NOT measure, and it is the larger half

**Parsing is the floor, not the bar.** The literal backspace that started this
sweep **parsed perfectly** — `re.compile(r'fixture invalid\x08|...')` is valid
Python that compiles, imports and runs. It matched nothing, for ever, and every
green light stayed green. A parse check would not have caught it, and neither
would the item-6 check.

That half is covered by a different tool, built this session:
`tools/dead_rule_sweep.py`, which neutralises each compiled rule in turn and
asks whether anything notices. **The two checks are complementary and neither
subsumes the other**: one catches damage that stops the file working, the other
catches damage that stops a rule working while the file looks fine.

The third defect of the three — command substitution inside a review record —
is caught by **neither**. It went into a JSON field, not a source file, and the
record parsed. Nothing in this repo checks that a prose instruction says what
its author typed.

**Re-run rather than quoting these figures.** The script is in this session's
scratchpad; the method is four lines of `git log --name-only` plus a parse per
blob.
