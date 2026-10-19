# The paragraph to paste into hank, cody and fourth's next batches

**cc b22 item 5.** Written for Michael to paste; **not run on any other
session.** Copy the block between the rules, verbatim. It is one paragraph plus
the two commands, and it is deliberately short enough to sit at the end of a
dispatch without displacing anything.

---

**Context figure — run these two before you write your digest.** The digest's
`CONTEXT` line is no longer something you type: push-gate CHECK 5c (gate id
`context-digest`) re-derives it from your own transcript and **denies** a push
carrying a digest of your own session whose line is not a measurement. Run, in
this order, once per session:

```
python tools/context_verify.py --provision-window 1000000
python tools/context_verify.py --digest-line
```

Paste the second command's output verbatim as your digest's `CONTEXT` line.
**Step one is not optional and skipping it is not a formality:** the window
inference is a *floor*, so on a fresh session it reported cc at 70.9% of
200,000 while the session was a 1M one at 14.2% — wrong by five times, in the
alarming direction. Until your session declares its window, the row reads
AMBIGUOUS, both candidate percentages print, and `--digest-line` refuses to
emit a figure rather than emitting the ceiling. The declaration is keyed to
your **session**, not your clone, so a new session declares again. The gate's
refusal names both commands, so you cannot get stuck — but you will lose a push
if you find out at the end of the batch.

---

## Notes for Michael, not for the paste block

- **`1000000` is the right number for an Opus 1M session, which all four build
  clones have been on.** If an agent is on a 200k session the correct value is
  `200000`, and the tool will refuse a declaration **smaller** than a prompt it
  has actually observed, naming the declaration as the wrong thing. It cannot
  catch a declaration that is too *large* — nothing in a transcript witnesses
  that — which is why the declaration is scoped to one session.
- **The agent can check the figure without writing anything:**
  `python tools/context_verify.py --agent self` prints the row with its window
  marked `declared` or `[window INFERRED]`.
- **Nothing needs to be run in hover or hover2.** `context_verify.py` excludes
  both by the separation boundary and CHECK 5c does not apply to their digests;
  a `SAIRN-digest-H1-*.txt` returns COULD_NOT_TELL rather than a refusal.
