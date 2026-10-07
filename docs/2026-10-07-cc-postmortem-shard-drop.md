# Blameless postmortem — sharding silently dropped 58 of 73 entries

**Written 2026-10-07 (cc). Subject: my own change.** Blameless in the sense that
matters: the question is what made this *easy to do and hard to see*, not who
did it. I did it.

---

## What happened

Resolving the ANDON on `tools/report_only_checks.py --hook` (five runs of
547.6–712.4s against a 600s ceiling, mean 612.0s), I added `--shard K/N` so the
`PostToolUse` hook runs one fifth of the registry per push. The implementation
was one line:

```python
entries = sel          # sel = this shard's slice
```

**The loop then iterated 15 of 73 entries, and the other 58 were removed from
the loop AND from `skipped`, so nothing named them.** The sweep reported its
findings and its could-not-runs for 15 checkers and said nothing at all about
58. A clean 15 read exactly like a clean 73.

**Blast radius, stated rather than estimated:** one push, caught by the probe
before the change left the working tree. `tests/run_report_only_checks_probe.py`
arm H7 failed because the fixture's dirty checker fell outside the shard that
ran — **the probe caught it for a different reason than the one that mattered**,
which is luck I should not plan on.

---

## Why it was easy to do

**THE BUDGET LOGIC NEXT TO IT WAS ALREADY CORRECT, AND THAT IS THE TRAP.** When
the sweep runs out of time it does the right thing and has for weeks:

```python
skipped = [e['tool'] for e in entries[i:]]
...
for tool in skipped:
    unrun.append('%s -- NOT RUN, the sweep reached its %ss cut first ...')
```

So the file already *had* the discipline, in the function I was editing, eight
lines from my change. I added a **second** way for an entry not to run and did
not extend the accounting to it. **A correct neighbour is not a check** — it
protected against the narrowing it knew about and nothing else.

---

## Why it was hard to see

1. **THE FAILURE MODE WAS SILENCE, AND SILENCE IS WHAT SUCCESS LOOKS LIKE
   HERE.** `--hook` prints nothing on a clean sweep by design — that is the
   contract, and it is the right contract. So "15 consulted, 58 never asked"
   and "73 consulted, nothing found" produce byte-identical output.
2. **NOTHING EVER PRINTED A DENOMINATOR.** The sweep printed findings, timings
   and skipped tools. It never printed *"consulted N of M"*, so there was no
   number to notice had changed.
3. **THE CODE READS CORRECTLY.** `entries = sel` is the obvious way to run a
   subset. The defect is not in what the line does; it is in what the *report*
   stopped covering, which is not visible at the line.

---

## Cause tag

| field | value |
|---|---|
| **phase** | authoring a change to an existing check |
| **sub-phase** | narrowing a population |
| **specific cause** | a second route to "this entry did not run" was added without extending the accounting that already covered the first route (`skipped`), so the narrowed entries appeared in no bucket and no output |
| **detection** | the controlling probe, **for an unrelated reason** — a fixture entry fell outside the running shard |
| **why not caught earlier** | nothing in the sweep printed a denominator, so there was no figure whose change would have been visible |

---

## The local fix, already landed

Out-of-shard entries are named in `unrun`:

    <tool> -- NOT RUN, NOT IN THIS SHARD (K/N). It runs on a later push in the
    rotation. This is an UNKNOWN for THIS push, not a clean result.

**That is a fix for the one way I happened to narrow the population.** It would
not have caught a third route, and a third route is exactly what I added to a
file that already had two.

---

## THE SYSTEM-LEVEL FIX — one invariant, inside an existing check

Added to `tools/report_only_checks.sweep()` — no new tool, no new file:

**EVERY REGISTRY ENTRY MUST END IN EXACTLY ONE OF `ran` / `stopped at the cut` /
`out of shard`. If the three do not sum to the registry, the sweep says so
instead of reporting.**

```
POPULATION DOES NOT RECONCILE: the registry holds 75 entries and this sweep
accounted for 15 (ran 15, stopped at the cut 0, out of shard 60). 60 entry(ies)
are in NO bucket, so this run cannot say whether they were consulted: <names>.
This is an accounting failure in the sweep itself, not a result about the
checkers.
```

**WHY THIS AND NOT A BETTER COMMENT.** It is indifferent to *how* the population
was narrowed. Any future fourth route — a filter, an exclusion list, an early
`continue` — is caught by arithmetic rather than by whoever adds it remembering
to extend a list. It is the scrubber's own rule for a bucketing pattern
(*account for 100% of the input and print the residue*) applied to this sweep's
own input.

**IT DOES NOT BLOCK.** An accounting failure is appended to `unrun`, which is
already how this sweep reports an unknown, and `main()` already returns non-zero
on a non-empty `unrun`. A sweep that cannot account for itself must not also
refuse somebody's push.

### Driven in both directions

| arm | result |
|---|---|
| **baseline**, real sharded run, `--shard 1/5 --budget 25` | exit 1, **does NOT fire** |
| **CONTROL**, the same file with `out_of_shard` removed from the accounting | exit 1, **FIRES**, naming 60 unaccounted entries |

Without the second arm, "it does not fire" and "it cannot fire" are the same
observation.

---

## What this postmortem does NOT claim

* **Not that the invariant catches the general class.** It catches an
  unaccounted population *in this sweep*. Every other tool that narrows its own
  input is unprotected, and that is the standing gap this names rather than
  closes.
* **Not that the probe caught it.** The probe failed for a different reason and
  I followed the failure to this. Planning on that is planning on luck.
* **Not that sharding was avoidable.** The ceiling is real and 39 of 73 entries
  cost 553.2s; no full pass fits under 300s. **The delay sharding introduces is
  a cost, not a defect** — a finding now surfaces up to five pushes later, and
  that is named on every run rather than hidden.
