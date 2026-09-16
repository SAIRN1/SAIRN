# Item 64: what happens when two of our own checks disagree — decided in advance

**2026-09-15 (Hank).** This platform runs ~50 checkers over overlapping
subjects. Two of them landing on opposite answers is not hypothetical, and
until now there was no stated rule for it — which means it would have been
resolved by whoever was under the most pressure, in the direction that
unblocked them.

`tools/check_precedence.py`, report-only, registered. 48-arm probe, 0 failures.

---

## 1. The four cases

| | resolution | why |
|---|---|---|
| **FINDING vs CLEAN** | **FINDING wins.** No exceptions. | CLEAN is the *vacuous default* — it is what a checker that does nothing produces. `checkblocks.py` exited 0 for months and looked exactly like a clean codebase. A finding is a positive assertion somebody's code made; clean is the absence of one. **They are not symmetric and must never be treated as two opinions of equal standing.** |
| **FINDING vs COULD_NOT_RUN** | **FINDING wins, and the could-not-run is CARRIED.** | The finding stands on its own evidence. The fact that another check *could not look* is a second, separate thing that is still true and still needs fixing. **Absorbing it into the finding loses it.** |
| **FINDING vs FINDING, contradicting on the same fact** | **CONFLICT. Neither wins.** Escalates to a human, **blocks nothing**. | See §2. |
| **CLEAN vs COULD_NOT_RUN** | **COULD_NOT_RUN. Never CLEAN.** | The one that would otherwise be decided the other way at 2am. One check looked and saw nothing; the other **did not look**. The pair does not add up to a clean bill, and a rule that let it would make every unrunnable check free. |

Agreement is not a case: FINDING+FINDING on the same value is corroboration,
CLEAN+CLEAN is clean, CNR+CNR is could-not-run.

**A fifth, which is about the table rather than the claims:** a verdict kind the
table does not answer resolves to **CONFLICT**, not to a guess. Silence there
would mean a newly-invented verdict quietly having no precedence at all — the
same reason `api/_lib/cron-response.js` carries a `NO_PLAN` row.

---

## 2. What is deliberately *not* the tiebreak

The obvious mechanism is to rank the two checkers with
`tools/checker_confidence.py` and let the higher one win. **Rejected**, and the
reason is about what that number *measures* rather than how good it is:

    confidence = min(stability_band, evidence_band)

**Stability** is *"has this checker's verdict moved on unchanged code"*.
**Evidence** is *"has a control ever shown it can fire at all"*. **Neither is a
statement about whether it is right on this input.** A checker with a perfect
flip rate and a thorough control can still be wrong about one file —
`secrets_inventory.py` reported four OIDC variables and a correctly-guarded live
Stripe key as unguarded on its first run, and nothing about its rating predicted
that.

**Using the rating as a tiebreak would convert a real disagreement into a
confident single answer, silently, in favour of whichever checker has been
around longer.** That is strictly worse than saying "these two disagree" out
loud: it destroys the only signal that something is wrong, and it does it in the
direction that looks most authoritative.

The rating is still **printed beside** a conflict, because it helps a human
decide. It does not decide.

---

## 3. Exit 3 exists and nothing may gate on it

A CONFLICT is a **question**, not a verdict. Blocking a push on *"two of our
tools disagree"* punishes whoever happens to be pushing for a disagreement that
predates them, and the reliable consequence is an override habit — which this
repo has already recorded costing more than the gate saved.

So: report-only, registered as such, and its exit 3 is for a human and for the
sweep. **If it is ever wired into a gate, that is a change to this rule and has
to be argued here first.**

---

## 4. The live pairing — a real overlap, not one invented to give the tool a job

A precedence rule nothing consults is a document. The first consumer is a
**genuine** overlapping pair: `checker_confidence.py` and
`checker_estimate_fusion.py` both answer *"how much is this checker's verdict
worth"*, by structurally different methods — conjunction (`min`) versus a
weighted INS/GPS fusion of the same two signals.

**THE MAPPING IS TAKEN FROM EACH TOOL'S OWN DOCUMENTED EXIT SEMANTICS, NOT FROM
A THRESHOLD INVENTED HERE.** Picking a `fused >= 0.8 means HIGH` cutoff would
manufacture disagreements out of an arbitrary line — the fabricated-figure
defect this platform polices hardest. So the comparison is made only on the
three-valued kind both tools genuinely speak. A probe arm asserts the mapping
contains no numeric threshold.

### What it found

**48 checkers rated by both. Four real disagreements.**

| checker | confidence | fusion | resolved |
|---|---|---|---|
| `master_plan.py` | HIGH | UNCORRECTED | **FINDING** |
| `traceability_matrix.py` | HIGH | UNCORRECTED | **FINDING** |
| `comment_sensitivity_check.py` | LOW | CORRECTION ONLY | **FINDING** |
| `subprocess_decode_check.py` | LOW | FUSED | **FINDING** |

The first two are the interesting ones: **a HIGH confidence rating does not
outrank "its corrector failed its own check."** Under a confidence tiebreak both
would have been silently resolved the other way.

**ZERO CONFLICTs on live data so far, and that is stated rather than left to be
assumed exercised.** These two tools map into the same three-valued vocabulary
and never assert different *values*, so case 3 has not fired outside fixtures.

---

## 5. The controls

- **Every ordering, not one sample per rule.** All six permutations of
  FINDING+CLEAN+COULD_NOT_RUN must give FINDING — if any ordering differed, the
  rule would depend on which checker happened to run first.
- **NO CONFIDENCE TIEBREAK, proved structurally rather than by reading the
  file.** The same claims are arbitrated with **125 combinations** of ratings
  attached to each side, and no verdict moves. A grep for `confidence` would
  pass against a version that used it. **Plus the other direction** — changing
  the *kinds* must still move the verdict, or the arm would pass against an
  arbiter that ignores its inputs entirely.
- **Carried, not absorbed**, driven separately: a finding beating a
  could-not-run must still report the could-not-run, and so must a CONFLICT.
- **TEETH, both rules.** Breaking rule 4 (`clean + cnr -> clean`) and breaking
  rule 1 each make the tool exit **COULD NOT RUN (2)**, never CLEAN. The rule
  table is proved on every run **before any real claim is arbitrated**, so an
  arbiter that had silently stopped applying rule 4 cannot then report a
  platform clean using the exact precedence this file forbids.
- **A conflict outranks a finding in the exit code**, or a run containing both
  would read as an ordinary finding and the question would be lost.

---

## 6. Not established

- **Case 3 has never fired on live data.** It is driven on fixtures only. A
  second consumer whose checks emit *graded values* would exercise it properly;
  none is wired today.
- **The tool arbitrates claims it is given.** It does not discover
  disagreements on its own — nothing enumerates every pair of checkers with an
  overlapping subject, and this does not claim to.
- **Registered as `--self-check`, not the live pairing**, and the reason is cost:
  the live run shells out to two tools the sweep already runs, inside a budget
  already at 330s of 600s. The rule table is the part that can silently rot; the
  live pairing is a deliberate manual run.
