# Checker determinism — the platform sweep, and what it did NOT find

**Written 2026-09-12 (Fourth).** Commissioned after `literal_drift_check.py`
turned out to answer differently on identical input: it sorted a **set** of
strings with `key=len`, and `sorted` is stable, so equal-length strings kept
whatever order the set iterated them in — which for strings depends on
`PYTHONHASHSEED` and varies between processes.

The question the sweep asks: **how many other checkers on this platform give a
different answer on the same input, with nothing changed and nothing to see?**

---

## The answer, stated before the detail: exactly one, and it is fixed

**Twenty-six promoted checkers examined, plus three unpromoted ones with the
same code shape. One was seed-dependent — the one that started this — and it is
fixed in `ac8f8491`. Every other checker is byte-identical across seeds.**

That is the result as it came out. The shape is real and genuinely invisible,
and the measurement says the platform has it in one place.

---

## Why this class is worth a sweep rather than a fix and a shrug

A seed-dependent checker cannot be noticed by **using** it. Every individual run
looks authoritative; the disagreement only exists between two runs, and nothing
compares two runs unless somebody sets out to. `literal_drift_check.py` was
caught only because `comment_sensitivity_check.py` diffs a run on the real file
against a run on a comment-blanked copy — i.e. by a tool built for an unrelated
purpose that happened to compare.

**Twenty-one of these twenty-six are wired into `report_only_checks.py`**, whose
output is read after every push by a mechanism rather than by a person. An
unstable one there produces a report that changes without the code changing.

---

## Method, and the control that makes the negative result mean something

Each checker was run at `PYTHONHASHSEED` **1, 7 and 12345**, and its stdout
compared byte for byte. Apps-mode checkers were then re-run across **six apps**
— `sairnvet`, `stonedesk`, `sairncode`, `sairnlaw`, `sairndental`,
`sairnsenior` — because one app is not coverage: with the defect present,
`literal_drift` gave six distinct outputs on `sairnvet` and **was perfectly
stable on `sairnsenior` and `sairnfreedom`**. A single-app sweep would have
cleared it.

**The control is the part that makes "NONE" a result rather than an absence.**
The fixed `literal_drift_check.py` was copied with the old sort restored and run
through the identical path: **3 distinct outputs, 234 lines each** — so the
method demonstrably sees the defect it is looking for. Without that arm, a sweep
returning NONE is indistinguishable from a sweep that is broken, which is the
same failure this document's sibling probe committed and caught in itself.

The copy was written **inside `tools/`**, because a copy in a temp directory
dies on `ModuleNotFoundError` — these tools import siblings relative to their
own path — and prints nothing at every seed, which reads as *stable*.

`npm_audit_check.py` was skipped: it reaches the network, so its variation is
not a question about determinism.

---

## What was examined

| | result |
|---|---|
| 26 promoted checkers × 3 seeds | **stable**, except `literal_drift_check.py` (fixed) |
| 6 apps-mode checkers × 6 apps × 3 seeds | **stable on all 6** |
| `traceability_matrix.py` **as a generator** | **stable** — sha256 of the written doc identical at 4 seeds |
| `local_only_collection_check.py` | stable at 4 seeds |
| `soup_register_check.py` | stable at 4 seeds |

The generator was measured separately on purpose: the registry runs it as
`--check`, which prints one line, and that would not have exercised the code
that writes `docs/traceability-matrix.md` — a file this repo regenerates and
commits constantly, where instability would show up as spurious diffs.

---

## The shape to look for, since "sorted a set" is usually FINE

`sorted(set(...))` with **no key** is a total order over distinct strings and is
completely deterministic. It is the correct idiom and appears 19 times in
`tools/`. **The dangerous shape is `sorted(set(...), key=<something lossy>)`** —
a key that can tie, leaving the tie broken by set iteration order.

Three sites in `tools/` have a lossy key. One was the defect. **The other two
are benign, and by reasoning rather than only by measurement:**

- **`traceability_matrix.py:82`** — `sorted(set(hits), key=len, reverse=True)`.
  The result feeds `top = [h for h in hits if not any(h != o and h in o ...)]`
  and is used only as `if len(top) == 1`. Whether that list has one element does
  not depend on its order.
- **`local_only_collection_check.py:555`** — `sorted(map(re.escape, others),
  key=len, reverse=True)` over a set, joined into a regex alternation. Tie order
  changes the pattern *text*, which is never printed; and the alternatives are
  distinct literal names, so at most one can match at a given position. The
  boolean result is order-independent.

Both are stable **by data and by argument** rather than by construction. Named
here so the next reader does not have to re-derive it, and so that if either
ever starts printing its intermediate, the hazard is already written down.

---

## No permanent checker was added, and that is a decision

A mechanical guard for this would flag `key=` on a `sorted(set(...))`. Across
`tools/` today that is **three sites, two of them benign** — a 67% false-positive
rate on its first real run, which is precisely the profile
`report_only_checks.py`'s own header says earns a checker the reputation that
gets it switched off before it is ever promoted.

What exists instead is concrete and cheap:
`tests/run_literal_drift_determinism_probe.py` pins the one checker that had the
defect, at three seeds, with a mutation arm proving the probe can see it. The
sweep itself is not wired — running 26 checkers at 3 seeds costs roughly six
minutes, and `write_without_readback_check.py` alone is 107 seconds. It is a
periodic exercise, and this document is how it gets repeated rather than
re-invented.
