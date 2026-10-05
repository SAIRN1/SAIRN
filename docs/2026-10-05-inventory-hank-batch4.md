# Hank inventory — batch 4, 2026-10-05

Companions: `docs/2026-10-05-register-corrections-hank-batch4.md` (items 1, 2,
7, 8, 9 and the premise log) and
`docs/2026-10-05-app-elapsed-and-rigor-hank.md` (item 10).

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| Drift checker reads **every** citation form; named citations resolve against the file they name; coverage disclosed per run | `37a857f2` | probe **22/0** (was 17/0), criteria → `2026-10-05.3`; full register re-run |
| `push_retry` can reach its remedy with `behind == 0`, and prints the real reason | `37a857f2` | probe **12/0** (was 7/0) |
| Registry-tail finding filed with **7 arms**, inline-reporting, at the front of the probe | `37a857f2` | all 7 pass; survive a 45s timeout |
| The reachability annotation corrected from "REGISTERED AND DEAD" to "DID NOT RUN in the last measured sweep" | `37a857f2` | arm T4 pins the wording |
| `citation_line_drift_check.py` cp1252 crash | `37a857f2` | `leg_` now reports 41+7+3 = 51, was a crash reported as 0/0/0 |

**Full register, expanded checker, 18 prefixes:**

    citations 444  (bare 416, named 28)      was 285 visible
    SOUND 213   DRIFTED 177   INCONCLUSIVE 54      213+177+54 = 444

---

## 2. Four things I got wrong or nearly did, in one batch

Recorded first because they are the useful part.

**A crash read as a clean file.** The first full-register run reported
`sairnlegacy` as `SOUND=0 DRIFTED=0 INCONCLUSIVE=0` over 51 citations. It had
died mid-run on a cp1252 encode of a cited line — **fourth instance of that
class today**. My own sweep script summed whatever its regexes found and
printed zeros. It now refuses to count a run whose verdicts do not add up to
its citation count.

**My annotation overstated what one run can support.** I shipped
`reach=NEVER REACHED -- REGISTERED AND DEAD` yesterday. Two consecutive sweeps
of the same registry reached **38 then 44** — six entries flipped on timing
variance. "Dead" was never measurable from one run. Corrected to "DID NOT RUN
in the last measured sweep", with both measurements in the record.

**A control arm matched its own documentation.** Arm D3 checked
`'tail[-6:]' not in loop_src` and failed — on the comment I had just written to
explain that `tail[-6:]` was the old behaviour. PR §1.2 committed inside a
control written the same hour. It strips comments now.

**The control for "a check that never runs" was itself a check that never
ran.** I appended the 7 registry-tail arms at the END of a probe that times out
at 280s. Moving them to the front was not enough — the probe accumulates
results and prints at the end, so a timeout still lost them. Both halves fixed:
front, and inline reporting.

---

## 3. Blocked

| Blocked | Holder | Evidence |
|---|---|---|
| Items **1, 2, 8** — every register edit | **`cc`**, live, claimed `11:12:09Z` | `sairn_claim.py check` returns **BLOCKED … same declared FILES: docs/CRITICALITY-TIERS.md`. cc is working the match.cost cell from my own previous delivery, applied at `4dfc4753`. |
| Rows 82 / 845 | **`cc`** (holds the index) | **Already delivered last batch** + flagged; re-flagged this batch. Nothing further for me to produce. |
| #745 **Part B** | nobody — it does not exist in this repo | 59 rows + an "original-46" set that live only in a chat transcript. Named, not inferred. |

**24 of 24 repoints in items 7 and 8 verify at HEAD** and are paste-ready. One
claim release is all that stands between the text and the register.

---

## 4. Gaps — ranked

All internal; **none is customer-visible and no competitor is affected**, so
none is ranked on that axis and no competitor evidence is cited.

| # | Gap | Severity |
|---|---|---|
| **1** | **`sd_email_threats` risk mis-rating is still live** — `"not a high risk"` stores **High** | **HIGH** |
| **2** | 177 of 444 register citations are DRIFTED and unread | **HIGH** |
| **3** | The registry-reachability boundary is **not reproducible** (±6 entries) | **MODERATE** |
| **4** | 237 tools share the cp1252 precondition — **four live hits today** | **MODERATE** |
| **5** | `sairncash` has **0 register rows** after 49 days and is shipped | **MODERATE** |
| **6** | Index rows unchecked against the repo | **MODERATE** (carried) |
| **7** | Measured-vs-advised convention | **MODERATE** (carried) |

### 1. The one I would put ahead of every repoint — HIGH

Hover log #796 re-confirmed live that `sd_email_threats` derives risk by a
naive `lower.includes('critical')` / `('high')` / `('medium')` substring match
**with no negation handling**. An AI response containing *"not a high risk"*
stores **High**. `sd_email_threats` is an **A/A** row.

**Not mine and not verified by me** — it is `stonedesk.html` behaviour and I am
repeating the auditor's re-confirmation. But it is a live wrong-answer on a
Tier A row, and this batch spent its effort on citation accuracy for the same
register. **Flagged rather than folded in**, because fixing it is a behaviour
change needing its own claim, its own control and a read of the AI response
contract.

### 2. 177 drifted citations, and roughly half must NOT be repointed — HIGH

The expanded sweep surfaces 177 DRIFTED across 444. **That is a candidate list,
not a work list.** On the measured base rate — `grd_irr_zones` 4/4,
`sb_perf` and `sc_encoder` — a substantial fraction are deliberate render or
read citations whose repointing would make the cell's own sentence false.

**Each needs its prose read.** 24 have been read and verified this batch. The
remaining ~150 are nobody's, and the cheap mistake available here is to
mechanically apply 177 arrows.

### 3. The boundary moves ±6 between runs — MODERATE

Two consecutive full sweeps, same registry, same machine: reached 38, then 44.
`sairn_dead_button_audit.py` took 153.5s then 130.6s;
`write_without_readback_check.py` 56.1s then 40.2s. Entries deep in the tail
are reliably dead; **entries within a few slots of the cutoff are a coin toss
per push**, and no single run can tell a reader which is which.

Consequence worth stating: the `reach=` annotation I added is only as good as
the last sweep, and a session reading it near the boundary is reading a
probability. The record says so now.

### 4. The cp1252 population is live, not dormant — MODERATE

**Four hits today**: `push_retry.py` usage, my derivation script, my
commit-message filter, and `citation_line_drift_check.py` (a crash reported as
a clean file). 237 of 286 `tools/*.py` carry non-ASCII with no `reconfigure`.

**That is still a PRECONDITION count, not a crash count** — two spot-checks
have the precondition and exit 0. But the fourth hit in a day was the one that
produced a false clean verdict, which is the expensive failure mode. **The real
number needs a sweep that runs each tool and greps for `UnicodeEncodeError`** —
a tool, not a claim, and nobody has written it.

### 5. `sairncash`: shipped, 49 days, zero tiered rows — MODERATE, new

Routed in `vercel.json`, `tiered ✅` in `MASTER-PLAN`, 25 commits, 5 test
files — and **0 criticality-register rows** (`res: 0`). So nothing it stores is
tiered, which means the defect and review columns have no denominator and
`tiered ✅` is true only because there is nothing to tier. Whether that is
correct (it genuinely stores nothing) or a gap (nobody registered its
resources) is a read nobody has done.

---

## 5. What I will not claim

* **No live verification applies.** Three tools, three probes, three documents;
  nothing deployed changed.
* **`SAIRN_SEED_GATE` was not used.**
* **I read the hover log; I did not audit it.** Hash chain unverified by me.
* **I did not verify the `sd_email_threats` defect independently.**
* **I did not read the prose of ~150 drifted rows.**
* **The elapsed table is not effort and not a delivery date.** No app has a
  specification in this repo to be complete against, and no human-firm baseline
  was imported. The limits are stated in that document rather than left to a
  reader.
* **I did not fix the 29–35 dead registry entries.** Raising the budget,
  splitting the sweep, or capping the two tools that are 54% of it is a
  decision with an owner.
* **The `sdn_vendors` tier call is mine and is arguable** — rested on the
  `properties` precedent, with the counter-argument stated.
