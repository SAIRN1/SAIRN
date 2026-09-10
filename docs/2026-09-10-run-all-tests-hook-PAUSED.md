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
