# Routed to cc: `save_reviews` has no retry against the Windows concurrent-replace failure, and a check spec for UNPROVEN arms

**Filed by:** cody, batch 27 b6, 2026-10-13
**Owner:** **cc.** `tools/tier_a_review_gate.py` and `tools/sairn_push_gate_hook.py`
are not this batch's to edit — b6 is tests/-only — and nothing in either was
touched. Everything below is reproduced by running existing code.
**Two items, unrelated in subject and related in shape:** both are a checker
that was silent about something it knew.

---

## PART 1 — `save_reviews` loses a writer on Windows, and the test was hiding it

### 1.1 The defect, measured

`tools/tier_a_review_gate.py:save_reviews()` writes to a `mkstemp` temp file and
then calls `os.replace(tmp, REVIEWS)`.

On POSIX, `rename(2)` is atomic and a concurrent rename onto the same
destination is safe. **On Windows `os.replace` is
`MoveFileEx(MOVEFILE_REPLACE_EXISTING)`, which fails `ERROR_ACCESS_DENIED`
(`WinError 5`) when the destination is held open — including by another
`MoveFileEx` in flight on the same target.**

| measurement | result |
|---|---|
| the two-thread race driven in isolation, 400 iterations | **305 raised `PermissionError [WinError 5]`** |
| `tests/run_tier_a_review_gate_probe.py` runs, b5 | **12 of 12 carried the traceback — and all 12 exited 0** |
| the same condition after the b6 test fix, 6 runs | 0 tracebacks; **0 or 1 retries needed per run** |

**It is not a flake. It is the normal case on this platform**, and it was
invisible for as long as arm 11 has existed.

### 1.2 Safety held; liveness did not — and that is the whole point

`save_reviews` was never producing a corrupt file. The property the arm exists
to prove — *a reader sees the old file or the new one and never half of each* —
**held throughout**, which is why nothing looked wrong.

What fails is **liveness**: one of two concurrent writers *errors instead of
completing*. In the probe that cost a test's honesty. **In production it costs a
record**: `--open`, `--discharge` and `--reseat-shas` all end in
`save_reviews`, and two sessions landing at the same moment means one of them
raises. The traceback surfaces, so it is not silent in a real run — but the
caller has already done its work and the record is simply not written.

### 1.3 The proposed fix — in `save_reviews`, not in its callers

```python
# in tools/tier_a_review_gate.py, save_reviews(), replacing the bare
#   os.replace(tmp, REVIEWS)
for _attempt in range(_REPLACE_RETRIES):          # 20
    try:
        os.replace(tmp, REVIEWS)
        break
    except PermissionError:
        # WINDOWS ONLY, AND NAMED RATHER THAN CAUGHT BROADLY. os.replace is
        # MoveFileEx here and fails ERROR_ACCESS_DENIED while the destination
        # is held open -- including by another MoveFileEx on the same target.
        # POSIX rename(2) cannot reach this branch, so the retry costs nothing
        # there. A bare `except OSError` would swallow a full disk.
        if _attempt == _REPLACE_RETRIES - 1:
            raise
        time.sleep(0.01)
```

**Three properties worth having, which is why this shape:**

1. **`PermissionError` by name.** `except OSError` would also catch a full disk
   or a vanished directory, and retrying those twenty times then raising is
   strictly worse than raising once.
2. **It re-raises on exhaustion.** A retry that gives up quietly converts a
   lost record into a silent one, which is worse than the defect.
3. **The cap is a decision, not a round number.** At a measured ~76%
   per-attempt failure rate, 20 attempts put exhaustion near 1e-11, so
   exhaustion is a signal. **Unbounded is wrong** — it turns a genuine deadlock
   into a hang, which PR §1.12 names as the shape that must never exist.

### 1.4 What it must be measured against before it lands

- **The existing probe is already the fixture.** `tests/run_tier_a_review_gate_probe.py`
  arms 11 and 12 now assert both writers complete and PRINT the retry count. With
  the retry in `save_reviews`, that count should fall to **0 on every run** —
  because the test's own retry would no longer be reached. **If it does not fall
  to zero, the fix is not working and the probe says so without a new arm.**
- **A POSIX run must show no behaviour change.** The retry branch is
  unreachable there; a difference would mean the `except` is catching something
  else.
- **Arm 12's expected answer stays `1`.** The read-modify-write race it
  documents is untouched by this; only the write is retried. If arm 12 ever
  finds both records, something else changed.

### 1.5 What I did instead, and why it is not a substitute

The retry now lives **in the probe's own saver thread**, so the arm achieves the
two-writer race it claims. **That fixes the test and not the product.** Every
real caller of `save_reviews` is still exposed. The probe prints the retry count
precisely so this routed item cannot become invisible again.

---

## PART 2 — the check spec for UNPROVEN arms (b6 item 5)

The full blameless account is in
**`docs/2026-10-13-cody-b6-methodology-unproven.md`**. This section is only the
mechanical part: what a checker should refuse, and the measurement it owes.

### 2.1 The rule being proposed

> **A suite must not exit 0 while any arm is UNPROVEN.**
> An arm that could not be evaluated is not a passing arm. A suite with
> unproven arms exits **3** — the could-not-run code this repo already uses —
> and its summary line states the unproven count beside the pass count.

Three sub-rules, because the single sentence is not enough to implement:

1. **UNPROVEN must be a COUNTED state, not a printed sentence.** In b5 it was a
   `print()`. A state the summary arithmetic cannot see is a state the exit code
   cannot reflect.
2. **The summary line carries all three numbers** — `N passed, M failed,
   K unproven` — because a reader who scrolls to the bottom must not read
   `0 failed` as *every arm held*.
3. **An arm may be unproven at most once.** If it is unproven on two
   consecutive runs it is a FAILURE: twice means the evidence is not
   intermittently unavailable, it is unavailable.

### 2.2 The proposed checker, scoped and cheap

`tools/unproven_arm_check.py`, **report-only to begin with**, over
`tests/**/*probe*.py` and `tests/**/*.test.js`:

- **A1 — the word without the count.** A file containing `UNPROVEN` whose
  summary `print` does not also carry an unproven count. This is exactly the b5
  defect and it is a cheap, specific, textual signal.
- **A2 — a `sys.exit(0)` reachable with an unproven arm recorded.** Narrow
  form: a file that assigns an unproven list/counter and whose exit expression
  mentions only the failure counter.
- **A3 — the inverse, and the one that keeps A1 honest.** A file that prints an
  unproven count but never sets one. Reports a state it cannot reach.

**Report-only first, for the reason this repo already records twice**: a checker
promoted to blocking while real findings exist refuses every push to the
affected file, and that is how a gate gets switched off. Promote it when the
tree is clean — the same decision `sairn_reachability_check.py` and
`dup_dom_ids_check.py` both carry in writing.

### 2.3 The measurement it owes before it blocks

This repo's standing rule for a new gate is that a widening is **measured, not
argued** (`DISJOINT_MARKERS` in `tools/sairn_claim.py` states it). So:

- **The current count.** How many files under `tests/` trip A1, A2 and A3
  today, listed by name. **I did not run it — the tool does not exist, and
  building it is explicitly outside b6.**
- **A control pair**, which is this platform's bar and not an optional extra:
  plant an arm that is unproven-and-uncounted and require A1 to fire; plant the
  same arm correctly counted and require A1 to stay silent.
- **The false-positive shape, named in advance.** A file that merely *mentions*
  UNPROVEN in prose — this document's own filename will appear in grep output —
  must not trip it. Match on the summary/exit construct, not on the word.

### 2.4 Scope note

**Nothing is built.** b6 item 5 said propose the rule, route the spec, build
nothing, and that is what this is. The three arms that were unproven in b5 are
now real passes (b6 item 3), so the rule has no outstanding instance in my
files — which is the right time to write it down and the wrong time to rely on
remembering it.

---

## 3. Reproduction

Read-only, writes nothing outside a temp directory, and each asserts its own
precondition before reporting:

```
python <scratch>/b5/race_repro.py 400          # 305/400 PermissionError (b5)
python <scratch>/b6/failfirst_arm11.py 40      # new arm RED 31/40 on the old
                                               # shape, GREEN 40/40 with retry
python <scratch>/b6/failfirst_check7_arms.py   # 10 arms, both directions
python tests/run_tier_a_review_gate_probe.py   # prints the retry count
```

`<scratch>` is
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\b9e5be49-2b5f-401f-99a3-d7fe4cd27336\scratchpad\`
— note the first script is under `b5/` and the other two under `b6/`. These are
evidence for two batches, not checkers, which is why they are in the scratchpad
and not in `tools/`: that directory enrols a file in four governance
populations and a one-off driver does not belong in any of them.

---

## 4. Not done here, and why

- **No edit to `tools/tier_a_review_gate.py`.** The patch in §1.3 is
  paste-ready content, with the measurement it owes stated rather than implied.
- **No edit to `tools/sairn_push_gate_hook.py`.** The `NO_REF_LINES`
  classification I added is in the PROBES, where it belongs: the gate's refusal
  is correct and its own text says so. Nothing about the gate needs changing for
  it.
- **`tools/unproven_arm_check.py` does not exist.** Specced, not written.
