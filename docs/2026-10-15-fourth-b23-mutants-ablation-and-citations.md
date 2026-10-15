# cody's other four mutants, the anchor-check ablation, and the 373 brought down to 371

**fourth / b23 items 4 and 5, 2026-10-15.** Both are measurements; both correct
a figure I previously published. **Every number names the command.**

---

## 1. cody's OTHER FOUR MUTANTS — REPRODUCED, ALL FIVE CAUGHT

**b22 drove M1 only and said why:** four of the five mutate
`tests/sd_data_grd_session_gate.js`, which
`tests/run_cross_tenant_dispatchers_sabotage_probe.py` reads from `ROOT` and not
from its sandbox, so driving them would have meant writing a live-clone file
inside another session's read-only zone. **cody's claim is released, so this
took the other route: copy the tree the probe needs into a tempdir and run the
COPIED probe, whose `ROOT` is then the copy.** `git status --porcelain` on the
live clone shows only my own b23 files afterwards.

`python <scratchpad>/cody_mutants_b23.py` → log `cody_mutants_b23.log`.

**THE BASELINE FIRST, because without it no mutant means anything** — the
control `sabotage_control_check.py` exists to enforce:

    BASELINE exit=0   419 passed, 0 failed
    ok  grd replacement  tests\sd_data_grd_session_gate.js covers all 6 traded
                         grd_* resources and asserts 401 NO_SESSION;
                         control name absent

| mutant | result | what the probe said |
|---|---|---|
| **M2** the named gate suite DOES NOT EXIST | **CAUGHT** exit 1 | `MISS grd replacement … missing` |
| **M3** the gate suite no longer names `grd_boq_rates` | **CAUGHT** exit 1 | `MISS … 1 member(s) uncovered` |
| **M4** the gate suite asserts no 401 `NO_SESSION` | **CAUGHT** exit 1 | `MISS … names but no refusal arm` |
| **M5** the gate suite contains the invented control name | **CAUGHT** exit 1 | `MISS … control name matched` |
| **M1** the GRD unit set back to `app: null` | **CAUGHT** exit **2** | *see below* |

**5 of 5 CAUGHT. cody's claim is independently reproduced**, and the four that
b22 left as "the author's measurement, uncorroborated" are now corroborated.

**M1's EXIT 2 IS NOT A WEAKER RESULT — IT IS THE RIGHT THIRD STATE, AND IT
CONFIRMS b22's OTHER MEASUREMENT FROM A SECOND DIRECTION.** The probe refuses
and names why:

    === BASELINE (unmutated copy) ===
      405 passed, 14 failed
    COULD NOT RUN: the baseline is not green (14 failing). A sabotage control
    on a red baseline cannot distinguish its own mutation from the pre-existing
    failure. Failing: grd_boq_rates [L] …

**405 / 14 is exactly the figure b22 obtained by driving the suite directly**,
arrived at here by a different route. And the refusal is the behaviour wanted:
a control that ran anyway would have reported its own mutation's effect mixed
with 14 unrelated failures.

---

## 2. THE ABLATION OF `tools/sf_events_anchor_check.py`

`python <scratchpad>/sf_anchor_ablation_b23.py` → log
`sf_anchor_ablation_b23.log`. Two parts, because the instruction's wording and
the house convention ask for different things and both are worth having.

### PART A — remove the fix, confirm the arm fails, restore, confirm it passes

Driven on the **real** rows against the **real** app, in memory:

| | anchors | findings | |
|---|---:|---:|---|
| **FIX REMOVED** — the row at `7a5e6a11` | 7 | **1** | **ARM FAILS** — `ROTTED: anchor 6 of 7 resolves ZERO times` |
| **FIX RESTORED** — the row at HEAD | 8 | **0** | **ARM PASSES** |

**The ablation is meaningful only because the two directions differ.** A check
that fails on both, or passes on both, measures nothing — which is precisely
what a one-sided ablation cannot tell you.

### PART B — per layer, per arm (the twelfth cross-domain discipline)

Each layer disabled **in memory** and the full 10-arm criteria lock re-run.
Unablated: **0 arms fail**, so every result below is interpretable.

| layer removed | arms broken |
|---|---|
| **L1** the `anchor ` keyword restriction (vs every backticked span) | **2** — *…and that finding says NO ANCHOR*; *a prose span with empty parens is IGNORED* |
| **L2** markdown entity unescaping (`&amp;` → `&`) | **1** — *an `&amp;`-escaped anchor matches the raw app text* |
| **L3** the AMBIGUOUS half of `count != 1` | **2** — *an anchor resolving TWICE is a finding*; **and the lock RAISED** (`IndexError`) |
| **L4** the NO-ANCHOR finding | **2** — *NO anchor at all is a FINDING, not a pass*; **and the lock RAISED** |
| **L5** the fail-closed file guard | **driven separately, see below** |

**EVERY LAYER IS LOAD-BEARING.** Removing any one of L1–L4 breaks at least one
arm; two of them break the lock so hard it raises rather than reporting, which
the harness captures as a failure rather than letting it stop the sweep — a
first version of this driver aborted at L3 and reported L4 as untested, which
reads as "not measured" when the truth is "broke the lock outright".

**L5, AND IT IS A FINDING ABOUT MY OWN TOOL:** the fail-closed guard lives in
`main()` and not in `check()`, **so no fixture arm can see it.** The 10-arm lock
would pass with the guard deleted. Driven directly instead, both directions plus
a control:

    the APP file absent      exit=2  COULD NOT RUN: no-such-app.html is missing (the app)…
    the REGISTER absent      exit=2  COULD NOT RUN: docs\nope.md is missing (the register)…
    both present (control)   exit=0

**Exit 2 is the only acceptable answer for the first two** — a check that cannot
read its subject has not passed (PR §1.11). **NEXT STEP: an arm for L5**, so the
lock covers the guard rather than the guard being covered only by a human
remembering to drive it.

### What this ablation does NOT establish, said rather than implied

**Part B is per-arm over SYNTHETIC fixtures.** It does not show that any layer
catches a defect on the real register. **Part A is the only measurement on real
text, and it exercises ONE layer (`count == 0`) on ONE document. Three of the
five layers have no real-data evidence at all.**

---

## 3. THE 373 BROUGHT DOWN TO AN ACTUAL COUNT: **371**

`python <scratchpad>/bare_citations_b23.py` → log `bare_citations_b23.log`.

**b22 published "373 bare `:NNNN`, an UPPER BOUND" and flagged that regulation
numbers were inside it. cc's tool publishes 323 with a different predicate.
Neither number was "bare code citations".** So this classifies **every**
occurrence of `:(\d{1,5})` not followed by a digit or dot — **571 in total** —
instead of narrowing with one regex, and reports what it cannot classify.

| class | count |
|---|---:|
| **QUALIFIED** `file.ext:NNN` | **198** |
| **BARE code citation, backticked** `` `:NNNN` `` | **323** |
| **BARE code citation, a backticked RANGE** `` `:NNNN-NNNN` `` | **48** |
| REGULATION (`OAC 4301:1-1-49`) | **1** |
| CLOCK TIME inside an ISO timestamp | **1** |
| | **571** |

**THE ACTUAL COUNT OF BARE CODE CITATIONS IS 371** — 323 single lines plus 48
ranges. **b22's 373 was high by exactly 2**, and the two are named: one Ohio
Administrative Code chapter number and one `…T15:18:11Z` obligation timestamp.
**cc's 323 is not low by a predicate error — it is the single-line form only;
the 48 ranges are the difference**, and they are real citations cc's regex
cannot see.

**AND THE 48 ARE THE INTERESTING ONES.** A range — `` `:25115-25116` `` — cannot
be checked by **any** single-line lookup, so no line-drift tool and no anchor
tool in this repo can assess them. They are not "unassessable because the target
must be inferred"; they are unassessable **because of their form**, and they are
13% of the bare population.

**CARRY 371, WITH THE SPLIT.** The standing conclusion is unchanged and
sharpens: of 571 line citations in `docs/CRITICALITY-TIERS.md`, **198 are
mechanically checkable, 323 need their target inferred from prose, and 48 cannot
be checked by a line lookup at all.**

---

## 4. ROUTED

* **cc** — `citation_anchor_rot_check.py`'s R3 counts 323; add the **range**
  form so the second-class figure is 371 and not 323, and report ranges as their
  own class, since no tool can assess them. The parallel to R3's existing
  argument is exact: a half-counted second class reads as a counted one.
* **me, next batch** — an arm for L5 of `sf_events_anchor_check.py`, or the
  deletion decision in §5 of the cc discharge (both tools are unwired; wire one,
  then delete mine).
