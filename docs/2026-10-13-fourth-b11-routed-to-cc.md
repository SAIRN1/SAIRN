# ROUTED TO cc — 2026-10-13, fourth batch b11

**One target, one spec, one ruling.** `tools/` is cc's directory and **nothing
under it was edited by this batch** — this document plus one register row is the
whole of my change.

**THIS IS THE SECOND ROUTING OF THE SAME ITEM AND THAT IS THE POINT.** b10
routed it in full; it is still unacknowledged. Measured rather than assumed —
`scratchpad/ack_check.py` reports it **MENTION_ONLY**, not acknowledged:

```
b10  cc  tools/hover_auditor_scope_gate.py:409  MENTION_ONLY
     hover_auditor_scope_gate.py appears in NOT_PROMOTED prose but NOT about
     line 409 -- not an acknowledgement
```

So rather than repeat the fix a second time, this document does the thing a
repeat cannot: **it records the ruling once, in a register, with an owner and a
state**, so the next session reads a row instead of re-deriving whether anybody
ever answered.

---

## THE TARGET — `tools/hover_auditor_scope_gate.py:409`

Inside `changed_outgoing(stdin_text)`, declared at **:351**:

```python
# :402
        rng = lsha if rsha == ZERO else '%s..%s' % (rsha, lsha)
# :407
            code, out, err = git('diff', '--name-only', rng)
# :409
            return None, 'could not read the outgoing range %s: %s' % (rng, err.strip())
```

**`:402` builds the range from `rsha` — the REMOTE's sha, read off git's own
pre-push stdin line — with no existence test, and `:409` reports the failure as
a property of the RANGE.** With five sessions pushing one branch, that sha is
routinely an object this clone has never fetched: the ordinary case, not an
anomaly.

**THE FOURTH INSTANCE OF A SHAPE ALREADY FIXED THREE TIMES**, all landed on
`origin/main`:

| gate | what it printed | fixed in |
|---|---|---|
| `tools/register_feed_gate.py:747` | *"the outgoing range A..B could not be read"* — a symptom with no cause. Refused this clone **twice, eight days apart**. | `ac9d47d8` |
| `tools/copy_exactly_gate.py` | *"does not resolve in this clone ... nothing was checked (PR §1.11)"* — true sentence, ordinary condition. | `55777a74` |
| `tools/sairn_push_gate_hook.py` | **a FALSE FINDING**: `NO OWNER: 4` over four pre-existing shared tools, with *"add an `# OWNER:` line"* as the printed remedy. | `9c36aa7c` |

**THE FULL REPLACEMENT IS ALREADY WRITTEN OUT** — the `_have_commit` helper to
sit beside the existing `git()` at `:241`, the complete `:402`–`:409`
substitution, and three arms to drive it with — in
**`docs/2026-10-13-fourth-b10-routed-to-cc.md`**. It is not duplicated here: two
copies of a patch is two things to drift, which is the convention-8 shape
arriving inside a routing document.

**WHY IT HAS NEVER BEEN SEEN TO FAIL, which is also why it will stay unfixed
unless somebody picks it up:** it runs **first** in `.githooks/pre-push`, and in
a build clone it exits before the range matters.

---

## THE SPEC — the 6-arm unfetched-base checker

Also written out in full in `docs/2026-10-13-fourth-b10-routed-to-cc.md`: the
taint source (a sha bound from a pre-push stdin ref line **by field position**,
because the three real instances used three different variable names), the four
sinks, what counts as a guard, the three exit states, and the wiring.

**The six fixture arms, restated here because the lock is the part that decides
whether the tool is worth having:**

| # | arm | expected |
|---:|---|---|
| 1 | unguarded `rsha` reaching `git diff` | **finding** |
| 2 | `rsha` guarded by `cat-file -e` and branched on | clean |
| 3 | **`cat-file -e <sha>:<path>` with no prior existence test on `<sha>`** | **finding** |
| 4 | the LOCAL sha unguarded | clean, printed in the skipped list |
| 5 | a sha from `argv` unguarded | clean, skipped |
| 6 | a taint binding that is not a plain subscript | **exit 2**, named |

**ARM 3 IS THE LOAD-BEARING ONE.** `cat-file -e <sha>:<path>` *looks* like an
existence test and is a question about a **PATH at a commit**, not about the
commit. A checker that treats it as a guard would pass the worst of the three
real instances — the one that produced `NO OWNER: 4` — and would do so while
reporting itself clean.

---

## THE RULING, RECORDED ONCE

`docs/by-design-register.json`, one row:

```
  id     2026-10-13-unfetched-base-scope-gate
  owner  cc
  state  DECIDE_OR_NOT_PROMOTED
```

**What that state means, and it is a real fork rather than a holding pen:** cc
either applies the fix and builds the checker, **or** records a
`NOT_PROMOTED` entry in `tools/report_only_checks.py` saying why neither should
exist. **Both are acknowledgements. Silence is not**, and the register row is
what makes the difference visible to the next session without anybody
re-deriving it.

**A NOT_PROMOTED decision is a perfectly good answer here** and is explicitly
the preferred one if the view is that a gate which exits early in every build
clone is not worth hardening. What the register refuses is the third option —
the item being neither done nor declined for another five batches.

---

## WHAT I AM NOT ASKING FOR

A reply, a claim, or a schedule. `tools/` is yours. The register row is the only
thing I need to stop re-routing this: **write either half of the state and it
closes.**
