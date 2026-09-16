# Items 52 and 59 — the fusion, and the dispersion number that would have been wrong

**2026-09-15 (Fourth).** Two items with both inputs already on disk. Both produced
a real finding, and in both cases the finding was about **a number that looked
like an answer and was not**.

---

## Item 52 — complementary measurement fusion

`tools/checker_estimate_fusion.py` · control: `tests/run_estimate_fusion_probe.py`
(19 arms, all paired, green).

### The two signals, and why this is not the existing min-fusion

`tools/checker_confidence.py` already combines these inputs — **by conjunction**,
`confidence = min(stability_band, evidence_band)` — and its header argues that
case correctly: under a minimum, one weak input caps the result and
`checkblocks.py` cannot average its way to MEDIUM.

**Item 52 asks a different question with a different shape.** A minimum throws
away the *tracking*:

| | signal | property |
|---|---|---|
| **INS** | flip rate (`flaky_checker_quarantine`) | always on, cheap, **drifts — and the drift is optimistic**: a checker that always exits 0 has a perfect flip rate forever |
| **GPS** | control evidence (`checker_control_check`) | accurate, absolute, **infrequent** — a human has to write it |

The flip rate's value is that it *moves between fixes*; the control's is that it
*anchors the level*. Fusing keeps both, with the weight visible.

### The caveat shaped the file more than the fusion did

**A compromised corrector makes a fused estimate worse than no fusion at all** —
and on this platform that is measured, not borrowed from GPS spoofing:

- `tools/sabotage_control_check.py` exists because controls were found that
  **never verify their own sabotage applied**. Such a control mutates nothing,
  the suite stays green, and it reports "the checker fired" having tested
  nothing.
- `tools/mutation_anchor_check.py` records four of six probes as unsweepable.

So the corrector is sanity-checked **before** it may correct. When it fails, the
weight goes to zero, the row is labelled **UNCORRECTED — CORRECTOR REFUSED**, and
the exit code is 1. It does not fall back to the drifting estimate wearing a
fused name.

### Measured on the real fleet: 46 checkers

| result | count | reading |
|---|---|---|
| FUSED | 43 | correction applied |
| CORRECTION ONLY | 1 | the continuous signal earned no weight — labelled, not called a fusion |
| **UNCORRECTED — CORRECTOR REFUSED** | **2** | `master_plan.py`, `traceability_matrix.py` — their controls are in `sabotage_control_check`'s UNGUARDED set |

**And the fusion does real work in both directions:**

- `npm_audit_check.py` and `subprocess_decode_check.py` sit at **INS 0.95** —
  perfectly stable — and fall to **fused 0.285**, because a control exists and
  does not prove both directions. That is the `checkblocks.py` lesson expressed
  as a number that moved.
- `comment_sensitivity_check.py` goes the other way: INS 0.30 (LOW stability),
  correction 1.00, and because its run count has earned no weight the result is
  labelled **CORRECTION ONLY** rather than being passed off as two signals
  agreeing.

### Two things the control caught in my own tool

1. **The file printed "THE WEIGHT IS VISIBLE ON PURPOSE" and then omitted the
   weight column.** A tool asserting a property it does not have. The column is
   in the human table now, not only in `--json`.
2. **A weight of 1.0 was being reported as `FUSED`.** That is a pure correction
   with the drifting signal contributing nothing — and it happens exactly when
   the continuous signal has too few runs, which is precisely when a reader most
   needs to know only one thing was measured.

Thresholds (`CORRECTOR_FLOOR = 1.0`, `MIN_RUNS_FOR_INS = 20`) are
**pre-registered** and the second is taken from `flaky_checker_quarantine`'s own
derivation rather than picked here.

---

## Item 59 — superspreading / dispersion

Additions to `tools/defect_dispersion.py` · control:
`tests/run_dispersion_probe.py` (18 arms, paired, green).

### The Gini columns were already there. They do not answer the question.

The tool reported Gini and top-20 share, both ways, carefully. **Neither is
evidence of clustering at these rates**, and that is the trap item 59 walks into
if the number is taken at face value:

> 77 defects over 1232 commits gives a Gini of **0.971** over the population. So
> does a **perfectly Poisson** process at the same rate — with a mean of 0.06
> defects per commit, almost every commit has zero and a handful have one, which
> is maximally "unequal" by any concentration index and is **not** superspreading.

**A concentration index measures sparseness at these rates, not clustering.**

### The test that does answer it

Variance relative to the mean, over the population with zeros included. Poisson
is 1; above 1 is clustered. The negative-binomial `k = mean²/(variance − mean)` is
the epidemiological form — small `k` is heavy clustering.

| dimension | index | NB k | verdict |
|---|---|---|---|
| originating commit | 2.056 | 0.059 | **OVER-DISPERSED** |
| file | 16.646 | 0.038 | OVER-DISPERSED |
| app | 29.398 | 0.118 | OVER-DISPERSED |
| session | 15.766 | 0.227 | OVER-DISPERSED |
| layer | 1.416 | — | **NOT TESTED — UNDERPOWERED** |
| detection method | — | — | NOT TESTED |

**So the shape genuinely is over-dispersed** — the user's precondition is met,
and it was worth checking rather than assuming, because `layer` shows what a
high index looks like when it means nothing.

### Three refusals, each a different kind of "no answer"

- **UNDERPOWERED.** With 3 units, 2 standard errors is ±2.0 — the index would
  have to exceed 3.0 to register, so the test **could only ever answer
  "indistinguishable"**. A test that cannot fail is not a test, and reporting
  its answer as a fact about the defects would be a fact about the number of
  units.
- **NOT TESTED.** An unknown population means the zeros cannot be counted.
- **No k without established over-dispersion** — see below.

### The control caught a fabricated superspreading figure in my own tool

`nb_k` was computed whenever `variance > mean`. On the Poisson fixture — pure
chance at the platform rate — the sample variance landed a hair above the mean
and the tool produced **k = 0.87**, which in epidemiological terms reads as heavy
superspreading. As `(variance − mean)` approaches zero the expression explodes or
collapses on noise alone.

**`k` is now emitted only when the verdict is OVER-DISPERSED.** A `k` without
established over-dispersion is not a small number, it is a meaningless one — and
this platform's history says a meaningless number gets quoted.

### Backward tracing, and only because the test licensed it

Forward tracing costs O(cases × contacts) and, in an over-dispersed process,
spends almost all of it on cases that infected nobody. **Backward** tracing
starts from a known cluster. The dispersion test is what licenses it: on a
Poisson-shaped distribution there are no clusters to trace back *from*, and
doing it anyway is reading a pattern into noise.

The largest cluster found — **5 confirmed defects in one commit**, `5b98fd27209b`
(2026-09-10, *"a dropped socket, a hang and a partial response were all silent"*):

- **shared `app = sairndental`, which is 8% of the register** — informative
  precisely because it is *not* the norm
- three files common to every member, including its own mutation control
- and the members are a coherent family: source assertions matching what came
  *after* the guard, a control anchored on a line two writers share verbatim, a
  dropped socket with no toast, a hung write with no timeout

**A shared attribute is a candidate origin, never a proven one** — the register
holds no causal graph. Each is scored against its rate in the register, because
*"all of them are in stonedesk"* says nothing if most records are.

---

## What neither of these claims

- **`fused` is not a probability** and is calibrated against nothing. It is a
  defined score, nothing gates on it, and its definition is in the file.
- **The `file` dimension's over-dispersion is partly an artefact.** The tool
  counts a defect against *every* file in its commit, so file counts are
  correlated by construction and a "file cluster" can be one commit wearing four
  hats. Its index is the least trustworthy of the four.
- **Over-dispersion here is at least as much about where we LOOKED as where
  defects ARE.** The register records what has been *found*, and finding is not
  uniform: most files have never been swept, and a file nobody looked at
  contributes a zero indistinguishable from a clean one. A concentrated source is
  a prioritisation signal, not proof.
- **`session` is a proxy, not an agent** — the tool says so already, and the
  dispersion number inherits that caveat rather than escaping it.
