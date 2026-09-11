# `run_all_tests.py --hook` is PAUSED — 2026-09-10

**Michael's call, this date, on severity rather than on schedule: pause the
trigger now rather than after the next one.**

The `PostToolUse` / `Bash` hook entry that ran `python tools/run_all_tests.py
--hook` has been **removed from `.claude/settings.json`**. It is paused, not
deleted — the exact entry is reproduced below and re-enabling is a copy-paste.

It could not be stashed inside `settings.json` itself: the settings validator
rejects unknown top-level keys, so a `_PAUSED_HOOKS` sibling fails the schema.
Hence this file.

---

## What happened

**FIVE stranded `PROBE` commits reached `origin/main` in one day**, and a sixth
was created locally and dropped before it could be pushed. One of them —
`c7295822`'s subject — deleted

```
service_methods: body.service_methods,
```

from `api/legal-deadlines.js`. That is the exact line whose absence made
SAIRNlaw compute Florida answer deadlines **five days late for five days**
(fixed originally in `37d87108`). The others were `PROBE clean api change`,
which adds a two-line `api/_lib/zz_probe_clean.js` that nothing imports —
harmless in itself, and that is the argument *for* reverting it rather than
against: **the mechanism does not know which kind it is publishing.**

## Root cause — the probe is not wrong, the trigger is

`tests/push_gate/check4_probe.py` does this, deliberately, to exercise push
gate check 4 end to end:

```python
run('git', 'add', 'api/_lib/zz_probe_clean.js')
run('git', 'commit', '-q', '-m', 'PROBE clean api change')
R['clean_api_change'] = dry_push()
run('git', 'reset', '--mixed', start)
```

Commit to `main`, measure, reset back. **That is safe for a single runner on a
quiet branch.** The hook fired on **every Bash tool call**, so several copies
ran concurrently — copy A resets to *its own* `start` while copy B's commit is
on the branch, and whichever commit survives is published by whoever pushes
next. A kill mid-probe leaves one behind the same way.

Nothing in the probe is incorrect in isolation. The trigger is what made it
unsafe.

## What is still running, and what is not

| | State |
|---|---|
| `tools/run_all_tests.py --hook` | **PAUSED** (this file) |
| `tools/run_all_tests.py` by hand, no `--hook` | **unaffected** — still the way to run the suite deliberately |
| `tools/report_only_checks.py --hook` | **still running**, deliberately. Report-only, commits nothing, not part of this failure |
| `tools/deploy_verify_notify.py` | **still running**, unchanged |
| every `PreToolUse` gate | **unchanged** — the push gate, the master guard and the redaction check all still fire |

**The safety net is not off.** What is off is the thing that was writing to the
branch.

## Re-enable when BOTH are true

1. The push-gate probes no longer commit to the working branch — a scratch
   clone, a detached HEAD, or a temp worktree. `tests/push_gate/check7_probe.py`
   has the same shape and needs the same treatment.
2. The trigger no longer fires on every Bash call.

Then restore this entry as the **first** element of
`hooks.PostToolUse[matcher="Bash"].hooks`, which is where it was:

```json
{
  "type": "command",
  "command": "python tools/run_all_tests.py --hook",
  "timeout": 400,
  "statusMessage": "Running the full test suite (report only)...",
  "async": true,
  "asyncRewake": true
}
```

## Ownership

Fourth holds the claim on the underlying fix
(`probe-subject-commits-must-not-reach-origin`). This pause is the trigger
only and changes no probe, no tool and no test. It was done without waiting
because the rate had changed: five in a day, the last one racing an active
push.

---

## Both re-enable conditions are now MET — 2026-09-11 (Fourth)

**Re-enabling is still Michael's call**, for the same reason pausing was: this
is a shared hook that fires in four live sessions. What follows is the evidence
that the two conditions above are satisfied, not a decision that they are
enough.

### Condition 1 — the probes no longer commit to the working branch ✅

**⚠ THE LIST ABOVE NAMED TWO FILES AND THERE WERE THREE.** This document says
*"`tests/push_gate/check7_probe.py` has the same shape and needs the same
treatment"* — and so does **`tests/push_gate/check8_probe.py`**, which plants
`PROBE check8 planted fixture` on the same branch in the same way. It is the
probe for the gate that exists *because a stranded PROBE commit shipped to
production*, and it had the defect that gate is about.

Found by grepping every `tests/**/*.py` that runs `git commit` rather than
working from this file's list — CLAUDE.md's standing lesson that a fix verified
on the copies somebody wrote down is not verified on the ones they did not. The
only other two hits, `tests/claims/run_push_verify_probe.py` and
`tests/push_gate/redaction_base_probe.py`, build their own throwaway repos and
were already safe. `check9_probe.py` drives the hook through stdin and commits
nothing.

All three now create a **detached throwaway worktree** at HEAD, plant every
fixture and run every `git commit` there, and remove it in an `atexit` handler.
A detached worktree has no branch tip, so there is no tip for a lost `reset`
race to strand a commit on — which is the exact mechanism that put five `PROBE`
commits on `origin/main`.

**One arm was passing for the wrong reason and the move exposed it.**
`check8_probe`'s two PreToolUse arms drove the hook with `git push origin
main`, and in a detached worktree `main` is the *clone's* branch, not the
checkout's HEAD where the fixture lives. The planted arm went from DENIED to
not-denied — but the more dangerous half is that the **control** arm had been
reporting ALLOWED for a reason that had nothing to do with check 8. Both now
use `git push origin HEAD:main`, which `pushed_tip()` resolves to `HEAD` and
which actually points at the commit under test.

Three things worth knowing before trusting that:

- **The pre-push hook still fires from the worktree**, so the probes still test
  the real gate. `core.hooksPath` is `.githooks` and worktrees share the common
  git dir. **Measured before the change was written**, by planting the seam
  violation in a prototype worktree and watching the real refusal text come
  back.
- **Each probe now asserts the clone was untouched** — `clone_untouched` in
  check 4 and *"and the CLONE was never touched"* in checks 7 and 8 — comparing
  `git status --porcelain` and `HEAD` in the real clone before and after. The
  old `restored` / `head_restored` assertions were about the tree the probe had
  just been mutating; **none of them was the claim that was actually violated**,
  and nothing asserted that claim until now.
- **The clean-tree precondition was removed, and that is a coverage gain.** It
  existed because `git add` in the clone could sweep uncommitted work into a
  probe commit; a worktree built from HEAD never contains the clone's
  uncommitted files, so there is nothing to sweep. That guard had been
  **skipping the only proof these BLOCKING gates have** on every run in any
  clone with a modified tracked file. All three were re-run against a
  deliberately dirty tree and passed.

### Condition 2 — the trigger no longer fires on every Bash call ✅

`hook_main()` in `tools/run_all_tests.py` reads the PreToolUse payload and
returns immediately unless the command actually runs `git push` as a command,
and returns again if `tool_response.success` is false, so a **denied** push no
longer launches the suite either. Measured:

| command | `pushes()` |
|---|---|
| `git status` | False |
| `echo hi` | False |
| `git push origin main` | True |
| `git commit -m "quotes git push in prose"` | False |

Held by `tests/run_all_tests_hook_gate_probe.py`.

### What is deliberately NOT claimed

- **No third, independent guard was added** to assert these probes keep using a
  worktree. The behavioural assertion lives *inside* each probe, which is the
  self-referential shape this platform spent 2026-09-10 sweeping for — an edit
  that removed the worktree would likely remove the assertion with it. The
  independent backstop is **push-gate check 8**, which refuses any push
  carrying a `PROBE`-subject commit and is in a different file with a different
  author's reasoning. A grep-based structural guard was considered and rejected
  as too weak to be worth the rot.
- **A hard kill still leaves a stray worktree.** `atexit` covers a normal exit,
  `sys.exit()` and an unhandled exception; it does not cover SIGKILL — exactly
  as the old `git reset` did not. The residue is now a directory in the temp
  folder rather than a commit on `main`, which is the trade being made.
