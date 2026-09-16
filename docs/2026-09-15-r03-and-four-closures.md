# R03 was half-fixed, and four closures — 2026-09-15 (CC)

Follow-ups from `docs/2026-09-15-five-followups.md`. Pushed as `94a4063f`.

---

## 1. R03 — a real, live defect, and the same shape one level up

**`bfe591a2` fixed the helper and not the callers.** `cmSavePoints()` awaits
`grdData()` and raises an honest toast when the push fails. The three call sites
were not changed: they call it **without `await`** and then toast *"Point
captured"* / *"N point(s) placed via AR"* unconditionally, so the success claim
still does not depend on the result and still fires **first**.

### The previous session considered this and decided it was fine

Its own words, at the site:

> *toast() is `textContent = m` — a later message REPLACES an earlier one. So
> the optimistic "Point captured" still appears immediately, and is replaced by
> the honest one when the push resolves.*

**That reasoning is wrong, and the case it misses is not an edge one.**

> **A message that corrects an earlier message only corrects it if it is the
> NEXT message.**

Capturing course points is inherently a **sequence** — tee, pin, each hazard —
and `addCoursePoint()` awaits a GPS fix that can take 8 seconds, so a second
capture routinely starts before the first push resolves:

```
capture 1 -> "Point captured"           (push 1 still pending)
capture 2 -> "Getting GPS fix..."       <- push 1's correction is now queued
push 1 fails -> "saved on this device only"
capture 2 -> "Point captured"           <- ...and overwritten again
```

The user ends on a success claim holding two points, one of which never reached
the server. **The correction was overwritten by the next optimistic claim** —
the same false success, arriving one toast later.

### The fix, and what it must not cost

The promise is **taken, not awaited immediately**. `cmSavePoints()` does the
local write and `rGolf()` synchronously before its first `await`, so the points
table still redraws instantly and **only the claim waits for the server**. A
caller that awaited first would block the redraw for up to the 15-second
timeout, and there is an arm for that.

`removeCoursePoint()` awaits too. It makes no success claim, but a removal that
did not sync should not be reported by a toast racing whatever the user does
next.

### Why the scanner reported this app clean — the new root shape

`tools/write_path_fault_scan.py` looks for the **data wrapper by name**
(`grdData(`). These call sites call a **local async helper**, so the dropped
promise is invisible to it.

**That is the new root shape: the fire-and-forget moved one level up.** It is
recorded here rather than fixed — a general indirect rule is a separate change,
and the specific case now has a structural arm.

### The suite had the same gap, one level up

`tests/faults/grd_write_faults.js` drove `cmSavePoints()` alone and asserted
*"the caller owns the good news"* — while **nothing anywhere asserted that the
caller only gives good news when it is good.** 18 → 25 arms: the two-capture
interleaving, a control that the good path still confirms with the accuracy, a
control that the table redraws before the push resolves, and a structural arm
that no call site drops the promise (with its own control that the detector can
fail).

---

## 2. The untraced count — a third citing source that is not co-location

243 of 248 citations came from the open-work index. `traced()` now also accepts
a **`REQUIREMENT:` declared in a test file's own header**.

**Counting co-location was still refused.** A filename says WHAT a test covers;
it cannot say WHY the coverage is required. A declaration is a sentence somebody
**wrote** — the same act as writing an index row, living next to the test where
it cannot go stale relative to it. It is labelled **`declared`** and is the
weakest of the three: nothing outside the file corroborates it.

**22 declarations written by hand** against each module's own header, never
generated from it — a generated line restates what the file already says and
traces nothing. **213 → 200 untraced**, with 9 new test files arriving from
other clones inside the same window.

Six arms hold the rule in both directions, and the last one is the important
one: **the `declared` source must not be carrying the whole figure** — if it
were, the metric would have been moved rather than closed.

**An existing arm caught my own change.** `C1` anchored on the old headline
sentence and went red when section 5 started leading with the absolute count.
That is the arm working; it now follows the headline and asserts the ratio sits
below it.

**33 of the 55 bound-to-subject files still have no declaration**, and the 158
with no binding at all are untouched.

---

## 3. The last Tier A artefact with nothing

`tests/run_sc_tier_a_live_probe_probe.py`, 30 arms, for
`tools/sc_tier_a_write_gate_live_probe.py` — which writes to and **deletes
from** the production demo tenant, and whose only verification was that somebody
had once run it.

**It does not run the probe.** That would wire a production writer into every
push, which is the sweep probe's first declared exclusion. It covers the half
that decides **whether and what** it writes:

- it must refuse with no credentials, and refuse as **UNVERIFIED (exit 2)** —
  not as a pass and not as a gate failure;
- the Tier A soft-delete-only list must come **from the registry**, never a copy:
  a stale copy would let it hard-delete a Tier A record while reporting clean;
- everything it creates is labelled `ZZ-GATE-*`, so a reader finding one in real
  data knows what it is;
- a cleanup failure is a **finding**.

Section 2 is the control that the refusal is about the environment rather than a
permanent off switch.

---

## 4. A self-test that cannot fail is not a check

`tests/run_selftest_independence_probe.py`. The sweep probe proved six
self-tests **pass**. It proved nothing about whether they can **fail**.

**11 mutants planted from outside**, in tracked files, each declared with the arm
it should trip:

| tool | mutants |
|---|---|
| `sabotage.py` | duplicated anchor accepted, no-op replacement accepted, stale line index ignored, read-back skipped, `Planted` stops restoring |
| `line_endings.py` | `compare()` collapsed to two states, a real difference called `ENDINGS_ONLY`, `MIXED` folded into a pure answer |
| `nhi_register.py` | the refusal stops firing on an unattributed credential, on an unregistered role, and a version where nothing can ever be unattributed |

**All 11 caught, each by the arm it was aimed at** — which the probe also
asserts, because a mutant caught by the *wrong* arm means the coverage is
somewhere other than where it was thought to be. Every tool is restored in a
`finally` and `git status` is compared before and after.

**What it does not establish:** that the self-tests cover everything. A mutant
nobody wrote is a line nobody checked.

---

## 5. Item 79, round two — and the split is the finding

The tool now **records completed rounds and excludes their records from future
ones**: re-judging a record whose answer you have seen is a memory test wearing
a blind round's clothes.

**Round 2, eight records: 3 agree, 5 differ. Across both rounds: 6 of 14.**

### The 8 disagreements split 4 more severe, 4 less

That split is what a second round buys and a rate cannot give:

| shape | what it means | the fix |
|---|---|---|
| **one-sided** | a **calibration offset** — two people on the same scale starting from different places | agree an anchor |
| **even** | **dispersion** — the same scale applied inconsistently because it has no definition to be consistent with | define the scale |

So `SEVERITIES` in `tools/defect_register.py` — four words that carried **no
definition**, while `layer` and `injection_phase` each carry a paragraph — now
defines all four against **consequence if the defect reaches a user**.

### The 85 existing records are NOT re-tiered

Stated where it matters: they were assigned with no definition to assign
against, so the corpus is **mixed**, and `tools/defect_budget_policy.py` weights
by severity across both vocabularies. Re-tiering 85 records is a governance
decision with a real cost either way and is not one a definition comment gets to
make silently.

### The sharpest individual judgements, both blind

- **sairnroofing's photo rule that did not refuse**, on a Tier A claim resource —
  judged `critical`, recorded `high`.
- **sairncash's unauthenticated route into a customer's Stripe billing** — judged
  `critical`, recorded `high`.

---

## What this does NOT claim

- **The indirect fire-and-forget shape is not swept platform-wide.** One call
  site family is fixed and the scanner's blind spot is recorded; no general rule
  was added.
- **200 test files still state no requirement.** 22 were closed by hand.
- **Three Tier A tools are still covered by their own self-tests** — now proven
  to bite, which is a different claim from independent coverage.
- **One seam is COULD-NOT-TELL and it is not from this work:**
  `api/sairndental/public-book.js -> stampLocation()` has no local function
  declaration because the name is re-exported from `locationScope`, so
  `sairn_seam_check.py` cannot read it. Pre-existing, reported by the tool
  correctly, and still unverified.
