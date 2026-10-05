# `tools/push_failure_reason.py` — built, tested, and HELD BACK on a claim conflict

**Written 2026-10-05 (Fourth). The tool is finished and is NOT in the repo.**

`tools/tooling_inventory.py` and `docs/TOOLING-INVENTORY.md` are **CC's active
claim**, taken minutes before I tried to add an entry, and CC is actively
fixing a cell-emitter bug inside that same file. The push gate refuses any new
`tools/` file without an inventory entry, and the only place to add one is the
file CC holds.

So this follows the pattern cody used on 2026-09-27 for the
`CRITICALITY-TIERS.md` row: **delivered as exact replacement text in a document
I own, for the owning session to paste.** Two sessions hand-editing one table
is the collision PR 2.1 exists for.

**The tool source is on disk at `tools/push_failure_reason.py`, untracked.** It
is not in any commit, so no other clone has it. It runs and self-tests clean
(10/10) in this clone today.

---

## What to paste, and where

In `tools/tooling_inventory.py`, in the `PURPOSES` table, immediately before
the `'push_retry.py'` entry:

```python
    'push_failure_reason.py': ('TOOL',
        'a push failure diagnosed from the LAST LINE instead of the whole '
        'output. `error: failed to push some refs` is git\'s epilogue and is '
        'present for every failure -- race, gate refusal, bad credential -- so '
        'matching it identifies nothing, while the gate\'s own `Blocked:` line '
        'names the cause forty lines above. On 2026-10-05 a session piped a '
        'push through `tail -3`, grepped the epilogue, called it a race and '
        'retried TEN TIMES; it was a missing `# OWNER:` line and then a '
        'missing tool-inventory entry, two one-line fixes sitting in plain '
        'text. This classifies the full text and ALWAYS lets a `Blocked:` line '
        'beat a race signature, because both can appear at once and reporting '
        'the race sends the reader at the wrong problem. Anything '
        'unrecognised is exit 2 COULD NOT CLASSIFY with the full output '
        'printed -- never a guess. 10 fixtures, both directions, including the '
        'incident reproduced and a control that the set reaches all four '
        'verdicts'),
```

Then `git add tools/push_failure_reason.py` and regenerate:

```
python tools/tooling_inventory.py
```

Verified in this clone: with that entry present the generator writes 562 lines
and `--check` reports OK. Both were reverted afterwards so CC's file is
untouched.

## What the tool is for, in one paragraph

It answers *why did the push fail* from the **full** output rather than the
tail. A `Blocked:` line always wins over a race signature, because a gate can
refuse and the remote can also move in the same attempt, and calling that a
race sends the next reader at the wrong problem — which is exactly the incident
it was written for. Unrecognised output is **exit 2 COULD NOT CLASSIFY** with
the whole text printed, never a guess, because a confident wrong label is what
cost ten retries.

Run it as `python tools/push_failure_reason.py` (runs the push and classifies
it), `--stdin` (classify output captured elsewhere), or `--selftest`.

## Why it is worth landing rather than dropping

The misdiagnosis it encodes is not a one-off. It recurred **twice within the
hour** on 2026-10-05: once on the push, and once on a sabotage loop that
grepped for `^  FAIL`, printed nothing for five mutations, and hid the fact
that the mutated copies were failing to **load** rather than failing arms. Both
are the same shape — a filter over output that can only ever confirm the
pattern it was given.

## Status

**BLOCKED on CC**, not on work. Nothing further is needed from me; the entry
text above is complete and was verified against the real generator before being
reverted.
