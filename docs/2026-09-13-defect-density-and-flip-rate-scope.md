# Two measurements before two mechanisms

**2026-09-13 (CC).** Task 1 re-derives the numbers the defect-budget trigger will
fire on. Task 2 scopes the flip-rate infrastructure the flaky-checker quarantine
would sit on. **Nothing was corrected in either subject** — where something looks
wrong it is flagged here and left alone, per the instruction.

---

## 1. Defect density — what is solid, and what is not

### 1a. The denominator is solid, and it cannot go stale

`app_lines()` runs `git ls-files '*.html'`, keeps root-level files, and counts
lines **at run time**. There is no stored figure, so there is nothing to go
stale — the failure mode that cost a day on the schema snapshot cannot happen
here.

**Independently re-derived rather than trusted:** same rule, computed
separately, **135,332 lines across 22 tracked root `.html` files — exact match**
with the tool's `ALL APPS` figure.

Two things about that denominator that are true and are not defects, said here
so the number is not quoted without them:

- **Five of the 22 "apps" are satellite pages**, not apps: `stonedesk-hr` (1,434),
  `stonedesk-intake` (376), `stonedesk-catalog` (349), `sairndental-book` (320),
  `sairndental-complaint` (168). 2,647 lines, **2.0% of the denominator.**
- **The density divides by all 22 while only 7 have a logged product defect.**
  `ALL APPS 0.14/1k` therefore spans 15 files nobody has swept. The tool's own
  output already says a density is "a fact about what has been LOOKED AT";
  this is the concrete size of that caveat.

Neither changes the arithmetic. Both change what the arithmetic means.

### 1b. The standing-rules-citation field does not exist

The instruction was to spot-check logged defects **against** that field. It is
not there to check against:

> Record schema, all 48 records, 100% coverage each:
> `app, commit, date, detection_method, files, layer, lines_added,
> lines_removed, severity, subject, summary`.

No citation field, no rule id, nothing equivalent — and `--add` has no flag for
one. `tools/fmea_prediction_check.py` already names this exactly: *"it therefore
scores ZERO until docs/defect-density-register.json records WHICH standing rule
each defect instantiated. That gap is the real finding of the first run."*

**So the answerable question is the one behind the instruction: would the field
be fillable, and for how many?** Classified below. This is a judgement, not a
measurement, so every call is written out to be argued with.

### 1c. How many would hold up: 24 clean, 13 arguable, 11 not citable

Against the `docs/SAIRN-PROCESS-RULES.md` section ids. A citation counts as
**clean** only where the defect is a genuine instance of that rule's named
class, not merely adjacent to it.

| # | layer | rule | verdict |
|---|---|---|---|
| 3 | test | 1.1 a check that stopped checking | clean |
| 5 | tooling | 1.1 | clean |
| 21 | tooling | 1.1 | clean |
| 30 | tooling | 1.1 | clean |
| 34 | test | 1.1 | clean |
| 39 | tooling | 1.1 | clean |
| 4 | test | 1.2 grep cannot tell code from text | clean |
| 19 | tooling | 1.2 | clean |
| 20 | tooling | 1.2 | clean |
| 37 | tooling | 1.2 | clean |
| 6 | test | 1.3 an anchor that still matches | clean |
| 7 | test | 1.3 | clean |
| 8, 10, 11, 12, 17, 18, 22, 25, 26, 27, 35 | product | 1.5 the confident line printed after the error | clean (11) |
| 28 | product | 1.6 a fix verified on one copy of two | clean |
| 31 | product | 3.4 SQL writing credential rows | clean |
| 40 | test | 1.10 only as current as its oldest input | clean |
| 2 | product | 1.1 | arguable — a suppression flag left on, not a check that passed |
| 9 | product | 1.5 | arguable — silence by omission rather than a false success |
| 13 | tooling | 1.7 a sampling window exempts what it does not reach | arguable |
| 23 | tooling | 2.3 a fact with a tense needs a read | arguable |
| 24, 29, 32, 33, 36, 38, 44, 45 | mixed | 1.1 / 1.7 / 1.9 | arguable (8) |
| 47 | test | Part 5 verification discipline | arguable |
| 0, 14, 15, 16 | product | — | **not citable** |
| 1 | tooling | — | **not citable** |
| 41, 42, 43, 46 | tooling | — | **not citable** |

**24 clean (50%), 13 arguable (27%), 11 not citable (23%).**

**The single most useful result is in the not-citable column, and it is not a
data-quality problem.** Four records — 41, 42, 43, 46 — are the same shape:

> a gate that **disables itself in silence** when a tool it calls is absent.

That is the most-repeated failure in the whole register after 1.5, it took down
**nine of ten push-gate checks at once** in record 41, and **there is no standing
rule for it.** A citation field added today would leave those four blank, and
the FMEA scorer would keep reading them as unpredicted.

The other not-citable group (0, 14, 15, 16) is product-domain — a KPI computed
from unqualified rows, a duplicate global, demo data reaching a live server, a
payload over a CHECK constraint. Those map to Guardian checks, not process
rules, which is a real distinction and not an omission.

### 1d. What I did not do

- **No citation field was added.** Adding it is a schema change to a standing
  document, and the classification above is a proposal, not a measurement.
- **No record was edited.** The four fail-open records are correct as written;
  what is missing is a rule for them to cite.
- **The `ALL APPS` density was not adjusted** for the 15 unswept files or the
  five satellite pages. Both are visible above; changing the divisor is a
  decision about what the number means.

---

## 2. Flaky-checker quarantine — what the measurement would cost

**Nothing on the platform re-runs a checker against fixed input and records
whether the verdict flips.** The nearest prior art is
`tests/run_literal_drift_determinism_probe.py`, which is **one checker, one
variable** — it varies `PYTHONHASHSEED` and demands byte-identical output. The
general case does not exist.

### 2a. Measured cost, not estimated

All 33 promoted checkers, timed individually on this clone:

| tier | checkers | per pass | 10 passes |
|---|---|---|---|
| A — under 2s each | 20 once-mode | **~15s** | **~2.5 min** |
| B — 2s to 12s | 6 once-mode | ~32s | ~5 min |
| C — the two outliers | `write_without_readback` 27.8s, `comment_sensitivity` 77.9s | ~106s | ~18 min |
| apps-mode, full 22-file fan-out | 7 | ~49s | ~8 min |
| **everything** | **33** | **~202s** | **~34 min** |

**Two checkers are 69% of the once-mode cost.** Tiering is therefore worth more
than any optimisation: **20 checkers can be re-run ten times in under three
minutes**, which is cheap enough to run on every sweep rather than nightly.

`sairn_dead_button_audit.py` dominates apps-mode at 1.11s/file — half that
tier's cost on its own.

### 2b. "Unchanged input" is the hard part, and it is where this would go wrong

A flip-rate runner that gets this wrong records other people's changes as
checker flakiness. Four categories, each needing a decision rather than a
default:

1. **Working tree fixed and clean.** Record the HEAD sha and
   `git status --porcelain` with every run; discard any run where either moved.
   Cheap and non-negotiable.

2. **⚠ Concurrent mutating suites are the biggest false-flip source, and this is
   not hypothetical.** Several probes **rewrite tracked files in place** and
   restore them in a `finally` — `tests/write_readback_shape_probe.py` plants
   `zzProbeWrite` into `stonedesk.html`. I watched that mutation sitting in the
   working tree mid-run on 2026-09-12. A flip-rate pass overlapping
   `run_all_tests.py` would attribute the suite's mutation to the checker. The
   runner must refuse to start on a dirty tree **and** re-check cleanliness
   between runs, not once at the top.

3. **Inputs outside the working tree — classify, do not ignore.** At least five
   of the 33 read something the repo does not contain:
   - `npm_audit_check.py` — **the network.** Inherently non-deterministic;
     exclude, or measure it and label the result as an availability signal.
   - `schema_snapshot_freshness.py` — **the clock.** Its expiry finding, added
     today, genuinely changes verdict as the capture ages. **A naive flip-rate
     detector would call this correct behaviour flaky**, and it is the sharpest
     example of why category 3 cannot be skipped.
   - `install_git_hooks.py --check` — **per-clone git config.** Legitimately
     differs between clones, should be stable within one.
   - `traceability_matrix.py`, `defect_register.py --check`,
     `index_duplicate_check.py` — **git history**, stable within a fixed sha.

4. **`PYTHONHASHSEED` is two different experiments, and the runner must say
   which it ran.** Fixing the seed hides exactly the class the literal-drift
   probe found; varying it measures seed-sensitivity rather than flakiness.
   Both are legitimate; reporting one as the other is not.

### 2c. Where the data would live

`docs/checker-flip-rate.json`, same shape and discipline as
`tools/removal_path_baseline.json`: one entry per checker, recording the sha
measured against, the run count, the distinct verdicts seen, the first
divergence, and **the seed policy used**. A checker with one distinct verdict
over N runs is not "not flaky" — it is "not flaky at N runs on this sha", and
the file should say so in those words.

### 2d. Size

- **Runner + probe: small.** ~150 lines and a probe that plants a deliberately
  non-deterministic fixture checker and demands the runner catch it — without
  that arm the runner is a thing that has never been seen to detect anything.
- **The per-checker input classification: the real work.** 33 judgement calls of
  the kind in 2b.3, none derivable, each needing a line of reasoning beside it.
- **The quarantine rule itself: trivial, and must not be built first.** A
  quarantine threshold with no measured flip rates underneath it is a number
  chosen rather than found.

**Recommended order:** tier A only, fixed seed, ten runs, on a clean tree —
under three minutes, covers 20 of 33 checkers, and produces the first real
flip-rate numbers this platform has had. Widen after reading them.
