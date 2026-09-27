# The empty walk: a read that succeeds, returns nothing, and is believed

**2026-09-27, CC.** Methodology sweep for the class `tools/push_retry.py`
caught in itself. Two more live instances found and fixed; two candidates
checked and cleared; the sweep's own reach is stated at the bottom and is
narrow.

---

## 1. The shape, from the one that was caught

`push_retry.py` needs the set of commits that exist locally and on no remote —
the "safe set" its amend guard checks HEAD against. The first version asked:

```
git log --format=%s --not --remotes
```

That command **has no positive rev**. `--not --remotes` says *exclude
everything on a remote*; nothing says what to walk **from**. Git therefore
walks nothing, **exits 0**, and prints nothing.

So the safe set came back empty. An empty safe set means "nothing at HEAD is
yours", so the guard **refused every amend, forever**. Fixed by naming the
positive rev: `git log HEAD --format=%s --not --remotes`.

**Two things make this worth a sweep rather than a one-line fix.**

**It failed in the SAFE direction, so nothing complained.** A guard that
refuses everything looks like caution. It is a broken tool, and the difference
is invisible from outside.

**The fixtures could not have caught it, by construction.** `push_retry.py`
splits into an *accessor* (reads real git state) and a *decider* (a pure
function of that state). Every fixture arm handed the decider a synthetic
state. They proved the decision model and said nothing about the code that
feeds it — and because the fixtures were *refusals*, a tool that always refuses
satisfied all of them. **A suite built out of refusals passes on a guard that
refuses everything.**

The general statement:

> **A read that exits 0 and returns nothing is a THIRD STATE.** It is not the
> same as "there is nothing there", and a return code is only half the
> question. This is PR §1.11 applied to the shape of the DATA rather than to
> the presence of a dependency.

---

## 2. How the sweep was run

Two passes, because the shape has two halves and each pass is blind to the
other.

**Pass A — the literal command.** Every `git log` / `git rev-list` invocation
in `tools/`, `tests/`, `.claude/` and `api/`. **The literal `--not --remotes`
with no positive rev appears exactly once on the platform**, in
`push_retry.py`, and is fixed. Every other rev-walk carries an explicit
positive rev — `HEAD`, a range, `--all`, `-1`, or `--since`.

**One was worth reading closely and is CORRECT:**
`tools/deploy_verify_notify.py:90` runs
`git log origin/main@{1}..origin/main --name-only` to decide whether a push
could have touched `stonedesk.html` and skip the verification if not. An empty
result there would skip a real check — and the code guards it:
`if changed.strip() and "stonedesk.html" not in changed: sys.exit(0)`. An empty
read falls through and **verifies anyway**. It fails OPEN, deliberately, and
says so in a comment.

**Pass B — the architecture.** Pass A only finds the command. The defect is the
*shape*: an accessor whose empty result a caller reads as a fact, protected by
a selftest that never runs the accessor. A one-off `ast` pass over every
`tools/*.py` found functions that reach `subprocess`, functions whose name
marks them a selftest, and the call graph between them — then reported
accessors the selftest can never reach.

Eleven tools have both an internal selftest and at least one real-state reader.
Three were already reaching every accessor. Three more are covered by an
external `tests/run_*_probe.py` that runs them end to end as a subprocess,
which exercises the accessors from outside. **Four had a genuine gap**, and
each was then **driven** with its accessor forced empty, because a gap in the
call graph is a question and only running it is an answer.

---

## 3. What was found

### `tools/ai_action_approval_audit.py` — FIXED

`app_files()` ran `git ls-files '*.html'`, checked the return code, and
returned the filtered list. **The return code was only half the failure mode:**
`ls-files` exits 0 and prints nothing whenever it matches nothing, and the
function then filters that empty list by path prefix.

Driven with `app_files()` forced to `[]`:

```
AI call sites found : 0 across 0 app file(s)
WRITES_UNGATED   0
GATED_IN_BODY    0
RENDER_ONLY      0
NO_WRITE         0
exit 0
```

**A clean sweep of a platform whose real answer is 73 call sites across 17
files, 14 of them ungated writes.** Nothing in the output distinguishes it.

Fixed in two places on purpose. `app_files()` folds an empty match into `None`
— zero app files is not a real state of this repo, so nothing is lost. And
`audit()` now refuses on `not files` rather than `files is None`, **so the
refusal does not depend on which layer broke**: the first version of the new
control arm replaced `app_files` outright, passed straight through
`files is None`, and reported a clean sweep of zero files. A guard that only
works while the layer beneath it is intact is the guard that was missing here
in the first place.

### `tools/accepted_risk_expiry_audit.py` — FIXED, two instances

**`_rows()`** returned `[]` when the open-work index existed but no line parsed
as a table row — a changed table shape, a rewritten legend, a different
separator. `os.path.isfile` stays happily true throughout. Driven with `_rows()`
forced to `[]`: **`population : 1`, four verdict counts, exit 0**, against a
real population of 19. A tool that lost the entire open-work index printed a
normal-looking result.

**`_paused_docs()` did not check the return code at all** — the worst version
of the shape rather than a milder one. A `git ls-files` that failed to launch
left `stdout` empty, the function returned `[]`, and "git is broken" and "there
are no paused documents" were one answer.

The two are fixed differently and the difference is the point. **Zero index
rows is not a real state, so `_rows()` returns `None` and refuses. Zero paused
documents IS a real state**, so `_paused_docs()` keeps `[]` as an answer and
returns `None` only when git could not be asked. Collapsing both into one rule
would have made the tool refuse on a legitimately empty repo.

### `tools/citation_drift_hook.py` — CHECKED, CORRECT

`covered_paths()` ends `return paths or None` and its docstring states the
reason in the same words this sweep arrived at independently: *"Returning an
empty list on failure would make 'the checker is gone' look exactly like 'this
edit touched nothing citation-bearing', and every later edit would be silently
unguarded."* Nothing to fix.

### `tools/index_duplicate_hook.py` — CHECKED, CORRECT on this question

`_idc()` and `covered_path()` both return `None` rather than an empty answer.
**One residual, recorded and NOT fixed:** `_pairs_for()` calls the checker's
`rows()`, which returns `[]` for an unparseable index. Both sides of the
comparison come from that same parser, so the "introduced" set is correctly
empty rather than wrong — and the hook is advisory. It is the weakest instance
of the shape on the platform and is left alone deliberately.

---

## 4. The half that is not a code fix

Both fixed tools now **drive their own accessors in their own selftest**, and
each carries a **control that the fix itself can fail**. Without the control,
`files or None` and the return-code check could be deleted and every arm would
still pass — which is the same trap one level up.

The arms distinguish what they can assert from what they cannot.
`_paused_docs()` is asserted only to have **asked git and got an answer**; the
count is not asserted, because zero is legitimate there. Asserting a number the
arm cannot know is how a control becomes decoration.

---

## 5. What this sweep did NOT do

- **Pass B reads `tools/*.py` only.** `tests/`, `api/`, `.claude/` and every
  JavaScript file were covered by Pass A's grep for rev-walks and by nothing
  else. A JS accessor with this shape is invisible here.
- **It only finds accessors a selftest cannot REACH.** An accessor the selftest
  calls but asserts nothing useful about reads as covered. Calling is necessary,
  not sufficient, and the sweep cannot tell the difference.
- **It is blind to accessors reached through a variable, `getattr`, or a dict
  of callables** — the call graph is static.
- **Three tools were cleared because an external probe runs them end to end**
  (`shape_search.py`, `claim_search.py`, `first_article_inspection.py`). That
  the probe *runs* them is verified; that the probe would *notice* an empty read
  is not.
- **Nothing was made to run on a cadence.** The `ast` pass is a one-off script
  in a scratch directory and is not committed, so there is no standing check.
  Whether it should become one is an open question rather than an omission: it
  would need the blind spots above written into its own output first, which is
  most of the work of making it a tool.
