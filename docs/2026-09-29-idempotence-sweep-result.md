# Idempotence sweep — the measured result

**2026-09-29 (Hank).** Item 11 of queue24. `tools/idempotence_double_run.py` run
over the whole corpus in a scratch copy of the tracked tree.

## Result

```
double-run CLEAN        : 59
double-run DIFFERENT    : 0
COULD NOT TELL          : 5  -- NOT a pass
EXIT = 2
```

**Exit 2, not 0**, because five tools could not be examined and a could-not-tell is
never folded into a pass.

## No committed mutating tool double-applies

**59 of 64 candidates changed nothing on their second run.** That is the answer to
the question item 11 asked, and it is a better answer than I expected.

**The tool that actually failed this property was MINE and was never a committed
tool.** The +25 citation repoint was an ad-hoc script in the session scratchpad. It
double-shifted ten citations on its first run and four more on its second, and it
is the reason this sweep exists — but it is not in `tools/` and would not have been
found by sweeping `tools/`. **Stated because the sweep's clean result could
otherwise read as "the problem did not exist":** the problem existed, in a script
nothing swept, which is its own finding about where mutations get written.

## The five that could not be examined

| Tool | Why |
|---|---|
| `comment_sensitivity_check.py` | timed out after 30s |
| `dead_rule_sweep.py` | timed out after 30s |
| `guard_ablation.py` | timed out after 30s |
| `metamorphic_check.py` | timed out after 30s |
| `run_all_tests.py` | timed out after 30s |

**All five are slow analysis tools, and 30s × 2 runs is not enough for any of
them.** The ceiling is deliberate: 64 candidates at the original 180s is over seven
hours in the worst case, and a sweep nobody can run is not a sweep — the same lesson
`--reseat-shas` learned when its first draft spawned ~7,000 subprocesses.

**These are NOT reported as clean and must not be read as safe.** `run_all_tests.py`
in particular runs the whole suite, so a double run of it is a double run of
everything. The honest position is that five tools are unexamined, and the way to
examine them is `--tool <path>` with a longer budget, one at a time.

## Eight tools excluded before the sweep, derived not listed

A tool that pushes, fetches over the network, or blocks on input cannot be
double-run in a scratch repo. Excluded by a source pattern
(`push`, `urllib`, `requests.`, `input(`, `getpass`, `webbrowser`, `sairn_http`,
`smtplib`) rather than by name, so a new one is covered without editing the sweep —
which is the pattern-enumeration lesson applied to this tool.

## Three argument-gated mutators, reported as NOT EXERCISED

| Tool | The mutating flag |
|---|---|
| `tier_a_review_gate.py` | `--backfill-shas --write` / `--reseat-shas --write` |
| `defect_register.py` | `--add` / `--reseat` |
| `hook_integrity_check.py` | `--regenerate` |

Their **default invocation cannot mutate**, so a clean double run says nothing about
the dangerous path. **`--reseat-shas --write` is the most important of the three**,
because it is the newest and it is a delta-applier — exactly the shape that
double-applies. Its own control covers the fixture case; the corpus sweep does not
reach it.

## The fixture gate runs before the corpus, every time

The sweep **refuses to report a corpus result if its own fixture arms do not pass.**
Known-bad: a tool that adds 25 every run — the citation repoint in miniature —
caught. Known-good: a tool that writes a computed constant — clean, so the
comparison is not simply reporting everything.

**That ordering is item 11's other half made structural rather than remembered.** A
corpus result from a comparison that cannot fire is the vacuous pass this repo names
most often, and it is what a "59 clean" line would look like if the comparison were
broken.
